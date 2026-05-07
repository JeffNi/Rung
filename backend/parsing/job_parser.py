"""Job description parsing utilities.

Originally from coverletter/company_info.py, now shared for resume generation.
"""
import os
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Add coverletter to path for imports
sys.path.append(str(Path(__file__).parent.parent / "coverletter"))
from utils import generate_with_retry, load_yaml
from provider_config import get_model_for_provider, get_fallback_models


def build_yaml_prompt(template_path: str, job_desc: str) -> str:
    """Build prompt for extracting job info into YAML template."""
    # Load YAML template as raw text
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Build prompt with proper string formatting
    prompt_parts = [
        "You are an assistant that extracts key information from a job description and fills it into the following YAML template.",
        "YAML template:",
        template,
        'Job description:\n"""',
        job_desc,
        '"""\n',
        "Fill the YAML template using information from the job description. Output ONLY the completed YAML. If some fields are missing in the job description, leave them blank or empty.",
        "Ensure all string values are properly quoted if they contain colons, dashes, or other YAML-sensitive characters.",
        "Do not add any explanations or extra text."
    ]

    return "\n".join(prompt_parts)


def strip_code_fence(text: str) -> str:
    """Remove markdown-style code fences (``` and ```yaml)"""
    lines = text.strip().splitlines()
    if lines[0].strip().startswith("```") and lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1])
    return text


def generate_job_yaml(job_description_text=None, api_key=None, provider="gemini"):
    """Generate structured YAML from job description text."""
    if api_key == None:
        # Load .env relative to the repository root (one level up from this module)
        dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=dotenv_path)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        genai.configure(api_key=api_key)

    # Resolve paths relative to this file so it works regardless of CWD
    base_dir = Path(__file__).parent
    template_path = str(base_dir / "templates" / "job_yaml_template.yaml")
    
    # Use provided job description text or read from coverletter inputs
    if job_description_text:
        job_desc = job_description_text
    else:
        # Default to coverletter's job_desc.txt for backward compatibility
        job_desc_path = Path(__file__).parent.parent / "coverletter" / "inputs" / "job_desc.txt"
        with open(str(job_desc_path), 'r', encoding='utf-8') as f:
            job_desc = f.read()

    prompt = build_yaml_prompt(template_path, job_desc)

    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    yaml = generate_with_retry(
        model, prompt, max_retries=5, api_key=api_key, 
        step_name="Job YAML Generation", provider=provider, 
        fallback_models=fallback_models
    )
    yaml = strip_code_fence(yaml)
    
    return yaml


def is_valid_yaml(path):
    """Check if YAML file exists and is valid."""
    if not os.path.exists(path):
        return False
    try:
        import yaml as _yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = _yaml.safe_load(f)
        return isinstance(data, dict)
    except Exception:
        return False


def ensure_generate_job_yaml(max_retries=3, delay=2):
    """Generate job YAML with retry logic for backward compatibility."""
    base_dir = Path(__file__).parent.parent / "coverletter" / "inputs"
    job_path = str(base_dir / "job_desc.yaml")
    for attempt in range(max_retries):
        generate_job_yaml()
        if is_valid_yaml(job_path):
            return load_yaml(job_path)
        print(f"Attempt {attempt + 1} failed. Retrying...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to generate a valid job YAML after {max_retries} attempts.")


def get_shortened_name(name, api_key=None, provider="gemini"):
    """Get shortened company name for casual reference."""
    prompt = f"""Given a company name, return a shortened version suitable for casual or brand reference.

Remove generic suffixes like "LLC", "Inc", "Technologies", "Solutions", "Vision", etc.

Keep distinctive names like "Goldman Sachs", "Procter & Gamble", or "Bank of America" intact.

Return only the core, identifiable name (e.g. "Virtek Vision" -> "Virtek", "Bree Technologies LLC" -> "Bree", but "Goldman Sachs" -> "Goldman Sachs").

Here is the company name to shorten:
{name}"""

    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    shortened = generate_with_retry(
        model, prompt, max_retries=5, api_key=api_key, 
        step_name="Company Name Shortening", provider=provider, 
        fallback_models=fallback_models
    )
    shortened = strip_code_fence(shortened)
    return shortened


def parse_job_to_dict(job_description: str, api_key: str = None, provider: str = "gemini") -> dict:
    """
    Parse job description into a structured dictionary.
    
    This is the main interface for the resume pipeline.
    Returns parsed job info with company, role, requirements, etc.
    """
    import yaml
    
    yaml_text = generate_job_yaml(job_description, api_key, provider)
    
    try:
        return yaml.safe_load(yaml_text)
    except Exception as e:
        print(f"[PARSING] Warning: Failed to parse YAML: {e}")
        # Return minimal structure on failure
        return {
            "company": "Unknown",
            "position": "Unknown",
            "summary": job_description[:500],
            "key_responsibilities": [],
            "required_skills": [],
            "preferred_skills": []
        }


def main():
    """CLI entry point for testing."""
    print(generate_job_yaml())


if __name__ == "__main__":
    main()
