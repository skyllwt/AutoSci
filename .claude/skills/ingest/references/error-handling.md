# /ingest Error Handling

Open this reference when a step fails. `/ingest` prefers to degrade gracefully: record what happened, continue with what remains, and surface the gap in the final report.

## Source parsing

- **`.tex` parse fails**: fall back to the PDF if one is available in the same source directory.
- **PDF text extraction fails**: fall back to a vision-API pass on the first few pages to recover the title and abstract, then run the preprocessing pipeline in `references/pdf-preprocessing.md` with the recovered title.
- **No readable source at all**: stop and report. Do not create a paper page from a title alone — a paper page without grounded content is noise.
- **INIT MODE input unreadable**: do not attempt to re-prepare the source (INIT MODE is read-only on `raw/`). Stop, record the failure, and let the parent `/init` retry or skip the paper at fan-in.

## External APIs

- **Semantic Scholar unavailable** (`fetch_s2.py paper` errors): skip S2 enrichment, default `importance` to 3, and note in the report that the paper's importance is provisional. Skip the citation backfill step entirely for this ingest.
- **DeepXiv unavailable** (`fetch_deepxiv.py` errors): skip enrichment silently. DeepXiv is optional; its absence is not degraded ingest, just plainer ingest. Do not surface this in the user report unless the user asked about DeepXiv specifically.
- **arXiv source fetch fails**: if the paper is on arXiv but the source archive does not exist or times out, fall through to the PDF path. Record a warning in the final report.

## Slug collisions

- **Generated slug matches an existing page with a different arXiv ID or title**: stop and report. Do not append a numeric suffix silently — a collision between two different papers at the same slug is a signal the wiki has a naming problem that the user should resolve.
- **Generated slug matches an existing page with the same paper**: the paper is already ingested. Report and exit.
- **Within a single ingest, a generated concept or method slug collides with a different existing page**: append a numeric suffix (`-2`, `-3`, ...) via the tool's built-in collision handling. This is the one case where suffixing is correct — it happens when two genuinely different ideas produce the same slug under the deterministic rule.

## Wiki not initialized

If `wiki/` is missing or empty, run:

```bash
"$PYTHON_BIN" tools/research_wiki.py init wiki/
```

Then retry `/ingest`. Do not attempt to create pages in a non-initialized wiki; `index.md` and `graph/` scaffolding must exist first.

## Partial failure mid-ingest

If an ingest fails after some writes have landed (paper page written, but concept dedup or graph edge fails):

- do not roll back the writes that succeeded
- append a log entry via `tools/research_wiki.py log` describing which steps completed and which are incomplete
- surface the incomplete steps in the user report so the user can run `/edit` or `/check --fix` to finish the job
- in INIT MODE, if the ingest completed successfully, commit inside the worktree before exiting (see `references/init-mode.md`). If the ingest partially failed, do **not** commit the incomplete state; let the parent `/init` handle the failed worktree at fan-in

## When to stop vs. continue

Stop outright when:

- no source can be read at all
- the paper is already ingested (slug + arXiv ID match an existing page)
- a slug collision would silently overwrite a different existing paper

Continue with a warning when:

- one enrichment source (S2 or DeepXiv) is down
- the reference list cannot be parsed (skip step 5; paper ingest still works)
- a single concept or method dedup call fails transiently (retry once; if it still fails, skip that candidate and note it)

The guiding principle: a partial ingest that preserves a well-shaped paper page is more useful than a clean abort that leaves the wiki unchanged. Partial state is recoverable via `/check` and `/edit`. Lost partial state is not.
