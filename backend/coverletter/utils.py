import time
import yaml
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from groq import Groq
from dotenv import load_dotenv

# This file contains shared functions

# Track cumulative token usage per session
_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}

def get_token_usage():
    """Return cumulative token usage."""
    return dict(_token_usage)

def reset_token_usage():
    """Reset token counters."""
    _token_usage.update({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0})

# Gemini Model Options and Rate Limits (as of 2026):
# - gemini-2.5-flash: Fast, cheap, ~15 RPM free tier, ~1000 RPM paid tier
# - gemini-2.5-pro: More capable, slower, ~2 RPM free tier, ~1000 RPM paid tier
# Currently using: gemini-2.5-flash for all calls

# Groq Model Options (FREE):
# - llama-3.3-70b-versatile: Best quality (replaces 3.1-70b), 14,400 RPD, 30 RPM
# - llama-3.1-8b-instant: Fastest, 14,400 RPD, 30 RPM
# - mixtral-8x7b-32768: Good balance, 14,400 RPD, 30 RPM

def generate_with_groq(model, prompt, max_retries=20, api_key=None, step_name="API call", fallback_models=None):
    """Generate content using Groq API with automatic fallback on quota limits"""
    print(f"[{step_name}] Starting with Groq model: {model}")
    
    if not api_key:
        load_dotenv(dotenv_path="../.env")
        api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print(f"[{step_name}] ERROR: No Groq API key provided!")
        raise Exception("No Groq API key provided")
    
    print(f"[{step_name}] Groq API key present: {len(api_key)} characters")
    
    # Remove any proxy-related environment variables that might interfere
    env_backup = {}
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]
    
    try:
        client = Groq(api_key=api_key)
    finally:
        # Restore environment variables
        for key, value in env_backup.items():
            os.environ[key] = value
    
    # Try primary model, then fallbacks
    models_to_try = [model] + (fallback_models or [])
    
    for model_attempt in models_to_try:
        if model_attempt != model:
            print(f"[{step_name}] Trying fallback model: {model_attempt}")
        
        retries = 0
        base_wait_time = 10
        rate_limit_wait = 60
        
        while retries < max_retries:
            try:
                print(f"[{step_name}] Attempt {retries + 1}/{max_retries}")
                response = client.chat.completions.create(
                    model=model_attempt,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2048
                )
                usage = response.usage
                _token_usage["prompt_tokens"] += usage.prompt_tokens
                _token_usage["completion_tokens"] += usage.completion_tokens
                _token_usage["total_tokens"] += usage.total_tokens
                _token_usage["calls"] += 1
                print(f"[{step_name}] [OK] Success! Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out (session total: {_token_usage['total_tokens']})")
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                error_str = str(e)
                retries += 1
                
                # Check for authentication/API key errors - fail fast
                if "invalid api key" in error_str.lower() or "authentication" in error_str.lower() or "401" in error_str:
                    print(f"[{step_name}] INVALID API KEY - Authentication failed")
                    print(f"[{step_name}] Error: {error_str}")
                    # Don't retry or try other models - API key is invalid
                    raise Exception("Invalid API key. Please check your API key and try again.")
                
                # Check if it's a DAILY quota limit (tokens per day)
                if "tokens per day" in error_str.lower() or "TPD" in error_str:
                    print(f"[{step_name}] DAILY QUOTA EXCEEDED for {model_attempt}")
                    print(f"[{step_name}] Error: {error_str}")
                    # Don't retry - daily quota won't reset by waiting
                    break  # Try next model in fallback list
                
                # Check if it's a per-minute rate limit
                elif "rate" in error_str.lower() or "429" in error_str:
                    print(f"[{step_name}] Rate limit hit (attempt {retries}/{max_retries})")
                    print(f"[{step_name}] Error details: {error_str}")
                    if retries < max_retries:
                        print(f"[{step_name}] Waiting {rate_limit_wait}s before retrying...")
                        time.sleep(rate_limit_wait)
                        rate_limit_wait = min(rate_limit_wait * 2, 60)  # Cap at 60s for rate limits
                else:
                    print(f"[{step_name}] ERROR (non-retryable): {type(e).__name__}: {error_str}")
                    raise
    
    print(f"[{step_name}] FAILED: All models exhausted")
    raise Exception(f"Max retries exceeded for {step_name} (tried {len(models_to_try)} models)")

def generate_with_gemini(model, prompt, max_retries=20, api_key=None, step_name="API call"):
    """Generate content using Gemini API"""
    print(f"[{step_name}] Starting with Gemini model: {model}")
    if api_key is None:
        load_dotenv(dotenv_path="../.env")
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print(f"[{step_name}] ERROR: No API key provided!")
        raise Exception("No API key provided")
    
    print(f"[{step_name}] API key present: {len(api_key)} characters")
    genai.configure(api_key=api_key)

    retries = 0
    wait_time = 60

    while retries < max_retries:
        try:
            print(f"[{step_name}] Attempt {retries + 1}/{max_retries}")
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            # Track Gemini token usage
            try:
                usage = response.usage_metadata
                _token_usage["prompt_tokens"] += usage.prompt_token_count
                _token_usage["completion_tokens"] += usage.candidates_token_count
                _token_usage["total_tokens"] += usage.total_token_count
                _token_usage["calls"] += 1
                print(f"[{step_name}] [OK] Success! Tokens: {usage.prompt_token_count} in / {usage.candidates_token_count} out (session total: {_token_usage['total_tokens']})")
            except Exception:
                _token_usage["calls"] += 1
                print(f"[{step_name}] [OK] Success! (token count unavailable)")
            
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
            error_str = str(e)
            print(f"[{step_name}] ERROR (non-retryable): {type(e).__name__}: {error_str}")
            raise
    print(f"[{step_name}] FAILED: Max retries exceeded")
    raise Exception(f"Max retries exceeded for {step_name}")

def generate_with_retry(model, prompt, max_retries=20, api_key=None, step_name="API call", provider="gemini", fallback_models=None):
    """
    Unified function to generate content with either Gemini or Groq
    
    Args:
        model: Model name (e.g., 'models/gemini-2.5-flash' or 'llama-3.3-70b-versatile')
        prompt: The prompt to send
        max_retries: Maximum number of retry attempts
        api_key: API key for the provider
        step_name: Name of the step for logging
        provider: 'gemini' or 'groq'
        fallback_models: List of fallback models to try if primary fails
    """
    if provider.lower() == "groq":
        return generate_with_groq(model, prompt, max_retries, api_key, step_name, fallback_models)
    else:
        return generate_with_gemini(model, prompt, max_retries, api_key, step_name)

def load_yaml(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return yaml.dump(data, sort_keys=False)

def load_file(path="inputs/writing_sample.txt"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sample file not found at: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()