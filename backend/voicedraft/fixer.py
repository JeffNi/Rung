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
    return f"""You are editing a cover letter paragraph to make it stronger and more human.

Your task:
1. Remove weak/hedging language: "I think," "I believe," "kind of," "really," "just," "actually"
2. Remove bloat: "my whole thing is," "is all about," "I'm keen to," "dive into," "just feels like"
3. Make it direct: "I built X" not "I've been working on building X"
4. Match the natural rhythm and phrasing style of the writing sample (voice, not content)
5. Keep it professional but human—confident without being arrogant

**IMPORTANT**: 
- Don't make it overly formal or stiff
- Don't add corporate jargon
- Don't remove all personality—just the weak filler
- Vary sentence starts: not every sentence should start with "I"

Here is the paragraph to edit:
{paragraph}

Here is the personal writing sample (for voice/rhythm reference only):
{user_sample}

Return only the edited paragraph—no explanation.
"""

def bloat_reduction_prompt(paragraph):
    return f"""
Edit this cover letter to be more direct and impactful by:

1. Removing hedging: "I think," "I believe," "kind of," "sort of," "really," "just," "actually"
2. Removing casual bloat: "my whole thing is," "is all about," "I'm keen to," "looking to," "dive into/deeper"
3. Cutting redundancy: if you've said it once clearly, don't say it again
4. Making statements direct: "I built X" not "my background in building X shows that I can build things"
5. Removing repeated phrases or ideas across paragraphs

Keep the meaning, facts, and examples. Just make every word count.

Here is the cover letter:
{paragraph}

Return only the edited cover letter—no explanation.
"""

def build_improvement_prompt(paragraph, suggestion, template):
    return f""""""


def generate_fixed(paragraph, api_key=None):
    # Resolve sample path relative to this file so it works regardless of CWD
    base_dir = Path(__file__).parent
    sample_path = str(base_dir / "inputs" / "writing_sample.txt")
    sample = load_file(sample_path)
    prompt = build_fixer_prompt2(paragraph, sample)

    model = "models/gemini-2.5-flash"
    response = generate_with_retry(model, prompt, max_retries=10, api_key=api_key, step_name="Fixing Paragraph")
    return response

def remove_bloat(paragraph, api_key=None):
    prompt = bloat_reduction_prompt(paragraph)

    model = "models/gemini-2.5-flash"
    response = generate_with_retry(model, prompt, max_retries=10, api_key=api_key, step_name="Bloat Removal")
    return response