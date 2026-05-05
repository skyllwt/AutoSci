---
description: Daily arXiv pull, relevance filtering, auto-ingest of high-priority papers, and SOTA update detection
argument-hint: "[--hours 24] [--max-ingest 5] [--dry-run]"
---

# /daily-arxiv

> Pulls new papers from arXiv RSS daily, automatically assesses relevance based on research directions and concepts in the wiki,
> calls /ingest to fully incorporate highly relevant papers into the wiki, detects SOTA updates, and generates a digest log.
> Supports cron-scheduled automatic execution as well as manual triggering.

## Inputs

- `--hours N`: pull papers from the last N hours (default 24)
- `--max-ingest N`: maximum papers to ingest per run (default 5, prevents wiki overload)
- `--dry-run`: generate digest only, do not execute ingest
- `--categories`: override default arXiv categories (default: cs.LG cs.CV cs.CL cs.AI stat.ML)

## Outputs

- `raw/discovered/{slug}/` or `raw/discovered/{slug}.pdf` — fetched source artifact for each auto-ingested paper
- `wiki/papers/{slug}.md` — highly relevant paper pages (created via /ingest)
- Corresponding `concepts/`, `people/`, `methods/` pages (created via /ingest)
- Updated `wiki/topics/*.md` — SOTA tracker annotations (if SOTA update detected)
- Updated `wiki/graph/` — edges.jsonl, context_brief.md, open_questions.md (maintained via /ingest)
- Updated `wiki/index.md` and `wiki/log.md`

## Wiki Interaction

### Reads
- `wiki/topics/*.md` — extract Overview keywords and SOTA tracker, used for relevance scoring and SOTA detection
- `wiki/concepts/*.md` — extract Definition keywords, assist relevance scoring
- `wiki/index.md` — check whether a paper is already collected (deduplicate by arXiv URL)
- `wiki/papers/*.md` — check whether an arxiv ID already exists
- `wiki/graph/open_questions.md` — prioritize ingesting papers that fill knowledge gaps

### Writes
- `wiki/papers/{slug}.md` — CREATE via /ingest
- `wiki/concepts/{slug}.md` — CREATE/EDIT via /ingest
- `wiki/people/{slug}.md` — CREATE/EDIT via /ingest
- `wiki/methods/{slug}.md` — CREATE/EDIT via /ingest
- `wiki/topics/{slug}.md` — EDIT (SOTA tracker annotations)
- `wiki/graph/edges.jsonl` — APPEND via /ingest
- `wiki/graph/context_brief.md` — REBUILD (once at the end)
- `wiki/graph/open_questions.md` — REBUILD (once at the end)
- `wiki/index.md` — EDIT via /ingest
- `wiki/log.md` — APPEND

### Graph edges created
- All edges created by /ingest (paper → concept, paper → method, etc.)

## Workflow

**Pre-conditions**: confirm the working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).
Set `WIKI_ROOT=wiki/`.

### Step 1: Pull arXiv RSS + Trending Papers

1. Run fetch_arxiv.py to get the new paper list:
   ```bash
   python3 tools/fetch_arxiv.py --hours <hours> -o /tmp/arxiv_feed.json
   ```
2. Fetch DeepXiv trending papers (past 7 days):
   ```bash
   python3 tools/fetch_deepxiv.py trending --days 7 --limit 20
   ```
   Merge trending papers into the candidate list (deduplicated by arxiv_id); trending papers receive extra attention in subsequent scoring.
   **If DeepXiv is unavailable**: skip this sub-step, use RSS results only.
3. Parse results to obtain the paper list (title, abstract, authors, arxiv_url, arxiv_id, category)
4. **Deduplication**: read `wiki/index.md`, skip papers whose arXiv URL is already in the wiki. Also check existing arxiv IDs in the `wiki/papers/` directory.
5. If no new papers, skip directly to Step 6 to generate an empty digest.

### Step 2: Build Relevance Context + DeepXiv Enhancement

1. Read `wiki/topics/*.md` and extract for each topic:
   - Core keywords from the Overview paragraph
   - Open problems / Research gaps list
   - Current best results from the SOTA tracker
2. Read `wiki/concepts/*.md` and extract for each concept:
   - Key terms from the Definition paragraph
   - tags list
3. Read `wiki/graph/open_questions.md` for the current knowledge gap list
4. Synthesize a "research direction summary" (≤ 2000 characters) containing: core topics, active concepts, gaps to fill
5. **DeepXiv TLDR enhancement** (optional): for each new paper, fetch an AI summary and keywords to improve scoring quality:
   ```bash
   python3 tools/fetch_deepxiv.py brief <arxiv_id>
   ```
   Supplement the original abstract with the returned `tldr` and `keywords` to help the LLM judge relevance more precisely.
   **If DeepXiv is unavailable**: use only the RSS original title + abstract for scoring (fallback to original behavior).

### Step 3: Relevance Scoring

For each new paper, LLM assesses relevance based on title and abstract vs. the research direction summary:

| Score | Meaning | Action |
|------|------|----------|
| 3 | Highly relevant: significant advance in a core direction | Auto-ingest |
| 2 | Moderately relevant: worth noting but not core | List in digest, do not auto-ingest |
| 1 | Weakly relevant: for reference only | Collapsed listing |
| 0 | Not relevant | Skip |

**Bonus rules** (can promote a score of 2 to 3):
- Paper directly addresses a knowledge gap in open_questions.md → +1
- Paper's benchmark may update the SOTA tracker → +1 (capped at 3)

**Batch scoring**: submit all papers' title+abstract to the LLM in a single call and return scores as JSON. Avoid per-paper calls.

### Step 4: Auto-Ingest High-Priority Papers (with checkpoint resume)

