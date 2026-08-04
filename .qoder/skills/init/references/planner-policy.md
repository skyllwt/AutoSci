# /init Planner Policy

当 `/init` 需要读取 `.checkpoints/init-plan.json`、裁剪 shortlist、或解释 planner 的 warning / error 时，打开此参考文件。

## 行为策略

- seeded 模式下，如果用户省略 `topic`，就从本地论文标题/摘要以及 notes/web 信号里提取 discovery 与 ranking 线索。
- bootstrap 模式下，如果 `topic` 与 notes/web 关键词都缺失，应把它记为 planner error，而不是发起空搜索。
- 优先 relevance、freshness、connectivity 与 survey coverage。
- 如有帮助，优先保留一篇 survey/overview。
- 在 seeded 模式且 introduced 容量有限时，应让 freshness 主导，并避免偏旧外部非 survey 论文仅凭 citation 优势堆积进入结果。
- 在 bootstrap 模式或非常宽裕的 seeded 情况下，如果确实有助于覆盖面，可以保留一篇偏旧 canonical anchor。
- 若检测到中文 notes/web 内容，要保留 planner warning，说明提取与排序可靠性可能较低，并把 provisional 输出视为较低置信度。
- 若 `SEMANTIC_SCHOLAR_API_KEY` 未配置，也继续执行；但要把公开限速路径记录为 planner warning。

## LLM 裁剪期望

- 在 `fetch` 前读取 `.checkpoints/init-plan.json`，并显式裁剪 over-picked 的 shortlist。
- 即使 shortlist 看起来已经“差不多”，也不得跳过裁剪步骤。
- 在 `fetch` 前给出最终选择结果，至少包含 `shortlist_count`、`final_count` 与最终 `candidate_id` 列表。
- 如果最终数量超出允许范围，就先修正选择，再进入 `fetch`，除非命中已文档化的例外分支。

## 真相源边界

- `tools/init_discovery.py` 是精确 weights、thresholds、shortlist 常量与 scoring math 的唯一实现权威。
- `SKILL.md` 与本参考文件只描述 orchestration 与行为期望。
- 不要在这里重复写数字常量，也不要在 LLM 推理里覆盖工具拥有的确定性策略。
