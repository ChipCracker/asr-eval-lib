from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .errors import SctkExecutionError, SctkNotFoundError
from .models import EvaluationProfile, Score


@dataclass(frozen=True)
class CompletedCommand:
    args: Tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


class SubprocessRunner:
    """Small subprocess wrapper to make SCTK execution testable."""

    def run(
        self,
        args: Sequence[object],
        stdin_path: Optional[Path] = None,
        stdout_path: Optional[Path] = None,
    ) -> CompletedCommand:
        normalized_args = tuple(str(arg) for arg in args)
        stdin_handle = None
        stdout_handle = None
        try:
            if stdin_path is not None:
                stdin_handle = Path(stdin_path).open("rb")
            if stdout_path is not None:
                Path(stdout_path).parent.mkdir(parents=True, exist_ok=True)
                stdout_handle = Path(stdout_path).open("wb")
            completed = subprocess.run(
                normalized_args,
                stdin=stdin_handle,
                stdout=stdout_handle if stdout_handle is not None else subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        finally:
            if stdin_handle is not None:
                stdin_handle.close()
            if stdout_handle is not None:
                stdout_handle.close()

        stdout = "" if stdout_path is not None else completed.stdout.decode("utf-8", "replace")
        stderr = completed.stderr.decode("utf-8", "replace")
        result = CompletedCommand(normalized_args, completed.returncode, stdout, stderr)
        if result.returncode != 0:
            raise SctkExecutionError(result.args, result.returncode, result.stdout, result.stderr)
        return result


class SctkToolchain:
    def __init__(
        self,
        sclite_path: Optional[str] = None,
        csrfilt_path: Optional[str] = None,
        check_tools: bool = True,
    ):
        self._sclite_path = sclite_path
        self._csrfilt_path = csrfilt_path
        self._check_tools = check_tools

    def sclite(self) -> str:
        return self._resolve("sclite", self._sclite_path, ("sclite",))

    def csrfilt(self) -> str:
        return self._resolve("csrfilt.sh", self._csrfilt_path, ("csrfilt.sh", "csrfilt"))

    def _resolve(self, label: str, configured: Optional[str], candidates: Sequence[str]) -> str:
        if not self._check_tools:
            return configured or candidates[0]
        if configured:
            path = Path(configured)
            if path.exists():
                return str(path)
            found = shutil.which(configured)
            if found:
                return found
            raise SctkNotFoundError(
                "Configured {0} executable was not found: {1}".format(label, configured)
            )

        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        raise SctkNotFoundError(
            "Required SCTK executable '{0}' was not found on PATH.".format(label)
        )


def csrfilt_command(
    executable: str,
    profile: EvaluationProfile,
    glm_path: Path,
    purpose: str,
) -> List[str]:
    args = [executable, "-s", "-i", "trn", "-t", purpose]
    if profile.transcript_type in ("orthographic", "transliteration"):
        args.append("-dh")
    args.append(str(glm_path))
    return args


def sclite_command(
    executable: str,
    reference_trn: Path,
    hypothesis_trn: Path,
    output_dir: Path,
    name: str,
) -> List[str]:
    return [
        executable,
        "-r",
        str(reference_trn),
        "trn",
        "-h",
        str(hypothesis_trn),
        "trn",
        "-i",
        "rm",
        "-s",
        "-o",
        "sum",
        "rsum",
        "pralign",
        "-O",
        str(output_dir),
        "-n",
        name,
    ]


def parse_raw_report(path: Path, metric: str, unit: str) -> Score:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _find_sum_line(text)
    if not match:
        raise SctkExecutionError(
            ("parse-sclite-raw", str(path)),
            1,
            stdout=text,
            stderr="Could not find SCLITE Sum line in raw report.",
        )

    values = {key: int(float(value)) for key, value in match.groupdict().items()}
    reference_units = values["wrd"]
    errors = values["err"]
    sentences = values["snt"]
    sentence_errors = values["serr"]
    return Score(
        metric=metric,
        unit=unit,
        sentences=sentences,
        reference_units=reference_units,
        correct=values["corr"],
        substitutions=values["sub"],
        deletions=values["del"],
        insertions=values["ins"],
        errors=errors,
        sentence_errors=sentence_errors,
        rate=errors / reference_units if reference_units else 0.0,
        sentence_error_rate=sentence_errors / sentences if sentences else 0.0,
    )


def _find_sum_line(text: str):
    pattern = re.compile(
        r"\|\s*Sum(?:/Avg)?\s*\|\s*"
        r"(?P<snt>\d+(?:\.\d+)?)\s+"
        r"(?P<wrd>\d+(?:\.\d+)?)\s*\|\s*"
        r"(?P<corr>\d+(?:\.\d+)?)\s+"
        r"(?P<sub>\d+(?:\.\d+)?)\s+"
        r"(?P<del>\d+(?:\.\d+)?)\s+"
        r"(?P<ins>\d+(?:\.\d+)?)\s+"
        r"(?P<err>\d+(?:\.\d+)?)\s+"
        r"(?P<serr>\d+(?:\.\d+)?)\s*\|"
    )
    return pattern.search(text)
