from typing import List, Dict, Any

# Per-user set of job IDs already returned. Cleared on server restart.
_seen_job_ids_by_user: Dict[str, set] = {}


def _seen_for_user(user_id: str) -> set:
    key = user_id or "_anonymous"
    if key not in _seen_job_ids_by_user:
        _seen_job_ids_by_user[key] = set()
    return _seen_job_ids_by_user[key]


def filter_new_jobs(jobs: List[Dict[str, Any]], user_id: str = "") -> List[Dict[str, Any]]:
    """Return only jobs whose job_id has NOT been seen before for this user."""
    seen = _seen_for_user(user_id)
    return [job for job in jobs if job.get("job_id") not in seen]


def mark_jobs_seen(jobs: List[Dict[str, Any]], user_id: str = "") -> None:
    """Mark the given jobs as seen so they are filtered out on the user's next search."""
    seen = _seen_for_user(user_id)
    for job in jobs:
        job_id = job.get("job_id")
        if job_id:
            seen.add(job_id)
