import os
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_yaml

def build_yaml_prompt(template_path: str, job_desc: str) -> str:
    # Load YAML template as raw text
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

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

def generate_job_yaml(job_description_text=None, api_key=None):
    if api_key == None:
        # Load .env relative to the repository root (one level up from this module)
        dotenv_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path=dotenv_path)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        genai.configure(api_key=api_key)

    # Resolve paths relative to this file so it works regardless of CWD
    base_dir = Path(__file__).parent
    template_path = str(base_dir / "inputs" / "job_yaml_template.yaml")
    
    # Use provided job description text or read from file
    if job_description_text:
        job_desc = job_description_text
    else:
        job_desc_path = base_dir / "inputs" / "job_desc.txt"
        with open(str(job_desc_path), 'r', encoding='utf-8') as f:
            job_desc = f.read()

    prompt = build_yaml_prompt(template_path, job_desc)

    model = "models/gemini-2.5-flash"
    # Forward api_key so deployment doesn't rely on a local .env
    yaml = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name="Job YAML Generation")
    yaml = strip_code_fence(yaml)
    
    # For backward compatibility, still write to file if no text provided
    if not job_description_text:
        output_path = base_dir / "inputs" / "job_desc.yaml"
        with open(str(output_path), "w", encoding="utf-8") as f:
            f.write(yaml)
    
    return yaml

def is_valid_yaml(path):
    if not os.path.exists(path):
        return False
    try:
        # Validate by actually loading a dict
        import yaml as _yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = _yaml.safe_load(f)
        return isinstance(data, dict)
    except Exception:
        return False

def ensure_generate_job_yaml(max_retries=3, delay=2):
    base_dir = Path(__file__).parent
    job_path = str(base_dir / "inputs" / "job_desc.yaml")
    for attempt in range(max_retries):
        generate_job_yaml()
        if is_valid_yaml(job_path):
            return load_yaml(job_path)
        print(f"Attempt {attempt + 1} failed. Retrying...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to generate a valid job YAML after {max_retries} attempts.")

def get_shortened_name(name, api_key=None):
    prompt = f"""Given a company name, return a shortened version suitable for casual or brand reference.

Remove generic suffixes like "LLC", "Inc", "Technologies", "Solutions", "Vision", etc.

Keep distinctive names like "Goldman Sachs", "Procter & Gamble", or "Bank of America" intact.

Return only the core, identifiable name (e.g. "Virtek Vision" -> "Virtek", "Bree Technologies LLC" -> "Bree", but "Goldman Sachs" -> "Goldman Sachs").

Here is the company name to shorten:
{name}"""

    model = "models/gemini-2.5-flash"
    shortened = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name="Company Name Shortening")
    shortened = strip_code_fence(shortened)
    return shortened

def main():
    print(generate_job_yaml())

if __name__ == "__main__":
    main()