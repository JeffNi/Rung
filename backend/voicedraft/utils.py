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
            gen_model = genai.GenerativeModel(model, api_key=api_key)
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
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sample file not found at: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()