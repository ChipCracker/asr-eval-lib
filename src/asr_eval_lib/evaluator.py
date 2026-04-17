from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .errors import ProfileError, SctkExecutionError
from .models import EvaluationProfile, EvaluationResult, Score, Utterance
from .normalization import normalize_text
from .sctk import (
    SctkToolchain,
    SubprocessRunner,
    csrfilt_command,
    parse_raw_report,
    sclite_command,
)
from .tokenization import tokens_for_metric
from .trn import coerce_paired_utterances, read_trn_text, write_trn_text, write_trn_tokens


_METRIC_UNITS = {
    "wer": "word",
    "cer": "character",
    "per": "phoneme",
}


class ScliteEvaluator:
    """Evaluate ASR transcripts with SCTK GLM filtering and SCLITE scoring."""

    def __init__(
        self,
        sclite_path: Optional[str] = None,
        csrfilt_path: Optional[str] = None,
        work_dir: Optional[Union[str, Path]] = None,
        keep_files: bool = False,
        check_tools: bool = True,
        runner: Optional[SubprocessRunner] = None,
    ):
        self.toolchain = SctkToolchain(
            sclite_path=sclite_path,
            csrfilt_path=csrfilt_path,
            check_tools=check_tools,
        )
        self.work_dir = Path(work_dir) if work_dir is not None else None
        self.keep_files = keep_files or work_dir is not None
        self.runner = runner or SubprocessRunner()

    def evaluate(
        self,
        references: Union[Mapping[str, str], Sequence[Union[str, Utterance]]],
        hypotheses: Union[Mapping[str, str], Sequence[Union[str, Utterance]]],
        profile: EvaluationProfile,
        metrics: Optional[Sequence[str]] = None,
    ) -> EvaluationResult:
        selected_metrics = self._validate_metrics(profile, metrics)
        paired = coerce_paired_utterances(references, hypotheses)

        if self.work_dir is None:
            if self.keep_files:
                root = Path(tempfile.mkdtemp(prefix="asr_eval_"))
                return self._evaluate_in_dir(
                    root, paired, profile, selected_metrics, report_dir=root
                )
            with tempfile.TemporaryDirectory(prefix="asr_eval_") as temp_dir:
                return self._evaluate_in_dir(
                    Path(temp_dir), paired, profile, selected_metrics, report_dir=None
                )

        self.work_dir.mkdir(parents=True, exist_ok=True)
        return self._evaluate_in_dir(
            self.work_dir, paired, profile, selected_metrics, report_dir=self.work_dir
        )

    def _evaluate_in_dir(
        self,
        root: Path,
        paired,
        profile: EvaluationProfile,
        metrics: Tuple[str, ...],
        report_dir: Optional[Path],
    ) -> EvaluationResult:
        commands: List[Tuple[str, ...]] = []
        normalized_ref = [(utt_id, normalize_text(ref, profile)) for utt_id, ref, _ in paired]
        normalized_hyp = [(utt_id, normalize_text(hyp, profile)) for utt_id, _, hyp in paired]

        filtered_ref, filtered_hyp = self._apply_glm_filter(
            root, profile, normalized_ref, normalized_hyp, commands
        )

        scores: Dict[str, Score] = {}
        sclite = self.toolchain.sclite()
        for metric in metrics:
            metric_dir = root / metric
            metric_dir.mkdir(parents=True, exist_ok=True)
            ref_trn = metric_dir / "ref.trn"
            hyp_trn = metric_dir / "hyp.trn"
            write_trn_tokens(
                ref_trn,
                (
                    (utt_id, tokens_for_metric(filtered_ref.get(utt_id, ""), metric, profile))
                    for utt_id, _, _ in paired
                ),
            )
            write_trn_tokens(
                hyp_trn,
                (
                    (utt_id, tokens_for_metric(filtered_hyp.get(utt_id, ""), metric, profile))
                    for utt_id, _, _ in paired
                ),
            )

            command = sclite_command(sclite, ref_trn, hyp_trn, metric_dir, metric)
            result = self.runner.run(command)
            commands.append(result.args)
            raw_report = _find_raw_report(metric_dir, metric)
            scores[metric] = parse_raw_report(raw_report, metric, _METRIC_UNITS[metric])

        return EvaluationResult(
            profile=profile,
            scores=scores,
            reports_dir=report_dir if self.keep_files else None,
            commands=tuple(commands),
        )

    def _apply_glm_filter(
        self,
        root: Path,
        profile: EvaluationProfile,
        normalized_ref,
        normalized_hyp,
        commands: List[Tuple[str, ...]],
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        if profile.glm_path is None:
            return dict(normalized_ref), dict(normalized_hyp)

        glm_path = Path(profile.glm_path)
        if not glm_path.exists():
            raise ProfileError("GLM file does not exist: {0}".format(glm_path))

        filter_dir = root / "glm_filter"
        filter_dir.mkdir(parents=True, exist_ok=True)
        raw_ref = filter_dir / "ref.raw.trn"
        raw_hyp = filter_dir / "hyp.raw.trn"
        filtered_ref = filter_dir / "ref.filtered.trn"
        filtered_hyp = filter_dir / "hyp.filtered.trn"
        write_trn_text(raw_ref, normalized_ref)
        write_trn_text(raw_hyp, normalized_hyp)

        csrfilt = self.toolchain.csrfilt()
        for purpose, source, destination in (
            ("ref", raw_ref, filtered_ref),
            ("hyp", raw_hyp, filtered_hyp),
        ):
            command = csrfilt_command(csrfilt, profile, glm_path, purpose)
            result = self.runner.run(command, stdin_path=source, stdout_path=destination)
            commands.append(result.args)

        return read_trn_text(filtered_ref), read_trn_text(filtered_hyp)

    def _validate_metrics(
        self, profile: EvaluationProfile, metrics: Optional[Sequence[str]]
    ) -> Tuple[str, ...]:
        selected = tuple(metric.lower() for metric in (metrics or profile.default_metrics))
        unsupported = [metric for metric in selected if metric not in _METRIC_UNITS]
        if unsupported:
            raise ProfileError("Unsupported metric(s): {0}".format(", ".join(unsupported)))
        not_in_profile = [metric for metric in selected if metric not in profile.default_metrics]
        if not_in_profile:
            raise ProfileError(
                "Metric(s) {0} are not enabled for profile {1}.".format(
                    ", ".join(not_in_profile), profile.name
                )
            )
        return selected


def _find_raw_report(metric_dir: Path, metric: str) -> Path:
    expected = metric_dir / "{0}.raw".format(metric)
    if expected.exists():
        return expected
    candidates = sorted(metric_dir.glob("*.raw"))
    if len(candidates) == 1:
        return candidates[0]
    raise SctkExecutionError(
        ("find-sclite-raw", str(metric_dir)),
        1,
        stderr="Could not find unique SCLITE .raw report in {0}".format(metric_dir),
    )
