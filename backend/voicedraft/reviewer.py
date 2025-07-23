import os
from pathlib import Path
import re
from utils import generate_with_retry, load_file

def detect_AI_prompt(cover_letter, NO_AI_DETECTED):
    return """You are an expert in detecting AI-generated writing. Your task is to analyze the following **cover letter** and identify the most AI-like aspects of the writing.

Carefully examine the tone, phrasing, sentence structure, and word choice. Focus on patterns commonly associated with large language models, such as:
- Overly formal or generic phrasing
- Repetitive structure or sentence rhythm
- Unusual politeness or excessive professionalism
- Buzzword stuffing or vague statements
- Lacking specific personal voice or point of view
- Unnatural transitions or “perfect” flow
- Cliché phrases or recruiter-speak

If any AI-like patterns are detected, respond with a numbered list of specific examples from the text, each followed by a short explanation of why it seems AI-generated.
- Do not generate any preamble, explanation, or commentary like “Sure!” or “Here’s the analysis.”
- Your output must be **only** the result: either a numbered list of AI-like features or the exact phrase `NO_AI_DETECTED` on its own line.

If no such patterns are present and the writing sounds entirely human, respond with this exact code on its own line:
{NO_AI_DETECTED}

Now analyze this cover letter:
{cover_letter}
"""

def make_fixer_prompt(cover_letter: str, issues: str) -> str:
    return f"""You are editing a cover letter to remove AI-generated giveaways and make it sound more natural, human, and authentic — without altering the core message, structure, or personal tone.

--- ORIGINAL COVER LETTER ---
{cover_letter}

--- AI DETECTION CRITIQUE ---
The following issues have been identified as AI-sounding, robotic, or unnatural:
{issues}

--- INSTRUCTIONS ---
Your job is to revise the original text, only addressing the issues listed. Fix awkward phrasing, remove generic or overly polished language, and rewrite unnatural transitions. Do NOT rewrite the entire letter, change the meaning, or add new content. Maintain the applicant’s intent, tone, and level of professionalism.

Make the revision sound like a thoughtful, smart person wrote it — not a chatbot. Do not mention this task, do not explain anything, and do not include extra formatting or markdown. Just output the revised cover letter.
"""

NO_AI_DETECTED = "NO_AI_DETECTED"
def generate_review(model, cover_letter):
    prompt = detect_AI_prompt(cover_letter, NO_AI_DETECTED)

    response = generate_with_retry(model, prompt, max_retries=1)
    return response

def generate_fix(model, problems, cover_letter):
    prompt = make_fixer_prompt(cover_letter, problems)

    response = generate_with_retry(model, prompt, max_retries=1)
    response = re.sub(r'—', ',', response)
    return response

def run_fix_iterations(max_iter, cover_letter):
    models = []
    suggestions = ""
    counter = 0

    for model in models:
        while not suggestions == NO_AI_DETECTED or counter % (max_iter-1) == 0:
            suggestions = generate_review(model, cover_letter)