# /ingest 交叉引用

在任何 wiki 页面上写链接时，打开此参考。每一条正向链接都有反向义务。下表是合同。

## 正向 → 反向义务

对应根 `CLAUDE.md`（"Cross-Reference 规则"）中的矩阵，裁剪到 `/ingest` 实际写入的 edge：

| 正向操作（你在页面 A 上写什么） | 必须同步的反向操作（在同一 turn 里你在页面 B 上写什么） |
|--------------------------------|--------------------------------------------------------|
| `papers/P` 写 `Related: [[concept-K]]` | `concepts/K` 的 `key_papers` 追加 `P` |
| `papers/P` 写 `[[person-R]]`（任意正文章节） | `people/R` 的 `## Recent work` 追加 `[[P]]` |
| `concepts/K` 写 `key_papers: [[paper-P]]` | `papers/P` 的 `## Related` 追加 `K` |
| `methods/M` 写 `source_papers: [[paper-P]]` | `papers/P` 的 `## Related` 追加 `M` |
| `methods/M` 写 `parent_methods: [[method-N]]` | `methods/N` 的 `child_methods` 追加 `M`（反之亦然） |
| `<entity>/E` 写 `parent_topics: [topic-T]` | `topics/T` 把 `E` 追加到对应的 `key_papers` / `key_concepts` / `key_methods` / `key_foundations` / `key_people` 列表 |
| `concepts/K` 写 `grounded_in: [foundation-X]` | `foundations/X` 的 `## Grounds concepts` 追加 `[[K]]` |
| `methods/M` 写 `grounded_in: [foundation-X]` | `foundations/X` 的 `## Grounds methods` 追加 `[[M]]` |
| `papers/P` 发出 `proposes_method`/`applies_method`/`extends_method` → `methods/M`（edge） | `methods/M` 的 `## Proposed by` / `## Applied by` / `## Extended by` 追加 `[[P]]` |
| `papers/P` 发出 `contributes_to_foundation` → `foundations/X`（edge） | `foundations/X` 的 `## Contributed by papers` 追加 `[[P]]` |
| `concepts/A` 发出 `shares_*` / `contrasts_with_concept` → `concepts/B`（对称 edge） | 仅图谱层；无 body 反向（endpoint 已规范化） |

写了正向却没写反向，是 `/check` 报 `missing-field` 的最常见来源。把两边放在同一 turn 内做，整类错误就被消灭。

## Foundation 不再是终端节点

`/ingest` 永远不**新建** foundation —— foundation 由 `/prefill` seed。但 foundation **不再**是终端节点：链入它的关系现在会把反向写进 foundation 正文：

- `concepts.grounded_in` → foundation 的 `## Grounds concepts`
- `methods.grounded_in` → foundation 的 `## Grounds methods`
- 来自论文的 `contributes_to_foundation` edge → foundation 的 `## Contributed by papers`

在同一 turn 内追加反向,或跑 `lint --fix` 回填。论文建立在教科书背景之上时,走 `contributes_to_foundation`(一条带 `--confidence`/`--evidence` 的、有证据的 edge),而不是普通链接。若某个 concept 候选看起来像 foundational 却没有匹配,仍走普通 concept 路径(必要时新建 concept 页面),让用户日后用 `/prefill` seed foundation。

## paper-to-concept 语义 edge

paper 与 concept 的关系是使用、引入、扩展或批评。每条 paper-to-concept 语义 edge 都必须带 `--confidence high|medium|low`。

edge 类型选择：

- **`introduces_concept`** —— 严格的新颖性：论文明确把该 concept 作为贡献来提出、命名或定义。
- **`uses_concept`** —— 默认选项：论文依赖已有 concept，但没有实质修改它。
- **`extends_concept`** —— 论文修改、泛化、特化或形式化已有 concept。
- **`critiques_concept`** —— 论文指出某个 concept 的限制、失败模式或错误假设。

在 `introduces_concept` 与 `uses_concept` 之间不确定时，选 `uses_concept`。在 `uses_concept` 与 `extends_concept` 之间不确定时，也选 `uses_concept`。不要再写 `paper → concept` 的 `supports` 或普通 `extends`。
该工具会拒绝缺少 confidence/evidence 的新写入，也会拒绝 legacy paper-to-concept edge 类型。

## paper-to-method 语义 edge

paper 与 method 的关系是提出、应用或扩展。每条 `paper → method` edge 都要带 `--confidence high|medium|low` 与 `--evidence`：

- **`proposes_method`** —— 论文把该方法作为贡献提出（它是该方法的 source paper）。
- **`applies_method`** —— 论文基本原样使用一个已有方法。
- **`extends_method`** —— 论文修改、泛化或在已有方法之上扩展。

