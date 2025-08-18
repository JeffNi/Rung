import os
import re
from datetime import date
from humanizer import clean_text
from pathlib import Path
import yaml
from utils import generate_with_retry, load_file, load_yaml
from company_info import generate_job_yaml, get_shortened_name
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat
from evaluator import evaluate_cl, compare_cls

def yaml_to_dict(yaml_string: str) -> dict:
    try:
        return yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML string: {e}")

def build_cover_letter_prompt(template: str, user_yaml: str, job_yaml: str, previous:str = "") -> str:
    return f"""
You are a thoughtful and articulate university student known for writing standout cover letters. You write in a way that feels honest, grounded, and personal — not like an AI or someone trying too hard to sound “professional.” Your goal is to write a paragraph for a standout cover letter given the previous paragraphs, a paragraph template, your user profile and the job description.

--- PREVIOUS PARAGRAPHS ---
{previous}

--- COVER LETTER TEMPLATE ---
{template}

--- USER PROFILE (YAML) ---
{user_yaml}

--- JOB DESCRIPTION (YAML) ---
{job_yaml}

INSTRUCTIONS:

Be natural and real. Write like someone who knows how to express sincere interest without sounding generic, robotic, or exaggerated. Aim for clarity, personality, and quiet confidence.

Pay attention to previous paragraphs to avoid unnecessarily repeating talking points.

Avoid stuffing key words, only use talking points that sound natural and make you more appealing.

Avoid repeating talking points from previous paragraphs

Avoid starting sentences with the same or, or overusing the same word. Use synonyms if possible

Avoid AI-sounding language. Never use phrases like “the bedrock of innovation,” “leveraging synergies,” “my passion for your esteemed company,” or “I am writing to express my interest.” Those are clichés. So are “dynamic team,” “fast-paced environment,” and “results-driven mindset.”

Avoid over-polish. You’re not writing for a corporate memo — you're a student trying to connect with another human. Slight imperfections are welcome. Let the letter breathe.

Use concrete examples *only* when they clearly relate to what this job needs. Don’t stuff in every skill or project — pick the one or two that make the strongest case.

Do not include references to well-known individuals unless directly relevant to the candidate’s experience or motivation.

Avoid generic phrases like “I want to discuss this more” or “Thank you for your time” that do not add value.

Be specific, not buzzwordy. Use concrete examples from the user’s experience that align with the job. It’s okay to be brief and to the point. Don’t stuff in every technical term — just what matters.

Let personality show. A moment of humor, curiosity, or honesty makes a letter memorable. The tone should be smart, reflective, and genuine — like someone who really thought about this opportunity and what they bring to it.

Keep paragraphs between 100 and 140 words.

Write a short, varied paragraph. No headers, markdown, or commentary — just the final plain text letter.
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

def generate_header(user_yaml=None, job_yaml=None, api_key=""):
    base_dir = Path(__file__).parent
    job_desc = job_yaml if job_yaml else load_file(str(base_dir / "inputs" / "job_desc.yaml"))
    user = user_yaml if user_yaml else load_file(str(base_dir / "inputs" / "user.yaml"))
    prompt = build_header_prompt(job_desc, user, date.today())
    model = "gemini-2.0-flash"
    response = generate_with_retry(model, prompt, max_retries=1, api_key=api_key)
    return response

def generate_cl(user_yaml, job_yaml, writing_sample=None, par_count=4, api_key=""):
    model = "gemini-2.5-flash-preview-05-20"
    paragraphs = []
    base_dir = Path(__file__).parent
    for i in range(par_count):
        print(i)
        template_path = str(base_dir / "inputs" / "templates" / f"template_p{i+1}.txt")
        print("s")
        template = load_file(template_path)
        previous = "\n\n".join(paragraphs)
        print("w")
        prompt = build_cover_letter_prompt(template, user_yaml, job_yaml, previous)
        response = generate_with_retry(model, prompt, max_retries=2, api_key=api_key)
        response = generate_fixed(response)
        paragraphs.append(response)
    cover_letter = "\n\n".join(paragraphs)
    cover_letter = remove_bloat(cover_letter)

    if writing_sample:
        from user_tuning import humanify_prompt
        personalization_prompt = humanify_prompt(writing_sample, cover_letter)
        cover_letter = generate_with_retry(model, personalization_prompt, max_retries=2, api_key=api_key)
    
    header = generate_header(user_yaml, job_yaml, api_key=api_key)
    print("FSDFSD")
    try:
        job_dict = yaml_to_dict(job_yaml)
        company_name = job_dict.get('job_profile', {}).get('company', 'Hiring Team')
        company_name = get_shortened_name(company_name)
        greeting = f"Dear {company_name} hiring team,"
    except (yaml.YAMLError, AttributeError):
        greeting = "Dear Hiring Team,"

    user_dict = yaml_to_dict(user_yaml)

    name = user_dict.get('user_profile', {}).get('name', {})
    closing = f"Best Regards,\n{name}"
    
    cover_letter = re.sub(r'—', ',', cover_letter)
    cover_letter = header + "\n\n\n" + greeting + "\n\n" + cover_letter + "\n\n" + closing
    return cover_letter

def get_best_cl(user_yaml, job_yaml, writing_sample=None, par_count=4, num=1, api_key=""):
    cover_letter = generate_cl(user_yaml, job_yaml, writing_sample, par_count, api_key=api_key)
    if (num > 1):
        for i in range(num):
            cover_letter2 = generate_cl(user_yaml, job_yaml, writing_sample, par_count, api_key=api_key)
            eval1 = evaluate_cl(cover_letter)
            eval2 = evaluate_cl(cover_letter2)
            comparison = compare_cls(cover_letter, eval1, cover_letter2, eval2)
            if comparison == "1":
                cover_letter = cover_letter2

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
    