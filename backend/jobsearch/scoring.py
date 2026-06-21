"""Rule-based job scoring: skills, experience fit, values, seniority penalty, tier."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", (text or "").lower())


def _keyword_overlap(terms: List[str], text: str) -> float:
    """Fraction of terms found in text (0-100)."""
    if not terms:
        return 50.0

    norm_text = _normalize(text)
    text_words = set(norm_text.split())
    matched = 0
    for term in terms:
        norm_term = _normalize(term)
        if not norm_term:
            continue
        if " " in norm_term:
            if norm_term in norm_text:
                matched += 1
        elif norm_term in text_words:
            matched += 1

    return round((matched / len(terms)) * 100, 1)


def _title_alignment(search_titles: List[str], profile_title: str, job_title: str) -> float:
    """How well the job title aligns with profile targets (0-100)."""
    targets = [t for t in search_titles if (t or "").strip()]
    if profile_title and profile_title.strip():
        targets.append(profile_title.strip())
    if not targets:
        return 50.0

    job_norm = _normalize(job_title)
    if not job_norm:
        return 50.0

    best = 0.0
    for target in targets:
        target_norm = _normalize(target)
        if not target_norm:
            continue
        if target_norm in job_norm or job_norm in target_norm:
            best = max(best, 100.0)
            continue
        target_words = set(target_norm.split())
        job_words = set(job_norm.split())
        if not target_words:
            continue
        overlap = len(target_words & job_words) / len(target_words)
        best = max(best, round(overlap * 100, 1))

    return best


def score_skill_match(job: Dict[str, Any], profile: Dict[str, Any]) -> float:
    title = job.get("job_title", "") or ""
    description = job.get("job_description", "") or ""
    combined = f"{title} {description}"

    skills = profile.get("skills") or []
    courses = [c for c in (profile.get("courses") or []) if len(c) < 60]
    skill_part = _keyword_overlap(skills + courses, combined)

    title_part = _title_alignment(
        profile.get("searchTitles") or [],
        profile.get("title") or "",
        title,
    )

    return round(0.7 * skill_part + 0.3 * title_part, 1)


def score_experience_match(
    user_years: float,
    years_required: Optional[float],
) -> float:
    if years_required is None:
        return 75.0

    gap = years_required - user_years
    if gap <= 0:
        return 100.0
    if gap <= 1:
        return 85.0
    if gap <= 2:
        return 70.0
    if gap <= 3:
        return 55.0
    if gap <= 4:
        return 40.0
    return max(15.0, round(100.0 - gap * 14, 1))


def score_value_match(job: Dict[str, Any], profile: Dict[str, Any]) -> float:
    values = profile.get("values") or []
    goals = profile.get("goals") or []
    interests = profile.get("interests") or []
    terms = [t for t in values + goals + interests if (t or "").strip()]
    if not terms:
        return 50.0

    title = job.get("job_title", "") or ""
    description = job.get("job_description", "") or ""
    return _keyword_overlap(terms, f"{title} {description}")


def seniority_multiplier(
    job_title: str,
    description: str,
    years_required: Optional[float],
) -> float:
    """Reduce composite score for clearly senior postings (0.5-1.0)."""
    mult = 1.0
    title_l = (job_title or "").lower()

    if re.search(r"\b(principal|staff|director|vice president|vp)\b", title_l):
        mult *= 0.55
    elif re.search(r"\b(senior|sr\.?)\b", title_l) and not re.search(
        r"\b(junior|jr\.?)\b", title_l
    ):
        mult *= 0.72
    elif re.search(r"\b(lead)\b", title_l) and not re.search(
        r"\b(junior|jr\.?)\b", title_l
    ):
        mult *= 0.78

    if years_required is not None:
        if years_required >= 7:
            mult *= 0.60
        elif years_required >= 5:
            mult *= 0.72
        elif years_required >= 3:
            mult *= 0.88

    return round(mult, 3)


WEIGHT_SKILL = 0.50
WEIGHT_EXPERIENCE = 0.35
WEIGHT_VALUE = 0.15


@dataclass
class JobScore:
    skill_score: float
    experience_score: float
    value_score: float
    composite_score: float
    tier: str
    years_required: Optional[float]
    user_years: float
    seniority_multiplier: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "skill_score": self.skill_score,
            "experience_score": self.experience_score,
            "value_score": self.value_score,
            "relevance_score": self.composite_score,
            "tier": self.tier,
            "years_required": self.years_required,
            "user_years": self.user_years,
            "seniority_multiplier": self.seniority_multiplier,
        }


def assign_tier(
    composite: float,
    skill_score: float,
    seniority_mult: float,
) -> str:
    """
    Tier for apply effort — not eligibility.
    S/A: strong fit · B: good · C: stretch / practice · D: weak match
    """
    if composite >= 82 and seniority_mult >= 0.88 and skill_score >= 72:
        return "S"
    if composite >= 72 and seniority_mult >= 0.85:
        return "A"
    if composite >= 52 and seniority_mult >= 0.72:
        return "B"
    if composite >= 28 or skill_score >= 35:
        return "C"
    return "D"


def score_job(job: Dict[str, Any], profile: Dict[str, Any]) -> JobScore:
    from .experience import compute_user_years, extract_years_required

    title = job.get("job_title", "") or ""
    description = job.get("job_description", "") or ""

    user_years = compute_user_years(profile)
    years_required = extract_years_required(title, description)

    skill = score_skill_match(job, profile)
    experience = score_experience_match(user_years, years_required)
    value = score_value_match(job, profile)

    raw_composite = (
        WEIGHT_SKILL * skill
        + WEIGHT_EXPERIENCE * experience
        + WEIGHT_VALUE * value
    )
    seniority_mult = seniority_multiplier(title, description, years_required)
    composite = round(raw_composite * seniority_mult, 1)

    tier = assign_tier(composite, skill, seniority_mult)

    return JobScore(
        skill_score=skill,
        experience_score=experience,
        value_score=value,
        composite_score=composite,
        tier=tier,
        years_required=years_required,
        user_years=user_years,
        seniority_multiplier=seniority_mult,
    )


def score_relevance(job: Dict[str, Any], user_skills: List[str]) -> float:
    """Backward-compatible skills-only score."""
    profile = {"skills": user_skills}
    return score_skill_match(job, profile)
