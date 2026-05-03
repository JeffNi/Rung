import os
import sys
import tempfile
import re
from pathlib import Path
from datetime import date

# Ensure all backend submodules are importable
_backend_dir = Path(__file__).parent.parent
_coverletter_dir = str(_backend_dir / "coverletter")
_resume_dir = str(_backend_dir / "resume")
for _p in [str(_backend_dir), _coverletter_dir, _resume_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import yaml
from utils import generate_with_retry, load_file, load_yaml
from coverletter.utils import get_token_usage, reset_token_usage
from parsing import generate_job_yaml
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat
from cl_generator import get_best_cl, build_header_prompt
from extractor import extract_keywords_with_rag
from strategizer import create_resume_strategy
from schemas import ResumeStrategy

app = FastAPI(title="Cover Letter Generator API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://skyward-ai.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],  # React and Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ContactInfo(BaseModel):
    email: str
    phone: str

class Experience(BaseModel):
    title: str
    company: str
    achievements: List[str]

class Project(BaseModel):
    name: str
    description: List[str]

class UserProfile(BaseModel):
    name: str
    title: str
    contact: ContactInfo
    skills: List[str]
    courses: List[str]
    experience: List[Experience]
    projects: List[Project]
    goals: List[str]
    values: List[str]
    interests: List[str]

class JobDescription(BaseModel):
    title: str
    company: str
    location: str
    summary: str
    responsibilities: str
    required_skills: List[str]
    nice_to_have_skills: Optional[List[str]] = None
    company_culture: Optional[str] = None

class CoverLetterRequest(BaseModel):
    user_profile: UserProfile
    job_description: str  # Now a string (pasted job description)
    writing_sample: str
    paragraph_count: int = 3
    provider: str = "gemini"  # AI provider: "gemini" or "groq"
    api_key: str = ""  # API key for the provider
    additional_instructions: str = ""  # Optional additional instructions for the AI

class CoverLetterResponse(BaseModel):
    cover_letter: str
    message: str

def create_temp_user_yaml(user_profile: dict) -> str:
    """Convert user profile dict to YAML format and save to temp file"""
    # Normalize experience
    experience = {}
    for exp in user_profile.get("experience", []):
        title = exp.get("title", "")
        company = exp.get("company", "")
        key = f"{title} at {company}".strip()
        achievements = exp.get("achievements", [])
        experience[key] = achievements
    # Normalize projects
    projects = {}
    for proj in user_profile.get("projects", []):
        name = proj.get("name", "")
        description = proj.get("description", [])
        projects[name] = description

    user_data = {
        "user_profile": {
            "name": user_profile.get("name", ""),
            "title": user_profile.get("title", ""),
            "contact": {
                "email": user_profile.get("contact", {}).get("email", ""),
                "phone": user_profile.get("contact", {}).get("phone", "")
            },
            "skills": user_profile.get("skills", []),
            "courses": user_profile.get("courses", []),
            "experience": experience,
            "projects": projects,
            "goals": user_profile.get("goals", []),
            "values": user_profile.get("values", []),
            "interests": user_profile.get("interests", [])
        }
    }
    return yaml.dump(user_data, sort_keys=False)

def create_temp_job_yaml(job_description: dict) -> str:
    """Convert job description dict to YAML format and save to temp file"""
    job_data = {
        "job_profile": {
            "title": job_description.get("title", ""),
            "company": job_description.get("company", ""),
            "location": job_description.get("location", ""),
            "address": job_description.get("address", ""),
            "postal": job_description.get("postal", ""),
            "provinceCode": job_description.get("provinceCode", ""),
            "description": job_description.get("summary", ""),
            "requirements": job_description.get("required_skills", []),
            "responsibilities": job_description.get("responsibilities", []),
            "values": job_description.get("values", []),
            "keywords": job_description.get("keywords", []),
            "hiring_manager": job_description.get("hiring_manager", ""),
            "hiring_manager_title": job_description.get("hiring_manager_title", "")
        }
    }
    return yaml.dump(job_data, sort_keys=False)

@app.post("/generate-cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(request: Request):
    try:
        print("\n" + "="*60)
        print("COVER LETTER GENERATION STARTED")
        print("="*60)
        
        print("[Step 1/7] Parsing request data...")
        data = await request.json()
        user_profile = data.get('user_profile')
        job_description = data.get('job_description')
        writing_sample = data.get('writing_sample', '')
        paragraph_count = data.get('paragraph_count', 3)
        api_key = data.get('api_key', '')
        provider = data.get('provider', 'gemini')  # Default to Gemini
        additional_instructions = data.get('additional_instructions', '')
        
        print(f"[PROVIDER] Using {provider.upper()} for generation")
        
        # Use server-side API key if client doesn't provide one
        if not api_key:
            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY", "")
            else:
                api_key = os.getenv("GEMINI_API_KEY", "")
            
            if not api_key:
                print("ERROR: No API key provided and no server key configured!")
                raise HTTPException(status_code=400, detail="API key is required")
        
        print(f"[Step 2/7] Creating user profile YAML...")
        user_yaml = create_temp_user_yaml(user_profile)
        print("[OK] User profile created")
        
        print(f"[Step 3/7] Parsing job description with AI...")
        job_yaml = generate_job_yaml(job_description, api_key, provider=provider)
        print("[OK] Job description parsed")
        
        print(f"[Step 4/7] Generating cover letter ({paragraph_count} paragraphs + header)...")
        if additional_instructions:
            print(f"  [INFO] Using additional instructions: {additional_instructions[:100]}...")
        cl = get_best_cl(user_yaml, job_yaml, writing_sample, paragraph_count, api_key=api_key, provider=provider, additional_instructions=additional_instructions)
        
        print("\n" + "="*60)
        print("COVER LETTER GENERATION COMPLETE!")
        print("="*60 + "\n")

        return CoverLetterResponse(
            cover_letter=cl,
            message="Cover letter generated successfully!"
        )
    except Exception as e:
        print(f"\n[ERROR] GENERATION FAILED: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error generating cover letter: {str(e)}")

@app.post("/extract-keywords")
async def extract_keywords(request: Request):
    """Extract ATS keywords from a job description and map them to the user's profile."""
    try:
        data = await request.json()
        job_description = data.get('job_description', '')
        user_profile = data.get('user_profile', {})
        api_key = data.get('api_key', '')
        provider = data.get('provider', 'gemini')

        if not job_description.strip():
            raise HTTPException(status_code=400, detail="Job description is required")

        if not api_key:
            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY", "")
            else:
                api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise HTTPException(status_code=400, detail="API key is required")

        import time
        reset_token_usage()
        start = time.time()

        result = extract_keywords_with_rag(job_description, user_profile, api_key, provider)

        elapsed = round(time.time() - start, 1)
        usage = get_token_usage()
        print(f"[EXTRACT] Done in {elapsed}s | {usage['calls']} LLM calls | {usage['prompt_tokens']} prompt tokens | {usage['completion_tokens']} completion tokens | {usage['total_tokens']} total tokens")

        return {
            "keyword_to_experiences": result.keyword_to_experiences,
            "easy_no_match": result.easy_no_match,
            "drop": result.drop,
            "all_keywords_to_include": result.all_keywords_to_include,
            "must_have": result.must_have,
            "nice_to_have": result.nice_to_have,
            "token_usage": usage,
            "elapsed_seconds": elapsed
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Keyword extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/generate-strategy")
async def generate_strategy(request: Request):
    """Generate resume strategy from job description and user profile."""
    body = await request.json()
    job_description = body.get("job_description", "")
    user_profile = body.get("user_profile", {})
    api_key = body.get("api_key", "")
    provider = body.get("provider", "groq")
    job_id = body.get("job_id", "")
    
    if not job_description or not user_profile:
        raise HTTPException(status_code=400, detail="Missing job_description or user_profile")
    
    # Get API key from env if not provided
    if not api_key:
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required")
    
    try:
        import time
        reset_token_usage()
        start = time.time()
        
        # Step 1: Extract keywords
        print("[API] Step 1: Extracting keywords...")
        extraction = extract_keywords_with_rag(job_description, user_profile, api_key, provider)
        
        # Step 2: Create strategy
        print("[API] Step 2: Creating resume strategy...")
        strategy = create_resume_strategy(
            extraction=extraction,
            user_profile=user_profile,
            job_description=job_description,
            api_key=api_key,
            provider=provider,
            job_id=job_id
        )
        
        elapsed = round(time.time() - start, 1)
        usage = get_token_usage()
        print(f"[API] Strategy done in {elapsed}s | {usage['calls']} LLM calls | {usage['total_tokens']} tokens")
        
        # Convert strategy to dict for JSON response
        return {
            "experiences": [
                {
                    "title": e.title,
                    "should_include": e.should_include,
                    "keywords_covered": e.keywords_covered,
                    "dotjots": e.dotjots
                }
                for e in strategy.selected_experiences
            ],
            "skills_strategy": {
                "front_load": strategy.skills_strategy.front_load if strategy.skills_strategy else [],
                "add": strategy.skills_strategy.add if strategy.skills_strategy else [],
                "keep": strategy.skills_strategy.keep if strategy.skills_strategy else [],
                "deprioritize": strategy.skills_strategy.deprioritize if strategy.skills_strategy else []
            },
            "title_suggestions": [
                {
                    "original": t.original,
                    "suggested": t.suggested,
                    "reason": t.reason
                }
                for t in strategy.title_suggestions
            ],
            "keywords": {
                "must_have": extraction.must_have,
                "nice_to_have": extraction.nice_to_have,
                "matched": list(extraction.keyword_to_experiences.keys()),
                "easy_no_match": extraction.easy_no_match,
                "drop": extraction.drop
            },
            "token_usage": usage,
            "elapsed_seconds": elapsed
        }
    except Exception as e:
        print(f"[ERROR] Strategy generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Strategy generation failed: {str(e)}")


@app.post("/compile-latex")
async def compile_latex(request: Request):
    """Compile LaTeX locally using pdflatex and return the PDF."""
    import subprocess
    import tempfile
    import shutil
    from fastapi.responses import Response
    body = await request.json()
    tex_content = body.get("text", "")
    if not tex_content:
        raise HTTPException(status_code=400, detail="Missing tex content")
    tmpdir = tempfile.mkdtemp()
    try:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "--enable-installer", "-output-directory", tmpdir, tex_path],
            capture_output=True, text=True, timeout=60
        )
        print(f"[LATEX] pdflatex exit code: {result.returncode}")
        if result.returncode != 0 or not os.path.exists(pdf_path):
            log = (result.stdout + result.stderr)[-1000:]
            print(f"[LATEX] Error log: {log}")
            raise HTTPException(status_code=422, detail=f"LaTeX compile error:\n{log}")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(content=pdf_bytes, media_type="application/pdf")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Compilation timed out")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LATEX] Exception: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Cover Letter Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)