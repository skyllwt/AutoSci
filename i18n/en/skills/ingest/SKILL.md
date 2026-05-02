---
description: Ingest a paper into the wiki — creates pages (papers + concepts + people + claims) and builds all cross-references and graph edges. Trigger whenever the user says "ingest", "add this paper", drops a `.pdf` / `.tex` / arXiv URL, or asks to fold a paper into the knowledge base.
argument-hint: <local-path-or-arXiv-URL> [--discover]
---

# /ingest

Turn one paper into a fully wired set of wiki pages. Emit well-formed entities and correct cross-references; leave semantic audits (backlink symmetry, dangling nodes, field-value policing) for `/check`.

Use these local references on demand:

- `references/pdf-preprocessing.md` — arXiv-ID recovery, tex fetching, prepare-paper handoff for direct PDF drops
- `references/dedup-policy.md` — merge-vs-create decision rule for concepts and claims, and the line that separates `/ingest` shape checks from `/check` semantic audits
- `references/cross-references.md` — forward/reverse link matrix and paper-to-paper edge-type selection
- `references/init-mode.md` — manifest-driven handoff from `/init` and parallel-safety conventions
- `references/error-handling.md` — source parse, API, and slug-collision fallbacks

Open `runtime/schema/entities.yaml` for frontmatter field definitions and `runtime/templates/{kind}.md.tmpl` for body section structure. For `index.md`, `log.md`, and `graph/` shapes, see `runtime/schema/conventions.yaml` and `runtime/schema/edges.yaml`.

## Inputs

- `source`: one of — arXiv URL (e.g. `https://arxiv.org/abs/2106.09685`), local `.tex`, local `.pdf`, or a `canonical_ingest_path` handed off by `/init` via `.checkpoints/init-sources.json`(see `references/init-mode.md`)
- `--discover` (optional, default **off**): after the final report, invoke `/discover --anchor <this-paper's-arxiv-id>` and append the shortlist to the report as "Related papers you may want to ingest next". Never auto-ingests the suggestions. Skipped automatically in INIT MODE. Treat this as a user-owned flag: do not set it based on repo state.

## Outputs

- One fully-wired paper page plus linked entities (concepts, claims, people)
- Graph edges and citations appended via `tools/research_wiki.py`
- Terminal summary with page counts and suggested follow-up ingests

## Wiki Interaction

### Reads

- `wiki/index.md` for existing slugs and tags
- `wiki/papers/*.md` to detect an already-ingested paper
- `wiki/concepts/*.md` and `wiki/foundations/*.md` for dedup matches
- `wiki/claims/*.md` for dedup matches
- `wiki/people/*.md` for existing authors
- `wiki/topics/*.md` to place the paper under existing topics
- `wiki/graph/open_questions.md` to notice when the paper addresses a known gap

### Writes

- `wiki/papers/{slug}.md` — CREATE
- `wiki/concepts/{slug}.md` — CREATE (new) or EDIT (append `key_papers`, aliases, variants)
- `wiki/claims/{slug}.md` — CREATE (new) or EDIT (append `evidence` entry)
- `wiki/people/{slug}.md` — CREATE (importance ≥ 4 only) or EDIT (append `Key papers`)
- `wiki/topics/{slug}.md` — EDIT only (no CREATE from `/ingest`)
- `wiki/graph/edges.jsonl` — APPEND via tool
- `wiki/graph/citations.jsonl` — APPEND via tool
- `wiki/graph/context_brief.md` — REBUILD (skipped in INIT MODE)
- `wiki/graph/open_questions.md` — REBUILD (skipped in INIT MODE)
- `wiki/index.md` — APPEND
- `wiki/log.md` — APPEND via tool

### Graph edges created

- `paper → concept`: `introduces_concept` / `uses_concept` / `extends_concept` / `critiques_concept` with `confidence`
- `paper → foundation`: `derived_from` (foundation is terminal; no reverse link)
- `paper → claim`: `supports` / `contradicts`
- `paper → paper`: `same_problem_as` / `similar_method_to` / `complementary_to` / `builds_on` / `compares_against` / `improves_on` / `challenges` / `surveys` with `confidence`
- bibliographic `paper → paper`: `cites` in `graph/citations.jsonl`

`tools/research_wiki.py add-edge` rejects missing confidence/evidence for
paper-paper and paper-concept semantic edges, and rejects legacy
paper-to-concept or paper-to-paper types on new writes.

## Workflow

**Pre-condition**: working directory contains `wiki/`, `raw/`, and `tools/`. Resolve the Python interpreter once and reuse it:

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

### Step 1: Resolve the source

