# Daily arXiv Recommendation and Ingest Policy

`/daily-arxiv` 是 LLM-first：确定性工具先构建 evidence packet，
再由 skill 判断相关性和动作。工具分数只用于排序，不是最终决策。

## Pipeline

1. 解析 `config/daily-arxiv.yml`；缺失时使用推断默认值。
2. 拉取最近 arXiv 论文，并按 wiki 已知 arXiv ID 去重。
3. 从 papers、topics、concepts、methods、ideas、open questions、recent log
   和可选 profile 偏好构建 wiki profile。
4. 用可用的 Semantic Scholar 和 DeepXiv evidence 增强候选。
5. 由 LLM 给出最终 decisions 和 rationales。
6. 通过 digest 通知；只有显式允许时才调用 `/ingest`。

## Evidence

新增逻辑前先使用已有集成：

- arXiv：title、authors、category、date、URL、abstract。
- Wiki：anchors、topics、concepts、methods、ideas、open questions、recent ingests。
- Semantic Scholar：paper metadata、citation counts、influential counts、
  fields of study、TLDR，以及来自 wiki anchors 的 recommendations。
- DeepXiv：trending rank、social impact、brief/TLDR、keywords，以及可用时的论文结构。

如果 S2 或 DeepXiv 失败，保持运行，并把 degraded signal 写入 digest。
缺失 enrichment 永远不能作为 ingest 依据。

## Decision Schema

LLM 为每个候选写一条 decision：

```json
{
  "arxiv_id": "2501.01234",
  "decision": "strong_recommend",
  "confidence": "high",
  "score": 0.82,
  "rationale": "Connects to the wiki's open question about ...",
  "wiki_connections": ["efficient adaptation", "retrieval"],
  "signals_used": ["arxiv", "wiki_profile", "semantic_scholar", "deepxiv"]
}
```

允许的 decisions 是 `strong_recommend`、`maybe`、`skip`、`ingest`。
允许的 confidence 是 `high`、`medium`、`low`。

OpenAI-compatible 第三方 LLM 只支持 `inform` mode，通过
`tools/daily_arxiv.py recommend-llm` 使用。在这条路径中，`ingest` 不是
允许输出；如果模型尝试输出 `ingest`，会降级为 `strong_recommend`。

## Modes

- `inform`：默认。生成 digest，按配置发送邮件，然后停止。
- `auto-ingest`：显式 opt-in。只有 `decision: ingest` 且
  `confidence: high` 的论文可继续，并且受 `max_auto_ingest` 限制。

不要从 repository 状态、branch、已有 workflow 或 credentials 推断
`auto-ingest`。必须由用户/config/workflow input 显式选择。

## Auto-Ingest Guardrails

- `/ingest` 负责所有论文纳入。`/daily-arxiv` 不得手写 paper pages、
  concepts、methods、people、graph files 或 index entries。
- 顺序调用 `/ingest`；parallel ingest 不在 scope 内。
- 通过 `ingest_status` 或 `ingest_error` 在 `llm-decisions.json` 和最终
  digest 中保留失败信息。
- 只提交 `/ingest` 产生的变更，通常位于 `wiki/` 和 `raw/discovered/`。
- 边界候选保留为 `maybe`；不要 ingest medium/low confidence 项。

## Relationship to `/discover`

`/discover` 回答用户主动提出的 “what should I read next?”，来源可以是
anchors、topic 或 wiki 状态，并且永不 ingest。`/daily-arxiv` 从一个新的
arXiv 时间窗口出发，可通知，也可在显式配置下 ingest。
