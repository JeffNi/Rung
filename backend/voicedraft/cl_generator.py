import os
import re
from datetime import date
from humanizer import clean_text
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_file, load_yaml
from company_info import generate_job_yaml
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat
from evaluator import evaluate_cl, compare_cls


# This file puts together the necessary information and generates the cover letter

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

def generate_header():
    dotenv_path = Path("../.env")
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    job_desc = load_file("inputs/job_desc.yaml")
    user = load_file("inputs/user.yaml")
    prompt = build_header_prompt(job_desc, user, date.today())

    model = "gemini-2.0-flash"
    response = generate_with_retry(model, prompt, max_retries=1)
    return response


def generate_cl(par_count=4):
    dotenv_path = Path("code/cover_letter/.env")
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    model = "gemini-2.5-flash-preview-05-20"
    # style_prompt = generate_style_prompt()
    generate_job_yaml()

    job_path = "inputs/job_desc.yaml"
    user_path = "inputs/user.yaml"

    user_yaml = load_yaml(user_path)
    job_yaml = load_yaml(job_path)

    paragraphs = []

    for i in range(par_count):
        template_path = f"inputs/templates/template_p{i+1}.txt"
        template = load_file(template_path)
        print(template)
        print("\n\n\n")

        previous = "\n\n".join(paragraphs)

        prompt = build_cover_letter_prompt(template, user_yaml, job_yaml, previous)
        response = generate_with_retry(model, prompt, max_retries=2)
        response = generate_fixed(response)
        # Potential improvement, call generate fixed again before saving, providing previous paragraphs when building paragraphs
        # Generate multiple cover letters and pick the best

        paragraphs.append(response)
    cover_letter = "\n\n".join(paragraphs)
    cover_letter = remove_bloat(cover_letter)

    header = generate_header()
    # code = clean_code(response)
    
    cover_letter = re.sub(r'—', ',', cover_letter)

    cover_letter = header + "\n\n" + cover_letter

    return cover_letter

    # humanized = clean_text(response)
    # final = generate_fixed(humanized)

    # output_path = os.path.join("outputs", f"final.txt")
    # response = personalize(style_prompt)
    # with open(output_path, "w", encoding="utf-8") as f:
    #     f.write(response)

def get_best_cl(num=3):
    cover_letter = generate_cl()

    if (num > 1):
        for i in range(num):
            cover_letter2 = generate_cl()
            eval1 = evaluate_cl(cover_letter)
            eval2 = evaluate_cl(cover_letter2)
            comparison = compare_cls(cover_letter, eval1, cover_letter2, eval2)
            if comparison == "1":
                cover_letter = cover_letter2

    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"cover_letter.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cover_letter)

def main():
    get_best_cl()

if __name__ == "__main__":
    main()
    