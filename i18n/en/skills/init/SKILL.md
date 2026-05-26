---
description: Bootstrap ΩmegaWiki from user sources plus optional discovery, then ingest the final paper set in parallel
argument-hint: "[topic] [--no-introduction]"
---

# /init

> Build a wiki from `raw/` with deterministic source preparation, planner-guided discovery, provisional notes/web scaffolding, and parallel `/ingest` fan-out/fan-in.

Use these local references on demand:

- `references/prepare-and-discovery.md` — prepare flow, final selection, fetch, and source-manifest rules
- `references/planner-policy.md` — planner behavior and LLM trim expectations
- `references/parallel-ingest.md` — worktree isolation, subagent prompt contract, merge, and cleanup

## Inputs

- `topic` (optional): research direction keywords; omit when `raw/` already defines the seed set
- `--no-introduction` (optional): disable external discovery; use only when the user explicitly requests it
- User-owned sources under `raw/papers/`, `raw/notes/`, `raw/web/`

## Outputs

- `wiki/` scaffold and provisional pages (Summary, topics, ideas, concepts)
- `raw/tmp/` and `raw/discovered/` prepared sources
- Final paper pages via parallel `/ingest` subagents
- `.checkpoints/init-*.json` manifests for resume and replay
- Updated `wiki/index.md`, `wiki/log.md`, `wiki/graph/*`
- Refreshed visualization artifacts: `wiki/.obsidian/graph.json` (per-entity-type color groups) and `wiki/canvases/*.canvas` (best-effort, see Step 6). The interactive web Graph view is served by `tools/serve.py` (SPA), not regenerated as a standalone file.

## Wiki Interaction

### Reads

- `raw/papers/`, `raw/notes/`, `raw/web/`
- `.checkpoints/init-prepare.json` and `.checkpoints/init-sources.json` for resume, planning, and fan-out
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
# Find the project root via git so worktree subagents can still locate .venv.
# .venv is gitignored, so a subagent whose cwd is ../.worktrees/<branch>/
# doesn't have one — without this lookup it falls back to system python3 and
# misses the .env-loaded API keys plus the installed deps (deepxiv-sdk etc.).
# git rev-parse --git-common-dir returns the main repo's .git regardless of
# which worktree the shell is in; its parent is the project root.
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi

if   [ -x "$PROJECT_ROOT/.venv/bin/python" ];         then PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -x .venv/bin/python ];                         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ];                 then PYTHON_BIN=.venv/Scripts/python.exe
else                                                       PYTHON_BIN=python3
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
- when the agent supplied a PDF title, treat that title as authoritative for the prepared manifest; fetched/source titles are sanitized fallback metadata only and must not overwrite it
- do not use PDF metadata or body text as arXiv-ID hints during prepare
- metadata or filename titles may remain as provisional display labels only; they are not trusted identity or title-search inputs
- keep notes/web on their original source paths; `/init` reads them directly during planning
- set each local paper's `canonical_ingest_path` to a prepared `raw/tmp/` path when available; otherwise fall back to the original `raw/papers/...` path
- record warnings for failed decode / title recovery / arXiv source fetch rather than aborting `/init`
- see `references/prepare-and-discovery.md` for the prepare decision tree and source-preference rules

### Step 3: Plan discovery, trim the final set, and write the source manifest

```bash
"$PYTHON_BIN" tools/init_discovery.py plan [--topic "<topic>"] --mode auto --raw-root raw --wiki-root wiki --prepared-manifest .checkpoints/init-prepare.json --allow-introduction <true|false> --output-plan .checkpoints/init-plan.json
```

- `mode=seeded` when the prepare manifest contains at least one parseable local paper; otherwise `mode=bootstrap`
- `plan` must read `.checkpoints/init-prepare.json` instead of rescanning `raw/`
- planner policy is qualitative at the skill layer: favor relevance, freshness, connectivity, and survey coverage
- in seeded mode with limited introduced capacity, avoid over-prioritizing older citation-heavy anchors
- in bootstrap mode, one older canonical anchor may be useful when it improves coverage
- when DeepXiv search is available, use returned `relevance_score` in tool scoring rather than merely noting it in prose
- exact ranking weights, shortlist constants, and threshold math belong to `tools/init_discovery.py`; treat the tool as the implementation authority and do not restate or override its constants in LLM reasoning
- read `.checkpoints/init-plan.json` and explicitly trim the over-picked `shortlist` to a final **8-10** papers total before `fetch`
- emit an explicit final selection artifact before `fetch` with `shortlist_count`, `final_count`, and the exact final `candidate_id` list in shortlist order
- if `final_count` falls outside **8-10**, stop and revise the final selection before `fetch`, unless `--no-introduction` is active or the user already supplied more than 10 parseable papers
- if `--no-introduction` is present, only use this branch when the user explicitly requested local-only behavior; still run `fetch` with zero external IDs so it writes `.checkpoints/init-sources.json`
- see `references/planner-policy.md` for planner behavior, trim expectations, and source-of-truth boundaries

