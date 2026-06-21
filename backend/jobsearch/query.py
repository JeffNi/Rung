import re
from typing import List, Dict, Any

# JSearch returns up to 10 jobs per page; num_pages caps at 50.
JSEARCH_PAGES_PER_REQUEST = 10
JSEARCH_ALTERNATE_PAGES = 5
JSEARCH_MAX_PAGE = 50


def build_search_query(title: str, skills: List[str]) -> str:
    """
    Build a short JSearch query string.

    JSearch often returns zero results when the query packs in title + many skills.
    Use the job title for the API query; skills are used separately for relevance scoring.
    """
    cleaned_title = (title or "").strip()
    if cleaned_title:
        return cleaned_title

    for skill in skills:
        cleaned = (skill or "").strip()
        if cleaned:
            return cleaned

    return "software engineer"


def get_alternate_queries(title: str, skills: List[str], primary: str) -> List[str]:
    """Return up to 2 broader alternate queries for the first search batch."""
    alternates: List[str] = []
    primary_l = primary.lower()

    if re.search(r"\bml\b", primary_l) and "machine learning" not in primary_l:
        if "engineer" in primary_l:
            alternates.append("machine learning engineer")
        elif "scientist" in primary_l:
            alternates.append("machine learning scientist")
        else:
            expanded = re.sub(r"\bML\b", "machine learning", primary, flags=re.IGNORECASE)
            if expanded.lower() != primary_l:
                alternates.append(expanded)

    seen = {primary_l}
    unique: List[str] = []
    for query in alternates:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            unique.append(query)
    return unique[:2]


def dedupe_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_ids: set = set()
    unique: List[Dict[str, Any]] = []
    for job in jobs:
        job_id = job.get("job_id")
        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        unique.append(job)
    return unique
