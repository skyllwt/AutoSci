#!/usr/bin/env python3
"""Convert AutoSci's bilingual skill source into Qoder-native assets.

This is the Qoder counterpart of the Claude Code activation step in
``setup.ps1`` / ``setup.sh``. It regenerates, from the shared source of
truth ``i18n/<lang>/skills``, the following Qoder artifacts:

- ``.qoder/skills/<skill>/``      — Qoder Agent Skills (SKILL.md frontmatter
  gains the required ``name`` field; ``argument-hint`` becomes a Usage line)
- ``.qoder/skills/shared-references/`` — shared reference docs
- ``AGENTS.md``                    — runtime contract read by Qoder
- ``.qoder/mcp.json``              — llm-review MCP server registration
- ``.qoder/.current-lang``         — activated language marker

The script is idempotent: the generated trees are wiped and rebuilt on every
run. Never hand-edit generated files; change the ``i18n/<lang>`` source and
re-run this script (or ``setup-qoder.ps1`` / ``setup-qoder.sh``).

Usage:
    python tools/convert_to_qoder.py --lang zh
    python tools/convert_to_qoder.py --lang en --project-root .
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Text substitutions applied to every generated markdown / yaml file.
# Order matters: most specific patterns first.
REPLACEMENTS = [
    # CI scaffold wording (daily-arxiv references)
    ("Claude Code Action", "Qoder agent runtime"),
    # setup skill status lines
    ("由 Claude Code 管理（claude login）", "由 Qoder 管理（Qoder 登录）"),
    ("managed by Claude Code (claude login)", "managed by Qoder (Qoder login)"),
    ("claude login", "Qoder login"),
    # skill asset paths
    (".claude/skills/shared-references/", ".qoder/skills/shared-references/"),
    (".claude/skills/", ".qoder/skills/"),
    (".claude/", ".qoder/"),
    # MCP tool naming: Claude Code `mcp__server__tool` -> Qoder `server.tool`
    ("mcp__llm-review__", "llm-review."),
    # MCP registration file
    (".mcp.json", ".qoder/mcp.json"),
    # Claude Code MCP permission setting
    ("enableAllProjectMcpServers", "MCP server enablement in Qoder settings"),
    # dependency section headers
    ("### Claude Code Native", "### Qoder Native"),
    # generic platform name last
    ("Claude Code", "Qoder"),
]

TEXT_EXTENSIONS = {".md", ".markdown", ".yaml", ".yml", ".txt", ".json"}

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)


def transform_text(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def insert_usage_line(body: str, hint: str, lang: str) -> tuple[str, bool]:
    """Insert a Usage callout right after the first H1 heading."""
    label = "> **用法**：" if lang == "zh" else "> **Usage**: "
    lines = body.split("\n")
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            lines[idx + 1 : idx + 1] = ["", f"{label}`{hint}`", ""]
            return "\n".join(lines), True
    return body, False


def convert_frontmatter(text: str, skill_name: str, lang: str) -> tuple[str, list[str]]:
    """Rewrite SKILL.md frontmatter to Qoder requirements.

    Qoder requires ``name`` + ``description``; Claude Code's
    ``argument-hint`` is preserved as a Usage line below the H1 title.
    """
    warnings: list[str] = []
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, [f"{skill_name}: no YAML frontmatter found, left unchanged"]

    description = None
    hint = None
    other_lines: list[str] = []
    for line in match.group(1).splitlines():
        if line.startswith("description:"):
            description = line[len("description:") :].strip()
        elif line.startswith("argument-hint:"):
            hint = _strip_quotes(line[len("argument-hint:") :].strip())
        elif line.startswith("name:"):
            continue  # regenerated below
        else:
            other_lines.append(line)

    body = text[match.end() :]
    if hint:
        body, inserted = insert_usage_line(body, hint, lang)
        if not inserted:
            warnings.append(f"{skill_name}: no H1 heading for Usage line, hint kept in frontmatter")
            other_lines.append(f"argument-hint: {hint}")

    fm_lines = [f"name: {skill_name}"]
    if description:
        fm_lines.append(f"description: {description}")
    fm_lines.extend(other_lines)
    return "---\n" + "\n".join(fm_lines) + "\n---\n" + body, warnings


def convert_file(src: Path, dst: Path, skill_name: str | None, lang: str) -> list[str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() not in TEXT_EXTENSIONS:
        shutil.copy2(src, dst)
        return []
    text = src.read_text(encoding="utf-8")
    warnings: list[str] = []
    if skill_name is not None and src.name == "SKILL.md":
        text, warnings = convert_frontmatter(text, skill_name, lang)
    text = transform_text(text)
    dst.write_text(text, encoding="utf-8", newline="\n")
    return warnings


def wipe_generated(path: Path) -> None:
    if not path.exists():
        return
    # Safety: only ever wipe paths inside the project's .qoder/ tree.
    if ".qoder" not in path.parts:
        raise RuntimeError(f"refusing to wipe non-generated path: {path}")
    shutil.rmtree(path)


def validate_skill(skill_md: Path) -> list[str]:
    problems: list[str] = []
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return [f"{skill_md}: missing frontmatter"]
    fm = match.group(1)
    if not re.search(r"^name:\s*[a-z0-9][a-z0-9-]*\s*$", fm, re.M):
        problems.append(f"{skill_md}: invalid or missing `name` field")
    if not re.search(r"^description:\s*\S", fm, re.M):
        problems.append(f"{skill_md}: missing `description` field")
    for bad in ("mcp__", ".claude/"):
        if bad in text:
            problems.append(f"{skill_md}: leftover Claude Code token `{bad}`")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", required=True, choices=["en", "zh"])
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    i18n_dir = root / "i18n" / args.lang
    skills_src = i18n_dir / "skills"
    if not skills_src.is_dir():
        print(f"ERROR: {skills_src} not found — run from the project root", file=sys.stderr)
        return 1

    qoder_dir = root / ".qoder"
    skills_dst = qoder_dir / "skills"

    # 1. Regenerate the skill tree (idempotent wipe + rebuild).
    wipe_generated(skills_dst)
    all_warnings: list[str] = []
    skill_count = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_count += 1
        for src in sorted(skill_dir.rglob("*")):
            if src.is_file():
                rel = src.relative_to(skill_dir)
                all_warnings += convert_file(
                    src, skills_dst / skill_dir.name / rel, skill_dir.name, args.lang
                )

    # 2. Shared references (loaded by several skills via relative .qoder paths).
    shared_src = i18n_dir / "shared-references"
    if shared_src.is_dir():
        for src in sorted(shared_src.rglob("*")):
            if src.is_file():
                convert_file(src, skills_dst / "shared-references" / src.relative_to(shared_src), None, args.lang)

    # 3. Runtime contract -> AGENTS.md (the file Qoder reads automatically).
    agents_src = i18n_dir / "AGENTS.md"
    if agents_src.is_file():
        agents_text = transform_text(agents_src.read_text(encoding="utf-8"))
        (root / "AGENTS.md").write_text(agents_text, encoding="utf-8", newline="\n")
        print(f"[ok] AGENTS.md generated from i18n/{args.lang}/AGENTS.md")
    else:
        all_warnings.append(f"i18n/{args.lang}/AGENTS.md missing — AGENTS.md not generated")

    # 4. MCP registration example -> .qoder/mcp.json (kept if user edited it).
    mcp_example = root / "config" / "mcp.qoder.json.example"
    mcp_dst = qoder_dir / "mcp.json"
    if mcp_example.is_file() and not mcp_dst.exists():
        shutil.copy2(mcp_example, mcp_dst)
        print("[ok] .qoder/mcp.json created from config/mcp.qoder.json.example")

    # 5. Language marker (mirrors .claude/.current-lang).
    (qoder_dir / ".current-lang").write_text(args.lang, encoding="utf-8")

    # 6. Validate the generated tree.
    problems: list[str] = []
    for skill_md in sorted(skills_dst.glob("*/SKILL.md")):
        problems += validate_skill(skill_md)

    print(f"[ok] {skill_count} skills converted into .qoder/skills (lang={args.lang})")
    for warning in all_warnings:
        print(f"[warn] {warning}")
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}", file=sys.stderr)
        return 1
    print("[ok] validation passed: frontmatter + terminology clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
