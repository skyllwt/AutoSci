---
name: init
description: Bootstrap AutoSci from user sources plus optional discovery, then ingest the final paper set
argument-hint: "[topic] [--no-introduction]"
---

# /init

> Build a wiki from `raw/` with deterministic source preparation, planner-guided discovery, provisional notes/web scaffolding, and sequential `/ingest`.

Use these local references on demand:

- `references/prepare-and-discovery.md` — prepare flow, final selection, fetch, and source-manifest rules
- `references/planner-policy.md` — planner behavior and LLM trim expectations
- `references/parallel-ingest.md` — optional parallel ingest via git worktrees (only when the runtime supports concurrent subagents; skip this reference in sandboxed environments)

## Inputs

- `topic` (optional): research direction keywords; omit when `raw/` already defines the seed set
- `--no-introduction` (optional): disable external discovery; use only when the user explicitly requests it
- User-owned sources under `raw/papers/`, `raw/notes/`, `raw/web/`

## Outputs

- `wiki/` scaffold and provisional pages (Summary, topics, ideas, concepts)
- `raw/tmp/` and `raw/discovered/` prepared sources
- Final paper pages via `/ingest`
- `.checkpoints/init-*.json` manifests for resume and replay
- Updated `wiki/index.md`, `wiki/log.md`, `wiki/graph/*`
- Refreshed visualization artifacts: `wiki/.obsidian/graph.json` (per-entity-type color groups) and `wiki/canvases/*.canvas` (best-effort, see Step 6). The interactive web Graph view is served by `tools/serve.py` (SPA), not regenerated as a standalone file.

## Wiki Interaction

### Reads

- `raw/papers/`, `raw/notes/`, `raw/web/`
- `.checkpoints/init-prepare.json` and `.checkpoints/init-sources.json` for resume, planning, and ingest ordering
- `wiki/index.md` plus existing `wiki/topics/`, `wiki/ideas/`, `wiki/concepts/`, `wiki/methods/` for duplicate avoidance and scaffold alignment

### Writes

- `wiki/` scaffold and provisional pages
- `raw/tmp/` and `raw/discovered/`
- `wiki/index.md`, `wiki/log.md`, `wiki/graph/*`
- `.checkpoints/init-prepare.json`, `.checkpoints/init-plan.json`, `.checkpoints/init-sources.json`, and `init-session` checkpoint metadata

### Graph edges created

- `/init` itself creates only scaffold-level edges when provisional pages need them
- all paper-driven edges are delegated to `/ingest`

## Workflow

**Pre-condition**: working directory is the project root containing `wiki/`, `raw/`, and `tools/`. Set `WIKI_ROOT=wiki/`. Resolve `PYTHON_BIN` once and reuse it for every Python command during `/init` so the workflow stays on the interpreter that `setup.sh` prepared:

```bash
if   [ -x .venv/bin/python ];         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then PYTHON_BIN=.venv/Scripts/python.exe
else                                       PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: Initialize wiki structure

```bash
"$PYTHON_BIN" tools/research_wiki.py init wiki/
```

Create the standard wiki directories, `graph/`, `outputs/`, `index.md`, and `log.md`. Do not add a second init log entry here.

### Step 2: Prepare local inputs into `raw/tmp/`

```bash
"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json
```

- before running `prepare`, inspect each local PDF and write the recovery handoff to `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }` or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title", "arxiv_id": "2401.00001" } }` when a confident arXiv ID is already known
- use `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]` for local paper normalization
- local PDF recovery order is strict: handed-off arXiv ID or filename/path arXiv ID -> agent-recovered title via Semantic Scholar -> fetched arXiv source -> synthetic `.tex`
- when the agent supplied a PDF title, treat that title as authoritative for the prepared manifest; fetched/source titles are display-only fallback metadata
- do not use PDF metadata or PDF body text as arXiv-ID hints during prepare
- when arXiv ID recovery succeeds, prefer fetched raw TeX source over synthetic `.tex`
- the prepare subcommand delegates to `prepare_paper_source.py` internally; do not call `prepare_paper_source.py` directly during `/init` Step 2

