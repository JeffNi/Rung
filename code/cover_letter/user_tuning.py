import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from utils import generate_with_retry, load_file
    

def make_style_extraction_prompt(sample: str) -> str:
    return f"""Your task is to analyze the writing sample below and focus exclusively on the *sentence structures* and *patterns* that reveal how the human writes naturally to generate a style profile.

Ignore the actual content, topic, tone, or style of the writing. Do not mimic vocabulary choices, figurative language, or subject matter. Instead, concentrate on characteristics like:

- Sentence length and variety (short, long, complex, simple)
- Use of punctuation and pauses (commas, dashes, periods)
- Rhythm and flow of sentences
- How sentences start and end
- Typical phrasing patterns and connectors (e.g., use of "and", "but", "however")

Your goal is to summarize how a *real human* structures their writing at the sentence and paragraph level, so that a chatbot can emulate *human-like sentence flow and natural writing patterns* in cover letters — without copying the content style, tone, or vocabulary of the sample.

Then, based on this, write a system prompt for a chatbot to generate cover letters that:

- Use natural, human-like sentence structures and flow as described
- Avoid AI clichés, robotic or repetitive phrasing
- Are clear, professional, and appropriate for job applications
- Match the user's voice in terms of sentence rhythm and flow, but use vocabulary and tone suited to cover letters
- Focus on sounding genuinely human, not overly formal, literary, or exaggerated
- Return only the style guide

WRITING SAMPLE:

{sample}
"""  

def humanify_prompt(writing_sample, cover_letter):
    return f"""You are an expert writing assistant that rewrites AI-generated content to sound distinctly human, while preserving the original meaning.

Below is a sample of a person's real writing style, followed by an AI-generated cover letter. Your task is to rewrite the cover letter in the style of the writing sample, while avoiding common patterns that reveal AI authorship.

---

**WRITING SAMPLE**  
(This is a real sample of the user’s writing. Match its tone, rhythm, sentence structure, and style.)

{writing_sample}

---

**AI-GENERATED COVER LETTER**  
(This contains all the content that must be preserved — facts, achievements, tone of intent — but it sounds AI-generated.)

{cover_letter}

---

**REWRITE INSTRUCTIONS**

- **Do NOT change the meaning or content.**
- **Do NOT remove accomplishments or technical terms.**
- **Make it sound like the writing sample.**
- **Use natural variation in sentence length and structure.**
- Avoid generic phrases like "I am excited to apply", "I believe I am a strong fit", or "Throughout my career..."
- Avoid overly formal or robotic tone — write like a thoughtful, confident human.
- Use contractions, analogies, humor, or informal transitions if present in the writing sample.
- Add subtle voice markers like “to be honest,” “what drew me in,” “I’ve always had a thing for...”, etc. if they match the sample.
- Aim to make it pass AI detectors like GPTZero or Originality.ai.

Avoid common signs of AI-generated text:
- No double dashes `--` or em-dashes `—`; use commas, colons, or semicolons instead
- No curly quotes (“ ”); use straight quotes (if applicable)
- Vary sentence lengths and structure — no robotic pacing
- Remove cliches like “I am excited to apply” or “I believe I’m a strong fit”
- Avoid overly formal tone — natural, confident, personal is better
- Use contractions and voice cues if they fit the style (e.g. "I'm", "I've", "honestly", "what drew me in", etc.)
- Don’t overuse transition phrases like “Furthermore”, “In addition”, etc.
- Keep formatting natural: no bullet points, no excessive line breaks, no weird spacing

---

Now return only the final rewritten version of the cover letter — no explanation or commentary.

    """

def personalize_prompt(style, sample, cover_letter):
    return f"""I need your help refining my cover letter to personalize it with my writing style. I will give you a description of my writings style, a sample of my writing and the cover letter to refine.

**DO NOT ADD OR CHANGE INFORMATION IN THE COVER LETTER**
Return only the finished cover letter

**WRITING STYLE DESCRIPTION**
{style}

**WRITING SAMPLE**
{sample}

**COVER LETTER TO EDIT**
{cover_letter}
"""


def generate_style_prompt():
    dotenv_path = Path("../.env")
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    sample = load_file()
    prompt = make_style_extraction_prompt(sample)

    model = "gemini-2.0-flash"
    new_prompt = generate_with_retry(model, prompt, max_retries=1)
    return new_prompt

def personalize(style):
    dotenv_path = Path("../.env")
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    sample = load_file()
    cl = load_file("outputs/cover_letter.txt")
    sample = load_file("inputs/writing_sample.txt")
    prompt = personalize_prompt(style, sample, cl)

    model = "gemini-2.5-flash-preview-05-20"
    new_prompt = generate_with_retry(model, prompt, max_retries=1)
    return new_prompt


def main():
    print(personalize())

if __name__ == "__main__":
    main()