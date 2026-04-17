from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from .errors import ProfileError
from .models import EvaluationProfile


_GLM_ROOT = Path(__file__).resolve().parent / "glm"

_COMPONENTS = {
    ("de", "orthographic", None): (
        ("dates", _GLM_ROOT / "de" / "orthographic_dates.glm"),
        ("numbers", _GLM_ROOT / "de" / "orthographic_numbers.glm"),
    ),
}


def available_glm_components(profile: EvaluationProfile) -> Tuple[str, ...]:
    """Return built-in GLM components available for a profile."""

    return tuple(name for name, _ in _components_for(profile))


def resolve_glm_for_evaluation(
    profile: EvaluationProfile,
    output_dir: Path,
    glm_components: Optional[Sequence[str]] = None,
    exclude_glm_components: Optional[Sequence[str]] = None,
    extra_glm_paths: Optional[Sequence[Union[str, Path]]] = None,
) -> Optional[Path]:
    """Resolve or compose the GLM file used for one evaluation run."""

    sources = _resolve_sources(
        profile=profile,
        glm_components=glm_components,
        exclude_glm_components=exclude_glm_components,
        extra_glm_paths=extra_glm_paths,
    )
    if not sources:
        return None
    if len(sources) == 1:
        return sources[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    composed_path = output_dir / "composed.glm"
    _write_composed_glm(composed_path, sources, profile)
    return composed_path


def _resolve_sources(
    profile: EvaluationProfile,
    glm_components: Optional[Sequence[str]],
    exclude_glm_components: Optional[Sequence[str]],
    extra_glm_paths: Optional[Sequence[Union[str, Path]]],
) -> List[Path]:
    components = _components_for(profile)
    available = {name for name, _ in components}
    selected = _normalize_names(glm_components)
    excluded = _normalize_names(exclude_glm_components)

    unknown = (selected | excluded) - available
    if unknown:
        raise ProfileError(
            "Unsupported GLM component(s) for profile {0}: {1}".format(
                profile.name, ", ".join(sorted(unknown))
            )
        )

    sources: List[Path] = []
    if profile.glm_path is not None:
        sources.append(_existing_path(profile.glm_path, "Profile GLM file"))

    active_components = selected - excluded
    for name, path in components:
        if name in active_components:
            sources.append(_existing_path(path, "GLM component '{0}'".format(name)))

    for path in extra_glm_paths or ():
        sources.append(_existing_path(Path(path), "Extra GLM file"))

    return sources


def _components_for(profile: EvaluationProfile) -> Tuple[Tuple[str, Path], ...]:
    key = (profile.language, profile.transcript_type, profile.notation)
    return _COMPONENTS.get(key, ())


def _normalize_names(names: Optional[Sequence[str]]) -> set:
    if names is None:
        return set()
    return {str(name).strip().lower() for name in names if str(name).strip()}


def _existing_path(path: Union[str, Path], label: str) -> Path:
    resolved = Path(path)
    if not resolved.exists():
        raise ProfileError("{0} does not exist: {1}".format(label, resolved))
    return resolved


def _write_composed_glm(
    composed_path: Path, sources: Sequence[Path], profile: EvaluationProfile
) -> None:
    case_sensitive = "F" if profile.transcript_type in ("orthographic", "transliteration") else "T"
    with composed_path.open("w", encoding="utf-8") as handle:
        handle.write(";; asr-eval-lib composed GLM\n")
        handle.write('* name "asr-eval-lib-composed.glm"\n')
        handle.write('* desc "Composed evaluation-time GLM"\n')
        handle.write("* format = 'NIST2'\n")
        handle.write("* copy_no_hit = 'T'\n")
        handle.write("* case_sensitive = '{0}'\n".format(case_sensitive))
        handle.write(";;\n")
        for source in sources:
            handle.write(";; BEGIN SOURCE {0}\n".format(source))
            for line in _iter_rule_lines(source):
                handle.write(line)
            handle.write(";; END SOURCE {0}\n".format(source))


def _iter_rule_lines(source: Path) -> Iterable[str]:
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.lstrip().startswith("*"):
                continue
            yield line if line.endswith("\n") else line + "\n"
