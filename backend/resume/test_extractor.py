"""Quick test script for the keyword extractor."""
import os
import sys
import json
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from extractor import (
    extract_keywords_from_jd,
    categorize_keywords,
    extract_keywords_with_rag,
    find_related_experiences,
    is_easy_keyword,
    is_hard_keyword,
    export_to_yaml
)

# ── Sample job description (edit or replace with your own) ──────────────
SAMPLE_JD = """
Job Description
Amazing Career Moments Happen Here 

 

Transforming the insurance industry is ambitious, we know. That’s why at Applied, we’re building a team that shows up every day ready to learn, willing to try new things, and driven to deliver innovative software and services that make us indispensable to our customers – all within a culture built on values that make us indispensable to each other too. With 40+ years of experience in the Insurtech game, we’re not just redefining what’s achievable, we’re creating a place where amazing career moments are made possible.  

  

Position Overview  

 

We're seeking an Associate AI Engineer / AI Engineer to build and enhance data solutions and AI initiatives for the business of insurance.

In this role, you will work closely with the Principal Data Architect, Data Scientists, and Software Engineers to build, model, and maintain data solutions as we optimize data architecture and accessibility of large-scale datasets for our global teams. 

 

What You’ll Do

Partner with Product, Engineering, and Data Science leaders to design and deliver AI-powered user experiences in our dashboard products
Build and integrate conversational AI solutions (e.g., Vertex AI, Generative AI APIs) into Applied’s products
Use AI tools responsibly (e.g., code assistance, test generation, analysis, and documentation) to accelerate velocity and improve quality while validation outputs and ownership of contributions to the customer experience
Work with Google Cloud APIs, Vertex AI, and related services to enable intelligent workflows
Prototype and implement AI-driven insights and recommendations directly in dashboards for client use
Collaborate with UX and product teams to design seamless user experiences powered by AI
Support development of generative AI prototypes, prompt design, and fine-tuned models
Stay current on advancements in Google Cloud, conversational AI, and applied AI engineering
Assist senior engineers and scientists on larger initiatives to scale AI capabilities across the platform
 

We’re Excited to Learn More About You  

 

Hybrid: Ability to work from an Applied Systems office on an ad hoc basis, with remote work days for deep work.
 

Must have:
Strong programming skills in Python and SQL.
Exposure to data science concepts (predictive modeling, ML/AI basics, or coursework/projects).
Interest in applied AI, conversational AI, and building user-facing insights.
Familiarity with cloud platforms (Google Cloud preferred) or willingness to learn quickly.
Understanding of APIs and how applications connect to each other.
Problem-solving skills with curiosity and eagerness to experiment and explore new technologies.
 

Nice to have (but not required):
Experience with Google Cloud tools such as Vertex AI, Dialogflow, or BigQuery.
Familiarity with dashboards/visualization tools (Looker, Tableau, or Power BI).
Version control knowledge (Git).
 

Education: Bachelor's or Master's degree in a related field (e.g., Computer Science, Data Science, Engineering, or related field)
We proudly support and encourage people with military experience, as well as military spouses, to apply. 
 

When You Join Team Applied, You Can Expect:  

 

A culture that values who you are and recognizes that you aren’t just an employee; you are a teammate, and you matter. We thrive on the benefits of our different experiences and celebrate the uniqueness our teammates bring to work with them every day.  

 

We flex our time together, collaborating remotely and in-person to empower our teams to work in the ways that work best for them.  

 

A comprehensive benefits and compensation package that centers our teammates and helps them to bring their best to work every day:  

Medical, Dental, and Vision Coverage  
Holiday and Vacation Time  
Health & Wellness Days  
A Bonus Day for Your Birthday  
 
Learn more about the people behind our products at https://www1.appliedsystems.com/en-us/about-us/jobs/  
"""

# ── Sample user profile (edit to match yours) ──────────────────────────
SAMPLE_PROFILE = {
    "skills": ["Python", "JavaScript", "React", "Node.js", "PostgreSQL", "Git", "Docker"],
    "experience": {
        "Software Developer at TechCo": {
            "bullets": [
                "Built REST APIs with Flask serving 10k daily users",
                "Developed React dashboards for internal analytics",
                "Managed PostgreSQL databases and wrote complex queries"
            ],
            "ai_bullets": {},
            "context": "Mid-size startup, team of 8 engineers"
        },
        "Junior Developer at StartupXYZ": {
            "bullets": [
                "Created frontend components with React and TypeScript",
                "Wrote unit tests with Jest achieving 85% coverage",
                "Deployed applications using Docker containers"
            ],
            "ai_bullets": {},
            "context": "Early-stage startup, 3 person dev team"
        }
    },
    "projects": {
        "Personal Portfolio Site": {
            "bullets": [
                "Built with Next.js and deployed on Vercel",
                "Integrated GitHub API to display recent projects"
            ],
            "ai_bullets": {},
            "context": ""
        }
    }
}


