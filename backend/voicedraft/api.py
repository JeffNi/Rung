from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import yaml
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_file, load_yaml
from company_info import generate_job_yaml
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat
from cl_generator import get_best_cl, build_header_prompt
from datetime import date
import re

# Load environment variables
dotenv_path = Path("../.env")
load_dotenv(dotenv_path=dotenv_path)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Cover Letter Generator API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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

def create_temp_user_yaml(user_profile: UserProfile) -> str:
    """Convert user profile to YAML format and save to temp file"""
    user_data = {
        "user_profile": {
            "name": user_profile.name,
            "title": user_profile.title,
            "contact": {
                "email": user_profile.contact.email,
                "phone": user_profile.contact.phone
            },
            "skills": user_profile.skills,
            "courses": user_profile.courses,
            "experience": {
                f"{exp.title} at {exp.company}": exp.achievements
                for exp in user_profile.experience
            },
            "projects": {
                project.name: project.description
                for project in user_profile.projects
            },
            "goals": user_profile.goals,
            "values": user_profile.values,
            "interests": user_profile.interests
        }
    }
    
    return yaml.dump(user_data, sort_keys=False)

def create_temp_job_yaml(job_description: JobDescription) -> str:
    """Convert job description to YAML format and save to temp file"""
    job_data = {
        "job_profile": {
            "title": job_description.title,
            "company": job_description.company,
            "location": job_description.location,
            "address": getattr(job_description, "address", ""),
            "postal": getattr(job_description, "postal", ""),
            "provinceCode": getattr(job_description, "provinceCode", ""),
            "description": getattr(job_description, "summary", ""),
            "requirements": getattr(job_description, "required_skills", []),
            "responsibilities": getattr(job_description, "responsibilities", []),
            "values": getattr(job_description, "values", []),
            "keywords": getattr(job_description, "keywords", []),
            "hiring_manager": getattr(job_description, "hiring_manager", ""),
            "hiring_manager_title": getattr(job_description, "hiring_manager_title", "")
        }
    }
    return yaml.dump(job_data, sort_keys=False)

@app.post("/generate-cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(request: CoverLetterRequest):
    try:
        # Convert request data to YAML format
        user_yaml = create_temp_user_yaml(request.user_profile)

        # Generate job YAML using the AI model
        job_yaml = generate_job_yaml(request.job_description)

        writing_sample = request.writing_sample
        # Use writing_sample as needed in your pipeline

        # Generate the complete cover letter using get_best_cl
        final_cover_letter = get_best_cl(user_yaml, job_yaml, writing_sample, request.paragraph_count)

        return CoverLetterResponse(
            cover_letter=final_cover_letter,
            message="Cover letter generated successfully!"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cover letter: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Cover Letter Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 