import shutil
from pathlib import Path

from asr_eval_lib import ScliteEvaluator, orthographic_profile
from asr_eval_lib.sctk import CompletedCommand


class FakeRunner:
    def run(self, args, stdin_path=None, stdout_path=None):
        args = tuple(str(arg) for arg in args)
        if "csrfilt" in args[0]:
            shutil.copyfile(stdin_path, stdout_path)
        else:
            output_dir = args[args.index("-O") + 1]
            name = args[args.index("-n") + 1]
            raw = Path(output_dir) / "{0}.raw".format(name)
            raw.write_text(
                "| Sum    |    1      2 |    1      1      0      0      1      1 |\n",
                encoding="utf-8",
            )
        return CompletedCommand(args=args, returncode=0)


def test_evaluator_applies_glm_then_runs_sclite_for_default_metrics(tmp_path):
    profile = orthographic_profile("en")
    evaluator = ScliteEvaluator(
        work_dir=tmp_path,
        check_tools=False,
        runner=FakeRunner(),
    )

    result = evaluator.evaluate({"utt": "Hello, world"}, {"utt": "hello word"}, profile)

    assert set(result.scores.keys()) == {"wer", "cer"}
    assert result.scores["wer"].rate == 0.5
    assert len(result.commands) == 4
    assert (tmp_path / "glm_filter" / "ref.raw.trn").exists()
    assert (tmp_path / "wer" / "ref.trn").read_text(encoding="utf-8").strip() == (
        "hello world (utt_000001)"
    )


def test_german_ort_evaluation_normalizes_transcripts_for_wer_and_cer(tmp_path):
    profile = orthographic_profile("de")
    evaluator = ScliteEvaluator(
        work_dir=tmp_path,
        check_tools=False,
        runner=FakeRunner(),
    )

    result = evaluator.evaluate(
        references={"utt": "Die Straße ist schön."},
        hypotheses={"utt": "Die Strasse schön"},
        profile=profile,
    )

    assert set(result.scores.keys()) == {"wer", "cer"}
    assert result.scores["wer"].unit == "word"
    assert result.scores["cer"].unit == "character"
    assert any("glm/de/orthographic.glm" in part for command in result.commands for part in command)
    assert (tmp_path / "wer" / "ref.trn").read_text(encoding="utf-8").strip() == (
        "die strasse ist schön (utt_000001)"
    )
    assert (tmp_path / "cer" / "ref.trn").read_text(encoding="utf-8").strip() == (
        "d i e s t r a s s e i s t s c h ö n (utt_000001)"
    )


def test_evaluator_uses_composed_glm_for_german_ort_components(tmp_path):
    profile = orthographic_profile("de")
    evaluator = ScliteEvaluator(
        work_dir=tmp_path,
        check_tools=False,
        runner=FakeRunner(),
    )

    result = evaluator.evaluate(
        references={"utt": "3. März"},
        hypotheses={"utt": "dritter März"},
        profile=profile,
        glm_components=["dates", "numbers"],
    )

    composed = tmp_path / "glm_filter" / "composed.glm"
    assert composed.exists()
    assert any(str(composed) in part for command in result.commands for part in command)
    assert (tmp_path / "wer" / "ref.trn").exists()
    assert (tmp_path / "cer" / "hyp.trn").exists()
