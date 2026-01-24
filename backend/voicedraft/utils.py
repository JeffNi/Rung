import time
import yaml
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

# This file contains shared functions

def generate_with_retry(model, prompt, max_retries=20, api_key=None, step_name="API call"):
    print(f"[{step_name}] Starting with model: {model}")
    if api_key is None:
        load_dotenv(dotenv_path="../.env")
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print(f"[{step_name}] ERROR: No API key provided!")
        raise Exception("No API key provided")
    
    print(f"[{step_name}] API key present: {len(api_key)} characters")
    genai.configure(api_key=api_key)

    retries = 0
    wait_time = 60  # Increased to match rate limit window

    while retries < max_retries:
        try:
            print(f"[{step_name}] Attempt {retries + 1}/{max_retries}")
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            print(f"[{step_name}] [OK] Success!")
            
            # Add delay after successful call to prevent rate limit (20 RPM = ~3s per request)
            print(f"[{step_name}] Waiting 4s before next API call to respect rate limits...")
            time.sleep(4)
            
            return response.text.strip()
        except ResourceExhausted as e:
            retries += 1
            print(f"[{step_name}] Rate limit hit (attempt {retries}/{max_retries})")
            print(f"[{step_name}] Error details: {str(e)}")
            if retries < max_retries:
                print(f"[{step_name}] Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
                wait_time *= 2
        except Exception as e:
            print(f"[{step_name}] ERROR: {type(e).__name__}: {str(e)}")
            retries += 1
            if retries >= max_retries:
                break
    print(f"[{step_name}] FAILED: Max retries exceeded")
    raise Exception(f"Max retries exceeded for {step_name}")

def load_yaml(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return yaml.dump(data, sort_keys=False)

def load_file(path="inputs/writing_sample.txt"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sample file not found at: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()