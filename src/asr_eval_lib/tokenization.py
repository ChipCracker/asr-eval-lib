from __future__ import annotations

import unicodedata
from typing import Iterable, List

from .errors import ProfileError
from .models import EvaluationProfile
from .normalization import collapse_whitespace


SPACE_TOKEN = "<space>"

_IPA_MODIFIERS = {
    "\u02d0",  # length mark
    "\u02d1",  # half length mark
    "\u02b0",
    "\u02b2",
    "\u02b7",
    "\u02e0",
    "\u02e4",
}
_IPA_TIE_BARS = {"\u0361", "\u035c"}
_IPA_PREFIX_MARKS = {"\u02c8", "\u02cc"}
_PHONETIC_BOUNDARIES = {".", "|", "#"}

_SAMPA_SYMBOLS = (
    "tS",
    "dZ",
    "pf",
    "ts",
    "aI",
    "aU",
    "OY",
    "eI",
    "OI",
    "@U",
    "oU",
    "I@",
    "e@",
    "U@",
    "E6",
    "i:",
    "y:",
    "u:",
    "e:",
    "2:",
    "o:",
    "E:",
    "9:",
    "O:",
    "a:",
    "A:",
    "3:",
    "p",
    "b",
    "t",
    "d",
    "k",
    "g",
    "m",
    "n",
    "N",
    "f",
    "v",
    "T",
    "D",
    "s",
    "z",
    "S",
    "Z",
    "C",
    "j",
    "x",
    "R",
    "h",
    "l",
    "r",
    "w",
    "i",
    "I",
    "y",
    "Y",
    "e",
    "E",
    "2",
    "9",
    "@",
    "6",
    "a",
    "A",
    "u",
    "U",
    "o",
    "O",
    "V",
    "{",
    "Q",
    "?",
)

_XSAMPA_SYMBOLS = tuple(
    sorted(
        set(_SAMPA_SYMBOLS)
        | {
            "r\\",
            "l\\",
            "n`",
            "m`",
            "N\\",
            "R\\",
            "B\\",
            "G\\",
            "H\\",
            "L\\",
            "J\\",
            "_h",
            "_j",
            "_w",
            "_G",
            "_?",
        },
        key=len,
        reverse=True,
    )
)

_SAMPA_SYMBOLS = tuple(sorted(_SAMPA_SYMBOLS, key=len, reverse=True))


def tokens_for_metric(text: str, metric: str, profile: EvaluationProfile) -> List[str]:
    metric_name = metric.lower()
    if metric_name == "wer":
        return word_tokens(text)
    if metric_name == "cer":
        return char_tokens(text, include_spaces=profile.include_space_tokens_for_cer)
    if metric_name == "per":
        if profile.transcript_type != "phonetic":
            raise ProfileError("Metric 'per' requires a phonetic profile.")
        return phoneme_tokens(text, notation=profile.notation or "custom")
    raise ProfileError("Unsupported metric '{0}'.".format(metric))


def word_tokens(text: str) -> List[str]:
    collapsed = collapse_whitespace(text)
    if not collapsed:
        return []
    return collapsed.split(" ")


def char_tokens(text: str, include_spaces: bool = False) -> List[str]:
    if include_spaces:
        units = []
        previous_space = False
        for ch in text:
            if ch.isspace():
                if not previous_space:
                    units.append(SPACE_TOKEN)
                previous_space = True
            else:
                units.extend(_unicode_graphemes(ch))
                previous_space = False
        return [unit for unit in units if unit]
    return list(_unicode_graphemes("".join(ch for ch in text if not ch.isspace())))


def phoneme_tokens(text: str, notation: str = "custom") -> List[str]:
    compact = _strip_known_boundaries(collapse_whitespace(text))
    if not compact:
        return []
    if " " in compact:
        return [token for token in compact.split(" ") if token]

    normalized_notation = notation.lower()
    if normalized_notation == "ipa":
        return _ipa_compact_tokens(compact)
    if normalized_notation == "sampa":
        return _longest_match_tokens(compact, _SAMPA_SYMBOLS)
    if normalized_notation == "xsampa":
        return _longest_match_tokens(compact, _XSAMPA_SYMBOLS)
    return [compact]


def _unicode_graphemes(text: str) -> Iterable[str]:
    current = ""
    for ch in text:
        if unicodedata.combining(ch) and current:
            current += ch
            continue
        if current:
            yield current
        current = ch
    if current:
        yield current


def _strip_known_boundaries(text: str) -> str:
    return collapse_whitespace(
        "".join(" " if ch in _PHONETIC_BOUNDARIES else ch for ch in text)
    )


def _ipa_compact_tokens(text: str) -> List[str]:
    tokens = []
    current = ""
    join_next = False
    for ch in text:
        if ch.isspace() or ch in _PHONETIC_BOUNDARIES:
            if current:
                tokens.append(current)
                current = ""
            join_next = False
            continue

        if ch in _IPA_TIE_BARS:
            current = (current or "") + ch
            join_next = True
            continue

        if unicodedata.combining(ch) or ch in _IPA_MODIFIERS:
            current = (current or "") + ch
            continue

        if ch in _IPA_PREFIX_MARKS:
            if current:
                tokens.append(current)
            current = ch
            join_next = True
            continue

        if current and not join_next:
            tokens.append(current)
            current = ""
        current += ch
        join_next = False

    if current:
        tokens.append(current)
    return tokens


def _longest_match_tokens(text: str, inventory) -> List[str]:
    tokens = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        matched = None
        for symbol in inventory:
            if text.startswith(symbol, index):
                matched = symbol
                break
        if matched is None:
            matched = text[index]
        tokens.append(matched)
        index += len(matched)
    return tokens