1. If `/init` passed a `canonical_ingest_path`, enter **INIT MODE** and consume that path verbatim. Do not rescan `raw/`. See `references/init-mode.md`.
2. If the source is an arXiv URL, extract the arXiv ID, use `"$PYTHON_BIN" tools/fetch_s2.py paper <arxiv-id>` to recover the title when possible, then run `"$PYTHON_BIN" tools/init_discovery.py download --raw-root raw --arxiv-id <arxiv-id> --title "<title-or-arxiv-id>"`. Continue from the returned `canonical_ingest_path`. The helper tries arXiv source first and falls back to PDF; do not call `fetch_arxiv.py` for a single paper because it is RSS-only.
3. If the source is a local `.tex`, use it directly.
4. If the source is a local `.pdf`, run the preprocessing pipeline in `references/pdf-preprocessing.md` to produce a prepared `.tex` under `raw/tmp/` before continuing.

Raw persistence rule: never copy or duplicate a file already under `raw/discovered/`, `raw/tmp/`, or `raw/papers/` into a different raw subtree.

### Step 2: Paper identity and enrichment

1. Generate the paper slug:

   ```bash
   "$PYTHON_BIN" tools/research_wiki.py slug "<paper-title>"
   ```

2. Stop-if-exists: if `wiki/papers/{slug}.md` already exists and the arXiv ID or title matches, report and exit. If they differ, resolve the collision per `references/error-handling.md`.
3. When an arXiv ID is available, query Semantic Scholar:

   ```bash
   "$PYTHON_BIN" tools/fetch_s2.py paper <arxiv-id>
   ```

   Use the result for `venue`, `year`, `s2_id`, citation count, and the evidence behind the `importance` score (1-5).
4. Optional DeepXiv enrichment, when available. Skip silently if it fails:

   ```bash
   "$PYTHON_BIN" tools/fetch_deepxiv.py brief <arxiv-id>
   "$PYTHON_BIN" tools/fetch_deepxiv.py head <arxiv-id>
   "$PYTHON_BIN" tools/fetch_deepxiv.py social <arxiv-id>
   ```

   `brief` seeds the Key-idea section; `head` sanity-checks your tex parsing against the section structure; `social` is an auxiliary importance signal.

### Step 3: Write the paper page

Open `runtime/schema/entities.yaml` (papers section) for the field set and `runtime/templates/papers.md.tmpl` for body section order. Fill every required frontmatter field; leave `cited_by` empty for now (step 5 backfills it).

Before writing, run a **shape check** on the frontmatter you are about to emit — no more than this:

- every required key is present and non-empty
- `importance` ∈ {1,2,3,4,5}; `status` on claims ∈ the documented set; `maturity` on concepts ∈ the documented set; claim `confidence` ∈ [0,1]
- YAML parses

The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job, not this skill's.

Body sections to populate: Problem, Key idea, Method, Results, Limitations, Open questions, My take, Related.

### Step 4: Concepts, claims, people

Follow `references/dedup-policy.md`. In short:

1. For each candidate concept or claim, call the matching `find-similar-*` tool first.
2. Prefer merging into the top result. Create a new page only when the tool returns no acceptable candidate and the paper's importance justifies it.
3. For each entity you write or edit, write the reverse link in the same turn. The obligation matrix lives in `references/cross-references.md`.
4. Create a `wiki/people/{slug}.md` only for papers with importance ≥ 4. Otherwise append to existing author pages only.

### Step 5: Paper-to-paper edges and `cited_by`

Skip this whole step in INIT MODE — the parent `/init` handles it at fan-in.

```bash
"$PYTHON_BIN" tools/fetch_s2.py references <arxiv-id>
"$PYTHON_BIN" tools/fetch_s2.py citations <arxiv-id>
```

- For each reference whose arXiv ID or title resolves to an existing `wiki/papers/{slug}.md`, add a bibliographic `cites` row to `graph/citations.jsonl`.
- Add a semantic paper-to-paper edge in `graph/edges.jsonl` only when the source text gives a clear cue. Edge-type selection is in `references/cross-references.md`. If no semantic relation cleanly fits, keep only the `cites` row.
- For each citation already in the wiki, append the citer's slug to this paper's `cited_by`.
- Surface unmatched high-citation references in the final report so the user can decide whether to follow up with another `/ingest`.

### Step 6: Topics and index

1. Match the paper's domain and tags against existing `wiki/topics/*.md`. For each match:
   - importance ≥ 4 → append to the topic's `## Seminal works`
   - importance < 4 → append under `## SOTA tracker` or `## Recent work` by year
   - if the paper directly addresses a listed open problem, annotate that line on the topic page
2. Do not create new topic pages from `/ingest` — topic creation belongs to `/init` and `/edit`.
3. Append new or edited page entries to `wiki/index.md` under their category headings. Format: each entity kind is a top-level YAML key (matching `runtime/schema/entities.yaml`), with `- slug: <slug>` entries beneath.