Then run:

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id> --id <candidate-id>
```

- external papers downloaded by `/init` go to `raw/discovered/`, never `raw/papers/`
- never fetch a paper that is already represented by a prepared local source from `raw/tmp/`
- `.checkpoints/init-sources.json` is the single source of truth for downstream ingest order

### Step 4: Create scaffold pages before paper ingest

Create one `wiki/Summary/{area}.md`, the needed `wiki/topics/{slug}.md`, and provisional `ideas/`, `concepts/`, and (optionally) `methods/` from notes/web when warranted.

Rules:

- notes/web are authoritative for user intent, not for literature confidence
- every notes/web-derived page must include this exact line immediately after frontmatter:

```markdown
Provisional note: seeded from raw/notes or raw/web during /init; pending validation from ingested papers.
```

- `topics/`: create when a direction is explicit or repeated
- `ideas/`: create when the user states or strongly implies a research direction or hypothesis
- `concepts/`: create only when the mechanism recurs across notes/web, or appears once in notes/web and once in the final paper set
- `methods/`: do not create from `/init` unless the user explicitly names a reusable, citable method in notes/web; ingest is responsible for promoting paper methods into reusable method entities
- `/prefill` is optional background seeding and is not part of `/init`
- `/init` must not create `people/` pages directly and must not auto-create foundations

### Step 5: Parallel paper ingest with worktree isolation

Paper sources for this step come strictly from `.checkpoints/init-sources.json`:

- `origin=user_local`: canonical prepared `.tex` under `raw/tmp/` when available, otherwise fallback `raw/papers/...`
- `origin=introduced`: fetched dirs or PDFs under `raw/discovered/`

Parallel ingest contract:

- stash unrelated dirty files before fan-out, then record `stash_ref`, `base_branch`, and `base_commit` in checkpoint metadata
- commit the freshly created scaffold and init manifests before fan-out so `BASE_COMMIT` actually contains the pages, manifests, and handoff metadata that subagents must branch from
- verify `.gitattributes` contains `merge=union` for `wiki/log.md`, `wiki/graph/edges.jsonl`, `wiki/graph/citations.jsonl`, and `wiki/index.md` before creating worktrees
- `/init` worktree mode must run from a named branch, not detached HEAD
- create each worktree from `BASE_COMMIT`, not from the already checked-out `BASE_BRANCH`
- subagent prompts must use **relative paths only**, and the subagent's shell working directory must be the worktree path (`$WT_PATH`), not the main repository root
- execute `/ingest` for exactly one handed-off source path; do not bypass `/ingest`
- in INIT MODE, consume the handed-off canonical path exactly as provided
- skip `fetch_s2.py citations`
- skip `fetch_s2.py references`
- skip per-subagent `rebuild-index`
- skip per-subagent `rebuild-context-brief`
- skip per-subagent `rebuild-open-questions`
- skip conflict-prone topic writes
- commit the ingest result inside the worktree before exiting so fan-in merges a real paper-specific commit instead of an empty branch
- see `references/parallel-ingest.md` for worktree commands, merge order, fan-in, and cleanup

### Step 6: Fan-in, rebuild, and final report

After all subagents complete:

- merge worktree branches sequentially on `BASE_BRANCH`
- resolve true concept / method conflicts conservatively: merge, do not multiply near-duplicates
- run:

```bash
"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/
"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix
```

Then backfill `cites` edges via Semantic Scholar — `fetch_s2.py references` was skipped per-worktree (parallel safety) and must be reinstated serially here. Best-effort: S2 outages must not fail `/init`.

```bash
"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/ \
  || echo "WARN: citation backfill failed or partial; check stderr above" >&2
```

Then regenerate visualization artifacts (best-effort; visualize failure must not fail `/init`). `generate-obsidian-config` rewrites `wiki/.obsidian/graph.json` from `config/visualize.json` so the per-entity-type color groups stay in sync with the runtime config — Obsidian's graph view shows uncolored nodes when `colorGroups` is empty, so this step keeps the graph readable across rebuilds.

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

If `stash_ref` exists, pop it at the end. If stash pop fails, keep the checkpoint and report the failure.

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
- all paper ingest must run through parallel `/ingest` subagents with worktree isolation
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
- **Current checkout is detached HEAD**: stop before worktree fan-out and ask the user to switch to or create a named branch first
- **stash pop fails**: keep checkpoint metadata and report the manual recovery step
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
- `"$PYTHON_BIN" tools/visualize.py generate-obsidian-config wiki/`
- `"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/`

### Skills

- `/ingest` — one paper per subagent, in INIT MODE
- `/visualize` — Step 6 fan-in regenerates Obsidian graph color groups, Canvas, and HTML by calling `tools/visualize.py` directly (best-effort); the user may also invoke `/visualize` manually later for `--focus` views or to re-render after editing `config/visualize.json`

### External APIs used by `init_discovery.py`

- Semantic Scholar
- DeepXiv (optional)
- arXiv download endpoints
