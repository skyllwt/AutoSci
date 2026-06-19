#!/usr/bin/env python3
"""Generate Codex skill wrappers for AutoSci's Claude Code skills.

AutoSci keeps its full workflow instructions in `.claude/skills` because that
is the upstream format. Codex discovers repo-scoped skills from `.agents/skills`
and requires `name` plus `description` frontmatter, so this script creates thin
wrappers that point Codex at the upstream skill documents.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CODEX_SKILLS = ROOT / ".agents" / "skills"

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def _parse_simple_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    meta: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        field = FIELD_RE.match(line)
        if not field:
            continue
        key, value = field.groups()
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        meta[key] = value
    return meta


def _source_skills() -> list[Path]:
    if not CLAUDE_SKILLS.is_dir():
        raise SystemExit(f"missing source skill directory: {CLAUDE_SKILLS}")
    return sorted(
        p for p in CLAUDE_SKILLS.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    )


def _wrapper_body(name: str, source_rel: str, source_dir_rel: str) -> str:
    return f"""# AutoSci /{name} (Codex Adapter)

This is a thin Codex wrapper around AutoSci's upstream Claude Code skill.
The upstream skill remains authoritative so `setup.sh --lang ...` can refresh
language-specific workflow instructions without duplicating content.

## How To Run

When this skill is selected, first read `{source_rel}` completely, then follow
that workflow as the source of truth.

Use these Codex-specific adaptations while following the upstream instructions:

- Treat AutoSci's original slash command `/{name}` as this Codex skill.
  If the user writes `/{name} ...`, execute it through this skill.
- Resolve any relative references from the upstream skill directory
  `{source_dir_rel}`. For example, `references/foo.md` means
  `{source_dir_rel}/references/foo.md`.
- Treat mentions of "Claude Code" as "the current Codex session" unless the
  instruction is specifically about Claude authentication or Claude-only CI.
- Translate upstream `Skill: other-skill` or `/other-skill` handoffs into the
  matching repo skill `$other-skill`.
- Use Codex's available shell, file editing, web, browser, MCP, and subagent
  tools for the corresponding upstream Bash/Read/Edit/WebSearch/WebFetch/Agent
  instructions.
- Prefer `.venv/bin/python` or `.venv/Scripts/python.exe` for AutoSci Python
  tools, then fall back to `python3` or `python`.
- Keep all wiki/raw/checkpoint writes inside this AutoSci repository unless the
  upstream skill explicitly asks for a configured remote experiment target.

## Source

- Upstream skill: `{source_rel}`
"""


def _render_wrapper(name: str, description: str) -> str:
    source_rel = f".claude/skills/{name}/SKILL.md"
    source_dir_rel = f".claude/skills/{name}"
    desc = (
        f"AutoSci /{name} Codex adapter. Use when the user invokes "
        f"`/{name}` or asks Codex to run AutoSci's {name} workflow. "
        f"Upstream behavior: {description}"
    )
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(desc, ensure_ascii=False)}\n"
        "---\n\n"
        f"{_wrapper_body(name, source_rel, source_dir_rel)}"
    )


def sync(check: bool = False) -> int:
    wrappers: dict[Path, str] = {}
    for skill_dir in _source_skills():
        name = skill_dir.name
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        meta = _parse_simple_frontmatter(text)
        description = meta.get("description", "").strip()
        if not description:
            raise SystemExit(f"missing description in {skill_dir / 'SKILL.md'}")
        dest = CODEX_SKILLS / name / "SKILL.md"
        wrappers[dest] = _render_wrapper(name, description)

    stale: list[str] = []
    for dest, expected in wrappers.items():
        if dest.exists() and dest.read_text(encoding="utf-8") == expected:
            continue
        stale.append(str(dest.relative_to(ROOT)))
        if not check:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(expected, encoding="utf-8")

    expected_dirs = {p.parent for p in wrappers}
    if CODEX_SKILLS.exists():
        for child in CODEX_SKILLS.iterdir():
            if child.is_dir() and child not in expected_dirs:
                stale.append(str(child.relative_to(ROOT)))
                if not check:
                    shutil.rmtree(child)

    if check and stale:
        print("Codex skill wrappers are stale:")
        for item in stale:
            print(f"  {item}")
        return 1

    if check:
        print(f"Codex skill wrappers are up to date ({len(wrappers)} checked).")
    else:
        print(f"Synced {len(wrappers)} Codex skill wrapper(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="report stale wrappers without writing files",
    )
    args = parser.parse_args()
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
