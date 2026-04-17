from __future__ import annotations

import re
import unicodedata

from .models import EvaluationProfile


_APOSTROPHES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\u2032": "'",
    "`": "'",
    "\u00b4": "'",
}

_DASHES = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
}

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str, profile: EvaluationProfile) -> str:
    """Normalize user text before GLM filtering and SCLITE scoring."""

    normalized = unicodedata.normalize("NFC", str(text))
    normalized = _translate_chars(normalized)

    if profile.transcript_type == "phonetic":
        normalized = _strip_outer_phonetic_delimiters(normalized)
    else:
        if profile.lowercase:
            normalized = normalized.casefold()
        if profile.remove_punctuation:
            normalized = _remove_punctuation(
                normalized,
                preserve_apostrophes=profile.preserve_apostrophes,
            )

    return collapse_whitespace(normalized)


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _translate_chars(text: str) -> str:
    return "".join(_APOSTROPHES.get(_DASHES.get(ch, ch), _DASHES.get(ch, ch)) for ch in text)


def _remove_punctuation(text: str, preserve_apostrophes: bool) -> str:
    chars = list(text)
    output = []
    for index, ch in enumerate(chars):
        category = unicodedata.category(ch)
        if ch == "'" and preserve_apostrophes and _inside_word(chars, index):
            output.append(ch)
        elif ch == "-" and _inside_word(chars, index):
            output.append(" ")
        elif category.startswith("P") or category.startswith("C"):
            output.append(" ")
        else:
            output.append(ch)
    return "".join(output)


def _inside_word(chars, index: int) -> bool:
    return (
        index > 0
        and index + 1 < len(chars)
        and chars[index - 1].isalnum()
        and chars[index + 1].isalnum()
    )


def _strip_outer_phonetic_delimiters(text: str) -> str:
    stripped = text.strip()
    while len(stripped) >= 2 and (
        (stripped.startswith("/") and stripped.endswith("/"))
        or (stripped.startswith("[") and stripped.endswith("]"))
    ):
        stripped = stripped[1:-1].strip()
    return stripped
