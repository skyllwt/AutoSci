# /init Batch Ingest

Use this reference when `/init` is handing sources to ingest. Codex should use the serial contract by default. Use the parallel worktree contract only when the runtime can guarantee subagent working directories, per-paper commits, and fan-in merge control.

## Serial Contract (Codex Default)

- Run from the main workspace; do not create worktrees.
- Read paper order from `.checkpoints/init-handoff.json` by `tasks[*].order`.
- For each task, load the active ingest skill instructions named in `tasks[*].active_ingest_skill` and execute the ingest workflow for exactly one relative `tasks[*].canonical_ingest_path`.
- State **INIT MODE SERIAL** in the handoff so ingest consumes the prepared path, treats `raw/` as read-only, skips per-paper citation/reference fetches, skips per-paper rebuilds, skips conflict-prone topic writes, and does not commit.
- Keep all final rebuild, dedup, lint, citation backfill, and visualization steps in `/init` after the batch.
- If a paper fails cleanly before writing pages, record it and continue. If it leaves ambiguous partial wiki state, stop and report the recovery point.
- Detached HEAD is acceptable in serial mode because no branch fan-out or merge is required.

## Parallel Worktree Contract (Optional)

Use this path only when the runtime can spawn one subagent per paper with a known `$WT_PATH` working directory and can merge branches afterward.

## Pre-Fan-Out Safety

- Run `git status --short`.
- Treat files under `wiki/`, `raw/papers/`, `raw/tmp/`, `raw/discovered/`, and `.checkpoints/init-*.json` as scaffold files.
- Stash unrelated dirty files outside those paths.
- Verify `.gitattributes` contains `merge=union` for `wiki/log.md`, `wiki/graph/edges.jsonl`, `wiki/graph/citations.jsonl`, and `wiki/index.md`.
- Commit the scaffold before fan-out so `BASE_COMMIT` contains the generated pages and manifests that every worktree must inherit:

```bash
git add wiki/ raw/papers/ raw/tmp/ raw/discovered/ .checkpoints/init-prepare.json .checkpoints/init-plan.json .checkpoints/init-sources.json
git commit -m "init: scaffold before parallel ingest" --no-gpg-sign
BASE_COMMIT=$(git rev-parse HEAD)
```

- Record `stash_ref`, `base_branch`, and `base_commit` with `tools/research_wiki.py checkpoint-set-meta`.
- `/init` worktree mode requires a named branch; stop on detached HEAD.

## Worktree Creation

For each paper, create the worktree from the scaffold commit on the current branch:

```bash
WT_BRANCH="init-${BASE_BRANCH//\//-}-<rank>-<paper-slug>"
WT_PATH="../.worktrees/$WT_BRANCH"
git worktree add -b "$WT_BRANCH" "$WT_PATH" "$BASE_COMMIT"
```

- Do not run `git worktree add` against the current branch name itself; Git will refuse because that branch is already checked out in the main workspace.
- Order papers by `shortlist_rank` from `.checkpoints/init-sources.json`, not by rescanning raw folders or by raw citation count.

## Subagent Prompt Contract

- The subagent's shell working directory must be the worktree path (`$WT_PATH`), not the main repository root. All relative paths resolve from there.
- Execute `/ingest` for exactly one relative source path.
- Do not bypass `/ingest`.
- In INIT MODE PARALLEL, consume the handed-off canonical path exactly as provided.
- Skip `fetch_s2.py citations`.
- Skip `fetch_s2.py references`.
- Skip per-subagent `rebuild-index`.
- Skip per-subagent `rebuild-context-brief`.
- Skip per-subagent `rebuild-open-questions`.
- Skip conflict-prone topic writes.
- Commit the result inside the worktree before exiting so fan-in merges a real ingest commit.

## Fan-In

After all agents complete:

1. Switch the main workspace back to `BASE_BRANCH` if needed, then merge worktree branches sequentially there in planner order.
2. Resolve true concept/method conflicts conservatively: merge, do not multiply near-duplicates.
3. Merge only committed worktree branches. A branch with no ingest commit is an error to stop and fix, not something to merge through.
3. Run:

```bash
git switch "$BASE_BRANCH"
git merge --no-ff "$WT_BRANCH" --no-edit
git worktree remove "$WT_PATH"
git branch -d "$WT_BRANCH"
"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/
"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix
```

If `stash_ref` exists, pop it at the end. If stash pop fails, keep the checkpoint and report the failure.
