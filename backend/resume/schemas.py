"""Data schemas for resume generation pipeline."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AttainabilityLevel(Enum):
    EXACT_MATCH = "exact_match"  # User has this skill
    RELATED = "related"          # User has similar skill (can hallucinate)
    UNATTAINABLE = "unattainable"  # Would require lying (years experience, degree)


@dataclass
class SkillRequirement:
    skill: str
    level: str  # required, preferred, bonus
    attainability: AttainabilityLevel
    user_has: bool
    related_skills: List[str] = field(default_factory=list)


@dataclass
class JobExtraction:
    must_have_skills: List[SkillRequirement] = field(default_factory=list)
    nice_to_have_skills: List[SkillRequirement] = field(default_factory=list)
    unattainable_requirements: List[str] = field(default_factory=list)
    seniority_level: str = "unknown"  # entry, mid, senior, staff
    key_responsibilities: List[str] = field(default_factory=list)
    company_values: List[str] = field(default_factory=list)
    industry: str = ""


@dataclass
class ExperienceSelection:
    experience_id: str
    title: str
    relevance_score: float  # 0-1
    keywords_covered: List[str]
    dotjots: List[str] = field(default_factory=list)
    should_include: bool = False


@dataclass
class TitleSuggestion:
    original: str
    suggested: str
    reason: str

@dataclass
class SkillsStrategy:
    front_load: List[str] = field(default_factory=list)  # Must-have keywords to put first in skills
    add: List[str] = field(default_factory=list)  # Keywords to add to skills section
    keep: List[str] = field(default_factory=list)  # Existing skills to keep (relevant)
    deprioritize: List[str] = field(default_factory=list)  # Existing skills to move to end or drop

@dataclass
class ResumeStrategy:
    selected_experiences: List[ExperienceSelection] = field(default_factory=list)
    selected_projects: List[ExperienceSelection] = field(default_factory=list)
    keyword_gaps: List[str] = field(default_factory=list)  # Missing must-haves
    suggested_skill_additions: List[str] = field(default_factory=list)  # Related skills to add
    skills_strategy: Optional[SkillsStrategy] = None
    title_suggestions: List[TitleSuggestion] = field(default_factory=list)
    ai_bullets_to_save: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)  # {job_id: {exp_title: [bullets]}}


@dataclass
class ReviewIssue:
    check_name: str
    severity: str  # error, warning
    message: str
    location: Optional[str] = None  # Which section
    suggestion: Optional[str] = None


@dataclass
class ResumeReview:
    passed: bool
    issues: List[ReviewIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Specific metrics
    page_count: float = 0.0
    experience_count: int = 0
    quantification_percentage: float = 0.0
    keyword_coverage: float = 0.0


@dataclass
class ResumeDraft:
    latex_source: str
    pdf_path: Optional[str] = None
    compilation_success: bool = False
    compilation_errors: List[str] = field(default_factory=list)




@dataclass
class ResumePipelineResult:
    extraction: Any  # KeywordExtractionResult from extractor
    strategy: ResumeStrategy
    draft: ResumeDraft
    review: ResumeReview
    iterations: int = 0
    final_pdf_path: Optional[str] = None
