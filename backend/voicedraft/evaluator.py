import os
from pathlib import Path
from utils import generate_with_retry, load_file

def generate_review_prompt(cl, eval_yaml):
    return """You are a critical reviewer of professional cover letters. Evaluate the following letter for clarity, relevance, tone, specificity, and persuasiveness. Respond in YAML format following the schema below:
{eval_yaml}

Here is the cover letter:
{cl}

Guidelines:

Give a score from 1 to 10, where:

9–10 = exceptional, polished, job-ready

7–8 = strong, with minor improvements needed

5–6 = average, noticeable issues to fix

below 5 = poor, needs major revision

If the score is 7 or higher, omit the issues list or leave it empty. Just give a concise overall_comment.

If the score is below 7, include detailed issues with:

paragraph: index starting at 0

problem: specific weakness or flaw

suggestion: how to fix it clearly

Do not rewrite the letter or include your reasoning outside of the YAML."""

def generate_comparison_prompt(cl1, eval1, cl2, eval2):
    return f"""You are a critical reviewer comparing two cover letters for the same job. Each letter has already been professionally evaluated for clarity, relevance, tone, specificity, and persuasiveness.

Use the evaluator feedback and your own judgment to determine which letter is better.

Respond with a single number:
- **0** if the first letter is better
- **1** if the second letter is better

Do not explain your reasoning or include any other text.

Evaluation of Letter 1:
{eval1}

Evaluation of Letter 2:
{eval2}

Cover Letter 1:
{cl1}

Cover Letter 2:
{cl2}
"""


def evaluate_cl(cl, api_key=None):
    base_dir = Path(__file__).parent
    eval_yaml_path = str(base_dir / "inputs" / "evaluation.yaml")
    eval_yaml = load_file(eval_yaml_path)
    prompt = generate_review_prompt(cl, eval_yaml)

    model = "gemini-2.5-flash-preview-05-20"
    response = generate_with_retry(model, prompt, max_retries=1, api_key=api_key)

    outputs_dir = base_dir / "outputs"
    os.makedirs(outputs_dir, exist_ok=True)
    output_path = outputs_dir / "feedback.yaml"

    with open(str(output_path), "w", encoding="utf-8") as f:
        f.write(response)
    return response


def compare_cls(cl1, eval1, cl2, eval2, api_key=None):
    prompt = generate_comparison_prompt(cl1, eval1, cl2, eval2)
    model = "gemini-2.5-flash-preview-05-20"
    response = generate_with_retry(model, prompt, max_retries=1, api_key=api_key)
    return response