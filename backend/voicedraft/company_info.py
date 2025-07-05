import os
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_yaml

def build_yaml_prompt(template_path: str, job_desc_path: str) -> str:
    # Load YAML template as raw text
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Load job description text
    with open(job_desc_path, 'r', encoding='utf-8') as f:
        job_desc = f.read()

    # Construct the prompt
    prompt = f"""You are an assistant that extracts key information from a job description and fills it into the following YAML template.
YAML template:
{template}
Job description:
\"\"\"
{job_desc}
\"\"\"

Fill the YAML template using information from the job description. Output ONLY the completed YAML. If some fields are missing in the job description, leave them blank or empty.

Ensure all string values are properly quoted if they contain colons, dashes, or other YAML-sensitive characters.

Do not add any explanations or extra text.
"""

    return prompt

def strip_code_fence(text: str) -> str:
    # Remove markdown-style code fences (``` and ```yaml)
    lines = text.strip().splitlines()
    if lines[0].strip().startswith("```") and lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1])
    return text

def generate_job_yaml():
    dotenv_path = Path("../.env")
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    template_path = "inputs/job_yaml_template.yaml"
    job_desc_path = "inputs/job_desc.txt"

    prompt = build_yaml_prompt(template_path, job_desc_path)

    model = "gemini-2.0-flash"
    yaml = generate_with_retry(model, prompt, max_retries=1)
    yaml = strip_code_fence(yaml)
    
    with open("inputs/job_desc.yaml", "w", encoding="utf-8") as f:
        f.write(yaml)

def is_valid_yaml(path):
    if not os.path.exists(path):
        return False
    try:
        data = load_yaml(path)
        return data is not None and isinstance(data, dict)
    except Exception:
        return False

def ensure_generate_job_yaml(max_retries=3, delay=2):
    job_path = "inputs/job_desc.yaml"
    for attempt in range(max_retries):
        generate_job_yaml()
        if is_valid_yaml(job_path):
            return load_yaml(job_path)
        print(f"Attempt {attempt + 1} failed. Retrying...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to generate a valid job YAML after {max_retries} attempts.")

def main():
    print(generate_job_yaml())

if __name__ == "__main__":
    main()