def test_keyword_extraction_only():
    """Test just the keyword extraction from JD (1 LLM call)."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
    provider = "groq" if os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY") else "gemini"
    
    if not api_key:
        print("ERROR: No API key found. Set GEMINI_API_KEY or GROQ_API_KEY in .env")
        return
    
    print(f"Using provider: {provider}")
    print(f"API key: {api_key[:8]}...{api_key[-4:]}")
    print("=" * 60)
    
    print("\n[TEST] Extracting keywords from JD...")
    keywords = extract_keywords_from_jd(SAMPLE_JD, api_key, provider)
    
    print(f"\n{'='*60}")
    print(f"EXTRACTED KEYWORDS ({len(keywords)}):")
    print(f"{'='*60}")
    for kw in sorted(keywords):
        easy = is_easy_keyword(kw)
        hard = is_hard_keyword(kw)
        tag = " [EASY]" if easy else (" [HARD]" if hard else " [UNKNOWN]")
        print(f"  - {kw}{tag}")


def test_keyword_matching():
    """Test keyword extraction + matching against profile (no LLM fallback)."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
    provider = "groq" if os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY") else "gemini"
    
    if not api_key:
        print("ERROR: No API key found. Set GEMINI_API_KEY or GROQ_API_KEY in .env")
        return
    
    print(f"Using provider: {provider}")
    print("=" * 60)
    
    print("\n[TEST] Extracting keywords...")
    keywords = extract_keywords_from_jd(SAMPLE_JD, api_key, provider)
    
    print(f"\n[TEST] Matching {len(keywords)} keywords against profile (fast path only)...")
    # Pass api_key=None to skip LLM fallback for faster testing
    result = categorize_keywords(keywords, SAMPLE_PROFILE, api_key=None)
    
    print(f"\n{'='*60}")
    print("KEYWORD → EXPERIENCE MAPPINGS:")
    print(f"{'='*60}")
    for kw, exps in sorted(result["keyword_to_experiences"].items()):
        print(f"  {kw} → {', '.join(exps)}")
    
    print(f"\n{'='*60}")
    print(f"EASY (no match, can add to skills): {result['easy_no_match']}")
    print(f"DROP (hard, no match): {result['drop']}")


def test_full_rag():
    """Test full RAG extraction (keywords + matching + LLM fallback). Uses 2+ LLM calls."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
    provider = "groq" if os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY") else "gemini"
    
    if not api_key:
        print("ERROR: No API key found. Set GEMINI_API_KEY or GROQ_API_KEY in .env")
        return
    
    print(f"Using provider: {provider}")
    print("=" * 60)
    
    print("\n[TEST] Running full RAG extraction...")
    result = extract_keywords_with_rag(SAMPLE_JD, SAMPLE_PROFILE, api_key, provider)
    
    print(f"\n{'='*60}")
    print("FULL RAG RESULTS:")
    print(f"{'='*60}")
    
    print(f"\nMAPPED ({len(result.keyword_to_experiences)}):")
    for kw, exps in sorted(result.keyword_to_experiences.items()):
        print(f"  {kw} → {', '.join(exps)}")
    
    print(f"\nEASY NO MATCH ({len(result.easy_no_match)}): {result.easy_no_match}")
    print(f"DROP ({len(result.drop)}): {result.drop}")
    print(f"\nALL TO INCLUDE ({len(result.all_keywords_to_include)}): {sorted(result.all_keywords_to_include)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test the keyword extractor")
    parser.add_argument("--mode", choices=["keywords", "match", "full"], default="keywords",
                       help="keywords=extract only, match=extract+fast match, full=extract+match+LLM fallback")
    parser.add_argument("--jd", type=str, help="Path to a .txt file with the job description")
    parser.add_argument("--provider", type=str, help="Override provider (gemini or groq)")
    args = parser.parse_args()
    
    # Load custom JD if provided
    if args.jd:
        with open(args.jd, 'r', encoding='utf-8') as f:
            SAMPLE_JD = f.read()
        print(f"Loaded JD from {args.jd} ({len(SAMPLE_JD)} chars)")
    
    if args.provider:
        os.environ["_OVERRIDE_PROVIDER"] = args.provider
    
    if args.mode == "keywords":
        test_keyword_extraction_only()
    elif args.mode == "match":
        test_keyword_matching()
    elif args.mode == "full":
        test_full_rag()