### Step 3: Provisional notes/web scaffolding and planner

```bash
"$PYTHON_BIN" tools/init_discovery.py plan \
  [--topic "<topic>"] \
  --mode auto \
  --raw-root raw \
  --wiki-root wiki \
  --prepared-manifest .checkpoints/init-prepare.json \
  --allow-introduction <true|false> \
  --output-plan .checkpoints/init-plan.json
```

- omit `--topic` when the user supplied no topic
- `--allow-introduction true` unless user passed `--no-introduction`
- the planner reads `.checkpoints/init-prepare.json` for local context
- it may create provisional `wiki/topics/`, `wiki/ideas/`, `wiki/concepts/` pages seeded from notes/web
- notes/web-derived pages must carry the exact provisional notice: `> ⚠️ **PROVISIONAL PAGE** — auto-generated from notes/web during /init. Does not (yet) cite a peer-reviewed source. Treat claims with caution.`
- planner details and selection policy are in `references/planner-policy.md`

### Step 4: Fetch external papers and write source manifest

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch \
  --raw-root raw \
  --plan-json .checkpoints/init-plan.json \
  --prepared-manifest .checkpoints/init-prepare.json \
  --output-sources .checkpoints/init-sources.json \
  --id <candidate-id> --id <candidate-id> ...
```

- pass every external candidate ID from the plan's shortlist (including zero IDs when no external papers were selected)
- external papers download to `raw/discovered/`, never `raw/papers/`
- the fetch subcommand writes `.checkpoints/init-sources.json` which is the single source of truth for Step 5
- see `references/prepare-and-discovery.md` for source preference and manifest schema

### Step 5: Ingest papers

Paper sources come strictly from `.checkpoints/init-sources.json`:

- `origin=user_local`: canonical prepared path under `raw/tmp/` when available, otherwise fallback `raw/papers/...`
- `origin=introduced`: fetched dirs or PDFs under `raw/discovered/`

Execute `/ingest` for each paper **sequentially** in `shortlist_rank` order:

- execute `/ingest` for exactly one source path per turn
- in INIT MODE, consume the handed-off `canonical_ingest_path` exactly as provided
- skip `fetch_s2.py citations`
- skip `fetch_s2.py references`
- skip per-paper `rebuild-index`, `rebuild-context-brief`, `rebuild-open-questions`
- skip conflict-prone topic writes
- record each paper's result in checkpoint metadata (`checkpoint-set-meta wiki/ init-session ingest:<candidate_id> <status>`) as papers complete
- on single-paper failure: record via checkpoint, skip it, continue the rest

> **Parallel ingest** (optional): when the runtime supports concurrent subagents and `git worktree`, you may use the parallel fan-out / fan-in workflow in `references/parallel-ingest.md` instead of the sequential loop above. Do NOT attempt parallel ingest in sandboxed environments where `git worktree add`, concurrent subagent sessions, or `git merge` are unavailable.

### Step 6: Rebuild, citation backfill, visualize, and final report

After all papers are ingested:

```bash
"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/
"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix
```

Then backfill `cites` edges via Semantic Scholar — `fetch_s2.py references` was skipped per-paper and must be reinstated here. Best-effort: S2 outages must not fail `/init`.

```bash
"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/ \
  || echo "WARN: citation backfill failed or partial; check stderr above" >&2
```

Then regenerate visualization artifacts (best-effort; visualize failure must not fail `/init`). `generate-obsidian-config` rewrites `wiki/.obsidian/graph.json` from `config/visualize.json` so the per-entity-type color groups stay in sync with the runtime config.

```bash
"$PYTHON_BIN" tools/visualize.py generate-obsidian-config wiki/ \
  || echo "WARN: visualize generate-obsidian-config failed; run /visualize manually" >&2
