# /init Parallel Ingest

当 `/init` 需要把来源交给并行 `/ingest` 子代理并把结果 merge 回来时，打开此参考文件。

## Fan-out 前的安全步骤

- 运行 `git status --short`。
- 将 `wiki/`、`raw/papers/`、`raw/tmp/`、`raw/discovered/` 与 `.checkpoints/init-*.json` 视作 scaffold 文件。
- 先 stash 这些路径之外的无关脏文件。
- 先验证 `.gitattributes` 对 `wiki/log.md`、`wiki/graph/edges.jsonl`、`wiki/graph/citations.jsonl`、`wiki/index.md` 使用了 `merge=union`。
- fan-out 前先提交 scaffold，确保 `BASE_COMMIT` 真的包含所有生成的页面与 manifests：

```bash
git add wiki/ raw/papers/ raw/tmp/ raw/discovered/ .checkpoints/init-prepare.json .checkpoints/init-plan.json .checkpoints/init-sources.json
git commit -m "init: scaffold before parallel ingest" --no-gpg-sign
BASE_COMMIT=$(git rev-parse HEAD)
```

- 用 `tools/research_wiki.py checkpoint-set-meta` 记录 `stash_ref`、`base_branch`、`base_commit`。
- `/init` 的 worktree 模式要求当前位于一个命名分支上；detached HEAD 必须先停止。

## 创建 Worktree

每篇论文的 worktree 都应从 scaffold commit 拉出：

```bash
WT_BRANCH="init-${BASE_BRANCH//\//-}-<rank>-<paper-slug>"
WT_PATH="../.worktrees/$WT_BRANCH"
git worktree add -b "$WT_BRANCH" "$WT_PATH" "$BASE_COMMIT"
```

- 不要对当前 branch 名直接执行 `git worktree add`；Git 会因为该 branch 已经在主工作区签出而拒绝。
- 论文顺序以 `.checkpoints/init-sources.json` 的 `shortlist_rank` 为准，而不是重新扫目录或按 citation count。

## 子代理 Prompt 合同

- 子代理的 shell 工作目录必须是 worktree 路径（`$WT_PATH`），而不是主仓库根目录。所有相对路径均从该路径解析。
- 只对一个相对路径执行 `/ingest`。
- 不得绕过 `/ingest`。
- 在 INIT MODE 下，必须原样消费 handoff 给它的 canonical path。
- 跳过 `fetch_s2.py citations`。
- 跳过 `fetch_s2.py references`。
- 跳过每个子代理自己的 `rebuild-index`。
- 跳过每个子代理自己的 `rebuild-context-brief`。
- 跳过每个子代理自己的 `rebuild-open-questions`。
- 跳过易冲突 topic 写入。
- 退出前必须在各自 worktree 内提交结果，确保 fan-in merge 的是实际 ingest commit。

## Fan-in

全部子代理完成后：

1. 如有需要先切回 `BASE_BRANCH`，再按 planner 顺序在该 branch 上逐个 merge worktree branch。
2. concept / method 冲突默认保守合并，不要扩散 near-duplicate 页面。
3. 只 merge 已经产生 ingest commit 的 worktree branch。若某个 branch 没有提交结果，应先停止并修复，而不是硬合并。
4. 运行：

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

若 `stash_ref` 存在，在最后再 pop。若 stash pop 失败，保留 checkpoint 并在报告中说明。
