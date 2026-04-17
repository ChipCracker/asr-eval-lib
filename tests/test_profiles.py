from asr_eval_lib import custom_phonetic_profile, orthographic_profile, phonetic_profile


def test_builtin_profiles_resolve_glm_files():
    de_orth = orthographic_profile("de")
    en_ipa = phonetic_profile("en", "ipa")

    assert de_orth.default_metrics == ("wer", "cer")
    assert de_orth.glm_path is not None
    assert de_orth.glm_path.exists()
    assert en_ipa.default_metrics == ("per",)
    assert en_ipa.glm_path is not None
    assert en_ipa.glm_path.exists()


def test_custom_phonetic_profile_uses_external_glm(tmp_path):
    glm = tmp_path / "phones.glm"
    glm.write_text(";; custom\n* copy_no_hit = 'T'\n", encoding="utf-8")

    profile = custom_phonetic_profile("de", "project_phones", glm)

    assert profile.notation == "project_phones"
    assert profile.glm_path == glm
    assert profile.default_metrics == ("per",)
