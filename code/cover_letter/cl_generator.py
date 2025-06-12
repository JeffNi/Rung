import os
import re
import yaml
from humanizer import clean_text
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_file
from company_info import generate_job_yaml
from user_tuning import generate_style_prompt, personalize
from fixer import generate_fixed, remove_bloat


# This file puts together the necessary information and generates the cover letter

def build_cover_letter_prompt(template: str, user_yaml: str, job_yaml: str) -> str:
    return f"""
You are a thoughtful and articulate university student known for writing standout cover letters. You write in a way that feels honest, grounded, and personal — not like an AI or someone trying too hard to sound “professional.” Your goal is to write a paragraph for a standout cover letter given a template, your user profile and the job description.

--- COVER LETTER TEMPLATE ---
{template}

--- USER PROFILE (YAML) ---
{user_yaml}

--- JOB DESCRIPTION (YAML) ---
{job_yaml}


INSTRUCTIONS

Be natural and real. Write like someone who knows how to express sincere interest without sounding generic, robotic, or exaggerated. Aim for clarity, personality, and quiet confidence.

Avoid AI-sounding language. Never use phrases like “the bedrock of innovation,” “leveraging synergies,” “my passion for your esteemed company,” or “I am writing to express my interest.” Those are clichés. So are “dynamic team,” “fast-paced environment,” and “results-driven mindset.”

Avoid over-polish. You’re not writing for a corporate memo — you're a student trying to connect with another human. Slight imperfections are welcome. Let the letter breathe.

Use concrete examples *only* when they clearly relate to what this job needs. Don’t stuff in every skill or project — pick the one or two that make the strongest case.

Do not include references to well-known individuals unless directly relevant to the candidate’s experience or motivation.

Avoid generic phrases like “I want to discuss this more” or “Thank you for your time” that do not add value.

Be specific, not buzzwordy. Use concrete examples from the user’s experience that align with the job. It’s okay to be brief and to the point. Don’t stuff in every technical term — just what matters.

Let personality show. A moment of humor, curiosity, or honesty makes a letter memorable. The tone should be smart, reflective, and genuine — like someone who really thought about this opportunity and what they bring to it.

Write a short, varied paragraph. No headers, markdown, or commentary — just the final plain text letter.
"""


def load_yaml(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return yaml.dump(data, sort_keys=False)


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

        prompt = build_cover_letter_prompt(template, user_yaml, job_yaml)
        response = generate_with_retry(model, prompt, max_retries=2)
        response = generate_fixed(response)
        # Potential improvement, call generate fixed again before saving, providing previous paragraphs when building paragraphs

        paragraphs.append(response)
    cover_letter = "\n\n".join(paragraphs)
    cover_letter = remove_bloat(cover_letter)
    # code = clean_code(response)
    
    cover_letter = re.sub(r'—', ',', cover_letter)

    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"cover_letter.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cover_letter)

    # humanized = clean_text(response)
    # final = generate_fixed(humanized)

    # output_path = os.path.join("outputs", f"final.txt")
    # response = personalize(style_prompt)
    # with open(output_path, "w", encoding="utf-8") as f:
    #     f.write(response)

def main():
    generate_cl()

if __name__ == "__main__":
    main()
    