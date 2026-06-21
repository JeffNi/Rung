"""Infer experience years from profile dates and job posting text (no LLM)."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_INTERNSHIP_MONTHS = 4
EXPERIENCE_CALC_VERSION = 3  # bump when logic changes (v3: inclusive months + normalize)

_INTERN_PATTERN = re.compile(
    r"\b(intern|internship|co-?op|cooperative)\b",
    re.I,
)


def _normalize_experience_map(experience: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize Firestore / legacy profile shapes into dated entry dicts."""
    if not experience:
        return {}
    if isinstance(experience, list):
        return {}
    if not isinstance(experience, dict):
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for key, entry in experience.items():
        if isinstance(entry, list):
            bullets = [b for b in entry if isinstance(b, str) and b.strip()]
            title = key
            company = ""
            if " at " in key:
                parts = key.split(" at ", 1)
                title, company = parts[0].strip(), parts[1].strip()
            out[key] = {
                "title": title,
                "company": company,
                "bullets": bullets,
                "startDate": "",
                "endDate": "",
            }
        elif isinstance(entry, dict):
            normalized = dict(entry)
            if not normalized.get("title"):
                normalized["title"] = key
            out[key] = normalized
    return out


def _entry_months(entry: Dict[str, Any]) -> float:
    """Months credited for a single experience entry."""
    if _is_year_only_same_year_intern(entry):
        return float(DEFAULT_INTERNSHIP_MONTHS)
    interval = _entry_interval(entry)
    if interval:
        return float(interval[1] - interval[0])
    return float(_estimate_months_without_dates(entry))


