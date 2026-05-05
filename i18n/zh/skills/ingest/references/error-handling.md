# /ingest 错误处理

某个步骤失败时打开此参考。`/ingest` 倾向于优雅降级：记录发生了什么、继续能继续的部分、在最终报告里把缺口暴露给用户。

## 来源解析

- **`.tex` 解析失败**：若同目录下有 PDF，fallback 到 PDF。
- **PDF 文本提取失败**：对前几页走 vision API 恢复 title 与 abstract，再带上恢复的 title 走 `references/pdf-preprocessing.md` 的预处理流程。
- **完全没有可读来源**：停机并报告。不得仅凭 title 就创建论文页面 —— 无内容支撑的论文页面是噪声。
- **INIT MODE 输入不可读**：不得尝试重新 prepare（INIT MODE 下 `raw/` 只读）。停机、记录失败，让上层 `/init` 在 fan-in 时决定重试或跳过。

## 外部 API

- **Semantic Scholar 不可用**（`fetch_s2.py paper` 报错）：跳过 S2 enrichment，`importance` 默认取 3，并在报告中说明该值为临时值。本轮 ingest 的 citation 回填步骤整体跳过。
- **DeepXiv 不可用**（`fetch_deepxiv.py` 报错）：静默跳过 enrichment。DeepXiv 是可选项，缺它只是 plainer ingest，不是降级 ingest。除非用户专门问起 DeepXiv，不要在用户报告中提及。
- **arXiv 源抓取失败**：论文在 arXiv 上但源归档不存在或超时，走 PDF 路径。在最终报告中记录一条 warning。

## slug 冲突

- **生成的 slug 与一个具有不同 arXiv ID 或 title 的已有页面撞名**：停机并报告。不得静默追加数字后缀 —— 两个不同论文落到同一 slug，是 wiki 命名问题的信号，应由用户解决。
- **生成的 slug 与同一篇论文的已有页面撞名**：该论文已 ingest，报告并退出。
- **单次 ingest 内，某个 concept / method 生成的 slug 与另一不同页面撞名**：通过工具内置冲突处理追加数字后缀（`-2`、`-3`……）。这是唯一允许追加后缀的场景 —— 两种真正不同的想法在确定性规则下生成同一 slug。

## wiki 未初始化

若 `wiki/` 不存在或为空，执行：

```bash
"$PYTHON_BIN" tools/research_wiki.py init wiki/
```

然后重跑 `/ingest`。不得在未初始化的 wiki 里创建页面；`index.md` 与 `graph/` 脚手架必须先就位。

## ingest 过程中的部分失败

若某次 ingest 在部分写入后失败（论文页面已写入，但 concept 去重或 graph edge 失败）：

- 不得回滚已成功的写入
- 通过 `tools/research_wiki.py log` 追加一条日志，说明哪些步骤完成、哪些未完成
- 在用户报告中暴露未完成的步骤，让用户通过 `/edit` 或 `/check --fix` 收尾
- INIT MODE 下，若 ingest 成功完成，子代理必须在退出前于 worktree 内 commit（见 `references/init-mode.md`）。若 ingest 部分失败，**不要** commit 不完整状态；让上层 `/init` 在 fan-in 时处理该失败的 worktree

## 停机 vs 继续

以下情况直接停机：

- 完全无法读取来源
- 论文已 ingest（slug + arXiv ID 与已有页面一致）
- slug 冲突会静默覆盖另一个不同的已有论文

以下情况带 warning 继续：

- 某一项 enrichment 源（S2 或 DeepXiv）宕机
- reference list 无法解析（跳过 Step 5；论文 ingest 主体仍可完成）
- 单个 concept / method 去重调用偶发失败（重试一次；仍失败就跳过该候选并记录）

核心原则：保留了一个 well-shaped 论文页面的部分 ingest，比什么都没写的干净 abort 更有用。部分状态可以通过 `/check` 与 `/edit` 恢复；丢失的部分状态则不可恢复。
