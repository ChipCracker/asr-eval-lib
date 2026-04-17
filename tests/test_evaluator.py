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
