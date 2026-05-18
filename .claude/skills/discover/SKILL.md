---
description: Build a ranked shortlist of candidate papers (anchor-driven, topic-driven, or derived from current wiki state) that the user — or an upstream skill — may decide to feed into `/ingest`. Use whenever the user asks "what should I read next", "find papers similar to this one", "recommend related work", "what's around this topic", or whenever `/ingest` is invoked with `--discover`. Does not ingest; only proposes.
argument-hint: "(--anchor <id> [--anchor <id>] [--negative <id>] | --topic <str> | --from-wiki | --venue <slug> --year <int>) [--limit N]"
---

# /discover

> Produce a ranked shortlist of paper candidates from one of four seed modes. Surface them to the user (or to the calling skill) with rationales. Never auto-ingest — `/discover` is a proposal stage, `/ingest` is the action stage.

Use these local references on demand:

- `references/seed-modes.md` — when to pick anchor / topic / wiki / venue mode and how to translate the user's phrasing into one
- `references/ranking-signals.md` — what `tools/discover.py` scores on.
- `references/wiki-dedup.md` — how candidates are filtered against `wiki/papers/` and what to do with matches

## Inputs

- `--anchor <id>` (repeatable): one or more anchor paper IDs (arXiv IDs preferred; S2 paperIds also accepted). Drives the **anchor mode** — the primary use case, including the post-`/ingest` "what to read next" flow.
- `--negative <id>` (repeatable, optional): IDs to push recommendations away from. Only meaningful with `--anchor`.
- `--topic "<str>"`: a topic / query string. Drives the **topic mode** — lighter alternative to `/init`'s planner.
- `--from-wiki`: derive seeds automatically from the wiki's most recently modified papers. Drives the **wiki mode**.
- `--venue <slug>` + `--year <int>`: venue slug and year (e.g. `neurips` `2024`). Drives the **venue mode** — ranks papers from that venue/year by relevance to the existing wiki.
- `--limit N` (optional, default 10): max shortlist size.

Exactly one of `--anchor`, `--topic`, `--from-wiki`, or `--venue` must be given.

## Outputs

- `.checkpoints/discover-{seed-slug}-{YYYY-MM-DD}.json` — full shortlist payload, machine-readable; the seed slug is derived from the first anchor or the topic
- a human-readable markdown summary printed to the user with rationale per candidate
- `wiki/log.md` — one append line via `tools/research_wiki.py log`.

`/discover` does not write anywhere else in `wiki/` and does not touch `raw/`.

## Wiki Interaction

### Reads

- `wiki/papers/*.md` — frontmatter `arxiv` (or legacy `arxiv_id`) for dedup against already-ingested papers
- `wiki/papers/*.md` modification times — for `--from-wiki` anchor selection
- `wiki/papers/*.md`, `wiki/concepts/*.md`, `wiki/topics/*.md` — titles and body text for venue-mode relevance scoring

### Writes

- `wiki/log.md` — APPEND via `tools/research_wiki.py log`

### Graph edges created

- none. Graph mutations belong to `/ingest`, not `/discover`.

## Workflow

**Pre-condition**: working directory contains `wiki/`, `raw/`, and `tools/`. Resolve the Python interpreter once and reuse it:

```bash
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  PYTHON_BIN=.venv/Scripts/python.exe
else
  PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: Pick the seed mode

Translate the user's request into exactly one of `from-anchors`, `from-topic`, `from-wiki`, or `from-venue`. The decision rule lives in `references/seed-modes.md`; the short version:

- the user named one or more specific papers, or this is a post-`/ingest` `--discover` follow-up → **anchors**
- the user gave a topic / direction / keywords → **topic**
- the user asked open-ended "what should I read next" with no anchor and no topic → **wiki**
- the user asked for papers from a specific venue and year → **venue**

If the user supplied negatives ("not these"), include them via `--negative` in anchor mode only.

### Step 2: Run the discovery tool

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <arxiv-id> [--id <arxiv-id>...] [--negative <id>...] \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

For venue mode, always pass `--wiki-root` so the tool can compute relevance against existing content. Venue mode requires a non-sparse wiki (the tool will fail clearly if the wiki is too empty).

Or for topic / wiki modes:

```bash
"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Anchor (and wiki) mode run three S2 channels per anchor by default — `recommend` + `references` + `citations`. This is what makes `/discover` meaningfully different from `/daily-arxiv`: references surface older canonical work the anchor built on, citations surface high-impact follow-ups. Pass `--no-citation-expand` only if API cost forces the narrower recommend-only path; the quality regression is sharp.

The tool handles candidate gathering, wiki dedup, ranking, and writes the checkpoint. Always pass `--wiki-root wiki` so already-ingested papers are filtered out — surfacing duplicates wastes the user's review time.

If S2 is unavailable in topic mode, the tool will continue with whatever sources responded; check the output and report degraded discovery to the user. If every channel fails, abort with a clear message rather than emitting an empty shortlist as if it were a real recommendation.

### Step 3: Present the shortlist

Show the markdown output to the user. For each candidate, the user needs enough to decide whether to ingest:

