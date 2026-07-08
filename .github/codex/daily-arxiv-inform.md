Run the AutoSci daily-arxiv inform-mode recommendation decision step.

Read `.daily-arxiv/run/codex-context.json`. Use only the evidence in that file.
Do not modify repository files, do not run ingestion, and do not call `$ingest`.

Return one JSON object with:

- `provider`: `codex`
- `mode`: `inform`
- `decisions`: one decision object for every candidate in `candidates`
- `notes`: short list of operational notes; use an empty list if there are none

For every candidate decision object, include:

- `arxiv_id`: exactly the candidate arXiv ID
- `decision`: `strong_recommend`, `maybe`, or `skip`
- `confidence`: `high`, `medium`, or `low`
- `score`: number from 0 to 1
- `rationale`: concise evidence-grounded reason
- `wiki_connections`: short strings naming relevant wiki topics, papers, concepts, ideas, methods, or profile signals
- `signals_used`: subset of available signals such as `arxiv`, `wiki_profile`, `semantic_scholar`, `deepxiv`

This is inform mode. Never use the `ingest` decision. If the context has no
candidates, return an empty `decisions` list.
