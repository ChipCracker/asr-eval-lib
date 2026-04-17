from asr_eval_lib.models import Utterance
from asr_eval_lib.trn import coerce_paired_utterances, read_trn_text, write_trn_text


def test_coerce_paired_utterances_uses_stable_internal_ids():
    paired = coerce_paired_utterances(
        [Utterance("external-a", "ref")],
        [Utterance("external-a", "hyp")],
    )

    assert paired == [("utt_000001", "ref", "hyp")]


def test_write_and_read_trn_text_roundtrip(tmp_path):
    path = tmp_path / "sample.trn"

    write_trn_text(path, [("utt_000001", "hello world"), ("utt_000002", "")])

    assert read_trn_text(path) == {
        "utt_000001": "hello world",
        "utt_000002": "",
    }
