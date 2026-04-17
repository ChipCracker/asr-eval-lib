from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from .errors import ProfileError
from .models import EvaluationProfile


SUPPORTED_LANGUAGES = ("de", "en")
SUPPORTED_PHONETIC_NOTATIONS = ("ipa", "sampa", "xsampa")


def _resource_glm(language: str, filename: str) -> Path:
    return Path(__file__).resolve().parent / "glm" / language / filename


def _validate_language(language: str) -> str:
    normalized = language.lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise ProfileError(
            "Unsupported language '{0}'. Supported languages: {1}".format(
                language, ", ".join(SUPPORTED_LANGUAGES)
            )
        )
    return normalized


def _coerce_glm_path(glm_path: Optional[object], default: Path) -> Optional[Path]:
    if glm_path is False:
        return None
    if glm_path is None:
        return default
    return Path(str(glm_path))


def orthographic_profile(language: str, glm_path: Optional[object] = None) -> EvaluationProfile:
    """Profile for German or English orthographic transcription."""

    lang = _validate_language(language)
    return EvaluationProfile(
        language=lang,
        transcript_type="orthographic",
        notation=None,
        glm_path=_coerce_glm_path(glm_path, _resource_glm(lang, "orthographic.glm")),
        default_metrics=("wer", "cer"),
        lowercase=True,
        remove_punctuation=True,
        preserve_apostrophes=True,
        include_space_tokens_for_cer=False,
    )


def transliteration_profile(
    language: str, glm_path: Optional[object] = None
) -> EvaluationProfile:
    """Profile for transliterated German or English text."""

    lang = _validate_language(language)
    return EvaluationProfile(
        language=lang,
        transcript_type="transliteration",
        notation="latin",
        glm_path=_coerce_glm_path(glm_path, _resource_glm(lang, "transliteration.glm")),
        default_metrics=("wer", "cer"),
        lowercase=True,
        remove_punctuation=True,
        preserve_apostrophes=False,
        include_space_tokens_for_cer=False,
    )


def phonetic_profile(
    language: str, notation: str = "ipa", glm_path: Optional[object] = None
) -> EvaluationProfile:
    """Profile for phoneme error rate scoring in a known notation."""

    lang = _validate_language(language)
    normalized_notation = notation.lower()
    if normalized_notation not in SUPPORTED_PHONETIC_NOTATIONS:
        raise ProfileError(
            "Unsupported phonetic notation '{0}'. Use one of {1} or "
            "custom_phonetic_profile(...).".format(
                notation, ", ".join(SUPPORTED_PHONETIC_NOTATIONS)
            )
        )
    return EvaluationProfile(
        language=lang,
        transcript_type="phonetic",
        notation=normalized_notation,
        glm_path=_coerce_glm_path(
            glm_path, _resource_glm(lang, "phonetic_{0}.glm".format(normalized_notation))
        ),
        default_metrics=("per",),
        lowercase=False,
        remove_punctuation=False,
        preserve_apostrophes=True,
        include_space_tokens_for_cer=False,
    )


def custom_phonetic_profile(
    language: str,
    notation: str,
    glm_path: object,
    default_metrics: Sequence[str] = ("per",),
) -> EvaluationProfile:
    """Profile for project-specific phoneme notations and GLM rules."""

    lang = _validate_language(language)
    if not notation:
        raise ProfileError("Custom phonetic profiles require a notation name.")
    metrics = tuple(metric.lower() for metric in default_metrics)
    unsupported = [metric for metric in metrics if metric not in ("per", "wer", "cer")]
    if unsupported:
        raise ProfileError("Unsupported metric(s): {0}".format(", ".join(unsupported)))
    return EvaluationProfile(
        language=lang,
        transcript_type="phonetic",
        notation=notation,
        glm_path=Path(str(glm_path)),
        default_metrics=metrics,
        lowercase=False,
        remove_punctuation=False,
        preserve_apostrophes=True,
        include_space_tokens_for_cer=False,
    )
