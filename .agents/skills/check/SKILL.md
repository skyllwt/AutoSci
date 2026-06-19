---
name: check
description: "AutoSci /check Codex adapter. Use when the user invokes `/check` or asks Codex to run AutoSci's check workflow. Upstream behavior: Scan the full wiki to detect health issues and produce a tiered fix-recommendation report (covers all entity types in runtime/schema/entities.yaml + graph consistency)"
---

# AutoSci /check (Codex Adapter)

This is a thin Codex wrapper around AutoSci's upstream Claude Code skill.
The upstream skill remains authoritative so `setup.sh --lang ...` can refresh
language-specific workflow instructions without duplicating content.

## How To Run

When this skill is selected, first read `.claude/skills/check/SKILL.md` completely, then follow
that workflow as the source of truth.

Use these Codex-specific adaptations while following the upstream instructions:

- Treat AutoSci's original slash command `/check` as this Codex skill.
  If the user writes `/check ...`, execute it through this skill.
- Resolve any relative references from the upstream skill directory
  `.claude/skills/check`. For example, `references/foo.md` means
  `.claude/skills/check/references/foo.md`.
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

- Upstream skill: `.claude/skills/check/SKILL.md`
