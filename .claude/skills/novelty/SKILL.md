---
description: Multi-source novelty verification — WebSearch + Semantic Scholar + PubMed (bio) + wiki + Review LLM cross-verify — outputs novelty score and recommendations. Optionally writes the score back to an idea page with --write.
argument-hint: <idea-description-or-slug> [--quick] [--verbose] [--write]
---

# /novelty

> Verify the novelty of a research idea or method using multiple sources. Searches WebSearch,
> Semantic Scholar, existing wiki work, and arXiv recent preprints, then Review LLM cross-verifies.
> Outputs a novelty score (1-5), closest prior work, differentiation points, and next-step recommendations.
> Can be used standalone or called by /ideate Phase 4.

## Inputs

- `target`: one of the following:
  - free-text description of the idea (a paragraph or a few sentences)
  - slug of an ideas/ page in the wiki (e.g. `sparse-lora-for-edge-devices`)
  - paper title or arXiv URL (check novelty of that paper's method)
- `--quick`: fast mode, skip Review LLM cross-verify (Step 3), search only
- `--verbose`: output full search results, not just summaries
- `--write` (optional, default **off**): persist the resulting `novelty_score` to the target's frontmatter. **Only takes effect when `target` is an idea slug** (i.e. `wiki/ideas/{slug}.md` exists). Free-text targets and paper-novelty checks remain read-only regardless of this flag. Treat as a user-owned flag — `/ideate` Phase 4 sets it explicitly when calling `/novelty`; do not infer it from repo state.

## Outputs

- **Novelty Report** (output to terminal):
  - Novelty Score (1-5)
  - List of closest prior work (top 3-5)
  - Differentiation points versus each prior work
  - Review LLM cross-verify assessment (unless --quick)
  - Recommended action: proceed / modify / abandon
- **Idea page write (only when `--write` is set AND target is an idea slug)**: updates `wiki/ideas/{slug}.md` frontmatter `novelty_score` field via `tools/research_wiki.py set-meta`. No other field is touched.

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — search existing papers for similar methods
- `wiki/concepts/*.md` — check concept overlap
- `wiki/methods/*.md` — check for already-cataloged methods that overlap with the candidate
- `wiki/ideas/*.md` — check for duplication with existing ideas (especially `failure_reason` of failed ideas)
- `wiki/graph/context_brief.md` — global context to assist search

### Writes
- `wiki/ideas/{slug}.md` (only when `--write` and target is an idea slug) — sets `novelty_score`. Otherwise none.
- `wiki/log.md` (only when a write occurs) — append "novelty | wrote novelty_score=N to ideas/{slug}".

### Graph edges created
- **None**.

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).

### Step 1: Extract Method Signature

1. **If target is a slug**: read `wiki/ideas/{slug}.md`, extract title, Hypothesis, Approach sketch
2. **If target is free text**: use directly
3. **If target is an arXiv URL**: download the abstract, extract method description
4. Extract the "method signature" from the target — the core elements of the method:
   - **What**: what it does (task / goal)
   - **How**: the method used (technical approach)
   - **Why novel**: claimed innovation
5. Generate 3-5 core keywords for subsequent searches

### Step 2: Multi-Source Search

Execute the following searches in parallel (use Agent tool for concurrency):

**Source A — Web Search (5+ queries):**
1. Direct query: `"<method-name>" + "<task>"` — exact phrase search
2. Component query: `<component-1> + <component-2> + <domain>` — component combination search
3. Survey query: `"survey" OR "review" + <task-area> + 2024 2025`
4. Competitor query: `<alternative-approach> + <same-task>`
5. Recent query: `<method-keywords> + arXiv + 2025 2026`

**Source B — Semantic Scholar + DeepXiv:**
```bash
python3 tools/fetch_s2.py search "<method-keywords>" --limit 20
python3 tools/fetch_deepxiv.py search "<method-keywords>" --mode hybrid --limit 20
```
Merge results from both sources (deduplicate by arxiv_id). DeepXiv's hybrid semantic search finds semantically similar work that S2 keyword search may miss.
- Fetch details and TLDR for top 5 results:
```bash
python3 tools/fetch_s2.py paper <s2_id>
python3 tools/fetch_deepxiv.py brief <arxiv_id>
```
Use DeepXiv brief TLDRs to quickly judge method similarity.
**If DeepXiv is unavailable**: fall back to S2 search only (original behavior).

**Source C — Wiki Internal Search:**
1. Scan Key idea and Method sections of all pages in `wiki/papers/`
2. Scan Definition and Variants sections of `wiki/concepts/`
3. Scan all content in `wiki/ideas/`, with special attention to:
   - ideas with status = failed and their failure_reason (anti-repetition)
   - ideas with status = proposed/in_progress (avoid internal duplication)
4. Read `wiki/graph/context_brief.md` for global perspective

**Source D — Recent arXiv Preprints:**
- Use WebSearch: `site:arxiv.org <method-keywords> 2025 2026`

