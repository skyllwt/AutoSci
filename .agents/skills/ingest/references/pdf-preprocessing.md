# /ingest PDF Preprocessing

Open this reference when `/ingest` receives a local `.pdf` and needs to convert it into a prepared `.tex` before ingest can proceed. Skip it in INIT MODE — `/init` already ran an equivalent batch preprocessing pass and handed off a canonical path.

## Why preprocessing exists

A PDF on its own is a poor ingest source: text extraction quality varies, equations and captions are easy to miss, and the reference list is often unreliable. When the paper is on arXiv we can do much better by resolving it to an arXiv ID and fetching the original TeX source. If no arXiv source is available we still normalize the PDF into a synthetic `.tex` so the rest of `/ingest` works from one uniform input shape.

This mirrors the pipeline `tools/init_discovery.py prepare` runs internally when `/init` batch-processes local PDFs. You are doing the same thing for a single paper, inline.

## Recovery order

Follow this exact order. Stop at the first step that produces a confident result.

1. **Agent inspection of the PDF itself.**
   Before invoking any tool, open the PDF and record:
   - a confident paper title (from the first-page title, not from PDF metadata — metadata is often wrong)
   - a confident arXiv ID if one is visibly printed on the first page or in a header
   Either or both may be empty. Do not guess.
2. **Filename / path arXiv ID extraction.**
   `prepare_paper_source.py` already regex-matches an arXiv ID embedded in the filename or containing folder. You do not need to do this yourself; just pass the PDF path through.
3. **Title-based Semantic Scholar lookup.**
   Only runs when the agent supplied a confident title. `prepare_paper_source.py` handles it internally when `--title` is passed.
4. **arXiv source fetch.**
   When an arXiv ID is known (from step 1 or 2), the helper downloads the TeX source under `raw/tmp/papers/.../<slug>-arxiv-src/` and uses it as the prepared source.
5. **Synthetic `.tex` fallback.**
   If none of the above produces an arXiv match, the helper writes a synthetic `.tex` distilled from the PDF text under `raw/tmp/`. The synthetic file is good enough for ingest but clearly marked as a fallback.

## Invocation

Once you have the title and/or arXiv ID (possibly both empty), run:

```bash
"$PYTHON_BIN" tools/prepare_paper_source.py \
  --raw-root raw \
  --source <pdf-path> \
  [--title "<agent-recovered-title>"] \
  [--arxiv-id "<agent-recovered-arxiv-id>"]
```

- Pass `--title` only when the agent is confident. Do not pass a title derived from PDF metadata or from the filename — the helper sanitizes those on its own and treating them as authoritative poisons the Semantic Scholar lookup.
- Pass `--arxiv-id` only when the agent read it off the page. Filename-embedded IDs are picked up automatically.
- Omit both flags when neither is confident. The helper will fall back cleanly.

The helper writes a prepared entry under `raw/tmp/` and prints a JSON record with `prepared_path`, `title`, `arxiv_id`, and any warnings. Use `prepared_path` as the source for the rest of `/ingest`.

## Title authority

When the agent supplied a confident title, treat that title as authoritative for the paper page's `title` field. Titles sanitized out of fetched TeX or PDF metadata are fallback display strings only; do not let them overwrite the agent title. This matters because the agent-recovered title is what drove the successful S2 lookup; letting a parsed-TeX title overwrite it creates subtle identity drift.

## Output

A successful preprocessing pass produces exactly one prepared source entry under `raw/tmp/`:

- if an arXiv source was fetched: a directory like `raw/tmp/papers/<slug>-arxiv-src/` containing the original `.tex` tree
- otherwise: a synthetic `raw/tmp/papers/<slug>.tex` distilled from the PDF

From this point on, treat the prepared entry exactly the same as you would treat a user-provided local `.tex`. Do not re-copy the PDF into `raw/papers/`; the original path remains the user-owned artifact.
