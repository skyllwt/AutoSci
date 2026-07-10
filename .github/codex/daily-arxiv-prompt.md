Run AutoSci's scheduled `/daily-arxiv` decision stage.

The deterministic preparation step has already written:

- `.daily-arxiv/run/recommendation-context.json`

Read that file and make LLM-first decisions using the supplied arXiv, wiki,
Semantic Scholar, and DeepXiv evidence. Do not fetch a second candidate list
or invent evidence that is not present in the context.

Your final response must be JSON matching
`.github/codex/llm-decisions.schema.json`, with one decision for each new
candidate. Do not wrap the JSON in Markdown fences and do not add commentary
outside the JSON object.

Decision rules:

1. Use only these decisions: `strong_recommend`, `maybe`, `skip`, and
   `ingest`.
2. Use only these confidence values: `high`, `medium`, and `low`.
3. Ground every rationale in the supplied evidence. Use `wiki_connections` for
   concrete wiki topics, concepts, papers, methods, or open questions; use an
   empty list when there is no meaningful connection.
4. In `inform` mode, never ingest or mutate the wiki. `ingest` is not allowed
   in this mode; use `strong_recommend` for a high-confidence recommendation.
5. In `auto-ingest` mode, select `ingest` only for genuinely high-confidence
   candidates and never select more than `config.max_auto_ingest` papers.
   Invoke the Codex `$ingest` skill sequentially for each selected paper using
   its arXiv URL. Do not hand-write wiki pages, graph files, index entries, or
   raw files. Record `ingest_status` or `ingest_error` in that decision after
   each attempt.
6. Keep borderline candidates as `maybe`; missing or degraded enrichment is
   not evidence for ingestion.

The repository's AGENTS.md and the daily-arxiv skill are authoritative for
path ownership and runtime conventions. Do not edit files outside the
`.daily-arxiv/` scratch area during inform runs, or outside the durable paths
owned by `$ingest` during auto-ingest.
