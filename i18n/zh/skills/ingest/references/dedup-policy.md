# /ingest 去重策略

准备新建或更新一个 concept、method 或 foundation 链接前，打开此参考。

## 心智模型

一个健康的 ΩmegaWiki 里，concept 与 method 的数量远少于 paper。每个 concept 由许多深化或扩展它的 paper 共享；每个 method 由许多复用或扩展它的 paper 共享。如果 `/ingest` 默认为每篇论文都新建 concept / method，wiki 会迅速沦为一堆近似重复的页面 —— 综述生成、gap 检测、idea novelty、citation 推理全部会被这种噪声破坏。

默认动作是**合并**。例外才是**新建**，并且每次新建都必须有清晰的理由。

## 何时打开此参考

- `/ingest` Step 4：识别论文引入或扩展的 concept 时。
- `/ingest` Step 4：识别论文引入的 method（命名、可复用、可被引用）时。
- 任何想"为保险起见"新建 concept / method 却没先查重的时刻。

## 强制工具调用

新建 concept 前，先调用去重工具：

```bash
"$PYTHON_BIN" tools/research_wiki.py find-similar-concept wiki/ "<candidate title>" --aliases "<a,b,c>"
```

返回按相似度排序的 JSON 列表。`find-similar-concept` 同时扫描 `wiki/concepts/` 与 `wiki/foundations/`，并给每条结果打 `entity_type` 标签。工具是相似度的真相来源；不要用肉眼重新估算分数。

method 没有 `find-similar-method` 工具。直接扫 `wiki/methods/*.md`：阅读每个已有 method 的 `name`、`tags` 与 `## Mechanism` 摘要，手工判断候选是否就是同一项技术换了个名字。使用与 concept 相同的合并偏好（默认合并；只在确实不同时才新建）。

跳过查重是 wiki 膨胀最常见的原因。即便你觉得本 session 早些时候已经读过相关页面，也仍要查重 —— 换句话说的近似重复很容易从人工扫描里滑过。

## 决策规则

concept 读取 top 结果的 `score`：

- **top 结果是 foundation 且 score ≥ 0.40** —— 走 foundation link 路径。候选是教科书级背景知识，不是新机制。在 `edges.jsonl` 写一条 `derived_from` edge，在 paper 的 `## Related` 里写 `[[foundation-slug]]`。不得修改 foundation 页面（foundation 是终端节点，见 `references/cross-references.md`）。foundation link 不计入每篇论文的新建上限。
- **score ≥ 0.80** —— 合并。候选与 top 是同一概念。把本论文追加到已有页面的 `key_papers`，补 graph edge，写反向链接。concept 默认用 `uses_concept`；只有论文实质修改、泛化或特化该 concept 时才用 `extends_concept`；只有明确批评时才用 `critiques_concept`。不要新建文件。
- **score 0.40–0.80** —— 阅读 top 的 `## Definition` 再决定。默认合并。只有当你能指出具体的技术差异时才新建：不同机制、不同形式化。若候选是已有 concept 的有意义子类，合并并在 `## Variants` 追加一条 bullet，而不是拆分。
- **score < 0.40 或结果为空** —— 无已有匹配。允许新建，但要遵守下面的每篇上限。

method 把 "score" 替换为人工判断：同名 + 同机制 ⇒ 合并（追加 `source_papers`）；不同机制 ⇒ 仅当新技术可命名、可复用、且很可能被未来论文引用时才新建。无论是否新建 `methods/` 页面，论文页面自身的 `## Method` 正文章节都捕捉这篇论文的方法叙述。

过度合并代价低：合并错了的页面可以日后拆分，历史保留。过度新建代价高：近似重复会静默污染所有下游 skill，事后难以察觉。

## 每篇论文的新建上限

上限的目的是让默认行为保守。它不是要填满的配额。

- importance < 4：最多 **1** 个新 concept、**1** 个新 method
- importance ≥ 4：最多 **3** 个新 concept、**2** 个新 method
- foundation link 不计入。

后续候选若会超过上限，就合并到最接近的已有条目 —— 即使其分数低于通常的合并阈值。若确实没有可安全合并的候选，就整体跳过该实体 —— `/check` 会在后续扫描里把缺口暴露出来，用户可决定是否 `/edit` 补齐。

## 只做形状检查，不做语义审计

确实要新建或编辑 concept / method 页面时，对它跑与 paper 页面相同的狭窄形状检查：

- 每个必需 frontmatter 字段存在且非空
- concept：`maturity` ∈ {`stable`, `active`, `emerging`, `deprecated`}；`definition` 是单句（正文 `## Definition` 可以展开）
- method：`type` ∈ {`architecture`, `training`, `inference`, `evaluation`, `data`, `benchmark`, `system`, `optimization`, `prompting`, `protocol`, `other`}
- YAML 可解析

该检查能避免 `/check` 下一轮把明显残缺的页面全部捞出。超出这个范围的一切 —— 反向链接对称性、concept 的 `linked_ideas` 是否被对向引用、method 的 `parent_methods` 链是否一致 —— 属于 `/check`。把这些审计搬进 `/ingest` 只会拖慢 skill 并与 `/check` 做重复工作。

## `/check` 负责的、`/ingest` 不负责的

- 跨实体反向链接对称性（A 链接到 B ⇒ B 是否链回 A）
- dangling node 检测（被引用但缺失的页面，或存在但不可达的页面）
- ideas 与 experiments 的 status 一致性
- edge 类型合法性与 edge 去重
- 上述一切的分级修复建议

你可以信任 `/check` 去发现这些并产出修复报告。`/ingest` 聚焦在**写入点**做出 well-shaped 的实体与正确的正向/反向链接即可。
