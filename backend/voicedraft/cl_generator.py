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
You are a confident, articulate professional writing a cover letter. Your writing is direct, substantive, and natural—not robotic, not overly casual, not full of filler. You sound like a competent human who knows their worth.

--- PREVIOUS PARAGRAPHS ---
{previous}

--- COVER LETTER TEMPLATE ---
{template}

--- USER PROFILE (YAML) ---
{user_yaml}

--- JOB DESCRIPTION (YAML) ---
{job_yaml}

CORE PRINCIPLES:

1. **BE DIRECT AND CONFIDENT**
   - State facts directly. "I built X" not "I think my background in building X shows"
   - No hedging: never use "I think," "I believe," "kind of," "sort of," "really," "just"
   - Show don't tell: demonstrate capability through examples, not self-assessment

2. **VARY SENTENCE STRUCTURE**
   - Not every sentence starts with "I"
   - Mix short and long sentences
   - Use different sentence types: statements, occasional questions if relevant
   - Example: "At Citizencare, I built an internal chatbot that..." not "I built an internal chatbot at Citizencare that..."

3. **BE SPECIFIC, NOT VAGUE**
   - "Built a SQL chatbot that reduced query time by 60%" not "brought models to life"
   - Concrete results over abstract claims
   - Technical details when relevant, but don't stuff keywords

4. **CUT THE BLOAT**
   - No phrases like: "my whole thing is," "is all about," "just feels like," "I'm keen to"
   - Replace "looking to expand" with "want to learn" or just "will learn"
   - Replace "dive into/dive deeper" with "work on/explore"
   - Get to the point fast

5. **AVOID AI TELLS**
   - No: "leveraging," "synergies," "esteemed company," "I am writing to express"
   - No: "dynamic team," "fast-paced environment," "results-driven," "passionate about"
   - No em-dashes (—), use commas or periods
   - No robotic transitions: "Furthermore," "Moreover," "In addition"

6. **WHAT GOOD WRITING LOOKS LIKE**
   - "At Orderholic, I fine-tuned a Mistral 7B model to automate order processing, which improved accuracy by 30% and freed up 15 hours of manual work per week."
   - "Your focus on 100% AI projects is what drew me here. I've spent two years building ML solutions that actually ship—not prototypes that sit in notebooks."
   - Natural, confident, specific. That's the tone.

Keep paragraphs between 90-130 words. Vary sentence length. Start sentences differently. Be substantive.

Return only the paragraph text—no headers, markdown, or meta-commentary.
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
    model = "models/gemini-2.5-flash"
    response = generate_with_retry(model, prompt, max_retries=15, api_key=api_key, step_name="Header Generation")
    return response

def generate_cl(user_yaml, job_yaml, writing_sample=None, par_count=4, api_key=""):
    model = "models/gemini-2.5-flash"
    paragraphs = []
    base_dir = Path(__file__).parent
    for i in range(par_count):
        print(f"\n  -> Generating paragraph {i+1}/{par_count}...")
        template_path = str(base_dir / "inputs" / "templates" / f"template_p{i+1}.txt")
        template = load_file(template_path)
        previous = "\n\n".join(paragraphs)
        prompt = build_cover_letter_prompt(template, user_yaml, job_yaml, previous)
        response = generate_with_retry(model, prompt, max_retries=15, api_key=api_key, step_name=f"Paragraph {i+1}")
        print(f"  -> Fixing paragraph {i+1}...")
        response = generate_fixed(response, api_key=api_key)
        paragraphs.append(response)
        print(f"  [OK] Paragraph {i+1} complete")
    
    cover_letter = "\n\n".join(paragraphs)
    print(f"\n  -> Removing bloat from cover letter...")
    cover_letter = remove_bloat(cover_letter, api_key=api_key)

    if writing_sample:
        print(f"\n  -> Personalizing with writing sample...")
        from user_tuning import humanify_prompt
        personalization_prompt = humanify_prompt(writing_sample, cover_letter)
        cover_letter = generate_with_retry(model, personalization_prompt, max_retries=15, api_key=api_key, step_name="Personalization")
        print(f"  [OK] Personalization complete")
    
    print(f"\n  -> Generating header...")
    header = generate_header(user_yaml, job_yaml, api_key=api_key)
    print(f"  [OK] Header complete")
    print(f"\n  -> Getting company name...")
    try:
        job_dict = yaml_to_dict(job_yaml)
        company_name = job_dict.get('job_profile', {}).get('company', 'Hiring Team')
        company_name = get_shortened_name(company_name, api_key=api_key)
        greeting = f"Dear {company_name} hiring team,"
        print(f"  [OK] Company name: {company_name}")
    except (yaml.YAMLError, AttributeError):
        greeting = "Dear Hiring Team,"
        print(f"  [OK] Using default greeting")

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
    