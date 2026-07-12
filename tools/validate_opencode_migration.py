#!/usr/bin/env python3
"""Static CI gate for the OpenCode-only distribution."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".sh", ".ps1"}
BANNED = (
    "argument-hint:", "mcp__", ".claude/", ".agents/", "Claude Code",
    "Codex", "codex-action", "claude-code-action", "${workspaceFolder}",
)
SCOPES = [ROOT / "i18n", ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "AGENTS.md", ROOT / "config", ROOT / "docs", ROOT / "setup.sh", ROOT / "setup.ps1", ROOT / ".github" / "workflows"]


def files_under(path: Path):
    if path.is_file():
        yield path
    elif path.exists():
        yield from (p for p in path.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)


def main() -> int:
    errors: list[str] = []
    for scope in SCOPES:
        for path in files_under(scope):
            text = path.read_text(encoding="utf-8")
            for token in BANNED:
                if token in text:
                    errors.append(f"{path.relative_to(ROOT)}: banned token {token!r}")

    language_names: dict[str, set[str]] = {}
    for lang in ("en", "zh"):
        skills_root = ROOT / "i18n" / lang / "skills"
        names: set[str] = set()
        for skill_file in sorted(skills_root.glob("*/SKILL.md")):
            text = skill_file.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            if not match:
                errors.append(f"{skill_file.relative_to(ROOT)}: invalid frontmatter")
                continue
            fields = [line.split(":", 1)[0].strip() for line in match.group(1).splitlines() if ":" in line]
            if set(fields) != {"name", "description"} or len(fields) != 2:
                errors.append(f"{skill_file.relative_to(ROOT)}: frontmatter must contain name and description only")
            name_match = re.search(r"^name:\s*(\S+)\s*$", match.group(1), re.M)
            name = name_match.group(1) if name_match else ""
            if name != skill_file.parent.name:
                errors.append(f"{skill_file.relative_to(ROOT)}: name {name!r} does not match directory")
            if name in names:
                errors.append(f"{lang}: duplicate skill name {name}")
            names.add(name)
        language_names[lang] = names
        if not (skills_root / "init").exists() or "init" not in names:
            errors.append(f"{lang}: init skill is missing")
    if language_names.get("en") != language_names.get("zh"):
        errors.append("English and Chinese skill sets differ")

    daily_text = (ROOT / "tools" / "daily_arxiv.py").read_text(encoding="utf-8")
    for token in ("max_auto_ingest", "auto_ingest", '"runtime"', '"mode"', "ingest_status", "ingest_error"):
        if token in daily_text:
            errors.append(f"tools/daily_arxiv.py: legacy daily-arXiv state {token!r}")

    for obsolete in (".claude", ".agents", ".github/codex"):
        path = ROOT / obsolete
        # Some managed environments mount an empty reserved directory. Only
        # repository content is an actionable migration residue.
        if path.exists() and any(item.is_file() for item in path.rglob("*")):
            errors.append(f"obsolete path contains files: {obsolete}")
    if (ROOT / "CLAUDE.md").exists():
        errors.append("obsolete path remains: CLAUDE.md")

    if errors:
        print("OpenCode migration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OpenCode migration validation passed ({len(language_names['en'])} bilingual skills).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