### Step 7: Log and rebuild

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki/ "ingest | added papers/<slug> | updated: <list>"
```

Unless in INIT MODE:

```bash
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
```

### Step 8: Report

Emit one compact summary covering: pages created, pages updated, graph edges added, contradictions surfaced (if any), and high-citation references not yet in the wiki (suggested follow-up ingests). Close with:

```
Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges
```

### Step 9: Optional discovery (only if `--discover` is set)

Skip this step unless the user explicitly passed `--discover`. Also skip it in INIT MODE — `/init`'s parent process decides whether to run discovery at fan-in, not individual subagents.

When active, invoke `/discover` with the just-ingested paper as the single anchor:

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <arxiv-id-of-this-paper> \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

Append the markdown output to the report under a heading like "Related papers you may want to ingest next". Do not auto-ingest anything from the shortlist — the user picks. If discovery fails (S2 outage, all channels empty), note the failure in one line and continue — a failed `/discover` must not fail an otherwise successful `/ingest`.

## Constraints

- `raw/papers/`, `raw/notes/`, `raw/web/` are user-owned and read-only. Direct local `/ingest` may add prepared sidecars under `raw/tmp/`; direct arXiv ingests may write fetched source artifacts under `raw/discovered/`. INIT MODE treats all of `raw/` as read-only.
- `wiki/graph/` is tool-owned. Edit only through `tools/research_wiki.py`.
- Slugs always come from `tools/research_wiki.py slug`. Never hand-craft.
- Every forward link writes its reverse link in the same turn — the wiki's bidirectional-link invariant. The only exception is links to `wiki/foundations/`, which are terminal.
- In INIT MODE, do not write reverse links into pages that already exist (created by a sibling worktree or scaffold). Record the relationship via `tools/research_wiki.py add-edge` only; the parent `/init` backfills reverse links during fan-in.
- Source priority: `.tex` > `.pdf` > vision API fallback. Never ingest from a PDF when a usable `.tex` is available.
- Ingest is conservative about new entities:
  - importance < 4: at most **1** new concept and **1** new claim per paper
  - importance ≥ 4: at most **3** new concepts and **2** new claims per paper
  - Any further candidates must be merged into their nearest `find-similar-*` result, or left out for `/check` to flag. Rationale and matching rules: `references/dedup-policy.md`.
- `/ingest` runs a shape check on its own output (required keys, enum ranges, YAML parses) and stops there. Backlink symmetry, dangling nodes, and full semantic audits belong to `/check`. Do not re-implement them here.
- Assume another `/ingest` may run concurrently in a sibling worktree. All shared-file writes (`graph/edges.jsonl`, `graph/citations.jsonl`, `index.md`, `log.md`) must go through `tools/research_wiki.py` or use append-only semantics. See `references/init-mode.md`.
- In INIT MODE, skip `fetch_s2.py citations`, `fetch_s2.py references`, and the `rebuild-*` commands — the parent `/init` runs them once after fan-in.

## Error Handling

See `references/error-handling.md`. Highlights: source parse failures cascade tex → PDF → vision API → user handoff; S2 outages default `importance` to 3 and skip citation backfill; DeepXiv outages skip enrichment silently; slug collisions append a numeric suffix.

## Dependencies

### Tools (via Bash)

- `"$PYTHON_BIN" tools/research_wiki.py slug "<title>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-concept wiki/ "<title>" --aliases "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-claim wiki/ "<title>" --tags "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py add-edge wiki/ --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`
  - `--confidence high|medium|low` is required for paper-paper and paper-concept semantic edges.
- `"$PYTHON_BIN" tools/research_wiki.py add-citation wiki/ --from papers/<citing> --to papers/<cited> --source semantic_scholar`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/`
- `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]`
- `"$PYTHON_BIN" tools/init_discovery.py download --raw-root raw --arxiv-id <id> --title "<title-or-id>"` — single-paper arXiv source/PDF download into `raw/discovered/`
- `"$PYTHON_BIN" tools/fetch_s2.py paper|citations|references <arxiv-id>`
- `"$PYTHON_BIN" tools/fetch_deepxiv.py brief|head|social <arxiv-id>`
- `"$PYTHON_BIN" tools/discover.py from-anchors --id <arxiv-id> --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown` — only when `--discover` is set

### Shared References

- `.claude/skills/shared-references/citation-verification.md`

### Skills

- `/init` — calls `/ingest` in parallel subagents via INIT MODE
- `/check` — audits wiki state after `/ingest` completes; owns every semantic check `/ingest` intentionally does not perform
- `/discover` — optional follow-up when `--discover` is set; produces a shortlist of related papers the user may want to ingest next

### External APIs

- Semantic Scholar (via `tools/fetch_s2.py`)
- DeepXiv (via `tools/fetch_deepxiv.py`, optional; graceful fallback)
- arXiv (source download)
