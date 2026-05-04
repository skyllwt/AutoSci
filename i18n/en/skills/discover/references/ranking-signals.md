# /discover ranking signals

The deterministic ranking lives in `tools/discover.py` — this file documents what it weighs and **why it differs from `/init`**, so that future edits do not accidentally re-converge the two.

## Anchor-mode candidate channels

Anchor mode gathers from **three** S2 channels per anchor, because any single channel has a characteristic bias:

- **`recommend`** (S2 semantic recommendations endpoint) — surfaces semantically similar papers, but the endpoint is heavily skewed toward recent work. On its own this collapses into "recent papers near the topic", overlapping `/daily-arxiv`.
- **`references`** (papers the anchor cites) — surfaces the **older canonical** work the anchor built on. This is the literature-review channel.
- **`citations`** (papers that cite the anchor) — surfaces **high-impact follow-ups** and subsequent work built on the anchor.

Together they form a real literature-graph walk: semantic neighbors + ancestors + descendants. Removing any one channel is a sharp quality regression. Use `--no-citation-expand` to drop references+citations only when API cost is the binding constraint (e.g., a very short anchor list where recommend alone is sufficient).

## What discovery scores on

Anchor mode (rough weight order):

1. **Aggregate influential citation count** — log-scaled. Reflects the candidate's general prestige. Weighted heavier than raw `citationCount`.
2. **Anchor-influence edge** — S2's per-edge `isInfluential` flag, lifted from the `references`/`citations` envelope onto each candidate as `is_influential_edge`. When True, S2's citation-analysis model judged that the anchor substantively built on this candidate (references channel) or that this candidate substantively built on the anchor (citations channel). Much sharper than the aggregate count: it tells you "this specifically matters to the anchor", not "this matters to the field". Often False — S2's flag is stringent — but when True it should dominate.
3. **Anchor overlap** — how many anchors surfaced this candidate. Two anchors pointing to the same paper means it sits at their intersection.
4. **Channel diversity** — bonus when the same candidate appears in multiple channels (e.g., both `recommend` and `references`). A paper present in all three is rare and usually central to the anchor's neighborhood.
5. **Freshness** — mild bonus for recent years. Recent ≠ better, so the curve is flat-ish (1.0 / 0.85 / 0.6 / 0.4 / 0.25 across age buckets).
6. **Author h-index** (max across authors) — capped tie-breaker. The list endpoints do not return `authors.hIndex`, so this signal mostly fires for topic-mode candidates that came via the richer single-paper graph API.

Topic / wiki mode: same signals minus anchor overlap and minus the anchor-influence edge (no anchor exists in topic mode; wiki-derived anchors do score the edge signal). Influence and freshness carry more weight to compensate.

Venue mode:

1. **Wiki relevance** — primary signal. `tools/discover.py` builds a small BM25-style local corpus from `wiki/papers/`, `wiki/concepts/`, and `wiki/topics/`, with stronger weights for page titles and frontmatter than body text. Candidate titles, abstracts, keywords, TLDRs, and track names are scored against that corpus. If the wiki is too sparse, or no venue candidate matches the corpus, the tool fails instead of pretending the ranking is personalized.
2. **Citation count** — Paper Copilot's available citation field, log-scaled as a secondary signal.
3. **Freshness** — mild tie-breaker; most venue runs use one year, so this normally does not move much.
4. **Paper Copilot rating / review metadata** — used only as secondary tie-breakers when present.
5. **Source diversity** — negligible for venue mode today because Paper Copilot is the required source.

Venue mode uses Paper Copilot's public GitHub JSON data (`papercopilot/paperlists`) for the venue/year list and does not scrape the live website or vendor the dataset.

### Why aggregate influence AND per-edge influence?

They answer different questions:

- `influentialCitationCount` = "does the field cite this paper substantively?" — a proxy for general importance
- `isInfluential` on the anchor edge = "does *this anchor* specifically build on / get built on by this paper?" — a proxy for anchor-specific relevance

A paper can score high on one and low on the other. Example: a well-known benchmark paper has a high aggregate count (everyone cites it) but rarely a True edge from a method paper (the benchmark is used, not built upon). Our ranking uses both, so benchmarks surface when there's no better signal, but papers the anchor literally built on outrank them.

## What discovery does **not** score on

This is where `/discover` deliberately differs from `/init`'s planner (`tools/init_discovery.py`):

- **No survey preference**. `/init` favors survey/review papers because a fresh wiki benefits from them as anchor coverage. `/discover` is invoked when a user already knows the area (anchor mode) or is exploring (topic mode); they rarely need yet another survey, and surfacing surveys above novel work would be noise.
- **No "older canonical anchor" bonus**. `/init`'s bootstrap mode promotes one older citation-heavy paper to broaden coverage. `/discover` users typically want forward-looking recommendations, not foundational re-anchoring.
- **No notes/web priority terms**. `/init` reads `raw/notes/` and `raw/web/` to extract the user's stated intent. `/discover` does not — its inputs are explicit (anchor, topic, or wiki state).

If a future ranking signal seems shared between `/init` and `/discover`, prefer keeping two implementations rather than extracting a shared scorer. The objectives genuinely differ; a shared scorer would force one skill to compromise.

## Field-set restrictions on S2 endpoints

`tools/fetch_s2.py` uses two field sets:

- `FIELDS` — full rich set. Accepted by `/paper/{id}` **and** `/paper/search`. Includes `authors.hIndex`, `tldr`, and every other nested selector we use.
- `FLAT_FIELDS` — flat authors, no `tldr`, no nested selectors. Required by `/paper/{id}/citations`, `/paper/{id}/references`, and `/recommendations/*` — these three endpoints return 400 Bad Request when passed nested selectors or `tldr`.

Do not re-merge the two sets: the restricted endpoints really do reject the nested form, verified with live probes.

Practical consequence for anchor mode: candidates that enter only via `references` / `citations` / `recommend` lack `hIndex` and `tldr` in their rationale. Topic mode candidates (which enter via `/paper/search`) carry both. A follow-up `fetch_s2.paper(arxiv_id)` call per candidate would enrich the missing ones, but the discovery tool deliberately does not do this — it would multiply per-run cost by (shortlist_size × latency) for a small rationale improvement. `/ingest` does the enrichment when the user actually picks a candidate to ingest.
