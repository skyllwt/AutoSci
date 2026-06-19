---
name: exp-design
description: "AutoSci /exp-design Codex adapter. Use when the user invokes `/exp-design` or asks Codex to run AutoSci's exp-design workflow. Upstream behavior: Idea-driven experiment design with iterative ablation — method candidate generation (direct / hybrid / cross-idea combination) → benchmark selection → iterative ablation (non-linear: ablation can trigger method simplification and re-planning) → sensitivity analysis → main experiment → optional generalization → deep analysis of intermediate quantities. Use when designing a full experiment suite for an idea after pilot evaluation."
---

# AutoSci /exp-design (Codex Adapter)

This is a thin Codex wrapper around AutoSci's upstream Claude Code skill.
The upstream skill remains authoritative so `setup.sh --lang ...` can refresh
language-specific workflow instructions without duplicating content.

## How To Run

When this skill is selected, first read `.claude/skills/exp-design/SKILL.md` completely, then follow
that workflow as the source of truth.

Use these Codex-specific adaptations while following the upstream instructions:

- Treat AutoSci's original slash command `/exp-design` as this Codex skill.
  If the user writes `/exp-design ...`, execute it through this skill.
- Resolve any relative references from the upstream skill directory
  `.claude/skills/exp-design`. For example, `references/foo.md` means
  `.claude/skills/exp-design/references/foo.md`.
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

- Upstream skill: `.claude/skills/exp-design/SKILL.md`
