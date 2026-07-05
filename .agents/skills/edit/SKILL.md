---
name: edit
description: Add or remove raw sources, or update wiki content, per user request
argument-hint: "[request]"
---

# /edit

> Add or remove raw sources, or update wiki content, per user request.

## Trigger

User manual: `/edit <user request>`

## Inputs

User request, for example:
- "Download this paper to raw/papers/"
- "Delete raw/papers/xxx.pdf"
- "Update the SOTA tracker in topics/efficient-llm-adaptation"
- "Add a new variant to concepts/lora"

## Outputs

Updated wiki files, `index.md`, `log.md`

## Steps

### STEP 1: Parse User Intent

1. **Add raw sources**:
   - If the user provides a local path: copy to the corresponding directory under `raw/`
   - If the user provides an arXiv URL: download to `raw/papers/`
   - If the user provides a web URL: fetch content with markdownify and save to `raw/web/`
2. **Delete raw sources**:
   - Confirm then execute deletion
3. **Update wiki**:
   - Read the relevant pages and modify content per user instructions

### STEP 2: Execute Updates

1. Newly added raw sources can later be incorporated into the wiki via `/ingest`
2. Direct wiki modifications: update the specified fields/content in specific pages per user instructions
3. When writing forward links, simultaneously write reverse links

### STEP 3: Update Navigation

1. `EDIT wiki/index.md`: update relevant entries
2. `APPEND wiki/log.md`: `## [{date}] update | {description}`

### STEP 4: Report

- List all changes made
- Suggest follow-up actions (e.g. ingest newly added raw sources if applicable)

## Constraints

- `raw/` is read-only for existing files (this skill may add files to `raw/`, but must not modify existing ones)
- Wiki modifications must follow template structure
- Bidirectional links must be kept in sync
