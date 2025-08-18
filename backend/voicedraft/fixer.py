import os
from pathlib import Path
from utils import generate_with_retry, load_file

def build_fixer_prompt(noisy_text: str) -> str:
    return f"""This cover letter was generated using AI and then intentionally modified with random noise to make it feel more human and less robotic.

Your task is to:
- Fix only the most confusing or clearly broken sentences
- Correct grammar or spelling issues *only when they hurt readability or are obvious*
- Keep the casual, slightly imperfect, conversational tone
- Preserve filler words, contractions, and minor awkwardness that help it feel natural
- Return only the fixed cover letter
- Correct errors that hurt the viability of the cover letter *You are not optimizing, do not make unnecessary changes*

Avoid common signs of AI-generated text:
- No double dashes `--` or em-dashes `—`; use commas, colons, or semicolons instead
- No curly quotes (“ ”); use straight quotes (if applicable)
- Vary sentence lengths and structure — no robotic pacing
- Remove cliches like “I am excited to apply” or “I believe I’m a strong fit”
- Avoid overly formal tone — natural, confident, personal is better
- Use contractions and voice cues if they fit the style (e.g. "I'm", "I've", "honestly", "what drew me in", etc.)
- Don’t overuse transition phrases like “Furthermore”, “In addition”, etc.
- Keep formatting natural: no bullet points, no excessive line breaks, no weird spacing

Do NOT make the output sound like a typical AI-generated response. Make it sound like a smart but slightly rushed human wrote it.


Here is the letter to fix:
---
{noisy_text}"""

def build_fixer_prompt2(paragraph, user_sample) -> str:
    return f"""You are editing part of a cover letter.

Your task is to simplify the writing by removing unnecessary or overly formal words, and replacing fancy words with more natural alternatives. You may only delete words, replace them, or add small helper words (like "a" or "the") to make grammar correct.

Additionally, match the tone and personality of the writing sample below. You are not copying its structure or content—just capturing the writer’s voice, phrasing style, and general rhythm. Prioritize clarity and authenticity, but keep the professionalism expected in a job application.

Here is the paragraph to edit:
{paragraph}

Here is the personal writing sample (for tone reference only):
{user_sample}

Return only the edited paragraph.
"""

def bloat_reduction_prompt(paragraph):
    return f"""
Edit this cover letter by removing redundant words, filler phrases, bloat, and repeated ideas or phrases. 
Keep the meaning and tone the same. Only remove or replace words or repeated content, do not rewrite entirely.
Keep the sentence structure natural and human.

Here is the cover letter:
{paragraph}

Return only the edited cover letter.
"""

def build_improvement_prompt(paragraph, suggestion, template):
    return f""""""


def generate_fixed(paragraph, api_key=None):
    # Resolve sample path relative to this file so it works regardless of CWD
    base_dir = Path(__file__).parent
    sample_path = str(base_dir / "inputs" / "writing_sample.txt")
    sample = load_file(sample_path)
    prompt = build_fixer_prompt2(paragraph, sample)

    model = "gemini-2.5-flash-preview-05-20"
    response = generate_with_retry(model, prompt, max_retries=1, api_key=api_key)
    return response

def remove_bloat(paragraph, api_key=None):
    prompt = bloat_reduction_prompt(paragraph)

    model = "gemini-2.0-flash"
    response = generate_with_retry(model, prompt, max_retries=1, api_key=api_key)
    return response