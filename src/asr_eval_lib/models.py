from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Utterance:
    """One reference or hypothesis utterance."""

    utterance_id: str
    text: str


@dataclass(frozen=True)
class EvaluationProfile:
    """Language, transcript type, notation, and GLM settings for an evaluation."""

    language: str
    transcript_type: str
    notation: Optional[str]
    glm_path: Optional[Path]
    default_metrics: Tuple[str, ...]
    lowercase: bool = True
    remove_punctuation: bool = True
    preserve_apostrophes: bool = True
    include_space_tokens_for_cer: bool = False

    @property
    def name(self) -> str:
        parts = [self.language, self.transcript_type]
        if self.notation:
            parts.append(self.notation)
        return "-".join(parts)


@dataclass(frozen=True)
class Score:
    """Aggregate SCLITE score for one metric."""

    metric: str
    unit: str
    sentences: int
    reference_units: int
    correct: int
    substitutions: int
    deletions: int
    insertions: int
    errors: int
    sentence_errors: int
    rate: float
    sentence_error_rate: float


@dataclass(frozen=True)
class EvaluationResult:
    """Scores and generated-report location for one evaluation run."""

    profile: EvaluationProfile
    scores: Mapping[str, Score]
    reports_dir: Optional[Path]
    commands: Tuple[Tuple[str, ...], ...]

    def as_dict(self) -> Dict[str, Dict[str, float]]:
        return {
            metric: {
                "rate": score.rate,
                "sentence_error_rate": score.sentence_error_rate,
                "reference_units": float(score.reference_units),
                "errors": float(score.errors),
                "substitutions": float(score.substitutions),
                "deletions": float(score.deletions),
                "insertions": float(score.insertions),
            }
            for metric, score in self.scores.items()
        }
