import time
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# This file contains shared functions

def generate_with_retry(model, prompt, max_retries=20):
    retries = 0
    wait_time = 10

    while retries < max_retries:
        try:
            model = genai.GenerativeModel(model)
            response = model.generate_content(prompt)
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

def load_file(path="inputs/writing_sample.txt"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sample file not found at: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()