"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/ \
  || echo "WARN: visualize generate-canvas failed; run /visualize manually" >&2
```

Report separately:

- user-provided papers ingested through prepared `raw/tmp/` paths
- user-provided papers that fell back to original `raw/papers/` paths
- discovered papers from `raw/discovered/`
- provisional pages seeded from notes/web
- pages created by `/ingest`
- pages updated by `/ingest`
- any skipped or failed papers
- visualization refresh status (Canvas + HTML succeeded, or which step warned)

## Constraints

- Do not infer `--no-introduction` from repository state alone. Use it only when the user explicitly asked to disable external discovery.
- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs
- `raw/tmp/` and `raw/discovered/` are generated handoff areas; direct local `/ingest` may also prepare reusable local sidecars under `raw/tmp/`
- `/init` may write external papers only to `raw/discovered/`; `/init` and direct local `/ingest` may write generated prepared local sources to `raw/tmp/`
- `/prefill` is optional background seeding, not part of `/init`
- no skill other than `/prefill` may auto-create foundations
- `/init` must not create `people/` pages directly
- notes/web-derived pages are provisional and must carry the exact notice line above
- paper evidence outranks notes/web for concept consolidation and method extraction
- all paper ingest must run through `/ingest`
- Step 5 must read paper inputs from `.checkpoints/init-sources.json`, not by ad hoc folder scanning
- exact deterministic planner policy belongs in `tools/init_discovery.py`, not in duplicated skill constants

## Error Handling

- **No parseable paper in `raw/papers/`**: enter bootstrap mode
- **`raw/notes/` and `raw/web/` empty**: skip provisional seeding, continue
- **PDF decode fails during prepare**: keep the local source, record the warning in `.checkpoints/init-prepare.json`, and fall back to the original path if needed
- **No confident PDF title is recovered**: omit `--title`, allow filename/path arXiv-ID recovery only, then fall back directly to synthetic `.tex`; any metadata-or-filename title is display-only
- **Chinese content is detected in `raw/notes/` or `raw/web/`**: keep going, but preserve a planner warning that note/web extraction and ranking may be less reliable and treat rankings plus provisional pages as lower-confidence
- **S2 or DeepXiv unavailable**: planner falls back to the remaining sources; preserve the warning in the checkpointed plan and note degraded discovery in the report
- **External fetch fails for one paper**: keep the remaining final set and report the failed download
- **Single paper ingest fails**: record it via checkpoint, skip it, continue the rest, and list it in the report
- **Visualization regeneration fails**: warn and continue; never fail `/init`. The user can rerun `/visualize --canvas --html` separately to diagnose

## Dependencies

### Tools (via Bash)

- `"$PYTHON_BIN" tools/research_wiki.py init wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py checkpoint-set-meta wiki/ init-session <key> <value>`
- `"$PYTHON_BIN" tools/research_wiki.py checkpoint-save/load/clear wiki/ init-session ...`
- `"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"`
- `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"]`
- `"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`
- `"$PYTHON_BIN" tools/init_discovery.py plan [--topic "<topic>"] --mode auto --raw-root raw --wiki-root wiki --prepared-manifest .checkpoints/init-prepare.json --allow-introduction <true|false> --output-plan .checkpoints/init-plan.json`
- `"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id>`
- `"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix`
- `"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/`
- `"$PYTHON_BIN" tools/visualize.py generate-obsidian-config wiki/`
- `"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/`

### Skills

- `/ingest` — one paper per invoke, in INIT MODE
- `/visualize` — Step 6 regenerates Obsidian graph color groups and Canvas by calling `tools/visualize.py` directly (best-effort); the user may also invoke `/visualize` manually later for `--focus` views or to re-render after editing `config/visualize.json`

### External APIs used by `init_discovery.py`

- Semantic Scholar
- DeepXiv (optional)
- arXiv download endpoints
