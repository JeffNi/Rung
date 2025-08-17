import time
import yaml
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

# This file contains shared functions

def generate_with_retry(model, prompt, max_retries=20, api_key=None):
    if api_key is None:
        load_dotenv(dotenv_path="../.env")
        api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    retries = 0
    wait_time = 10

    while retries < max_retries:
        try:
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            return response.text.strip()
        except ResourceExhausted as e:
            print(f"Rate limit hit, waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            wait_time *= 2
            retries += 1
        except Exception as e:
            print(f"Other error: {e}")
            break
    raise Exception("Max retries exceeded")

def load_yaml(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return yaml.dump(data, sort_keys=False)

def load_file(path="inputs/writing_sample.txt"):
    # Try the provided path relative to current working directory first
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()

    # If not found, try resolving relative to this module's directory
    module_dir = os.path.dirname(__file__)
    alt_path = os.path.join(module_dir, path)
    if os.path.exists(alt_path):
        with open(alt_path, "r", encoding="utf-8") as file:
            return file.read().strip()

    raise FileNotFoundError(f"Sample file not found at: {path} (also tried: {alt_path})")