**Source E — PubMed E-utilities (bio-C9 minimal pilot merged 2026-05-12):**

Bio prior art lives largely in PubMed (>30M abstracts) and is under-represented in Semantic Scholar. Run this channel in parallel with A–D. When the target is bio-shaped, give PubMed hits **full weight** in scoring (same as S2/WebSearch). When the target is pure-ML/non-bio, still run it but expect low recall — treat as supplementary.

**Bio-claim detection**: classify the target as bio-shaped if any of:
- `target` is an idea slug and its frontmatter `domain` matches one of `structural-bio | chembio | comp-drug-discovery | cancer-bio | systems-bio | bioinformatics | clinical-translation` or the legacy free-text variants (`Computational Drug Design`, `Chemical Biology`, `Cancer biology`, `Structural Bioinformatics`, `Computational Biology / ML for Science`, etc.);
- the method signature contains gene-symbol-like tokens (all-caps 3–8 letters), UniProt-style accessions, PDB IDs, drug/PROTAC names, disease names, PTM types (phospho, ubiq, methyl, acetyl), or species names (human, mouse, yeast, …);
- the source idea page has any of the A2-light protein-anchor fields (`gene_symbol`, `uniprot_id`, `pdb_ids`, `species`) populated, or links a `wiki/concepts/*.md` that does.

**Queries** (run 3–5, mirroring the WebSearch query shapes from Source A but biased toward bio vocabulary):

```
# esearch — returns up to 20 PMIDs per query
WebFetch: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=<URL-encoded-query>&retmax=20&retmode=json&sort=relevance
# esummary — title/journal/year/abstract for the top hits
WebFetch: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=<comma-separated-pmids>&retmode=json
# (optional) efetch abstracts when esummary's snippet is insufficient
WebFetch: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<pmid>&rettype=abstract&retmode=text
```

Query shapes to use:
1. Direct: `"<method-name>" AND "<bio-task>"` — exact phrase
2. Component: `<protein-or-target>[Title/Abstract] AND <technique>[Title/Abstract]`
3. PTM-specific (when applicable): `<PTM-type>[Title/Abstract] AND <protein>[Title/Abstract]` (e.g. `phosphorylation[Title/Abstract] AND BCL-XL[Title/Abstract]`)
4. Clinical-anchor (when applicable): `<drug-name>[Title/Abstract] AND <indication>[Title/Abstract]`
5. Survey: `(review[Publication Type] OR survey[Title]) AND <topic>`

Merge the resulting top hits with Sources A/B by DOI / PMID / title-normalised match. **De-duplicate**: a paper already returned by S2 with the same DOI does not get re-counted; PubMed-only hits go into the "closest prior work" list with the PMID surfaced. Surface `pmid` and `doi` on every PubMed-sourced citation so they wire up to the [[bio-A3 minimal]] paper fields if/when ingested.

**Politeness**: NCBI rate-limits unauthenticated callers at ~3 req/sec. Throttle: run the 3–5 esearch queries sequentially or with `&api_key=<NCBI_API_KEY>` if `~/.env` defines one (not required for the minimal pilot). Cache esearch JSON in `raw/tmp/novelty-pubmed/<slug>-<query-hash>.json` to enable replay without re-hitting the API.

**Full C9 deferred**: a `tools/fetch_pubmed.py` CLI wrapping E-utilities with pagination, MeSH expansion, abstract-text NER, and PMC full-text fallback is planned but out of scope for the minimal pilot. The minimal pilot relies on the agent calling WebFetch directly with the URLs above.

### Step 3: Review LLM Cross-Verify

(Skip if `--quick`)

Submit the following to Review LLM for independent assessment:

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher assessing the novelty of a proposed method.
           Be rigorous: if the method is essentially a recombination of known techniques
           with minor changes, score it low. Only score 4-5 if there is a genuinely new
           insight or formulation."
  message: |
    ## Proposed Method
    {method signature from Step 1}

    ## Existing Similar Work Found
    {top 5 similar works from Step 2, with title + one-line summary; mark each source channel — WebSearch / S2 / DeepXiv / PubMed / wiki — so Review LLM can spot bio prior art it would otherwise miss}

    ## Questions
    1. Is this method genuinely novel, or a minor variation of existing work?
    2. What is the closest existing work and what's the real difference?
    3. Novelty score 1-5 with justification.
    4. If score <= 2, what modification could increase novelty?
```

### Step 4: Generate Novelty Report

Synthesize Step 2 search results and Step 3 Review LLM assessment into a structured report:

```markdown
# Novelty Report: {idea title}

## Score: {1-5}/5 — {label}

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Published | Highly similar published work exists |
| 2 | Very Similar | Very similar method exists, only minor differences |
| 3 | Incremental | Clear incremental contribution over existing work |
| 4 | Novel Combination | Creatively combines existing techniques, producing new insight |
| 5 | Fundamentally New | Proposes an entirely new paradigm or formulation |