1. Filter papers with relevance = 3, sorted by the following priority:
   - Papers that fill gap_map gaps first
   - Papers with higher citation counts first (if abstract mentions SOTA results)
2. Load checkpoint (skip already-completed papers if one exists):
   ```bash
   python3 tools/research_wiki.py checkpoint-load wiki/ "daily-arxiv-{date}"
   ```
3. Take the first `--max-ingest` papers (default 5). For each selected paper:
   - Download the source artifact into `raw/discovered/` first:
     ```bash
     python3 tools/init_discovery.py download --raw-root raw --arxiv-id <arxiv_id> --title "<title>"
     ```
   - Pass the returned `canonical_ingest_path` from `raw/discovered/` into `/ingest`, not the bare arXiv URL
   - /ingest completes the full wiki incorporation flow (paper + concepts + people + methods + cross-refs + graph)
   - After each success, record checkpoint:
     ```bash
     python3 tools/research_wiki.py checkpoint-save wiki/ "daily-arxiv-{date}" "{arxiv_id}"
     ```
   - On failure, mark and continue:
     ```bash
     python3 tools/research_wiki.py checkpoint-save wiki/ "daily-arxiv-{date}" "{arxiv_id}" --failed
     ```
4. If `--dry-run`, skip both the `raw/discovered/` download and the actual ingest; mark "would ingest" in the digest
5. After all done, clear checkpoint:
   ```bash
   python3 tools/research_wiki.py checkpoint-clear wiki/ "daily-arxiv-{date}"
   ```

### Step 5: SOTA Detection and Update

1. For each paper ingested in Step 4, check the benchmark numbers in its Results section
2. Compare benchmarks against the `## SOTA tracker` in the corresponding `wiki/topics/` page
3. If the paper's results beat the current SOTA record:
   - Append/update an entry in the topic page's `## SOTA tracker`:
     ```
     - **{benchmark_name}**: {score} ← [[{paper-slug}]] ({year}) [previously: {old_score}]
     ```
   - Set `sota_updated` for that topic to today's date
4. If SOTA updates are detected, highlight them in the digest

### Step 6: Generate Digest and Write to Log

1. Rebuild graph derived files (only if any ingest happened):
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

2. Append digest to `wiki/log.md`:
   ```bash
   python3 tools/research_wiki.py log wiki/ "daily-arxiv | {N_ingested} ingested, {N_relevant} relevant / {N_total} total"
   ```

3. Append detailed digest below the current day's log entry:
   ```markdown
   ### High Priority (ingested)
   - [[paper-slug]] — {title} ({one-line insight})

   ### Worth Watching (relevance = 2)
   - {title} — {arxiv_url} — {one-line summary}

   ### Trending This Week (from DeepXiv)
   - {title} — {arxiv_id} — {tweets} tweets, {views} views

   ### SOTA Updates
   - {topic}: {benchmark} new record by [[paper-slug]]

   <details>
   <summary>Weakly Relevant ({K} papers)</summary>

   - {title} — {arxiv_url}

   </details>
   ```

### Step 7: Report to User

Output summary:
- Total papers scanned / count after deduplication
- Distribution across relevance levels
- List of ingested papers (with slug links)
- List of SOTA updates (if any)
- Recommended manual ingest candidates (top 3 most notable from relevance = 2)
- Next run time reminder

## Constraints

- **Only ingest papers with relevance >= 3**: leave the rest for user judgment, do not auto-create wiki pages
- **At most `--max-ingest` papers per run** (default 5): prevents single-run wiki overload
- **`/daily-arxiv` is raw-read-only except `raw/discovered/` for auto-ingested papers**: never write to `raw/papers/`, `raw/tmp/`, `raw/notes/`, or `raw/web/`
- **graph/ maintained via tools only**: do not manually edit graph files
- **Bidirectional links**: guaranteed by /ingest
- **Deduplication must be strict**: double-check by both arxiv_url and arxiv_id
- **Batch scoring**: one LLM call to score all papers, no per-paper calls
- **Digest stays concise**: see individual papers pages for details; at most one line per paper in the digest
- **log.md is append-only**: use `python3 tools/research_wiki.py log` to append

## Error Handling

- **DeepXiv API unavailable**: fall back to pure RSS mode (original behavior). Trending section omitted from digest; scoring uses only raw RSS data. Note DeepXiv unavailability in the report.
- **RSS fetch fails**: report network error, suggest user check network and retry. Do not modify the wiki.
- **Partial ingest failures**: keep completed ingests, mark failed papers in the report, suggest user manually `/ingest <url>`.
- **wiki directory does not exist**: prompt user to run `/init` first.
- **Empty RSS results**: normal situation (fewer papers on holidays/weekends), generate empty digest without error.
- **SOTA comparison fails**: if benchmark format does not match, skip and note in report.

## Dependencies

### Skills（via Skill tool）
- `/ingest` — full paper incorporation flow (called in Step 4)

### Tools（via Bash）
- `python3 tools/fetch_arxiv.py --hours <N> -o <path>` — pull arXiv RSS
- `python3 tools/fetch_deepxiv.py trending --days 7 --limit 20` — fetch trending papers
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — fetch paper TLDR and keywords
- `python3 tools/init_discovery.py download --raw-root raw --arxiv-id <id> --title "<title>"` — download selected papers into `raw/discovered/`
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild compressed context
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild knowledge gap map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### External APIs
- arXiv RSS (via tools/fetch_arxiv.py)
- DeepXiv API (via tools/fetch_deepxiv.py, optional; graceful fallback when unavailable)

### Scheduling
- Can be scheduled for daily automatic execution via CronCreate:
  ```
  CronCreate: schedule "/daily-arxiv" daily at 08:00
  ```
