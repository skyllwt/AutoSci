# /init Parallel Ingest

Use this reference when `/init` is handing sources to parallel `/ingest` subagents and merging their work back.

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
- In INIT MODE, consume the handed-off canonical path exactly as provided.
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
