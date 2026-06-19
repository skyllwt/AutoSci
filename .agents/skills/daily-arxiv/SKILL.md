---
name: daily-arxiv
description: "AutoSci /daily-arxiv Codex adapter. Use when the user invokes `/daily-arxiv` or asks Codex to run AutoSci's daily-arxiv workflow. Upstream behavior: Run or manage the daily arXiv recommendation feed. Use for one-off fresh-paper recommendations, scheduled GitHub Actions setup/status/disable, email digests, and explicit high-confidence auto-ingest through /ingest."
---

# AutoSci /daily-arxiv (Codex Adapter)

This is a thin Codex wrapper around AutoSci's upstream Claude Code skill.
The upstream skill remains authoritative so `setup.sh --lang ...` can refresh
language-specific workflow instructions without duplicating content.

## How To Run

When this skill is selected, first read `.claude/skills/daily-arxiv/SKILL.md` completely, then follow
that workflow as the source of truth.

Use these Codex-specific adaptations while following the upstream instructions:

- Treat AutoSci's original slash command `/daily-arxiv` as this Codex skill.
  If the user writes `/daily-arxiv ...`, execute it through this skill.
- Resolve any relative references from the upstream skill directory
  `.claude/skills/daily-arxiv`. For example, `references/foo.md` means
  `.claude/skills/daily-arxiv/references/foo.md`.
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

- Upstream skill: `.claude/skills/daily-arxiv/SKILL.md`
