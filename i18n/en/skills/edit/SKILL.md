---
name: edit
description: Update wiki content or prepare generated raw inputs per user request without mutating user-owned raw sources
argument-hint: "[request]"
---

# /edit

> Update wiki content or prepare generated raw inputs per user request. User-owned raw sources remain read-only.

## Trigger

User manual: `/edit <user request>` in Claude Code or `$edit <user request>` in Codex.

## Inputs

User request, for example:
- "Download this paper for later ingest"
- "Prepare this arXiv source under raw/discovered/"
- "Plan deletion of raw/papers/xxx.pdf"
- "Update the SOTA tracker in topics/efficient-llm-adaptation"
- "Add a new variant to concepts/lora"

## Outputs

Updated wiki files, `index.md`, `log.md`, and optionally generated helper files under `raw/discovered/` or `raw/tmp/`.

## Steps

### STEP 1: Parse User Intent

1. **Prepare generated raw inputs**:
   - If the user provides a local path under `raw/papers/`, `raw/notes/`, or `raw/web/`: treat it as read-only input and do not copy, rewrite, or delete it.
   - If the user provides an arXiv URL and asks the agent to fetch it: write generated source artifacts only under `raw/discovered/`.
   - If the user provides temporary intermediate content: write only under `raw/tmp/`.
   - Do not write fetched web content to `raw/web/`; that directory is user-owned. Use `raw/tmp/` for temporary generated web extracts unless a different writable path is explicitly documented.
2. **Delete raw sources**:
   - Do not delete files under `raw/papers/`, `raw/notes/`, or `raw/web/`. Present a deletion plan and tell the user these user-owned files must be removed by the user or through a separately authorized destructive operation.
   - Generated files under `raw/discovered/` or `raw/tmp/` may be removed only after explicit confirmation.
3. **Update wiki**:
   - Read the relevant pages and modify content per user instructions

### STEP 2: Execute Updates

1. Generated raw inputs can later be incorporated into the wiki via `/ingest` in Claude Code or `$ingest` in Codex.
2. Direct wiki modifications: update the specified fields/content in specific pages per user instructions
3. When writing forward links, simultaneously write reverse links

### STEP 3: Update Navigation

1. `EDIT wiki/index.md`: update relevant entries
2. `APPEND wiki/log.md`: `## [{date}] update | {description}`

### STEP 4: Report

- List all changes made
- Suggest follow-up actions (e.g. ingest newly added raw sources if applicable)

## Constraints

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned and read-only. This skill must not create, overwrite, move, or delete files there.
- Skill-generated raw artifacts may be written only under `raw/discovered/` or `raw/tmp/`.
- Wiki modifications must follow template structure
- Bidirectional links must be kept in sync
