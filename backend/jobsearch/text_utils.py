import re
from html import unescape


def clean_job_description(text: str) -> str:
    """Strip HTML and normalize whitespace from JSearch job descriptions."""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    cleaned = unescape(text)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</p\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</div\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</li\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<li[^>]*>", "- ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = unescape(cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()
