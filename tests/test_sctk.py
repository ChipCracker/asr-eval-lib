from asr_eval_lib.sctk import parse_raw_report


def test_parse_raw_report_reads_sum_counts(tmp_path):
    report = tmp_path / "wer.raw"
    report.write_text(
        """
       | Sum    |    3     10 |    7      2      1      1      4      2 |
        """,
        encoding="utf-8",
    )

    score = parse_raw_report(report, "wer", "word")

    assert score.reference_units == 10
    assert score.errors == 4
    assert score.rate == 0.4
    assert score.sentence_error_rate == 2 / 3
