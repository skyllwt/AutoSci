"""Read-only bridge from existing AutoSci experiment pages to Hiera."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import HieraError, canonical_digest, project_root, sha256_file, validate_slug


def _yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        return [_yaml_scalar(item) for item in value[1:-1].split(",") if item.strip()]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _fallback_frontmatter(text: list[str]) -> dict[str, Any]:
    lines = [(len(line) - len(line.lstrip(" ")), line.strip()) for line in text]

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        is_list = index < len(lines) and lines[index][1].startswith("- ")
        result: Any = [] if is_list else {}
        while index < len(lines):
            level, line = lines[index]
            if not line or level < indent:
                index += 1
                continue
            if level > indent:
                break
            if is_list:
                if not line.startswith("- "):
                    break
                item = line[2:].strip()
                index += 1
                if ":" in item:
                    key, raw = item.split(":", 1)
                    item_map = {key.strip(): _yaml_scalar(raw)}
                    while index < len(lines) and lines[index][0] > indent:
                        _, continuation = lines[index]
                        if ":" in continuation:
                            child_key, child_raw = continuation.split(":", 1)
                            item_map[child_key.strip()] = _yaml_scalar(child_raw)
                        index += 1
                    result.append(item_map)
                else:
                    result.append(_yaml_scalar(item))
                continue
            if ":" not in line:
                index += 1
                continue
            key, raw = line.split(":", 1)
            key, raw = key.strip(), raw.strip()
            index += 1
            if raw:
                result[key] = _yaml_scalar(raw)
            elif index < len(lines) and lines[index][0] > indent:
                result[key], index = parse_block(index, lines[index][0])
            else:
                result[key] = {}
        return result, index

    return parse_block(0, lines[0][0] if lines else 0)[0]


def _read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        from tools.research_wiki import _parse_frontmatter

        value = _parse_frontmatter(path)
        return value if isinstance(value, dict) else {}
    except ModuleNotFoundError:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            return {}
        end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
        if end is None:
            raise HieraError(f"unclosed frontmatter: {path}")
        return _fallback_frontmatter(lines[1:end])
    except Exception as exc:  # pragma: no cover - parser boundary
        raise HieraError(f"could not parse wiki frontmatter: {path}: {exc}") from exc


def read_entity(project: Path, kind: str, slug: str) -> tuple[dict[str, Any], str, Path]:
    validate_slug(slug, f"{kind} slug")
    wiki = (project / "wiki").resolve()
    path = (wiki / kind / f"{slug}.md").resolve()
    try:
        path.relative_to(wiki)
    except ValueError as exc:
        raise HieraError("wiki entity path escaped wiki root") from exc
    if not path.is_file():
        raise HieraError(f"wiki {kind} page not found: {path}")
    return _read_frontmatter(path), path.read_text(encoding="utf-8"), path


@dataclass(frozen=True)
class ExperimentContext:
    project_root: Path
    experiment_slug: str
    experiment: dict[str, Any]
    experiment_text: str
    experiment_path: Path
    idea: dict[str, Any]
    idea_text: str
    idea_path: Path
    design_path: Path | None

    @property
    def source_files(self) -> dict[str, str]:
        files = {
            str(self.experiment_path.relative_to(self.project_root)): sha256_file(self.experiment_path),
            str(self.idea_path.relative_to(self.project_root)): sha256_file(self.idea_path),
        }
        if self.design_path and self.design_path.is_file():
            files[str(self.design_path.relative_to(self.project_root))] = sha256_file(self.design_path)
        return files


def load_experiment_context(project: Path, experiment_slug: str) -> ExperimentContext:
    project = project_root(project)
    validate_slug(experiment_slug, "experiment slug")
    experiment, experiment_text, experiment_path = read_entity(
        project, "experiments", experiment_slug
    )
    linked_idea = experiment.get("linked_idea")
    if not isinstance(linked_idea, str) or not linked_idea:
        raise HieraError(f"experiment {experiment_slug} has no linked_idea")
    idea, idea_text, idea_path = read_entity(project, "ideas", linked_idea)
    design_candidates = [
        project / "experiments" / "designs" / f"{linked_idea}-master.md",
        project / "experiments" / "designs" / f"{experiment_slug}-master.md",
    ]
    design_path = next((path for path in design_candidates if path.is_file()), None)
    return ExperimentContext(
        project,
        experiment_slug,
        experiment,
        experiment_text,
        experiment_path,
        idea,
        idea_text,
        idea_path,
        design_path,
    )


def wiki_snapshot(context: ExperimentContext) -> dict[str, Any]:
    files = context.source_files
    return {
        "experiment_slug": context.experiment_slug,
        "linked_idea": context.experiment.get("linked_idea"),
        "source_files": files,
        "source_digest": canonical_digest(files),
    }


def source_snapshot_unchanged(project: Path, manifest: dict[str, Any]) -> bool:
    """Check provenance without mutating any wiki file."""
    source = manifest.get("wiki_snapshot", {}).get("source_files", {})
    if not isinstance(source, dict):
        return False
    for relative, digest in source.items():
        path = (project / relative).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            return False
        if not path.is_file() or sha256_file(path) != digest:
            return False
    return True
