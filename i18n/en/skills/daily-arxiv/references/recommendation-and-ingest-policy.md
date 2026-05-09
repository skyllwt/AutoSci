# Daily arXiv Recommendation and Ingest Policy

`/daily-arxiv` is LLM-first: deterministic tools build an evidence packet, then
the skill judges relevance and action. The tool ranking is only a sorting aid.

## Pipeline

1. Resolve `config/daily-arxiv.yml`; missing config means inferred defaults.
2. Fetch recent arXiv papers and dedupe against known wiki arXiv IDs.
3. Build a wiki profile from papers, topics, concepts, claims, ideas, open
   questions, recent log entries, and optional profile preferences.
4. Enrich candidates with available Semantic Scholar and DeepXiv evidence.
5. Let the LLM assign final decisions and rationales.
6. Notify by digest and, only when explicitly allowed, call `/ingest`.

## Evidence

Use existing integrations before adding new logic:

- arXiv: title, authors, category, date, URL, abstract.
- Wiki: anchors, topics, concepts, claims, ideas, open questions, recent ingests.
- Semantic Scholar: paper metadata, citation counts, influential counts, fields
  of study, TLDR, and recommendations from wiki anchors.
- DeepXiv: trending rank, social impact, brief/TLDR, keywords, and paper
  structure when available.

If S2 or DeepXiv fails, keep the run alive and put the degraded signal in the
digest. Missing enrichment is never evidence for ingestion.

## Decision Schema

The LLM writes one decision per candidate:

```json
{
  "arxiv_id": "2501.01234",
  "decision": "strong_recommend",
  "confidence": "high",
  "score": 0.82,
  "rationale": "Connects to the wiki's open question about ...",
  "wiki_connections": ["efficient adaptation", "retrieval"],
  "signals_used": ["arxiv", "wiki_profile", "semantic_scholar", "deepxiv"]
}
```

Allowed decisions are `strong_recommend`, `maybe`, `skip`, and `ingest`.
Allowed confidence values are `high`, `medium`, and `low`.

OpenAI-compatible third-party LLMs are supported only for `inform` mode via
`tools/daily_arxiv.py recommend-llm`. In that path, `ingest` is not an allowed
output; any attempted `ingest` decision is downgraded to `strong_recommend`.

## Modes

- `inform`: default. Produce digest, e-mail when configured, and stop.
- `auto-ingest`: explicit opt-in. Only `decision: ingest` with
  `confidence: high` can proceed, and only up to `max_auto_ingest`.

Never infer `auto-ingest` from repository state, branch name, existing workflow,
or available credentials. The user/config/workflow input must choose it.

## Auto-Ingest Guardrails

- `/ingest` owns all paper incorporation. `/daily-arxiv` must not hand-write
  paper pages, concepts, claims, people, graph files, or index entries.
- Invoke `/ingest` sequentially; parallel ingest is out of scope.
- Preserve failures in `llm-decisions.json` and the final digest via
  `ingest_status` or `ingest_error`.
- Commit only changes produced by `/ingest`, normally under `wiki/` and
  `raw/discovered/`.
- Borderline candidates stay `maybe`; do not ingest medium/low confidence items.

## Relationship to `/discover`

`/discover` answers user-driven "what should I read next?" requests from
anchors, topics, or wiki state and never ingests. `/daily-arxiv` starts from a
time-window stream of new arXiv papers and may notify or explicitly ingest.