def compute_experience_detail(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Breakdown for debugging — months per entry and total."""
    experience = _normalize_experience_map(profile.get("experience") or {})
    projects = _normalize_experience_map(profile.get("projects") or {})

    work_rows: List[Dict[str, Any]] = []
    work_intervals: List[Tuple[int, int]] = []
    work_orphan = 0.0

    for key, entry in experience.items():
        months = _entry_months(entry)
        work_rows.append({
            "key": key,
            "title": entry.get("title", key),
            "start": entry.get("startDate", ""),
            "end": entry.get("endDate", ""),
            "months": months,
        })
        if _is_year_only_same_year_intern(entry):
            work_orphan += DEFAULT_INTERNSHIP_MONTHS
        else:
            interval = _entry_interval(entry)
            if interval:
                work_intervals.append(interval)
            elif _estimate_months_without_dates(entry) > 0:
                work_orphan += _estimate_months_without_dates(entry)

    merged_work = _merge_intervals(work_intervals)
    work_months = sum(e - s for s, e in merged_work) + work_orphan

    project_rows: List[Dict[str, Any]] = []
    project_intervals: List[Tuple[int, int]] = []
    project_orphan = 0.0

    for key, entry in projects.items():
        months = _entry_months(entry)
        project_rows.append({
            "key": key,
            "title": entry.get("title", key),
            "start": entry.get("startDate", ""),
            "end": entry.get("endDate", ""),
            "months": months,
        })
        if _is_year_only_same_year_intern(entry):
            project_orphan += DEFAULT_INTERNSHIP_MONTHS
        else:
            interval = _entry_interval(entry)
            if interval:
                project_intervals.append(interval)
            elif _estimate_months_without_dates(entry) > 0:
                project_orphan += _estimate_months_without_dates(entry)

    merged_proj = _merge_intervals(project_intervals)
    project_months = (sum(e - s for s, e in merged_proj) + project_orphan) * 0.5

    total_months = work_months + project_months
    return {
        "calc_version": EXPERIENCE_CALC_VERSION,
        "work_months": round(work_months, 1),
        "project_months": round(project_months, 1),
        "total_months": round(total_months, 1),
        "user_years": round(total_months / 12.0, 1) if total_months > 0 else 0.0,
        "work_entries": work_rows,
        "project_entries": project_rows,
    }


def parse_date(value: str) -> Optional[Tuple[int, int]]:
    """Parse a date string to (year, month). None end date means still active."""
    s = (value or "").strip().lower()
    if not s:
        return None
    if s in {"present", "current", "now", "ongoing"}:
        return None

    # ISO: YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))

    # US: MM/DD/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m:
        return int(m.group(3)), int(m.group(1))

    m = re.match(r"^(\d{4})$", s)
    if m:
        return int(m.group(1)), 1

    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.match(r"^(\d{1,2})[-/](\d{4})$", s)
    if m:
        return int(m.group(2)), int(m.group(1))

    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.match(r"^([a-z]{3,9})\s+(\d{4})$", s)
    if m:
        month = months.get(m.group(1)[:3])
        if month:
            return int(m.group(2)), month

    season_month = {
        "spring": 1, "summer": 6, "fall": 9, "autumn": 9, "winter": 12,
    }
    m = re.match(r"^(spring|summer|fall|autumn|winter)\s+(\d{4})$", s)
    if m:
        return int(m.group(2)), season_month[m.group(1)]

    return None


def _to_month_index(year: int, month: int) -> int:
    return year * 12 + month


def _months_between(
    start: Tuple[int, int],
    end: Optional[Tuple[int, int]],
) -> int:
    if end is None:
        now = datetime.now()
        end = (now.year, now.month)
    start_total = _to_month_index(start[0], start[1])
    end_total = _to_month_index(end[0], end[1])
    return max(0, end_total - start_total)


def _entry_label(entry: Dict[str, Any]) -> str:
    return f"{entry.get('title', '')} {entry.get('company', '')}"


def _looks_like_internship(entry: Dict[str, Any]) -> bool:
    return bool(_INTERN_PATTERN.search(_entry_label(entry)))


def _estimate_months_without_dates(entry: Dict[str, Any]) -> int:
    """When dates are missing, estimate duration from role type."""
    bullets = entry.get("bullets") or entry.get("achievements") or []
    if not (bullets or entry.get("title")):
        return 0
    if _looks_like_internship(entry):
        return DEFAULT_INTERNSHIP_MONTHS
    # co-op academic year default when dates unparseable
    if re.search(r"\bco-?op\b", _entry_label(entry), re.I):
        return 8
    return 0


def _is_year_only_same_year_intern(entry: Dict[str, Any]) -> bool:
    """Summer intern stored as e.g. 2023–2023 (year only) — count each separately."""
    start_raw = (entry.get("startDate") or "").strip()
    end_raw = (entry.get("endDate") or "").strip()
    if not (
        re.match(r"^\d{4}$", start_raw)
        and re.match(r"^\d{4}$", end_raw)
        and start_raw == end_raw
    ):
        return False
    return _looks_like_internship(entry)


def _entry_interval(entry: Any) -> Optional[Tuple[int, int]]:
    """Return (start_month_idx, end_month_idx) for an entry, or None if unestimated."""
    if isinstance(entry, list):
        return None
    if not isinstance(entry, dict):
        return None

    start = parse_date(entry.get("startDate", ""))
    end_raw = entry.get("endDate", "")
    end = parse_date(end_raw)

    if not start:
        return None

    start_idx = _to_month_index(start[0], start[1])

    if end is None and (end_raw or "").strip().lower() in {"", "present", "current", "now", "ongoing"}:
        now = datetime.now()
        # Exclusive end index: include the current month
        end_idx = _to_month_index(now.year, now.month) + 1
        return (start_idx, end_idx)

    if end is None:
        end_idx = _to_month_index(datetime.now().year, datetime.now().month) + 1
    else:
        # Exclusive end index so May–Aug counts 4 months (both months inclusive)
        end_idx = _to_month_index(end[0], end[1]) + 1

    if end_idx <= start_idx:
        if _looks_like_internship(entry):
            end_idx = start_idx + DEFAULT_INTERNSHIP_MONTHS
        else:
            end_idx = start_idx + 12

    return (start_idx, end_idx)


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: List[Tuple[int, int]] = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _months_from_entries(entries: Dict[str, Any], weight: float = 1.0) -> float:
    entries = _normalize_experience_map(entries)
    intervals: List[Tuple[int, int]] = []
    orphan_months = 0.0

    for entry in entries.values():
        if _is_year_only_same_year_intern(entry):
            orphan_months += DEFAULT_INTERNSHIP_MONTHS
            continue
        interval = _entry_interval(entry)
        if interval:
            intervals.append(interval)
        elif isinstance(entry, dict) and _estimate_months_without_dates(entry) > 0:
            orphan_months += _estimate_months_without_dates(entry)

    merged = _merge_intervals(intervals)
    interval_months = sum(end - start for start, end in merged)
    return (interval_months + orphan_months) * weight


def compute_user_years(profile: Dict[str, Any]) -> float:
    """Estimate years of experience from profile work history (+ half weight projects)."""
    detail = compute_experience_detail(profile)
    return detail["user_years"]


_TITLE_LEVEL_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\b(principal|staff)\b", re.I), 7.0),
    (re.compile(r"\b(director|vice president|vp)\b", re.I), 10.0),
    (re.compile(r"\b(senior|sr\.?)\b", re.I), 5.0),
    (re.compile(r"\b(lead)\b", re.I), 4.0),
    (re.compile(r"\b(mid[- ]level|intermediate)\b", re.I), 3.0),
    (re.compile(r"\b(associate)\b", re.I), 2.0),
    (re.compile(r"\b(junior|jr\.?|entry[- ]level|intern)\b", re.I), 0.0),
]

_JUNIOR_SIGNALS = re.compile(
    r"\b(new grad|new graduate|entry[- ]level|junior|internship|intern\b|0-2 years|0 to 2 years)\b",
    re.I,
)


def infer_years_from_title(title: str) -> Optional[float]:
    title_l = title or ""
    if re.search(r"\b(junior|jr\.?|entry|intern)\b", title_l, re.I):
        return 0.0
    for pattern, years in _TITLE_LEVEL_PATTERNS:
        if pattern.search(title_l):
            return years
    return None


def extract_years_required(title: str, description: str) -> Optional[float]:
    """Parse minimum years of experience from a job posting."""
    text = f"{title} {description}"
    text_l = text.lower()
    years_found: list[float] = []

    for m in re.finditer(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_l):
        years_found.append(float(m.group(1)))

    for m in re.finditer(
        r"(?:at least|minimum of|min\.?)\s*(\d+)\s*\+?\s*years?",
        text_l,
    ):
        years_found.append(float(m.group(1)))

    for m in re.finditer(r"(\d+)\+\s*years?", text_l):
        years_found.append(float(m.group(1)))

    for m in re.finditer(r"(\d+)\s+years?\s+(?:of\s+)?(?:experience|exp)\b", text_l):
        years_found.append(float(m.group(1)))

    title_years = infer_years_from_title(title)

    if _JUNIOR_SIGNALS.search(text_l):
        if years_found:
            return min(max(years_found), 2.0)
        return 0.0

    if years_found:
        return max(years_found)
    return title_years
