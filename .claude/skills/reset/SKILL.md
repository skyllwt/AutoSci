---
name: reset
description: Reset wiki state to a clean scaffold by scope (wiki / raw / log / checkpoints / all). Useful during development or carefree restarts after a botched setup.
argument-hint: "--scope wiki|raw|log|checkpoints|all"
---

# /reset

> Resets generated AutoSci state by scope. Designed for development iteration and recovery after a failed setup — not a routine operation.

## Trigger

Manual: `/reset --scope wiki` in Claude Code or `$reset --scope wiki` in Codex. Supported scopes are `wiki`, `raw`, `log`, `checkpoints`, and `all`. Multiple scopes may be combined comma-separated: `--scope wiki,log`.

## Inputs

- `--scope` *(required)*: one of
  - `wiki` — delete every `*.md` under `wiki/<entity>/` and `wiki/outputs/`, plus `wiki/index.md`, `wiki/log.md`, and `wiki/graph/` files. Preserves `.gitkeep` and `wiki/CLAUDE.md`.
  - `raw` — delete generated entries under `raw/discovered/` and `raw/tmp/` (except `.gitkeep`). Preserve user-owned `raw/papers/`, `raw/notes/`, and `raw/web/`.
  - `log` — reset `wiki/log.md` to the empty header.
  - `checkpoints` — clear batch state via `research_wiki.py checkpoint-clear`.
  - `all` — every scope above.

## Outputs

- Cleared / reset files on disk.
- Console summary of deleted files and reset files.

## Wiki Interaction

### Reads
- All `wiki/<entity>/*.md` (to enumerate the deletion plan).
- `raw/discovered/*` and `raw/tmp/*` (to enumerate generated raw deletions).

### Writes
- Deletes `wiki/<entity>/*.md` (preserves `.gitkeep`).
- Rewrites `wiki/index.md`, `wiki/graph/*`, optionally `wiki/log.md`.
- Deletes generated `raw/discovered/*` and `raw/tmp/*` (except `.gitkeep`). Never deletes user-owned `raw/papers/`, `raw/notes/`, or `raw/web/`.

## Workflow

**Pre-conditions**: working directory contains `wiki/`, `tools/`. Set `WIKI_ROOT=wiki/`.

### Step 1: Build the deletion plan (dry-run)

```bash
python3 tools/reset_wiki.py --scope <scope>
```

This prints a JSON plan listing every file that would be deleted or reset, **without modifying anything**. Display the plan to the user grouped by scope (wiki entity dirs, raw subdirs, log, checkpoints).

### Step 2: Confirm with the user

Print the plan summary and ask for explicit confirmation:

```
About to delete N files and reset M files. Continue? [y/N]
```

If the user says no, exit. **Never proceed without explicit approval** — `/reset` is destructive and `raw/` deletions are not tracked by git.

### Step 3: Execute

```bash
python3 tools/reset_wiki.py --scope <scope> --yes
```

The tool prints a JSON status report (`{deleted_files, reset_files}`).

### Step 4: Log (unless `log` scope was reset)

If the executed scope did not include `log`, append a log entry so future sessions can see the reset happened:

```bash
python3 tools/research_wiki.py log wiki/ "reset | scope: <scope>"
```

### Step 5: Report

Print the result and suggest next steps:

```
## Reset complete — scope: <scope>

Deleted: N files
Reset:   M files

Next steps:
- /init in Claude Code or $init in Codex       — bootstrap wiki from raw/
- /prefill in Claude Code or $prefill in Codex — seed foundational background
- /ingest in Claude Code or $ingest in Codex   — add a single source manually
```

## Constraints

- **Confirm before destructive action**: never call `--yes` without showing the plan and asking the user.
- **Preserves**: `.gitkeep` placeholders, `wiki/CLAUDE.md`, `.claude/`, and `.agents/` (skills are never touched).
- **User-owned raw is never deleted**: `raw/papers/`, `raw/notes/`, and `raw/web/` are read-only to this skill even under `raw` or `all` scope. The helper clears only generated `raw/discovered/` and `raw/tmp/`.
- **`/reset` does not touch `tools/`, `mcp-servers/`, `i18n/`, `.env`, or git state.**
- **Scope is required**: no default action (`/reset` with no flag prompts for scope rather than guessing).

## Error Handling

- **Unknown scope**: print valid scopes and exit nonzero.
- **Missing wiki directory**: report and suggest running `/init`.
- **`checkpoint-clear` failure**: log a warning but do not fail other scopes.

## Dependencies

### Tools (via Bash)
- `python3 tools/reset_wiki.py --scope <scope> [--yes] [--project-root .]` — deterministic destructive helper; `raw` scope is limited to generated `raw/discovered/` and `raw/tmp/`
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `reset_wiki.py` clears `wiki/.checkpoints/*.json` directly for `checkpoints` scope (no CLI dispatch — the `checkpoint-clear` subcommand requires a specific `task_id`, while `/reset --scope checkpoints` semantics is "clear everything")
