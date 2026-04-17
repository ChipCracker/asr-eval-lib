import pytest

from asr_eval_lib import available_glm_components, orthographic_profile
from asr_eval_lib.errors import ProfileError
from asr_eval_lib.glm_composition import resolve_glm_for_evaluation


def test_available_glm_components_for_german_orthographic_profile():
    assert available_glm_components(orthographic_profile("de")) == ("dates", "numbers")


def test_resolve_glm_rejects_unknown_component(tmp_path):
    with pytest.raises(ProfileError):
        resolve_glm_for_evaluation(
            profile=orthographic_profile("de"),
            output_dir=tmp_path,
            glm_components=["foo"],
        )


def test_resolve_glm_without_components_keeps_profile_glm(tmp_path):
    profile = orthographic_profile("de")

    resolved = resolve_glm_for_evaluation(profile=profile, output_dir=tmp_path)

    assert resolved == profile.glm_path


def test_resolve_glm_can_remove_selected_component(tmp_path):
    resolved = resolve_glm_for_evaluation(
        profile=orthographic_profile("de"),
        output_dir=tmp_path,
        glm_components=["dates", "numbers"],
        exclude_glm_components=["numbers"],
    )

    content = resolved.read_text(encoding="utf-8")
    assert resolved.name == "composed.glm"
    assert "3 märz => date_03_03" in content
    assert "3 => num_3" not in content


def test_resolve_glm_appends_extra_glm_paths(tmp_path):
    extra = tmp_path / "extra.glm"
    extra.write_text(
        ";; extra rules\n* copy_no_hit = 'T'\nsonderfall => special_case\n",
        encoding="utf-8",
    )

    resolved = resolve_glm_for_evaluation(
        profile=orthographic_profile("de"),
        output_dir=tmp_path,
        extra_glm_paths=[extra],
    )

    content = resolved.read_text(encoding="utf-8")
    assert resolved.name == "composed.glm"
    assert "sonderfall => special_case" in content


def test_composed_glm_contains_date_rules_before_number_rules(tmp_path):
    resolved = resolve_glm_for_evaluation(
        profile=orthographic_profile("de"),
        output_dir=tmp_path,
        glm_components=["numbers", "dates"],
    )

    content = resolved.read_text(encoding="utf-8")
    assert resolved.name == "composed.glm"
    assert "3 märz => date_03_03" in content
    assert "dritter märz => date_03_03" in content
    assert "03 03 => date_03_03" in content
    assert "drei => num_3" in content
    assert "3 => num_3" in content
    assert content.index("3 märz => date_03_03") < content.index("3 => num_3")
    assert content.index("31 => num_31") < content.index("3 => num_3")
    assert content.index("einundzwanzig => num_21") < content.index("ein => num_1")
