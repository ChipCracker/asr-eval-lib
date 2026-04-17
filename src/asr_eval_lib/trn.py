from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple, Union

from .errors import TranscriptError
from .models import Utterance


_TRN_RE = re.compile(r"^(?P<text>.*?)(?:\s+)?\((?P<utt_id>[^()]*)\)\s*$")


PreparedRecord = Tuple[str, str, str]


def coerce_paired_utterances(
    references: Union[Mapping[str, str], Sequence[Union[str, Utterance]]],
    hypotheses: Union[Mapping[str, str], Sequence[Union[str, Utterance]]],
) -> List[PreparedRecord]:
    """Return records as (internal_id, reference_text, hypothesis_text)."""

    refs = _coerce_to_mapping(references, "references")
    hyps = _coerce_to_mapping(hypotheses, "hypotheses")
    ref_ids = list(refs.keys())
    hyp_ids = set(hyps.keys())
    missing = [utt_id for utt_id in ref_ids if utt_id not in hyp_ids]
    extra = [utt_id for utt_id in hyps.keys() if utt_id not in refs]
    if missing or extra:
        raise TranscriptError(
            "Reference and hypothesis IDs differ. Missing hypotheses: {0}. "
            "Extra hypotheses: {1}.".format(missing, extra)
        )

    return [
        ("utt_{0:06d}".format(index + 1), refs[utt_id], hyps[utt_id])
        for index, utt_id in enumerate(ref_ids)
    ]


def write_trn_text(path: Path, records: Iterable[Tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for utt_id, text in records:
            text = str(text).strip()
            if text:
                handle.write("{0} ({1})\n".format(text, utt_id))
            else:
                handle.write("({0})\n".format(utt_id))


def write_trn_tokens(path: Path, records: Iterable[Tuple[str, Sequence[str]]]) -> None:
    write_trn_text(path, ((utt_id, " ".join(tokens)) for utt_id, tokens in records))


def read_trn_text(path: Path) -> Dict[str, str]:
    parsed = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(";;"):
                continue
            match = _TRN_RE.match(stripped)
            if not match:
                raise TranscriptError(
                    "Invalid TRN line in {0}:{1}: {2}".format(path, line_number, stripped)
                )
            parsed[match.group("utt_id")] = match.group("text").strip()
    return parsed


def _coerce_to_mapping(
    values: Union[Mapping[str, str], Sequence[Union[str, Utterance]]], name: str
) -> Dict[str, str]:
    if isinstance(values, Mapping):
        return {str(key): str(value) for key, value in values.items()}
    if isinstance(values, (str, bytes)):
        raise TranscriptError("{0} must not be a single string.".format(name))

    mapping = {}
    for index, item in enumerate(values):
        if isinstance(item, Utterance):
            utt_id = str(item.utterance_id)
            text = str(item.text)
        else:
            utt_id = "utt_{0:06d}".format(index + 1)
            text = str(item)
        if utt_id in mapping:
            raise TranscriptError("Duplicate utterance ID '{0}' in {1}.".format(utt_id, name))
        mapping[utt_id] = text
    return mapping