- title and arXiv ID (or S2 paperId fallback)
- one-line rationale (already produced by the tool: anchor count, influential citations, year)
- TLDR if the tool surfaced one (topic-mode candidates often have it; anchor-mode usually does not — the recommendations endpoint does not return TLDRs)

Append a short "next step" hint:

```
To ingest a candidate: /ingest https://arxiv.org/abs/<arxiv-id>
```

**Do not ingest anything yourself. The user picks.**

### Step 4: Log

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki "discover | mode=<anchors|topic|wiki> | seed=<short-desc> | shortlist=<N>"
```

Skip this step for `from-venue`; venue discovery must not write to `wiki/` or `raw/`.

## Internal Callers

`/discover` is designed to be invoked both by users (manually) and by other skills (as a subroutine).

### From `/ingest --discover`

When `/ingest` is invoked with the optional `--discover` flag (default off), it calls `/discover` after the final report, with the just-ingested paper's arXiv ID as the single anchor. The shortlist is appended to `/ingest`'s report under a "Related papers you may want to ingest next" heading. `/ingest` never auto-ingests anything from this list.

## Constraints

- **Never auto-ingest**: `/discover` returns a shortlist and stops. Even when called by `/ingest --discover`, the caller surfaces results and the user decides what to ingest.
- **No content writes to `wiki/`**: paper pages, concepts, methods, graph edges all belong to `/ingest`. Anchor/topic/wiki runs may append `wiki/log.md`; `from-venue` must not write to `wiki/` at all.
- **No writes to `raw/`**: `/discover` does not download papers. The user runs `/ingest <arxiv-url>` afterwards if they want a candidate.
- **Always dedupe against the wiki**: pass `--wiki-root wiki` so the shortlist contains only papers not yet in the wiki. Surfacing duplicates is the most common low-quality failure mode.
- **Ranking is discovery-specific**: do not import or duplicate `tools/init_discovery.py`'s scoring helpers. The two skills have different objectives — `/init` wants broad foundational coverage; `/discover` wants relevant *next reads*. See `references/ranking-signals.md`.
- **Three-channel anchor gather**: by default, anchor mode pulls from S2 `recommend` + `references` + `citations` per anchor. Removing the citation channels (via `--no-citation-expand`) collapses the result into a recency-biased semantic cluster that overlaps heavily with `/daily-arxiv`. Keep all three on unless API cost is a hard constraint. See `references/ranking-signals.md`.
- **Some S2 endpoints have a flatter field set**: `/citations`, `/references`, and `/recommendations/*` reject nested selectors — no `authors.hIndex`, no `tldr`. `/paper/{id}` and `/paper/search` do accept them, so topic-mode candidates carry full enrichment; anchor-mode candidates that entered only via citations/references/recommend do not. That is a real API constraint, not a bug.
- **Rate limits apply**: each anchor in anchor mode costs up to three S2 calls (recommend + references + citations). Default per-anchor limit is 50 for recs and 30 each for references/citations. Multi-anchor runs multiply accordingly; with an API key (1 req/sec) a 3-anchor run takes ~10 seconds.

## Error Handling

- **All seed channels fail**: report the failure, write no shortlist, and do not log a successful run.
- **S2 unavailable, DeepXiv available (topic mode)**: continue with DeepXiv only; note the degradation in the report.
- **S2 returns zero recommendations for an anchor**: keep going with the remaining anchors; if all anchors return zero, treat as total failure.
- **`--from-wiki` finds no anchorable papers** (`wiki/papers/` empty or all missing `arxiv_id`): tell the user the wiki is too sparse for wiki-mode discovery and suggest topic mode.
- **`from-venue` with a sparse wiki** (too few terms extracted from wiki content): fail clearly and suggest ingesting papers or using topic mode. Venue mode relies on existing wiki content for relevance; without it the ranking would be arbitrary.
- **Anchor ID is malformed or unknown**: S2 will return 404; surface the bad ID in the report and continue with any remaining anchors.

## Dependencies

### Tools (via Bash)

- `"$PYTHON_BIN" tools/discover.py from-anchors --id <id> [--id <id>...] [--negative <id>...] --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-venue --venue <slug> --year <int> --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki "<message>"`

### Skills

- `/ingest` — caller via `--discover` flag; also the action the user takes on a chosen candidate
- `/init` — independent planner; does not call `/discover`

### External APIs

- Semantic Scholar — recommendations (`/recommendations/v1/papers/forpaper/{id}`, `POST /recommendations/v1/papers/`), search, paper detail (via `tools/fetch_s2.py`)
- DeepXiv — search fallback in topic mode (via `tools/fetch_deepxiv.py`, optional; graceful fallback when unavailable)
- Paper Copilot — public GitHub raw JSON (`papercopilot/paperlists`) for venue/year paper lists. Live-site scraping is not used; do not vendor the dataset. Venue normalization should preserve documented relevance fields such as title, abstract, TLDR, keywords / primary area / topic, track, status, citations, ratings, reviews, and paper URLs when present.
