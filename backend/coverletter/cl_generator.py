import os
import re
from datetime import date
from pathlib import Path
import yaml
from utils import generate_with_retry, load_file, load_yaml
from parsing import generate_job_yaml, get_shortened_name
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat, reduce_repetition
from evaluator import evaluate_cl, compare_cls
from provider_config import get_model_for_provider, get_fallback_models
from quality_check import validate_cover_letter, print_quality_report

def yaml_to_dict(yaml_string: str) -> dict:
    try:
        return yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML string: {e}")

def fix_hyphens(text, api_key=None, provider="gemini", fallback_models=None):
    """Intelligently remove hyphens used as sentence breaks"""
    # Check if there are any hyphens used as breaks (not compound words)
    if not re.search(r'\s+[-–—]+\s+', text):
        return text  # No hyphens to fix
    
    prompt = f"""Rewrite this text to remove ALL hyphens used as sentence breaks or connectors.

**Rules:**
- Replace hyphens with commas, periods, or semicolons depending on context
- Keep compound words like "full-stack" or "AI-powered" unchanged
- Maintain all content and meaning
- Use proper grammar and punctuation

**Examples:**
BAD: "I built a chatbot - it improved accuracy by 20%"
GOOD: "I built a chatbot that improved accuracy by 20%"
OR: "I built a chatbot. It improved accuracy by 20%"

BAD: "My skills - Python, React, and AWS - align with your needs"
GOOD: "My skills (Python, React, and AWS) align with your needs"

Text to fix:
{text}

Return only the fixed text with no explanation."""

    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    return generate_with_retry(model, prompt, max_retries=3, api_key=api_key, step_name="Hyphen Removal", provider=provider, fallback_models=fallback_models)

def build_cover_letter_prompt(template: str, user_yaml: str, job_yaml: str, previous:str = "", additional_instructions:str = "") -> str:
    additional_section = f"\n\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n" if additional_instructions else ""
    return f"""
You are writing a professional cover letter for a job application. Write naturally and confidently without sounding generic or overly formal.

--- PREVIOUS PARAGRAPHS ---
{previous}

--- COVER LETTER TEMPLATE ---
{template}

--- USER PROFILE (YAML) ---
{user_yaml}

--- JOB DESCRIPTION (YAML) ---
{job_yaml}{additional_section}

WRITING GUIDELINES:

**STEP 1: Answer These Questions (DO NOT include these questions in your output - just use them to guide your thinking):**

Before writing, identify:
1. What SPECIFIC project/achievement from the user's profile is most relevant to THIS job requirement?
2. What CONCRETE result/impact did it have? (Use actual numbers/metrics if available)
3. WHICH EXACT requirement from the job description does this address?
4. HOW did you accomplish this? (What specific tools/technologies/approach?)
5. WHY does this matter for THIS role at THIS company?

**STEP 2: Write Using These Rules:**

**Professional and Direct:**
- Write with confidence and clarity
- Be specific about your skills and achievements
- Use concrete examples when they strengthen your case
- Keep sentences varied in length and structure

**CRITICAL: Connect Skills to Job Requirements:**
- For EACH skill or achievement you mention, explicitly tie it to a requirement in the job description
- Don't just list skills - explain WHY they matter for THIS specific role
- Reference specific technologies, responsibilities, or requirements from the job posting
- Show you understand what the role needs and how your experience addresses it
- Example: Instead of "I have experience with Python", write "At [Company], I used Python to [achievement], which directly addresses your need for [specific job requirement]"

**CRITICAL: Avoid These AI/Generic Patterns:**

**BANNED Sentence Patterns (DO NOT START MORE THAN 2 SENTENCES THIS WAY):**
BANNED: "I'm [adjective]" (e.g., "I'm confident," "I'm excited," "I'm impressed")
BANNED: "I am [adjective]"
BANNED: "I have [experience]"
BANNED: "I believe"
BANNED: "I think"
BANNED: "I feel"

**Instead, use varied openings:**
OK: "My experience with X has..."
OK: "At [Company], I..."
OK: "Working on X taught me..."
OK: "This role combines..."
OK: "[Company]'s approach to X..."

**BANNED Phrases (NEVER USE THESE):**
- "to be honest," "honestly," "actually"
- "what drew me in," "I've always had a thing for"
- "I'm excited to apply," "I believe I'm a strong fit"
- "make a difference," "make a real impact"  
- "leveraging synergies," "bedrock of innovation"
- "dynamic team," "fast-paced environment"
- "my tenure at," "my aspiration is to"
- "resonate with me," "aligns with me"
- "thereby supporting," "something I anticipate"
- "realizing its ambitions," "overarching aspirations"
- Personal issues: "social anxiety," "struggles," "weaknesses"

**BANNED Vague Words/Phrases (Be specific instead):**
- "impressive outcomes" → Use actual numbers/metrics
- "swift, dependable, optimized" → Say what you actually built
- "yield valuable insights" → Explain the specific insight/impact
- "crucial aspect," "showcasing my capability"
- "align with business objectives," "equipped me to contribute"
- "innovative approach," "commitment to fostering"
- "craft AI solutions," "enabling me to"

**BANNED Punctuation:**
- NO hyphens as sentence breaks: NO em-dashes (—), en-dashes (–), or double dashes (--)
- Compound words like "full-stack" are OK, but NEVER use hyphens to connect clauses

**Do This Instead:**
- Start sentences with strong, varied openings
- Use active voice and concrete verbs
- Show impact with specific examples or results
- Keep a professional but human tone
- Vary sentence structure naturally
- Replace vague words with concrete details and numbers

**Content Rules:**
- Don't repeat points from previous paragraphs
- Only mention skills/projects that directly relate to this job
- Keep paragraphs between 100-140 words
- Focus on what you bring to the role, not generic praise of the company
- Every sentence must contain specific, concrete information

Write only the paragraph content in plain text. No headers, no markdown, no commentary.
"""

