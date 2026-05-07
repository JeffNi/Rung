"""Review compiled resume for quality, length, hallucinations, and quantification."""
import os
import sys
import re
from typing import List, Dict, Set, Tuple
from schemas import (
    ResumeReview, ReviewIssue, ResumeDraft, ResumeStrategy, JobExtraction
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coverletter.utils import generate_with_retry
from coverletter.provider_config import get_model_for_provider, get_fallback_models


def review_resume(
    draft: ResumeDraft,
    strategy: ResumeStrategy,
    job_extraction: JobExtraction,
    user_profile: dict,
    api_key: str,
    provider: str = "gemini"
) -> ResumeReview:
    """
    Comprehensive resume review:
    - Length check (≤ 2 pages)
    - Experience count (≥ 2 work experiences)
    - Hallucination guard (no fake claims)
    - Quantification check (% of bullets with numbers)
    - Keyword coverage (% of must-haves present)
    """
    print("[REVIEWER] Reviewing resume...")
    
    review = ResumeReview(passed=True)
    issues: List[ReviewIssue] = []
    
    # 1. Length Check
    length_issue = check_length(draft)
    if length_issue:
        issues.append(length_issue)
    
    # 2. Experience Count Check
    exp_count, exp_issue = check_experience_count(strategy, draft)
    review.experience_count = exp_count
    if exp_issue:
        issues.append(exp_issue)
    
    # 3. Hallucination Guard
    hallucination_issues = check_hallucinations(
        draft, user_profile, api_key, provider
    )
    issues.extend(hallucination_issues)
    
    # 4. Quantification Check
    quant_pct, quant_issue = check_quantification(draft, strategy)
    review.quantification_percentage = quant_pct
    if quant_issue:
        issues.append(quant_issue)
    
    # 5. Keyword Coverage
    coverage, coverage_issue = check_keyword_coverage(draft, job_extraction)
    review.keyword_coverage = coverage
    if coverage_issue:
        issues.append(coverage_issue)
    
    # Compile review
    review.issues = issues
    
    # Determine pass/fail
    errors = [i for i in issues if i.severity == 'error']
    review.passed = len(errors) == 0
    
    review.metrics = {
        'page_count': estimate_page_count_from_latex(draft.latex_source),
        'experience_count': review.experience_count,
        'quantification_pct': review.quantification_percentage,
        'keyword_coverage': review.keyword_coverage,
        'total_issues': len(issues),
        'errors': len(errors)
    }
    
    print(f"[REVIEWER] {len(issues)} issues found ({len(errors)} errors)")
    print(f"[REVIEWER] Keyword coverage: {coverage:.0%}, Quantification: {quant_pct:.0%}")
    
    return review


def check_length(draft: ResumeDraft) -> Optional[ReviewIssue]:
    """Check if resume is ≤ 2 pages."""
    page_count = estimate_page_count_from_latex(draft.latex_source)
    
    if page_count > 2.0:
        return ReviewIssue(
            check_name="Length Check",
            severity="error",
            message=f"Resume is {page_count:.1f} pages. Must be ≤ 2 pages.",
            suggestion="Remove 1-2 experiences or shorten bullet points. Focus on most relevant roles."
        )
    elif page_count > 1.8:
        return ReviewIssue(
            check_name="Length Check",
            severity="warning",
            message=f"Resume is {page_count:.1f} pages. Getting close to limit.",
            suggestion="Consider condensing bullets if content grows."
        )
    
    return None


def check_experience_count(
    strategy: ResumeStrategy,
    draft: ResumeDraft
) -> Tuple[int, Optional[ReviewIssue]]:
    """Check if at least 2 work experiences are listed."""
    included_exps = sum(1 for e in strategy.selected_experiences if e.should_include)
    
    if included_exps < 2:
        return included_exps, ReviewIssue(
            check_name="Experience Count",
            severity="error",
            message=f"Only {included_exps} work experience(s) listed. Need at least 2.",
            suggestion="Add another relevant experience to your profile, or include academic projects/internships."
        )
    
    return included_exps, None


def check_hallucinations(
    draft: ResumeDraft,
    user_profile: dict,
    api_key: str,
    provider: str
) -> List[ReviewIssue]:
    """
    Check for hallucinated claims not in user profile.
    This is the critical integrity check.
    """
    issues = []
    latex_source = draft.latex_source
    
    # Extract all bullet points from resume
    bullet_pattern = r'\\resumeItem\{([^}]+)\}'
    bullets = re.findall(bullet_pattern, latex_source)
    
    # Get user's verified facts
    verified_experiences = user_profile.get("experience", {})
    verified_projects = user_profile.get("projects", {})
    verified_skills = set(user_profile.get("skills", []))
    
    # Build verification corpus
    verification_corpus = []
    for company, achievements in verified_experiences.items():
        verification_corpus.append(company)
        verification_corpus.extend(achievements)
    for project, details in verified_projects.items():
        verification_corpus.append(project)
        verification_corpus.extend(details)
    
    verification_text = "\n".join(verification_corpus)
    
    # Check each bullet for hallucinations
    for bullet in bullets:
        # Look for suspicious patterns
        suspicious_patterns = [
            r'\d+%',  # Percentages (might be made up)
            r'\$[\d,]+',  # Dollar amounts
            r'increased [\w\s]+ by \d+',  # Specific improvement claims
            r'reduced [\w\s]+ by \d+',
            r'led [\w\s]+ of \d+',  # Team size claims
            r'managed \$?[\d,]+',  # Budget claims
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, bullet, re.IGNORECASE):
                # Verify this claim is substantiated in original profile
                if not verify_claim(bullet, verification_text, api_key, provider):
                    issues.append(ReviewIssue(
                        check_name="Hallucination Guard",
                        severity="error",
                        message=f"Potentially fabricated claim: '{bullet[:60]}...'",
                        location=bullet[:40],
                        suggestion="Remove specific metric or verify it's in your original profile."
                    ))
                    break  # One issue per bullet
    
    return issues


def verify_claim(bullet: str, verification_text: str, api_key: str, provider: str) -> bool:
    """
    Use LLM to verify if a claim is substantiated in the original profile.
    Returns True if claim appears legitimate.
    """
    prompt = f"""Verify if this resume bullet point is supported by the original profile text.

RESUME BULLET:
{bullet}

ORIGINAL PROFILE TEXT:
{verification_text[:2000]}  # Truncate for efficiency

Is the bullet point's claim (especially any numbers, percentages, or metrics) directly supported by the original text?

Respond with only TRUE or FALSE.
- TRUE if the metric/claim is in the original or is a reasonable interpretation
- FALSE if the bullet introduces specific numbers not mentioned anywhere"""

    try:
        model = get_model_for_provider(provider)
        response = generate_with_retry(model, prompt, api_key=api_key, provider=provider, step_name="Verify Bullet")
        return "TRUE" in response.upper()
    except:
        # Default to suspicious if verification fails
        return False


def check_quantification(
    draft: ResumeDraft,
    strategy: ResumeStrategy
) -> Tuple[float, Optional[ReviewIssue]]:
    """
    Check what percentage of bullets have quantified impact.
    Good resumes have 40-60% quantified bullets.
    """
    # Extract all bullets
    bullet_pattern = r'\\resumeItem\{([^}]+)\}'
    bullets = re.findall(bullet_pattern, draft.latex_source)
    
    if not bullets:
        return 0.0, ReviewIssue(
            check_name="Quantification",
            severity="error",
            message="No bullet points found in resume.",
            suggestion="Add experience entries with bullet points."
        )
    
    # Count quantified bullets
    quantified_patterns = [
        r'\d+%',
        r'\d+ users',
        r'\d+ customers',
        r'\$[\d,]+',
        r'\d+ [\w\s]+ (million|billion|thousand)',
        r'\d+x',
        r'\d+ teams',
        r'\d+ engineers',
        r'increased [\w\s]+ by',
        r'decreased [\w\s]+ by',
        r'reduced [\w\s]+ by',
        r'improved [\w\s]+ by',
    ]
    
    quantified_count = 0
    for bullet in bullets:
        for pattern in quantified_patterns:
            if re.search(pattern, bullet, re.IGNORECASE):
                quantified_count += 1
                break
    
    percentage = quantified_count / len(bullets)
    
    if percentage < 0.3:
        return percentage, ReviewIssue(
            check_name="Quantification",
            severity="warning",
            message=f"Only {percentage:.0%} of bullets have quantified impact. Aim for 40-60%.",
            suggestion="Add metrics where possible: team size, users affected, time saved, % improvement."
        )
    
    return percentage, None


def check_keyword_coverage(
    draft: ResumeDraft,
    job_extraction: JobExtraction
) -> Tuple[float, Optional[ReviewIssue]]:
    """Check what percentage of must-have keywords are present."""
    latex_lower = draft.latex_source.lower()
    
    # Get must-have skills that are attainable
    must_haves = [
        s.skill.lower() for s in job_extraction.must_have_skills
        if s.attainability in ['exact_match', 'related']  # Skip unattainable
    ]
    
    if not must_haves:
        return 1.0, None
    
    matched = 0
    for keyword in must_haves:
        if keyword in latex_lower:
            matched += 1
    
    coverage = matched / len(must_haves)
    
    if coverage < 0.5:
        return coverage, ReviewIssue(
            check_name="Keyword Coverage",
            severity="error",
            message=f"Only {coverage:.0%} of must-have keywords present ({matched}/{len(must_haves)}).",
            suggestion="Add missing keywords to skills section or incorporate into experience bullets."
        )
    elif coverage < 0.7:
        return coverage, ReviewIssue(
            check_name="Keyword Coverage",
            severity="warning",
            message=f"{coverage:.0%} keyword coverage. Consider adding more relevant keywords.",
            suggestion=f"Missing keywords: {', '.join([k for k in must_haves if k not in latex_lower][:3])}"
        )
    
    return coverage, None


def estimate_page_count_from_latex(latex_source: str) -> float:
    """Estimate page count from LaTeX source."""
    # Remove LaTeX commands for rough char count
    text_only = re.sub(r'\\[a-zA-Z]+\*?(\{[^}]*\})*(\[[^\]]*\])*', '', latex_source)
    text_only = re.sub(r'[{}\\]', '', text_only)
    
    # ~2500 chars per page for dense resume
    return len(text_only) / 2500
