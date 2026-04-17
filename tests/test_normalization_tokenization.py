from asr_eval_lib import orthographic_profile, phonetic_profile
from asr_eval_lib.normalization import normalize_text
from asr_eval_lib.tokenization import char_tokens, phoneme_tokens, tokens_for_metric


def test_orthographic_normalization_is_casefolded_and_punctuation_light():
    profile = orthographic_profile("de", glm_path=False)

    text = normalize_text("Die Straße - wirklich!", profile)

    assert text == "die strasse wirklich"


def test_english_apostrophes_inside_words_are_preserved():
    profile = orthographic_profile("en", glm_path=False)

    text = normalize_text("Don't stop, OK?", profile)

    assert text == "don't stop ok"


def test_cer_tokenization_ignores_spaces_by_default():
    assert char_tokens("ab cd") == ["a", "b", "c", "d"]


def test_ipa_compact_tokenizer_keeps_tie_bar_and_length():
    assert phoneme_tokens("t\u0361\u0283a\u02d0", notation="ipa") == [
        "t\u0361\u0283",
        "a\u02d0",
    ]


def test_sampa_compact_tokenizer_uses_longest_match():
    assert phoneme_tokens("tSa:", notation="sampa") == ["tS", "a:"]


def test_tokens_for_per_requires_phonetic_profile():
    profile = phonetic_profile("en", "ipa", glm_path=False)

    assert tokens_for_metric("h \u0259 l o\u028a", "per", profile) == [
        "h",
        "\u0259",
        "l",
        "o\u028a",
    ]
