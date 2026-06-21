from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from .api_client import search_jobs
from .keywords import build_search_queue
from .query import JSEARCH_MAX_PAGE

BATCH_SIZE = 100
MANUAL_NUM_PAGES = 10
KEYWORD_NUM_PAGES = 5

_sessions: Dict[str, "SearchSession"] = {}


@dataclass
class TermLedger:
    next_page: int = 1
    exhausted: bool = False


@dataclass
class SearchSession:
    fetch_ledger: Set[Tuple[str, int, int]] = field(default_factory=set)
    term_ledgers: Dict[str, TermLedger] = field(default_factory=dict)
    api_calls: int = 0


def _session_key(user_id: str) -> str:
    return user_id or "_anonymous"


def get_session(user_id: str) -> SearchSession:
    key = _session_key(user_id)
    if key not in _sessions:
        _sessions[key] = SearchSession()
    return _sessions[key]


def reset_session(user_id: str) -> SearchSession:
    key = _session_key(user_id)
    session = SearchSession()
    _sessions[key] = session
    return session


def _ledger_key(query: str, page: int, num_pages: int) -> Tuple[str, int, int]:
    return (query.lower().strip(), page, num_pages)


def _has_more_capacity(session: SearchSession, queue: List[Tuple[str, str]]) -> bool:
    for term, _ in queue:
        ledger = session.term_ledgers.get(term)
        if ledger is None or not ledger.exhausted:
            return True
    return False


def fetch_batch(
    session: SearchSession,
    profile: Dict[str, Any],
    seen_job_ids: Set[str],
    date_posted: str = "week",
    location: str = "",
) -> Tuple[List[Dict[str, Any]], int, int, bool, int]:
    """
    Fetch up to BATCH_SIZE jobs not in seen_job_ids.
    Returns (jobs, total_from_api, total_skipped_seen, has_more, api_calls_this_batch).
    """
    queue = build_search_queue(profile)
    if not queue:
        return [], 0, 0, False, 0

    calls_at_start = session.api_calls

    batch: List[Dict[str, Any]] = []
    batch_ids: Set[str] = set()
    total_from_api = 0
    total_skipped_seen = 0

    for term, kind in queue:
        ledger = session.term_ledgers.get(term)
        if ledger is None:
            ledger = TermLedger()
            session.term_ledgers[term] = ledger
        if ledger.exhausted:
            continue

        num_pages = MANUAL_NUM_PAGES if kind == "manual" else KEYWORD_NUM_PAGES

        while len(batch) < BATCH_SIZE and not ledger.exhausted:
            page = ledger.next_page
            key = _ledger_key(term, page, num_pages)
            if key in session.fetch_ledger:
                ledger.next_page += num_pages
                if ledger.next_page > JSEARCH_MAX_PAGE:
                    ledger.exhausted = True
                continue

            session.fetch_ledger.add(key)
            session.api_calls += 1

            try:
                jobs = search_jobs(
                    query=term,
                    location=location,
                    page=page,
                    num_pages=num_pages,
                    date_posted=date_posted,
                )
            except Exception as e:
                print(f"[JOBSEARCH] API error for '{term}' page {page}: {e}")
                ledger.exhausted = True
                break

            if not jobs:
                ledger.exhausted = True
                break

            total_from_api += len(jobs)
            ledger.next_page += num_pages
            if ledger.next_page > JSEARCH_MAX_PAGE:
                ledger.exhausted = True

            for job in jobs:
                jid = job.get("job_id")
                if not jid:
                    continue
                if jid in seen_job_ids:
                    total_skipped_seen += 1
                    continue
                if jid in batch_ids:
                    continue
                job["_search_term"] = term
                batch.append(job)
                batch_ids.add(jid)

            if len(batch) >= BATCH_SIZE:
                break

        if len(batch) >= BATCH_SIZE:
            break

    batch.sort(key=lambda j: j.get("job_posted_at_datetime_utc") or "", reverse=True)
    batch = batch[:BATCH_SIZE]

    if len(batch) < BATCH_SIZE and not _has_more_capacity(session, queue):
        has_more = False
    else:
        has_more = _has_more_capacity(session, queue)

    return batch, total_from_api, total_skipped_seen, has_more, session.api_calls - calls_at_start