## Closest Prior Work

1. **{title}** ({year}) — {one-sentence description of the similarity}
   - Difference: {key distinction between this method and the prior work}
   - Wiki link: [[slug]] (if it exists)
2. ...

## Review LLM Assessment
{summary of Review LLM's independent judgment}

## Anti-repetition Check
- Failed ideas in wiki: {list relevant failed ideas with failure_reason}
- In-progress ideas in wiki: {list potentially overlapping ideas}

## Recommendation
- **{proceed / modify / abandon}**
- Rationale: {one paragraph}
- If modify: suggested differentiation directions: {specific suggestions}
```

**Scoring rules (composite judgment):**
- Take the lower of Claude's search-based score and Review LLM's score (conservative principle)
- If wiki contains a failed idea whose failure_reason overlaps with this idea → lower score by 1
- If wiki contains a highly overlapping in_progress idea → mark as abandon (internal duplication)
- **Bio-C9 minimal pilot**: when the target is bio-shaped (see Source E detection) AND PubMed returns ≥ 3 highly-similar hits that S2 + WebSearch did NOT independently surface → lower score by 1 (PubMed-specific anti-repetition signal). When PubMed and WebSearch agree on a closest-prior-work paper that wiki does not yet ingest → flag it in the report under "Recommend /ingest before scoring".

### Step 5: Persist score (only when `--write` is set AND target is an idea slug)

Skip this step entirely if the target was a free-text description or a paper slug, or if `--write` was not set. Otherwise:

```bash
python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md novelty_score {N}
python3 tools/research_wiki.py log wiki/ "novelty | wrote novelty_score=${N} to ideas/${slug}"
```

Where `{N}` is the integer 1-5 from the composite scoring rules above. If `set-meta` errors (e.g. the field is missing from the existing page because it was created before this schema version), surface the error in the report — do not silently swallow it.

## Constraints

- **Default is read-only**: without `--write`, novelty check produces only a terminal report; no wiki content is modified.
- **`--write` is the only persistence path**: when set, only `novelty_score` and `wiki/log.md` are written. Do not edit any other field of the idea page (status, priority, body sections, etc.).
- **`--write` is meaningless for non-idea targets**: if the target is free text or a paper slug, ignore `--write` and produce the read-only report.
- **Conservative scoring**: underestimate novelty rather than overestimate to avoid wasting effort on known work
- **Must check failed ideas**: ideas with status=failed in wiki/ideas/ are important anti-repetition signals
- **Search coverage**: at least 5 distinct WebSearch queries + Semantic Scholar + wiki internal search. **For bio-shaped targets**: additionally 3–5 PubMed E-utilities queries (Source E); PubMed hits receive full weight in scoring.
- **Review LLM independence**: do not include Claude's own novelty judgment when submitting to Review LLM; let Review LLM assess independently
- **Cite real sources**: all prior work listed in the report must be real (returned by WebSearch/S2); do not fabricate

## Error Handling

- **WebSearch unavailable**: skip Sources A and D, rely only on S2 + wiki search; note limited coverage in report
- **Semantic Scholar API unavailable**: skip S2 portion, use DeepXiv + WebSearch as compensation
- **DeepXiv API unavailable**: skip DeepXiv portion, rely on S2 + WebSearch (fall back to original behavior)
- **PubMed E-utilities unavailable** (NCBI rate-limit / network / 5xx): skip Source E with a "PubMed channel unavailable" annotation in the report. For bio-shaped targets this is a coverage gap — surface it explicitly so the user can rerun later; do not silently degrade.
- **Review LLM unavailable**: skip Step 3; annotate report with "Review LLM cross-verify unavailable, single-model assessment only"
- **Wiki empty**: proceed with external searches normally; annotate wiki internal search section with "wiki empty"
- **idea slug not found**: prompt user to check the slug, list available slugs in wiki/ideas/

## Dependencies

### Tools（via Bash）
- `python3 tools/fetch_s2.py search "<query>" --limit 20` — Semantic Scholar keyword search
- `python3 tools/fetch_s2.py paper <s2_id>` — fetch paper details
- `python3 tools/fetch_deepxiv.py search "<query>" --mode hybrid --limit 20` — DeepXiv semantic search
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — fetch paper TLDR for similarity judgment
- `python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md novelty_score <1-5>` — only when `--write` is set and target is an idea slug
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log on write

### MCP Servers
- `mcp__llm-review__chat` — Review LLM cross-verify (Step 3)

### Claude Code Native
- `WebSearch` — multi-query web search (Step 2 Sources A + D)
- `WebFetch` — PubMed E-utilities calls (Step 2 Source E, bio-C9): esearch / esummary / efetch on `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/*.fcgi`. Throttled ≤ 3 req/sec.
- `Agent` tool — parallel execution of multi-source search (Step 2)

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` (created in Phase 2, Review LLM independence principle)
