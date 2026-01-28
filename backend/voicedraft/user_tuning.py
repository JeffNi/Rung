import os
from pathlib import Path
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
    return f"""Rewrite this AI-generated cover letter to sound like a confident, articulate human wrote it, matching the voice and rhythm of the writing sample provided.

**WRITING SAMPLE** (match the voice, rhythm, and natural phrasing—NOT the content or topic):
{writing_sample}

**COVER LETTER TO REWRITE**:
{cover_letter}

**REQUIREMENTS**:

1. **Preserve all facts, achievements, and technical content**—just change how they're expressed
2. **Match the writing sample's voice**: sentence rhythm, natural phrasing, level of formality
3. **Remove AI tells**:
   - No hedging: delete "I think," "I believe," "kind of," "really," "just"
   - No bloat: remove "my whole thing is," "is all about," "I'm keen to," "dive into"
   - No generic phrases: "excited to apply," "strong fit," "throughout my career"
   - No em-dashes (—), use commas/periods. No curly quotes
   - No corporate buzzwords: "leverage," "synergies," "dynamic," "passionate"
   
4. **Make it direct and confident**:
   - "At X, I built Y that achieved Z" not "I think my experience building Y shows..."
   - Start sentences differently—not always with "I"
   - Mix short and long sentences
   
5. **Add natural voice markers** (ONLY if they match the writing sample):
   - Strategic contractions (I'm, I've, that's)
   - Occasional informal transitions that fit the sample's style
   - Personal touches that match the sample's personality

6. **Professional but human**: This is a job application, so keep it professional. But make it sound like a competent person wrote it, not a robot.

Return only the rewritten cover letter—no explanations, no commentary.
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
    sample = load_file()
    prompt = make_style_extraction_prompt(sample)

    model = "models/gemini-2.5-flash"
    new_prompt = generate_with_retry(model, prompt, max_retries=1)
    return new_prompt

def personalize(style):
    sample = load_file()
    cl = load_file("outputs/cover_letter.txt")
    sample = load_file("inputs/writing_sample.txt")
    prompt = personalize_prompt(style, sample, cl)

    model = "models/gemini-2.5-flash"
    new_prompt = generate_with_retry(model, prompt, max_retries=1)
    return new_prompt


def main():
    style = generate_style_prompt()
    print(personalize(style))

if __name__ == "__main__":
    main()