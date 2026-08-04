# /ingest INIT MODE 与并行安全

当 `/ingest` 被 `/init` 作为并行子代理调用，或你需要理解并发 ingest 会对共享文件做什么时，打开此参考。

## 何时处于 INIT MODE

只要 `/ingest` 的来源路径来自 `.checkpoints/init-sources.json`，就处于 INIT MODE。上层 `/init` 会为每篇论文在隔离的 `git worktree` 内跑一个 `/ingest`，流程见 `skills/init/references/parallel-ingest.md`。

在 INIT MODE 下：

- 来源始终是 `/init` 已经 prepare 过的 `canonical_ingest_path`（用户自有论文是 `raw/tmp/...`，外部引入论文是 `raw/discovered/...`）
- `raw/` 严格只读 —— 不得写 `raw/tmp/`、`raw/discovered/`，也不得写 `raw/` 下任何路径
- **跳过** `fetch_s2.py citations <arxiv-id>` 与 `fetch_s2.py references <arxiv-id>` —— 由上层 `/init` 在 fan-in 时统一做 citation sweep
- **跳过** `rebuild-context-brief` 与 `rebuild-open-questions` —— 上层在所有子代理 merge 后统一运行一次
- **跳过** 易冲突的 topic 写入 —— 多个并行 ingest 同时 append 相同 topic 会引发 merge 冲突。让上层在 fan-in 后处理 topic 更新，或交给 `/edit`。
- **跳过对已有页面的反向链接编辑** —— 不要向已有 concept 页面追加 `key_papers`，不要向已有 paper 页面的 `## Key papers` 或 `## Related` 追加内容，也不要向已有 people 页面追加内容。只通过 `tools/research_wiki.py add-edge` 记录关系。上层 `/init` 在 fan-in 后统一重建这些反向链接。

其余一切（paper 页面创建、通过 `find-similar-concept` 做 concept 去重、通过手工扫描 `wiki/methods/` 做 method 去重、people 页面创建、paper 的 `## Related` 链接、concept / method / foundation 的 graph edge）在每个子代理内正常执行。

## 如何识别 INIT MODE

`/init` 会在子代理 prompt 中传入 canonical path。任一下列信号出现即判定为 INIT MODE：

- 来源路径以 `raw/tmp/` 或 `raw/discovered/` 开头，**且** `.checkpoints/init-sources.json` 引用到该路径
- 子代理 prompt 显式写出 "INIT MODE"

两个信号都缺失时，按用户直接调用处理，跑完整 workflow（包含 citation、rebuild，以及 `raw/tmp/` prepare 的必要步骤）。

## 并行安全写入

即便不在 INIT MODE 下，也应假设有另一个 `/ingest` 在并发运行 —— 批量 ingest 已在路线图上。三条规则能让并发写入安全：

1. **共享文件的每次写入都经过工具。** `graph/edges.jsonl`、`graph/citations.jsonl`、`index.md`、`log.md` 分别通过 `tools/research_wiki.py add-edge`、`add-citation`、index 更新命令、`log` 写入。工具层使用 append 语义，仓库 `.gitattributes` 对这几条路径声明了 `merge=union`，并行 worktree 可以无冲突地 merge。
2. **slug 的分配是确定性的。** `tools/research_wiki.py slug "<title>"` 对同一 title 始终给出同一 slug，和 worktree 无关。冲突由工具内部以数字后缀解决，不允许临时自行重命名。
3. **绝不对共享文件加锁或整体改写。** 把 `wiki/index.md`、`wiki/graph/edges.jsonl` 或 `wiki/graph/citations.jsonl` 作为整体块替换写回，会在 worktree merge 时覆盖并行 peer 的工作。用工具命令即可，它们做 append。

## 并行创建新页面

当两个并行 `/ingest` 子代理都需要同一个 concept slug 时，两边都会尝试创建，fan-in merge 会失败。缓解措施：

- 每篇论文的新建上限（见 `references/dedup-policy.md`）让冲突面本就很小
- `/init` 在上层按顺序 merge worktree branch；第二个 worktree 写同一 slug 时，顺序 merge 会作为冲突暴露出来，由上层在 fan-in 时采用先到先得并对后者重跑 `find-similar-concept`
- 不要在 ingest 过程中跨 worktree 自行协调 —— worktree 的隔离是设计目的

如果在非 INIT 直连 ingest 下发现 slug 冲突（即已有论文页面使用同一 slug 但 arXiv ID 不同），按 `references/error-handling.md` 停机并报告，不得强行写入。

## `/ingest` 不为 `/init` 做的事

- 不 stash，也不切换 branch。
- 不 merge worktree，也不跑 `dedup-edges`、`rebuild-index`、`lint.py --fix`。这些是 fan-in 操作，归 `/init`。

在 INIT MODE 下，`/ingest` **必须**在成功完成后于 worktree 内提交结果：
- 将 `wiki/` 下所有新建或修改的文件加入暂存区
- commit 前先执行 `git branch --show-current`，确认当前 branch 是 worktree branch（包含 `init-` 前缀），而不是 base branch。若在 base branch 上，停止并报告，不要 commit
- 执行 `git commit -m "ingest: <论文标题>"`（或含义类似的提交信息）
- 不要 push；上层 `/init` 会在 fan-in 时合并该分支

若 ingest 过程中部分失败（partial failure），**不要** commit 不完整状态。让上层 `/init` 在 fan-in 时处理该失败的 worktree。
