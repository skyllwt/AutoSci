# $ingest INIT MODE and Batch Safety

Open this reference when ingest is invoked by the init workflow, or any time you need to understand what batch ingests may be doing to shared files.

## When INIT MODE is active

INIT MODE is active for any ingest invocation whose source path originates from `.checkpoints/init-sources.json`. The parent init workflow may run one paper at a time in the main workspace (**INIT MODE SERIAL**, the Codex default) or one paper per isolated `git worktree` (**INIT MODE PARALLEL**, the optional parallel path). See `skills/init/references/parallel-ingest.md`.

In INIT MODE:

- the source is always a `canonical_ingest_path` already prepared by `$init` (a `raw/tmp/...` path for user-owned papers, or a `raw/discovered/...` path for introduced papers)
- `raw/` is strictly read-only — do not write to `raw/tmp/`, `raw/discovered/`, or anywhere else under `raw/`
- `fetch_s2.py citations <arxiv-id>` and `fetch_s2.py references <arxiv-id>` are **skipped** — the parent init workflow does a unified citation sweep after the batch
- `rebuild-context-brief` and `rebuild-open-questions` are **skipped** — the parent runs them once after all papers are ingested
- conflict-prone topic writes are **skipped** — multiple batch ingests may touch the same topic. Let the parent handle topic updates after the batch, or defer them to `$edit`.
- **skip reverse-link edits to existing pages** — do not append `key_papers` to an existing concept page, do not append to `## Key papers` or `## Related` of an existing paper page, and do not append to an existing people page. Record the relationship via `tools/research_wiki.py add-edge` instead. The parent init workflow rebuilds these backlinks after the batch.

Everything else — paper page creation, concept dedup via `find-similar-concept` and method dedup via manual scan of `wiki/methods/`, people page creation, paper `## Related` links, graph edges for concept/method/foundation — still runs per paper.

## Detecting INIT MODE

The init workflow passes the canonical path in the handoff. An ingest invocation can recognize INIT MODE by either of:

- the source path starts with `raw/tmp/` or `raw/discovered/` **and** the `.checkpoints/init-sources.json` manifest references it
- the handoff explicitly states "INIT MODE SERIAL" or "INIT MODE PARALLEL"

When both signals are absent, treat the invocation as a direct user call and run the full workflow (including citations, rebuilds, and any `raw/tmp/` preparation needed).

## Serial vs. parallel completion

- In **INIT MODE SERIAL**, do not commit after each paper. Leave changes in the main workspace for the parent init workflow to rebuild, lint, and report once after all papers finish.
- In **INIT MODE PARALLEL**, commit the successful paper ingest inside the worktree before exiting so fan-in can merge a real paper-specific commit.

## Batch-safe writes

Even outside INIT MODE, assume another ingest may be running in the same batch or a sibling worktree. Three rules make shared writes safe:

1. **Every shared-file write goes through a tool.** `graph/edges.jsonl`, `graph/citations.jsonl`, `index.md`, and `log.md` are written via `tools/research_wiki.py add-edge`, `add-citation`, index updates, and `log`. The tool layer uses append semantics and the repository's `.gitattributes` declares `merge=union` for these paths, so parallel worktrees can merge without conflict.
2. **Slugs are allocated deterministically.** `tools/research_wiki.py slug "<title>"` produces the same slug from the same title regardless of which worktree runs it. Collisions are resolved by numeric suffix via the tool, not by ad-hoc renaming.
3. **Never lock or in-place-rewrite a shared file.** Rewriting `wiki/index.md`, `wiki/graph/edges.jsonl`, or `wiki/graph/citations.jsonl` as a block replaces parallel peers' work when the worktrees merge. Use the tool commands, which append.

## Creating a new page in batch mode

When two batch ingest steps both need a new concept page with the same slug, serial mode should see the first page before the second paper runs; parallel mode may expose the collision during fan-in. Mitigations:

- the per-paper creation limit (`references/dedup-policy.md`) keeps the collision surface small
- in parallel mode, the init parent merges worktree branches sequentially; when the second worktree's ingest writes the same slug, the sequential merge resolves it as a conflict that the parent handles by picking the earlier write and re-running `find-similar-concept` on the later one at fan-in
- do not try to coordinate across worktrees during parallel ingest — worktrees are isolated by design

If you do notice a slug collision during a direct (non-INIT) ingest — i.e. the paper page already exists with a different arXiv ID — stop and report, per `references/error-handling.md`. Do not write through.

## What ingest does not do for init

- It does not stash or switch branches.
- It does not merge worktrees or run `dedup-edges`, `rebuild-index`, or `lint.py --fix`. Those are batch-finalization operations owned by init.

In INIT MODE PARALLEL, ingest **must** commit its work inside the worktree before exiting, but only when the ingest completed successfully:
- stage every file you created or modified under `wiki/`
- before committing, run `git branch --show-current` and verify the branch name is the worktree branch (contains `init-`), not the base branch. If you are on the base branch, stop and report instead of committing
- run `git commit -m "ingest: <paper-title>"` (or a similarly descriptive message)
- do not push; the parent `$init` will merge the branch during fan-in

In INIT MODE SERIAL, do **not** commit. If the ingest fails part-way through (partial failure), do not hide the incomplete state; stop when cleanup is ambiguous and let the parent init workflow report the recovery point.
