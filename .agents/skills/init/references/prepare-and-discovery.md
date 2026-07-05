# /init Prepare And Discovery

Use this reference when `/init` is preparing local inputs, selecting the final paper set, or writing `.checkpoints/init-sources.json`.

## Prepare Flow

- Run `"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`.
- Before preparing local PDFs, recover confident titles when possible and write `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }` or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title", "arxiv_id": "2401.00001" } }` when a confident arXiv ID is already known.
- `tools/init_discovery.py prepare` must pass those recovered titles and IDs into `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]`.
- `tools/init_discovery.py prepare` must delegate local paper normalization to the same helper and reuse pre-staged `raw/tmp/` artifacts when they already exist.
- For local PDFs, use this recovery order only: handed-off arXiv ID or filename/path arXiv ID -> title-based Semantic Scholar recovery when a confident title was supplied -> fetched arXiv source -> synthetic `.tex`.
- When the agent supplied a confident PDF title, that title is authoritative for the prepared manifest. Sanitized titles from fetched TeX are fallback metadata only and must not overwrite the agent title.
- Do not use PDF metadata or PDF body text as arXiv-ID hints during prepare.
- When arXiv ID recovery succeeds, prefer fetched raw TeX source under `raw/tmp/papers/...-arxiv-src/` over synthetic `.tex`.
- If no confident PDF title is available, omit `--title`; if no confident arXiv ID is available, omit `--arxiv-id`; then allow filename/path arXiv-ID recovery only and fall back directly to synthetic `.tex`. Metadata or filename titles remain display-only.

## Source Preference Rules

- Prefer local sources in this order: original local `.tex` > archive-extracted source `.tex` or fetched arXiv source directory > PDF-derived synthetic `.tex` > raw `.pdf`.
- Keep notes/web on their original source paths. `/init` reads them directly during planning.
- If the handed-off source already lives under `raw/tmp/` or `raw/discovered/`, treat that path as canonical and do not duplicate it into `raw/papers/`.
- Set each local paper's `canonical_ingest_path` to a prepared `raw/tmp/` path when available; otherwise fall back to the original `raw/papers/...` path.

## Final Selection And Fetch

- `plan` must read `.checkpoints/init-prepare.json` instead of rescanning `raw/`.
- Over-pick a shortlist first, then explicitly trim it to the documented final target before `fetch`.
- Keep all parseable user-owned papers by default, then use remaining slots for introduced papers.
- If seeded discovery adds no external papers, proceed with the user-owned paper set instead of treating that as a fatal planner error.
- If the user already provided more than 10 parseable papers, add no new papers.
- If `--no-introduction` is active, final paper set = all parseable user papers, and `fetch` still runs with zero external IDs so it writes `.checkpoints/init-sources.json`.

Run:

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id> --id <candidate-id>
```

- External papers downloaded by `/init` go to `raw/discovered/`, never `raw/papers/`.
- Never fetch a paper that is already represented by a prepared local source from `raw/tmp/`.

## Source Manifest Contract

- `.checkpoints/init-sources.json` is the single source of truth for Step 5 ingest order.
- User-owned papers appear in `init-sources.json` with `origin=user_local` and their canonical prepared path when available.
- Introduced papers appear in `init-sources.json` with `origin=introduced` and their canonical `raw/discovered/` path.
- Step 5 must consume the handed-off `canonical_ingest_path` exactly as written.