反向落在 method 页的 `## Proposed by` / `## Applied by` / `## Extended by` 区（同一 turn 内追加,或由 `lint --fix` 补）。`methods.source_papers` 仍是"提出或复用该方法的论文"的稳定 frontmatter 索引。

## concept-to-concept 语义 edge

仅当原文明确表达两个 concept 之间的关系时,加一条**对称** edge（带 `--confidence`、`--evidence`）：

- **`shares_mechanism_with`** —— 两个 concept 依赖同一底层机制。
- **`shares_assumption_with`** —— 它们建立在相同假设之上。
- **`related_problem_formulation`** —— 它们以不同方式形式化同一问题。
- **`contrasts_with_concept`** —— 它们是明确对立 / 互斥的 framing。

对称 edge 由 `add-edge` 规范化（endpoint 排序、`symmetric: true`）—— 没有单独的 body 反向。松散、无类型的关联用 `related_concepts`（frontmatter）；这些 typed edge 留给论文确实陈述的关系。

## paper-to-paper edge

bibliographic 层与 semantic 层分开：

- 当 reference 能解析到已有 `wiki/papers/{slug}.md` 时，总是写 `graph/citations.jsonl`，`type: cites`
- 只有论文文本给出清晰语义信号时，才写 `graph/edges.jsonl`
- 不要把每条 citation 都强行解释成 semantic edge

paper-to-paper semantic edge 应该保持稀疏。它要求两篇论文的贡献之间有具体关系，而不是仅仅共享主题、模态、架构族、benchmark 族或高层方法词。如果同一句描述可以同时套到 wiki 里几十篇论文上，就不要写 paper-to-paper edge；交给 topic/concept 链接和 citation 层表达。

semantic edge 类型选择：

- **`same_problem_as`** —— 对称；两篇论文处理同一个具体任务、研究问题或问题形式化，因此它们的答案可以直接比较。不要因为都属于 "attention"、"video generation" 或 "LLM evaluation" 这类宽泛方向就使用它。当两篇论文从不同角度攻同一问题（即原 `complementary_to` 情景）时，也用这个类型。
- **`similar_method_to`** —— 对称；两篇论文共享有辨识度的机制、形式化、训练策略或算法设计。不要因为都"使用 transformer"、"使用 diffusion" 或 "使用 RL" 就使用它。
- **`builds_on`** —— 有方向；当前论文直接依赖、改造或扩展另一篇论文的具体方法、形式化、数据集、结果或系统。包含"improves on"情景 —— 当前论文宣称在质量/效率/适用范围上优于前作时也写 `builds_on`。不要用于模糊的 inspiration。
- **`challenges`** —— 有方向；当前论文削弱、质疑或给出反证，挑战另一篇论文的结果、假设或 framing。

注：`compares_against` / `improves_on` / `surveys` / `complementary_to` 已被移除。
比较 baseline 归入 `cites`；"improves on" 是 `builds_on` 的子集；
survey 关系由 `papers.contribution_type` 包含 `survey` 派生。

所有 paper-to-paper semantic edges 都必须带 `--confidence high|medium|low`。对称类型由 `tools/research_wiki.py add-edge` 自动规范 endpoint 顺序并写入 `symmetric: true`。
该工具会拒绝缺少 confidence/evidence 的新写入，也会拒绝 legacy paper-paper edge 类型。

- **无 / 跳过** —— 以上都不能干净对应时，跳过 semantic edge。graph 噪声比缺一条 edge 更糟。

不确定时，跳过。paper-to-paper semantic edge 用于高信号的局部关系，不用于按领域聚类。

## 正反两侧原子写入

`/ingest` 写的每一条链接，反向都应在同一 turn 内落地。具体做法：

1. 决定建立此链接。
2. 在源页面写正向条目。
3. 在目标页面写反向条目。
4. 若该链接对应一条 semantic graph edge（paper↔concept、paper→method、paper→foundation contribution、concept↔concept、paper↔paper），通过 `tools/research_wiki.py add-edge` 写出。
5. 若一条 paper reference 能解析到已有 paper 页面，通过 `tools/research_wiki.py add-citation` 写出 bibliographic 记录。

这种做法让 `/check` 下一轮不会报半吊子链接。也让回滚变简单：若某篇论文 ingest 被中止，直接撤销该论文的编辑就能把两侧同时撤销。

## `/ingest` 在此处不做的检查

`/ingest` 边写边写反向链接，但不会审计 wiki 中既有链接是否仍有反向。那是全图审计，属于 `/check`。不要在 ingest 过程中全量读 `wiki/` 去查已有的反向缺失 —— 时间与 token 成本都不小，而且与 `/check` 做重复工作。
