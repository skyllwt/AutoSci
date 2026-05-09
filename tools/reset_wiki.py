#!/usr/bin/env python3
"""Reset wiki state to a clean scaffold (used by /reset skill).

Scopes:
    wiki         delete all .md content under wiki/<entity>/, wiki/outputs/,
                 wiki/index.md, wiki/log.md, and wiki/graph/ files.
                 Preserves .gitkeep and wiki/CLAUDE.md.
    raw          delete all files under raw/<sub>/ except .gitkeep.
    log          reset wiki/log.md to empty header.
    checkpoints  call `research_wiki.py checkpoint-clear` to drop batch state.
    all          all of the above.

Usage:
    python3 tools/reset_wiki.py --scope wiki --yes
    python3 tools/reset_wiki.py --scope all --dry-run

Without --yes the tool prints the plan and exits without touching the filesystem.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime.loader import ENTITIES  # noqa: E402

ENTITY_DIRS = list(ENTITIES.keys())
RAW_SUBDIRS = ["papers", "discovered", "tmp", "notes", "web"]
ALL_SCOPES = ["wiki", "raw", "log", "checkpoints"]

INDEX_TEMPLATE = "# Wiki Index\n\n" + "\n".join(f"{e}:" for e in ENTITY_DIRS) + "\n"
LOG_TEMPLATE = "# OmegaWiki Log\n\n"
GRAPH_FILES = ["edges.jsonl", "citations.jsonl", "context_brief.md", "open_questions.md"]


def _list_md(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.glob("*.md") if p.is_file()]


def _list_raw(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.iterdir() if p.name != ".gitkeep"]


def plan(project_root: Path, scopes: list[str]) -> dict:
    """Return a structured plan of what will be deleted/reset."""
    p: dict = {"scopes": scopes, "delete_files": [], "reset_files": [], "actions": []}
    wiki = project_root / "wiki"

    if "wiki" in scopes:
        for entity in ENTITY_DIRS:
            for f in _list_md(wiki / entity):
                p["delete_files"].append(str(f.relative_to(project_root)))
        for f in _list_md(wiki / "outputs"):
            p["delete_files"].append(str(f.relative_to(project_root)))
        # Scaffold files — deleted, not reset (init recreates them)
        if (wiki / "index.md").exists():
            p["delete_files"].append("wiki/index.md")
        if (wiki / "log.md").exists():
            p["delete_files"].append("wiki/log.md")
        for gf in GRAPH_FILES:
            gf_path = wiki / "graph" / gf
            if gf_path.exists():
                p["delete_files"].append(f"wiki/graph/{gf}")

    if "raw" in scopes:
        for sub in RAW_SUBDIRS:
            for f in _list_raw(project_root / "raw" / sub):
                p["delete_files"].append(str(f.relative_to(project_root)))

    if "log" in scopes and "wiki" not in scopes:
        p["reset_files"].append("wiki/log.md")

    if "checkpoints" in scopes:
        p["actions"].append("research_wiki.py checkpoint-clear")

    return p


def execute(project_root: Path, scopes: list[str]) -> dict:
    """Apply the plan. Returns counts of what was actually changed."""
    deleted = 0
    reset = 0
    wiki = project_root / "wiki"

    if "wiki" in scopes:
        for entity in ENTITY_DIRS + ["outputs"]:
            for f in _list_md(wiki / entity):
                f.unlink()
                deleted += 1
            # Ensure .gitkeep exists so the directory survives commits
            keep = wiki / entity / ".gitkeep"
            if not keep.parent.exists():
                keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.touch()
        # Delete scaffold files (init recreates them from scratch)
        for scaffold in ["index.md", "log.md"]:
            sp = wiki / scaffold
            if sp.exists():
                sp.unlink()
                deleted += 1
        graph = wiki / "graph"
        if graph.exists():
            for gf in GRAPH_FILES:
                gfp = graph / gf
                if gfp.exists():
                    gfp.unlink()
                    deleted += 1

    if "raw" in scopes:
        for sub in RAW_SUBDIRS:
            for f in _list_raw(project_root / "raw" / sub):
                if f.is_dir():
                    shutil.rmtree(f)
                else:
                    f.unlink()
                deleted += 1
            keep = project_root / "raw" / sub / ".gitkeep"
            if not keep.parent.exists():
                keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.touch()

    if "log" in scopes and "wiki" not in scopes:
        # Standalone log scope: reset to empty header
        (wiki / "log.md").write_text(LOG_TEMPLATE, encoding="utf-8")
        reset += 1

    if "checkpoints" in scopes:
        cp_dir = wiki / ".checkpoints"
        if cp_dir.exists():
            for cp_file in cp_dir.glob("*.json"):
                cp_file.unlink()
                deleted += 1

    return {"deleted_files": deleted, "reset_files": reset}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scope", required=True,
                   help="Comma-separated list, or one of: wiki, raw, log, checkpoints, all")
    p.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    p.add_argument("--yes", action="store_true", help="Apply changes (default: dry-run plan only)")
    p.add_argument("--dry-run", action="store_true", help="Print plan and exit (default behavior)")
    args = p.parse_args()

    if args.scope == "all":
        scopes = list(ALL_SCOPES)
    else:
        scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
        for s in scopes:
            if s not in ALL_SCOPES:
                print(json.dumps({"status": "error",
                                  "message": f"unknown scope: {s}",
                                  "valid": ALL_SCOPES}))
                sys.exit(1)

    root = Path(args.project_root).resolve()
    the_plan = plan(root, scopes)

    if not args.yes or args.dry_run:
        print(json.dumps({"status": "plan", **the_plan}, ensure_ascii=False, indent=2))
        return

    result = execute(root, scopes)
    print(json.dumps({"status": "ok", "scopes": scopes, **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
