import os
import re
from collections import Counter
from pathlib import Path
from utils import generate_with_retry, load_file
from provider_config import get_model_for_provider

# Common words to exclude from repetition detection
COMMON_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
    'may', 'might', 'can', 'this', 'that', 'these', 'those', 'it', 'its',
    'he', 'she', 'they', 'we', 'you', 'my', 'your', 'their', 'our',
    'what', 'which', 'who', 'when', 'where', 'why', 'how'
}

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
Edit this cover letter by removing redundant words, filler phrases, bloat, AI-sounding language, and vague descriptions.

**Remove or Replace These AI-Sounding Phrases:**
- "my tenure at" → "at"
- "my aspiration is to" → "I want to"
- "resonate with me" → remove or rephrase
- "align with" → "match" or remove
- "thereby supporting" → remove
- "something I anticipate" → "I look forward to"
- "realizing its ambitions" → remove
- "overarching aspirations" → "goals"
- "innovative approach" → be specific or remove
- "commitment to fostering" → remove or simplify
- "equipped me to contribute" → "helped me"
- "showcasing my capability" → remove
- "align with business objectives" → be specific or remove
- "craft AI solutions" → "build AI solutions"
- "enabling me to" → remove

**Replace Vague Descriptions with Specifics:**
- "impressive outcomes" → replace with actual numbers/metrics or remove
- "swift, dependable, optimized" → describe what you actually built
- "yield valuable insights" → explain the specific insight/impact
- "crucial aspect" → remove
- Generic adjectives without context → make concrete or remove

**Rules:**
- Keep the meaning and core facts
- Only remove or replace words, don't rewrite entirely
- Replace vague language with more direct phrasing
- Keep the sentence structure natural

Here is the cover letter:
{paragraph}

Return only the edited cover letter.
"""

def detect_repetition(text):
    """
    Detect repeated words and phrases in text, excluding common words.
    Returns a dict with repeated words and their counts.
    """
    # Extract words (lowercase, alphanumeric only)
    words = re.findall(r'\b[a-z]+\b', text.lower())
    
    # Count word frequencies, excluding common words
    word_counts = Counter(word for word in words if word not in COMMON_WORDS and len(word) > 2)
    
    # Find words used more than twice
    repeated = {word: count for word, count in word_counts.items() if count > 2}
    
    # Detect sentence-start patterns (e.g., "I'm", "I am", "I have")
    sentence_starts = re.findall(r'(?:^|\. |\n)([A-Z][^\s\.]{0,15})', text)
    start_counts = Counter(start.lower() for start in sentence_starts)
    repeated_starts = {start: count for start, count in start_counts.items() if count > 2}
    
    return {
        'words': repeated,
        'sentence_starts': repeated_starts
    }

def build_repetition_fix_prompt(text, repetition_data):
    """Build prompt to fix repetition using synonyms"""
    repeated_words = repetition_data.get('words', {})
    repeated_starts = repetition_data.get('sentence_starts', {})
    
    if not repeated_words and not repeated_starts:
        return None  # No significant repetition
    
    word_list = ', '.join([f"'{word}' ({count}x)" for word, count in repeated_words.items()])
    start_list = ', '.join([f"'{start}' ({count}x)" for start, count in repeated_starts.items()])
    
    prompt = f"""Rewrite this cover letter to reduce repetition by using synonyms and varied sentence structures.

**Overused words detected:** {word_list if word_list else "None"}
**Overused sentence starts:** {start_list if start_list else "None"}

**Instructions:**
- Replace repeated words with natural synonyms
- Vary sentence openings to avoid starting multiple sentences the same way
- Keep ALL content, facts, and achievements exactly as written
- Maintain professional tone
- Preserve the meaning and flow

**Example fixes:**
- "I'm confident" → "My experience shows"
- "I'm excited" → "I look forward to"
- "I have experience with" → "At [Company], I worked with"

Text to fix:
{text}

Return only the rewritten text with no explanation."""
    
    return prompt

def build_improvement_prompt(paragraph, suggestion, template):
    return f""""""


def generate_fixed(paragraph, api_key=None, provider="gemini", fallback_models=None):
    # Resolve sample path relative to this file so it works regardless of CWD
    base_dir = Path(__file__).parent
    sample_path = str(base_dir / "inputs" / "writing_sample.txt")
    sample = load_file(sample_path)
    prompt = build_fixer_prompt2(paragraph, sample)

    model = get_model_for_provider(provider)
    response = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name="Fixing Paragraph", provider=provider, fallback_models=fallback_models)
    return response

def remove_bloat(paragraph, api_key=None, provider="gemini", fallback_models=None):
    prompt = bloat_reduction_prompt(paragraph)

    model = get_model_for_provider(provider)
    response = generate_with_retry(model, prompt, max_retries=5, api_key=api_key, step_name="Bloat Removal", provider=provider, fallback_models=fallback_models)
    return response

def reduce_repetition(text, api_key=None, provider="gemini", fallback_models=None):
    """
    Detect and fix repetition in text using targeted LLM prompts.
    Only calls LLM if significant repetition is detected.
    """
    # Detect repetition
    repetition_data = detect_repetition(text)
    
    # Only fix if there's significant repetition
    if not repetition_data['words'] and not repetition_data['sentence_starts']:
        return text  # No significant repetition, return as-is
    
    print(f"  -> Detected repetition: {len(repetition_data['words'])} words, {len(repetition_data['sentence_starts'])} sentence starts")
    
    # Build targeted prompt
    prompt = build_repetition_fix_prompt(text, repetition_data)
    if not prompt:
        return text
    
    # Get LLM fix
    model = get_model_for_provider(provider)
    response = generate_with_retry(model, prompt, max_retries=3, api_key=api_key, step_name="Repetition Reduction", provider=provider, fallback_models=fallback_models)
    return response