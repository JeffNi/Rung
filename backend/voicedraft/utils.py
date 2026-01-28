import time
import yaml
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

# This file contains shared functions

# Gemini Model Options and Rate Limits (as of 2026):
# - gemini-2.5-flash: Fast, cheap, ~15 RPM free tier, ~1000 RPM paid tier
# - gemini-2.5-pro: More capable, slower, ~2 RPM free tier, ~1000 RPM paid tier
# - gemini-1.5-flash: Legacy, ~15 RPM free tier
# - gemini-1.5-pro: Legacy, ~2 RPM free tier
# Currently using: gemini-2.5-flash for all calls

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
    base_wait_time = 10  # Start with shorter wait for non-rate-limit errors
    rate_limit_wait = 60  # Longer wait for rate limits

    while retries < max_retries:
        try:
            print(f"[{step_name}] Attempt {retries + 1}/{max_retries}")
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            print(f"[{step_name}] [OK] Success!")
            
            # Add delay after successful call to prevent rate limit (15 RPM = ~4s per request)
            # Using 5s to be safe and leave buffer
            print(f"[{step_name}] Waiting 5s before next API call to respect rate limits...")
            time.sleep(5)
            
            return response.text.strip()
        except ResourceExhausted as e:
            retries += 1
            print(f"[{step_name}] Rate limit hit (attempt {retries}/{max_retries})")
            print(f"[{step_name}] Error details: {str(e)}")
            print(f"[{step_name}] Model being used: {model}")
            if retries < max_retries:
                print(f"[{step_name}] Waiting {rate_limit_wait}s before retrying...")
                time.sleep(rate_limit_wait)
                rate_limit_wait = min(rate_limit_wait * 2, 300)  # Cap at 5 minutes
        except Exception as e:
            retries += 1
            print(f"[{step_name}] ERROR: {type(e).__name__}: {str(e)}")
            print(f"[{step_name}] Model being used: {model}")
            if retries < max_retries:
                wait_time = base_wait_time * (2 ** (retries - 1))  # Exponential backoff: 10, 20, 40, 80...
                wait_time = min(wait_time, 120)  # Cap at 2 minutes for non-rate-limit errors
                print(f"[{step_name}] Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
            else:
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