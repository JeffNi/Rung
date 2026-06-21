import os
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
JSEARCH_HOST = "jsearch.p.rapidapi.com"


def search_jobs(
    query: str,
    location: str = "",
    page: int = 1,
    num_pages: int = 1,
    date_posted: str = "all",
) -> List[Dict[str, Any]]:
    """
    Query JSearch via RapidAPI and return a list of job listings.

    Args:
        query: Search query (e.g. "Python software engineer")
        location: Location filter (e.g. "United States" or "Remote")
        page: Page number (1-based)
        num_pages: Number of pages to fetch (max ~5 per RapidAPI docs)
        date_posted: "all", "today", "3days", "week", "month"

    Returns:
        List of raw job dicts from JSearch.
    """
    load_dotenv(_ENV_PATH, override=True)
    api_key = os.getenv("JSEARCH_API_KEY", "")
    print(f"[JSEARCH] __file__={__file__} | ENV path: {_ENV_PATH} | exists: {_ENV_PATH.exists()} | key_len: {len(api_key)}")
    if not api_key:
        raise RuntimeError("JSEARCH_API_KEY not set in environment")

    url = f"https://{JSEARCH_HOST}/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": JSEARCH_HOST,
    }
    params = {
        "query": query,
        "page": str(page),
        "num_pages": str(num_pages),
        "date_posted": date_posted,
        "country": "us",
    }
    if location:
        params["location"] = location

    response = requests.get(url, headers=headers, params=params, timeout=90)
    response.raise_for_status()
    data = response.json()

    # JSearch returns {"data": [...]}
    jobs = data.get("data", []) if isinstance(data, dict) else []
    return jobs
