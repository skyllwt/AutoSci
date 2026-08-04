# /discover seed 模式

每次调用只选一个模式。决策依据是用户（或调用方 skill）实际说了什么，而不是 wiki 里已有什么。

## Anchor 模式（`from-anchors`）

使用场景：用户指明了一或多篇具体论文，或者这是 `/ingest --discover` 的后续。

触发信号：

- "找和 LoRA 相似的论文"
- "这篇刚 ingest 的，周围还有什么"
- 请求里出现了 arXiv URL / ID / wiki paper slug
- `/ingest --discover` 的内部调用（anchor = 刚 ingest 论文的 arXiv ID）

anchor 模式是最强信号通道 —— Semantic Scholar 的 recommendations endpoint 基于训练模型返回语义相似论文，比在用户手握具体参考点时做关键词搜索更有效。

如果用户给了负例（"不要这些"、"和 X 不一样的"），通过 `--negative` 传入。S2 recommendations endpoint 会把结果分布推离负 anchor，当用户想跳出自己已熟悉的子领域时非常有用。

## Topic 模式（`from-topic`）

使用场景：用户给的是 topic / 方向 / 关键词，没有指明具体论文。

触发信号：

- "找 diffusion model fine-tuning 方向的论文"
- "retrieval augmented generation 这块都写了些什么"
- 只有领域短语，没有 anchor

topic 模式跑 S2 search 加（如可用的）DeepXiv search，再排序。它是 `/init` planner 的轻量替代：适合探索，但**不**替代 `/init` 的完整 bootstrap workflow。用户想用一个 topic 从头建 wiki，应该引导到 `/init`，而不是让 `/discover` 承担那个职责。

## Wiki 模式（`from-wiki`）

使用场景：用户开放式地问 "接下来读什么"，没有 anchor 也没有 topic。

触发信号：

- "给我下一批要读的论文"
- "当前 wiki 的一个好后续是什么"
- 显式 `--from-wiki` flag

wiki 模式取 wiki 最近修改过的几篇论文页，提取 arXiv ID 作为 anchor。这会隐式把 discovery 偏向用户最近在做的东西 —— 通常正是期望行为。

如果 `wiki/papers/` 为空，或没有论文带 `arxiv` 或 `arxiv_id` frontmatter，wiki 模式无法运行。告诉用户 wiki 过于稀疏，建议改用 topic 模式（或 `/init`）。

## Venue 模式（`from-venue`）

使用场景：用户要求查看某个具体会议/venue 和年份的论文。

触发信号：

- "给我看看 NeurIPS 2024 里和我 wiki 相关的论文"
- "ICML 2023 里有哪些关于 diffusion model 的论文"
- "ICLR 2024 有什么值得读的"

Venue 模式从 Paper Copilot 的公开 GitHub JSON 源（`papercopilot/paperlists`）拉取该 venue/year 的完整论文列表，规范化每条记录，并按与用户现有 wiki 内容的相关性排序。该模式要求 wiki 不能过于稀疏 —— 若 wiki 太空，工具会明确报错而不是返回一份未个性化的列表。

Venue 模式**不**使用 Semantic Scholar 或 DeepXiv，也**不**向 `wiki/` 或 `raw/` 写入。

## 用户同时给了 anchor 和 topic 怎么办？

优先 anchor 模式。anchor 是比 topic 字符串强得多的信号。可以在给用户的 report 里提一下 topic 已被注意，但 discovery 本身走 `from-anchors`。

## 用户同时给了 venue 和 topic 怎么办？

若用户明确指名了 venue 和年份，优先 venue 模式。可以在报告中提及 topic，但 venue 模式的排名由 wiki 相关性驱动，而非 topic 字符串。若 wiki 过于稀疏导致 venue 模式无法运行，应明确报错并建议先 ingest 更多论文，或另行运行 topic discovery；不要静默回退到未个性化的 venue ranking。
