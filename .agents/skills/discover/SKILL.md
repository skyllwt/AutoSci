---
name: discover
description: "AutoSci /discover Codex adapter. Use when the user invokes `/discover` or asks Codex to run AutoSci's discover workflow. Upstream behavior: Build a ranked shortlist of candidate papers (anchor-driven, topic-driven, or derived from current wiki state) that the user — or an upstream skill — may decide to feed into `/ingest`. Use whenever the user asks \"what should I read next\", \"find papers similar to this one\", \"recommend related work\", \"what's around this topic\", or whenever `/ingest` is invoked with `--discover`. Does not ingest; only proposes."
---

# AutoSci /discover (Codex Adapter)

This is a thin Codex wrapper around AutoSci's upstream Claude Code skill.
The upstream skill remains authoritative so `setup.sh --lang ...` can refresh
language-specific workflow instructions without duplicating content.

## How To Run

When this skill is selected, first read `.claude/skills/discover/SKILL.md` completely, then follow
that workflow as the source of truth.

Use these Codex-specific adaptations while following the upstream instructions:

- Treat AutoSci's original slash command `/discover` as this Codex skill.
  If the user writes `/discover ...`, execute it through this skill.
- Resolve any relative references from the upstream skill directory
  `.claude/skills/discover`. For example, `references/foo.md` means
  `.claude/skills/discover/references/foo.md`.
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

- Upstream skill: `.claude/skills/discover/SKILL.md`
