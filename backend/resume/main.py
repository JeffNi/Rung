"""Main orchestrator for resume generation pipeline."""
import os
import sys
import json
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import ResumePipelineResult, KeywordExtractionResult, ResumeStrategy, ResumeDraft, ResumeReview
from extractor import extract_keywords_with_rag, export_to_yaml
from strategizer import create_resume_strategy
from drafter import draft_resume
from reviewer import review_resume
from editor import edit_resume


def generate_resume(
    job_description: str,
    user_profile: dict,
    latex_template: str,
    api_key: str,
    provider: str = "gemini",
    output_dir: str = "./output",
    max_iterations: int = 3
) -> ResumePipelineResult:
    """
    Full pipeline: Extract → Strategize → Draft → Review → (Edit → Review)* → Final
    """
    print("\n" + "="*60)
    print("RESUME GENERATION PIPELINE STARTED")
    print("="*60 + "\n")
    
    result = ResumePipelineResult(
        extraction=KeywordExtractionResult(),
        strategy=ResumeStrategy(),
        draft=ResumeDraft(),
        review=ResumeReview(passed=False),
        iterations=0
    )
    
    try:
        # Step 1: RAG Extract
        print("\n[Pipeline] Step 1/5: RAG extraction - matching keywords to experiences...")
        extraction = extract_keywords_with_rag(
            job_description, user_profile, api_key, provider
        )
        result.extraction = extraction
        
        # Report dropped keywords
        if extraction.dropped_keywords:
            dropped_list = [d['keyword'] for d in extraction.dropped_keywords]
            print(f"\n[INFO] Dropped {len(dropped_list)} keywords with no relevant experience: {', '.join(dropped_list[:5])}")
        
        # Step 2: Strategize
        print("\n[Pipeline] Step 2/5: Creating resume strategy...")
        strategy = create_resume_strategy(
            extraction, user_profile, api_key, provider
        )
        result.strategy = strategy
        
        # Step 3: Draft
        print("\n[Pipeline] Step 3/5: Drafting resume...")
        draft = draft_resume(
            strategy, extraction, user_profile, latex_template, output_dir
        )
        result.draft = draft
        
        if not draft.compilation_success:
            print("\n[ERROR] Resume compilation failed. Check LaTeX template.")
            return result
        
        # Step 4: Review (initial)
        print("\n[Pipeline] Step 4/5: Reviewing resume...")
        review = review_resume(
            draft, strategy, extraction, user_profile, api_key, provider
        )
        result.review = review
        
        # Step 5: Edit & Re-review (iterative)
        if not review.passed and max_iterations > 0:
            print(f"\n[Pipeline] Step 5/5: Editing issues (max {max_iterations} iterations)...")
            
            for iteration in range(max_iterations):
                print(f"\n[Pipeline] Edit iteration {iteration + 1}...")
                
                # Edit the draft
                edited_draft = edit_resume(draft, review, strategy, max_iterations=1)
                result.draft = edited_draft
                result.iterations = iteration + 1
                
                # Re-review
                review = review_resume(
                    edited_draft, strategy, extraction, user_profile, api_key, provider
                )
                result.review = review
                
                if review.passed:
                    print(f"\n[Pipeline] All checks passed after {iteration + 1} edit(s)!")
                    break
                elif iteration < max_iterations - 1:
                    print(f"[Pipeline] Issues remain, attempting another edit...")
            else:
                print(f"\n[WARNING] Could not resolve all issues after {max_iterations} iterations.")
                print("          Manual review recommended.")
        
        # Set final output
        if draft.compilation_success and review.passed:
            result.final_pdf_path = draft.pdf_path
            print("\n" + "="*60)
            print("RESUME GENERATION COMPLETE!")
            print(f"PDF: {result.final_pdf_path}")
            print("="*60 + "\n")
        else:
            print("\n" + "="*60)
            print("RESUME GENERATION INCOMPLETE")
            print(f"Issues: {len([i for i in review.issues if i.severity == 'error'])} errors")
            print("="*60 + "\n")
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return result


def generate_resume_json(
    job_description: str,
    user_profile: dict,
    latex_template: str,
    api_key: str,
    provider: str = "gemini",
    output_dir: str = "./output"
) -> Dict[str, Any]:
    """
    Generate resume and return structured JSON response.
    Useful for API endpoints.
    """
    result = generate_resume(
        job_description=job_description,
        user_profile=user_profile,
        latex_template=latex_template,
        api_key=api_key,
        provider=provider,
        output_dir=output_dir
    )
    
    # Convert to serializable dict
    return {
        "success": result.review.passed and result.draft.compilation_success,
        "pdf_path": result.final_pdf_path,
        "metrics": result.review.metrics if result.review else {},
        "issues": [
            {
                "check": i.check_name,
                "severity": i.severity,
                "message": i.message,
                "suggestion": i.suggestion
            }
            for i in (result.review.issues if result.review else [])
        ],
        "keyword_coverage": result.review.keyword_coverage if result.review else 0,
        "quantification_pct": result.review.quantification_percentage if result.review else 0,
        "iterations": result.iterations,
        "gaps": {
            "dropped_keywords": [
                d['keyword'] for d in result.extraction.dropped_keywords
            ] if result.extraction else [],
            "keyword_coverage": f"{len(result.extraction.keyword_mappings)}/{len(result.extraction.keyword_mappings) + len(result.extraction.dropped_keywords)}"
            if result.extraction else "0/0"
        },
        "extraction_yaml": export_to_yaml(result.extraction) if result.extraction else ""
    }


if __name__ == "__main__":
    # Test the pipeline
    test_profile = {
        "name": "Test User",
        "title": "Software Engineer",
        "contact": {"email": "test@example.com", "phone": "555-1234"},
        "skills": ["Python", "React", "AWS", "Docker", "Kubernetes"],
        "experience": {
            "Google": [
                "Built Python microservices serving 1M users",
                "Led migration from monolith to microservices"
            ],
            "Startup": [
                "Created React frontend with TypeScript",
                "Implemented CI/CD pipeline with GitHub Actions"
            ]
        },
        "projects": {
            "ML Platform": [
                "Built ML training pipeline with TensorFlow",
                "Deployed to AWS ECS with auto-scaling"
            ]
        },
        "courses": ["Machine Learning", "Distributed Systems"]
    }
    
    test_jd = """
    Senior Software Engineer - Backend
    
    Requirements:
    - 5+ years experience with Python
    - Experience with Go or Rust
    - Kubernetes and Docker expertise
    - AWS or GCP cloud experience
    - Experience with microservices architecture
    """
    
    # Simple template for testing
    test_template = r"""
\documentclass[11pt]{article}
\begin{document}
\section*{ {{NAME}} }
{{TITLE}} | {{EMAIL}} | {{PHONE}}

\section{Summary}
{{SUMMARY}}

\section{Skills}
{{SKILLS}}

\section{Experience}
{{EXPERIENCE}}

{{PROJECTS}}

{{EDUCATION}}
\end{document}
"""
    
    # Get API key from env
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if api_key:
        result = generate_resume(
            job_description=test_jd,
            user_profile=test_profile,
            latex_template=test_template,
            api_key=api_key,
            provider="gemini",
            output_dir="./test_output"
        )
        print("\nResult:", result)
    else:
        print("Set GEMINI_API_KEY environment variable to test")
