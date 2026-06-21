from .api_client import search_jobs
from .scoring import score_job, score_relevance, JobScore
from .experience import compute_user_years, extract_years_required
from .cache import filter_new_jobs, mark_jobs_seen
from .query import (
    build_search_query,
    get_alternate_queries,
    dedupe_jobs,
    JSEARCH_PAGES_PER_REQUEST,
    JSEARCH_ALTERNATE_PAGES,
    JSEARCH_MAX_PAGE,
)
from .keywords import (
    build_search_queue,
    extract_profile_keywords,
    suggest_search_terms_llm,
    dedupe_case_insensitive,
)
from .search_session import (
    fetch_batch,
    get_session,
    reset_session,
    BATCH_SIZE,
)
from .text_utils import clean_job_description

__all__ = [
    "search_jobs",
    "score_relevance",
    "score_job",
    "JobScore",
    "compute_user_years",
    "extract_years_required",
    "filter_new_jobs",
    "mark_jobs_seen",
    "build_search_query",
    "get_alternate_queries",
    "dedupe_jobs",
    "JSEARCH_PAGES_PER_REQUEST",
    "JSEARCH_ALTERNATE_PAGES",
    "JSEARCH_MAX_PAGE",
    "build_search_queue",
    "extract_profile_keywords",
    "suggest_search_terms_llm",
    "dedupe_case_insensitive",
    "fetch_batch",
    "get_session",
    "reset_session",
    "BATCH_SIZE",
    "clean_job_description",
]