def build_header_prompt(company_desc, user_yaml, date):
    return f"""You are a professional writing assistant.
Given:

A company description:
{company_desc}

The applicant's information:
{user_yaml}

Today's date:
{date}

Generate a cover letter header formatted for a formal application.
It must include:

Applicant's name, phone number, and email

Date

Company name, address, and postal code (if available from the company description)

Format the result with appropriate line breaks and spacing so it can be directly prepended to a cover letter body.

If the company description contains clues about location or contact info, extract and format those accordingly.
If address details are missing, leave them out rather than guessing.

Output only the header in plain text, like this example:
Firstname Lastname 
user phone
user email

date 

Company name  
Company address  
company city, company province code company postal code
"""

def generate_header(user_yaml=None, job_yaml=None, api_key="", provider="gemini"):
    base_dir = Path(__file__).parent
    job_desc = job_yaml if job_yaml else load_file(str(base_dir / "inputs" / "job_desc.yaml"))
    user = user_yaml if user_yaml else load_file(str(base_dir / "inputs" / "user.yaml"))
    prompt = build_header_prompt(job_desc, user, date.today())
    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    response = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name="Header Generation", provider=provider, fallback_models=fallback_models)
    return response

def generate_cl(user_yaml, job_yaml, writing_sample=None, par_count=4, api_key="", provider="gemini", additional_instructions=""):
    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    paragraphs = []
    base_dir = Path(__file__).parent
    for i in range(par_count):
        print(f"\n  -> Generating paragraph {i+1}/{par_count}...")
        template_path = str(base_dir / "inputs" / "templates" / f"template_p{i+1}.txt")
        template = load_file(template_path)
        previous = "\n\n".join(paragraphs)
        prompt = build_cover_letter_prompt(template, user_yaml, job_yaml, previous, additional_instructions)
        response = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name=f"Paragraph {i+1}", provider=provider, fallback_models=fallback_models)
        print(f"  -> Fixing paragraph {i+1}...")
        response = generate_fixed(response, api_key=api_key, provider=provider, fallback_models=fallback_models)
        paragraphs.append(response)
        print(f"  [OK] Paragraph {i+1} complete")
    
    cover_letter = "\n\n".join(paragraphs)
    print(f"\n  -> Removing bloat from cover letter...")
    cover_letter = remove_bloat(cover_letter, api_key=api_key, provider=provider, fallback_models=fallback_models)
    
    print(f"\n  -> Reducing repetition...")
    cover_letter = reduce_repetition(cover_letter, api_key=api_key, provider=provider, fallback_models=fallback_models)
    print(f"  [OK] Repetition check complete")

    if writing_sample:
        print(f"\n  -> Personalizing with writing sample...")
        from user_tuning import humanify_prompt
        personalization_prompt = humanify_prompt(writing_sample, cover_letter)
        cover_letter = generate_with_retry(model, personalization_prompt, max_retries=5, api_key=api_key, step_name="Personalization", provider=provider, fallback_models=fallback_models)
        print(f"  [OK] Personalization complete")
    
    print(f"\n  -> Generating header...")
    header = generate_header(user_yaml, job_yaml, api_key=api_key, provider=provider)
    print(f"  [OK] Header complete")
    print(f"\n  -> Getting company name...")
    try:
        job_dict = yaml_to_dict(job_yaml)
        company_name = job_dict.get('job_profile', {}).get('company', 'Hiring Team')
        company_name = get_shortened_name(company_name, api_key=api_key, provider=provider)
        greeting = f"Dear {company_name} hiring team,"
        print(f"  [OK] Company name: {company_name}")
    except (yaml.YAMLError, AttributeError):
        greeting = "Dear Hiring Team,"
        print(f"  [OK] Using default greeting")

    user_dict = yaml_to_dict(user_yaml)

    name = user_dict.get('user_profile', {}).get('name', {})
    closing = f"Best Regards,\n{name}"
    
    # Clean up AI patterns
    cover_letter = re.sub(r'[\u201C\u201D]', '"', cover_letter)  # Replace curly quotes with straight
    cover_letter = re.sub(r'[\u2018\u2019]', "'", cover_letter)  # Replace curly apostrophes
    
    # Intelligently fix hyphens with AI (if any exist)
    if re.search(r'\s+[-–—]+\s+', cover_letter):
        print(f"\n  -> Removing hyphens...")
        cover_letter = fix_hyphens(cover_letter, api_key=api_key, provider=provider, fallback_models=fallback_models)
        print(f"  [OK] Hyphens removed")
    
    # Quality check before finalizing
    print(f"\n  -> Running quality check...")
    is_valid, issues = validate_cover_letter(cover_letter)
    if not is_valid:
        print(f"  [WARNING] Quality issues detected: {len(issues)} problems")
        for issue in issues:
            print(f"     - {issue}")
        print(f"  -> Applying additional fixes...")
        # Run repetition reducer again if validation failed
        cover_letter = reduce_repetition(cover_letter, api_key=api_key, provider=provider)
        # Check again
        is_valid_retry, issues_retry = validate_cover_letter(cover_letter)
        if is_valid_retry:
            print(f"  [OK] Quality check passed after fixes")
        else:
            print(f"  [WARNING] Still has {len(issues_retry)} issues (acceptable)")
    else:
        print(f"  [OK] Quality check passed")
    
    cover_letter = header + "\n\n\n" + greeting + "\n\n" + cover_letter + "\n\n" + closing
    return cover_letter

