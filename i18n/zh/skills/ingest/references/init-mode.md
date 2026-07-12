# $ingest INIT MODE 与 batch 安全

当 ingest 被 init workflow 调用，或你需要理解 batch ingest 会对共享文件做什么时，打开此参考。

## 何时处于 INIT MODE

只要 ingest 的来源路径来自 `.checkpoints/init-sources.json`，就处于 INIT MODE。上层 init workflow 可以在主工作区逐篇串行执行（**INIT MODE SERIAL**，Codex 默认），也可以在隔离的 `git worktree` 中每篇论文一个子代理并行执行（**INIT MODE PARALLEL**，可选路径）。见 `skills/init/references/parallel-ingest.md`。

在 INIT MODE 下：

- 来源始终是 `$init` 已经 prepare 过的 `canonical_ingest_path`（用户自有论文是 `raw/tmp/...`，外部引入论文是 `raw/discovered/...`）
- `raw/` 严格只读 —— 不得写 `raw/tmp/`、`raw/discovered/`，也不得写 `raw/` 下任何路径
- **跳过** `fetch_s2.py citations <arxiv-id>` 与 `fetch_s2.py references <arxiv-id>` —— 由上层 init workflow 在 batch 后统一做 citation sweep
- **跳过** `rebuild-context-brief` 与 `rebuild-open-questions` —— 上层在所有论文 ingest 后统一运行一次
- **跳过** 易冲突的 topic 写入 —— 多个 batch ingest 可能触碰同一 topic。让上层在 batch 后处理 topic 更新，或交给 `$edit`。
- **跳过对已有页面的反向链接编辑** —— 不要向已有 concept 页面追加 `key_papers`，不要向已有 paper 页面的 `## Key papers` 或 `## Related` 追加内容，也不要向已有 people 页面追加内容。只通过 `tools/research_wiki.py add-edge` 记录关系。上层 init workflow 在 batch 后统一重建这些反向链接。

其余一切（paper 页面创建、通过 `find-similar-concept` 做 concept 去重、通过手工扫描 `wiki/methods/` 做 method 去重、people 页面创建、paper 的 `## Related` 链接、concept / method / foundation 的 graph edge）在每篇论文 ingest 中正常执行。

## 如何识别 INIT MODE

init workflow 会在 handoff 中传入 canonical path。任一下列信号出现即判定为 INIT MODE：

- 来源路径以 `raw/tmp/` 或 `raw/discovered/` 开头，**且** `.checkpoints/init-sources.json` 引用到该路径
- handoff 显式写出 "INIT MODE SERIAL" 或 "INIT MODE PARALLEL"

两个信号都缺失时，按用户直接调用处理，跑完整 workflow（包含 citation、rebuild，以及 `raw/tmp/` prepare 的必要步骤）。

## 串行与并行的完成动作

- **INIT MODE SERIAL** 下，每篇论文结束后不要 commit。把变更留在主工作区，由上层 init workflow 在所有论文完成后统一 rebuild、lint 与报告。
- **INIT MODE PARALLEL** 下，成功 ingest 后必须在 worktree 内 commit，确保 fan-in 能 merge 到实际论文提交。

## Batch 安全写入

即便不在 INIT MODE 下，也应假设有另一个 ingest 正在同一 batch 或 sibling worktree 中运行。三条规则能让共享写入安全：

1. **共享文件的每次写入都经过工具。** `graph/edges.jsonl`、`graph/citations.jsonl`、`index.md`、`log.md` 分别通过 `tools/research_wiki.py add-edge`、`add-citation`、index 更新命令、`log` 写入。工具层使用 append 语义，仓库 `.gitattributes` 对这几条路径声明了 `merge=union`，并行 worktree 可以无冲突地 merge。
2. **slug 的分配是确定性的。** `tools/research_wiki.py slug "<title>"` 对同一 title 始终给出同一 slug，和 worktree 无关。冲突由工具内部以数字后缀解决，不允许临时自行重命名。
3. **绝不对共享文件加锁或整体改写。** 把 `wiki/index.md`、`wiki/graph/edges.jsonl` 或 `wiki/graph/citations.jsonl` 作为整体块替换写回，会在 worktree merge 时覆盖并行 peer 的工作。用工具命令即可，它们做 append。

## Batch 模式下创建新页面

当两个 batch ingest 步骤都需要同一个 concept slug 时，串行模式应能让第二篇看到第一篇已创建的页面；并行模式可能在 fan-in 时暴露冲突。缓解措施：

- 每篇论文的新建上限（见 `references/dedup-policy.md`）让冲突面本就很小
- 并行模式下，init 上层按顺序 merge worktree branch；第二个 worktree 写同一 slug 时，顺序 merge 会作为冲突暴露出来，由上层在 fan-in 时采用先到先得并对后者重跑 `find-similar-concept`
- 并行 ingest 过程中不要跨 worktree 自行协调 —— worktree 的隔离是设计目的

如果在非 INIT 直连 ingest 下发现 slug 冲突（即已有论文页面使用同一 slug 但 arXiv ID 不同），按 `references/error-handling.md` 停机并报告，不得强行写入。

## ingest 不为 init 做的事

- 不 stash，也不切换 branch。
- 不 merge worktree，也不跑 `dedup-edges`、`rebuild-index`、`lint.py --fix`。这些是 batch finalize 操作，归 init。

在 INIT MODE PARALLEL 下，ingest **必须**在成功完成后于 worktree 内提交结果：
- 将 `wiki/` 下所有新建或修改的文件加入暂存区
- commit 前先执行 `git branch --show-current`，确认当前 branch 是 worktree branch（包含 `init-` 前缀），而不是 base branch。若在 base branch 上，停止并报告，不要 commit
- 执行 `git commit -m "ingest: <论文标题>"`（或含义类似的提交信息）
- 不要 push；上层 `$init` 会在 fan-in 时合并该分支

在 INIT MODE SERIAL 下，不要 commit。若 ingest 过程中部分失败（partial failure），不要隐藏不完整状态；若 cleanup 含糊，停止并让上层 init workflow 报告恢复点。
