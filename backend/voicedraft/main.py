from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import yaml
from pathlib import Path
from utils import generate_with_retry, load_file, load_yaml
from company_info import generate_job_yaml
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat
from cl_generator import get_best_cl, build_header_prompt
from datetime import date
import re

app = FastAPI(title="Cover Letter Generator API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://skyward-ai.vercel.app/",
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
    paragraph_count: int = 4

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
        data = await request.json()
        user_profile = data.get('user_profile')
        job_description = data.get('job_description')
        writing_sample = data.get('writing_sample', '')
        paragraph_count = data.get('paragraph_count', 4)
        api_key = data.get('api_key', '')

        user_yaml = create_temp_user_yaml(user_profile)
        job_yaml = generate_job_yaml(job_description)
        
        cl = get_best_cl(user_yaml, job_yaml, writing_sample, paragraph_count, api_key=api_key)

        return CoverLetterResponse(
            cover_letter=cl,
            message="Cover letter generated successfully!"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cover letter: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Cover Letter Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("your_module:app", host="0.0.0.0", port=port)