def get_best_cl(user_yaml, job_yaml, writing_sample=None, par_count=4, num=1, api_key="", provider="gemini", additional_instructions=""):
    cover_letter = generate_cl(user_yaml, job_yaml, writing_sample, par_count, api_key=api_key, provider=provider, additional_instructions=additional_instructions)
    if (num > 1):
        for i in range(num):
            cover_letter2 = generate_cl(user_yaml, job_yaml, writing_sample, par_count, api_key=api_key, additional_instructions=additional_instructions)
            eval1 = evaluate_cl(cover_letter, api_key=api_key)
            eval2 = evaluate_cl(cover_letter2, api_key=api_key)
            comparison = compare_cls(cover_letter, eval1, cover_letter2, eval2, api_key=api_key)
            if comparison == "1":
                cover_letter = cover_letter2

    base_dir = Path(__file__).parent
    output_path = base_dir / "outputs" / "cover_letter.txt"
    os.makedirs(output_path.parent, exist_ok=True)
    with open(str(output_path), "w", encoding="utf-8") as f:
        f.write(cover_letter)
    return cover_letter

def main():
    job_yaml = generate_job_yaml()

    api_key = os.getenv("GEMINI_API_KEY")
    base_dir = Path(__file__).parent
    user_yaml = load_file(str(base_dir / "inputs" / "user.yaml"))
    job_yaml = load_file(str(base_dir / "inputs" / "job_desc.yaml"))
    print(get_best_cl(user_yaml, job_yaml, api_key=api_key))

if __name__ == "__main__":
    main()
    