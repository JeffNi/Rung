"""Legacy module — skill overlap scoring lives in scoring.py."""

from .scoring import score_relevance, score_skill_match

__all__ = ["score_relevance", "score_skill_match"]
