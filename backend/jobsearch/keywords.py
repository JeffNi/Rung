import json
import re
from typing import Any, Dict, List, Tuple

MAX_EXTRACTED_CANDIDATES = 20
MAX_TERM_LEN = 50
MAX_LLM_TERMS = 15

_SKIP_TOKENS = frozenset({
    "a", "an", "the", "and", "or", "for", "to", "in", "on", "at", "by", "with",
    "from", "as", "is", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "did", "will", "would", "can", "could", "should", "may", "might",
    "i", "we", "you", "they", "he", "she", "it", "my", "our", "your", "their",
    "this", "that", "these", "those", "not", "but", "if", "than", "then", "so",
    "of", "all", "also", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again", "further", "once",
})


def dedupe_case_insensitive(terms: List[str]) -> List[str]:
    seen: set = set()
    unique: List[str] = []
    for term in terms:
        cleaned = " ".join((term or "").strip().split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            unique.append(cleaned[:MAX_TERM_LEN])
    return unique


def _entry_texts(entry: Any) -> List[str]:
    if isinstance(entry, list):
        return [str(b) for b in entry]
    if isinstance(entry, dict):
        parts: List[str] = []
        parts.extend(entry.get("bullets", []) or [])
        ctx = entry.get("context", "") or ""
        if ctx:
            parts.append(str(ctx))
        return [str(p) for p in parts if p]
    return []


def tokenize_keywords(text: str) -> List[str]:
    if not text:
        return []
    tokens: List[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]*", text):
        word = raw.strip("-./")
        if len(word) < 3 or word.lower() in _SKIP_TOKENS:
            continue
        tokens.append(word)
    return tokens


def extract_profile_keywords(profile: Dict[str, Any]) -> List[str]:
    terms: List[str] = []
    terms.extend(profile.get("skills", []) or [])
    terms.extend(profile.get("skillsToLearn", []) or [])
    terms.extend(profile.get("courses", []) or [])

    for entry in (profile.get("experience", {}) or {}).values():
        for text in _entry_texts(entry):
            terms.extend(tokenize_keywords(text))

    for entry in (profile.get("projects", {}) or {}).values():
        for text in _entry_texts(entry):
            terms.extend(tokenize_keywords(text))

    return dedupe_case_insensitive(terms)[:MAX_EXTRACTED_CANDIDATES]


def build_search_queue(profile: Dict[str, Any]) -> List[Tuple[str, str]]:
    manual = dedupe_case_insensitive(profile.get("searchTitles", []) or [])
    llm = dedupe_case_insensitive(profile.get("llmSearchTerms", []) or [])
    rule = dedupe_case_insensitive(extract_profile_keywords(profile))

    seen: set = set()
    queue: List[Tuple[str, str]] = []
    for term, kind in (
        [(t, "manual") for t in manual]
        + [(t, "llm") for t in llm]
        + [(t, "rule") for t in rule]
    ):
        key = term.lower()
        if key and key not in seen:
            seen.add(key)
            queue.append((term, kind))
    return queue


def validate_llm_terms(raw_terms: List[str]) -> List[str]:
    cleaned: List[str] = []
    for term in raw_terms:
        if not isinstance(term, str):
            continue
        t = " ".join(term.strip().split())
        if not t or len(t) > MAX_TERM_LEN:
            continue
        if "," in t and len(t.split()) > 4:
            continue
        cleaned.append(t)
    return dedupe_case_insensitive(cleaned)[:MAX_LLM_TERMS]


def suggest_search_terms_llm(
    profile: Dict[str, Any],
    api_key: str,
    provider: str = "gemini",
) -> List[str]:
    """Generate hidden search terms from profile via LLM. Returns empty on failure."""
    if not api_key:
        return []

    from utils import generate_with_retry

    skills = profile.get("skills", []) or []
    goals = profile.get("goals", []) or []
    experience_titles = []
    for key, entry in (profile.get("experience", {}) or {}).items():
        if isinstance(entry, dict):
            experience_titles.append(entry.get("title", key))
        else:
            experience_titles.append(key)

    prompt = f"""You help generate short job search keywords for Google Jobs API.

Profile summary:
- Resume title: {profile.get("title", "")}
- Skills: {", ".join(skills[:15])}
- Goals: {", ".join(goals[:5])}
- Experience titles: {", ".join(experience_titles[:8])}
- Skills to learn: {", ".join((profile.get("skillsToLearn", []) or [])[:8])}
- Manual search titles (do not duplicate): {", ".join((profile.get("searchTitles", []) or [])[:8])}

Return ONLY valid JSON with this shape:
{{"role_titles": ["short role name"], "keywords": ["short keyword"]}}

Rules:
- Max 15 strings total across both arrays
- Each string <= 50 characters
- Single concepts only (no comma lists, no "Python, TensorFlow, Pandas")
- Alternate job titles and niche tech keywords the user might search
- Do not repeat manual search titles listed above
"""

    model = "llama-3.3-70b-versatile" if provider == "groq" else "gemini-2.5-flash"
    try:
        response = generate_with_retry(
            model,
            prompt,
            max_retries=2,
            api_key=api_key,
            step_name="Search term suggestions",
            provider=provider,
        )
        text = response.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        terms: List[str] = []
        terms.extend(data.get("role_titles", []) or [])
        terms.extend(data.get("keywords", []) or [])
        return validate_llm_terms(terms)
    except Exception as e:
        print(f"[KEYWORDS] LLM suggest failed: {e}")
        return []
