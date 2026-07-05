# AutoSci Codex Migration Plan

This document tracks the migration state of the `migrate-codex` branch as of
commit `0f5ccb9` (`origin/migrate-codex`). It replaces the initial plan that was
written before this branch already contained Codex migration work.

## Current Branch State

The branch already contains substantial Claude Code + Codex dual-runtime work:

- `AGENTS.md`, `i18n/en/AGENTS.md`, and `i18n/zh/AGENTS.md` exist as Codex-facing runtime instructions.
- `.agents/skills/` exists and contains repo-scoped Codex skills generated from the i18n skill sources.
- Existing `.claude/skills/` remains for Claude Code compatibility.
- `setup.sh` and `setup.ps1` check for either Claude Code or Codex and activate both `.claude/skills` and `.agents/skills`.
- README, the local SPA command helpers, and `tools/serve.py` have started moving from Claude-only slash commands to Claude `/skill` plus Codex `$skill` wording.
- `tools/_sandbox.py` and the `AGENTS.md` sandbox section document Codex network escalation behavior for Python tools.

## Status By Original Plan

### 1. Project Instructions — Done

- `AGENTS.md` is present and acts as the Codex companion to `CLAUDE.md`.
- `i18n/en/AGENTS.md` and `i18n/zh/AGENTS.md` are present.
- The current guidance explicitly distinguishes Claude Code slash commands from Codex `$skill` invocation.
- Setup syncs the selected language's `AGENTS.md` to the root.

Remaining cleanup:

- Keep `AGENTS.md` and `CLAUDE.md` equivalent for shared repository rules, but avoid adding developer-only coding policy to the user-facing runtime contract.

### 2. Skill Directory Migration — Mostly Done

- `.agents/skills/` exists and includes the full skill tree plus references.
- `SKILL.md` files include required `name:` metadata.
- `.claude/skills/` remains in place for compatibility.
- `i18n/<lang>/skills` remains the source of truth.
- Skill references have been made runtime-neutral for shared references,
  `llm-review` MCP calls, native capability headings, and interactive prompts.

Remaining cleanup:

- Keep `.agents/skills` committed for now so Codex repo-scoped skills work
  immediately after checkout. Treat `.agents/skills` and `.claude/skills` as
  generated active copies: edit `i18n/<lang>/skills`, run setup, and commit the
  regenerated output together.
- Continue migrating the remaining genuinely runtime-specific workflows one at a
  time instead of masking unsupported behavior with neutral wording.

### 3. MCP Configuration — Partly Done

- Claude MCP config still exists via `.mcp.json` and `.claude/settings.local.json`.
- Current Codex CLI reads MCP server config from the user-level
  `$CODEX_HOME/config.toml` (usually `~/.codex/config.toml`), not from a
  repository-local `.codex/config.toml`.
- `config/codex.config.toml.example` now provides the `llm-review` MCP snippet,
  and `config/README.md` documents the `codex mcp add ...` setup path.

Next steps:

- Decide whether setup should ever offer to write the user-level Codex config.
  Default should remain documentation-only, because setup should not silently
  mutate files outside the repository.
- If Codex later gains repository-local MCP config support, revisit whether a
  checked-in `.codex/config.toml` is useful.

### 4. Setup Scripts — Mostly Done

- `setup.sh` and `setup.ps1` now accept either Claude Code or Codex.
- Setup activates both `CLAUDE.md` and `AGENTS.md`.
- Setup syncs both `.claude/skills` and `.agents/skills`.
- `.agents/.current-lang` is ignored.

Remaining cleanup:

- Consider adding a setup option that prints or installs the Codex MCP snippet,
  but do not silently modify `~/.codex/config.toml`.
- If stale files become a recurring problem, make setup delete each active skill
  directory before copying from `i18n/<lang>/skills`.

### 5. User Entrypoints And Docs — Partly Done

- README, SPA UI text, and `tools/serve.py` already contain some Codex `$skill` support.
- The project now distinguishes Claude `/init` from Codex `$init` in some places.

Remaining cleanup:

- Audit all user-facing docs and UI for stale "Claude Code only" wording.
- Ensure generated commands in the SPA use the correct runtime-specific form.
- Document Codex invocation clearly: `$setup`, `$init`, `$ingest`, or selecting skills from Codex `/skills`.
- Keep Claude Code usage documented as compatibility, not as the only path.

### 6. Complex Workflows — Not Done

The following workflows still need dedicated migration work because they rely on
Claude-specific interaction or execution assumptions:

- `/init`: parallel `/ingest` fan-out/fan-in and subagent orchestration.
- `/poster`: image/multimodal review and interactive prompt flows.
- `/research`, `/exp-design`, `/exp-run`: manual gates and runtime-specific interaction assumptions.
- `daily-arxiv` CI: currently tied to Claude Code Action assumptions and auth.

These should be migrated one workflow at a time with tests or dry-run scripts.

## Recommended Next Execution Order

1. Finish user-facing docs and SPA command text.
2. Rework `/init` subagent orchestration for Codex.
3. Rework `/poster` and interactive gate-heavy workflows.
4. Design a separate Codex-compatible CI story for `daily-arxiv`.

## Known Risks

- Maintaining `i18n/*/skills`, `.claude/skills`, and `.agents/skills` creates drift risk. Setup should be the only normal way to regenerate active skill trees.
- If `.agents/skills` is committed, reviewers must treat it as generated output and verify it matches `i18n/<lang>/skills`.
- Codex built-in slash commands such as `/init` and `/review` can collide conceptually with AutoSci skill names. User docs should prefer `$init`, `$review`, or `/skills`.
- Network-dependent tools require Codex sandbox escalation. The `SANDBOX GATE` behavior must stay visible and consistent.
