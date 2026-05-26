# /ingest 交叉引用

在任何 wiki 页面上写链接时，打开此参考。每一条正向链接都有反向义务（指向 foundation 的除外）。下表是合同。

## 正向 → 反向义务

对应根 `CLAUDE.md`（"Cross-Reference 规则"）中的矩阵，裁剪到 `/ingest` 实际写入的 edge：

| 正向操作（你在页面 A 上写什么） | 必须同步的反向操作（在同一 turn 里你在页面 B 上写什么） |
|--------------------------------|--------------------------------------------------------|
| `papers/P` 写 `Related: [[concept-K]]` | `concepts/K` 的 `key_papers` 追加 `P` |
| `papers/P` 写 `[[person-R]]`（任意正文章节） | `people/R` 的 `## Recent work` 追加 `[[P]]` |
| `concepts/K` 写 `key_papers: [[paper-P]]` | `papers/P` 的 `## Related` 追加 `K` |
| `methods/M` 写 `source_papers: [[paper-P]]` | `papers/P` 的 `## Related` 追加 `M` |
| `methods/M` 写 `parent_methods: [[method-N]]` | `methods/N` 的 `child_methods` 追加 `M`（反之亦然） |
| 任意页面写 `[[foundation-X]]` | **不写反向链接** —— foundation 是终端节点 |

写了正向却没写反向，是 `/check` 报 `missing-field` 的最常见来源。把两边放在同一 turn 内做，整类错误就被消灭。

## Foundation 是终端节点

`/ingest` 不得修改 foundation 页面。没有 `key_papers` 字段，也没有任何形式的反向引用。一篇论文链到 foundation，只留下两处痕迹：

- 论文页面 `## Related` 中的 `[[foundation-slug]]`
- `wiki/graph/edges.jsonl` 中一条 `paper → foundation`、type 为 `derived_from` 的 edge

foundation 仅由 `/prefill` 创建。`/ingest` 永远不新建 foundation —— 即便某个 concept 候选看起来像是 foundational 却没有匹配。这种情况下，走普通 concept 路径（必要时新建 concept 页面），让用户日后需要时自行 seed foundation。

## paper-to-concept 语义 edge

paper 与 concept 的关系是使用、引入、扩展或批评。每条 paper-to-concept 语义 edge 都必须带 `--confidence high|medium|low`。

edge 类型选择：

- **`introduces_concept`** —— 严格的新颖性：论文明确把该 concept 作为贡献来提出、命名或定义。
- **`uses_concept`** —— 默认选项：论文依赖已有 concept，但没有实质修改它。
- **`extends_concept`** —— 论文修改、泛化、特化或形式化已有 concept。
- **`critiques_concept`** —— 论文指出某个 concept 的限制、失败模式或错误假设。

在 `introduces_concept` 与 `uses_concept` 之间不确定时，选 `uses_concept`。在 `uses_concept` 与 `extends_concept` 之间不确定时，也选 `uses_concept`。不要再写 `paper → concept` 的 `supports` 或普通 `extends`。
该工具会拒绝缺少 confidence/evidence 的新写入，也会拒绝 legacy paper-to-concept edge 类型。

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
4. 若该链接对应一条 semantic graph edge（paper↔concept、paper↔paper、paper→foundation），通过 `tools/research_wiki.py add-edge` 写出。
5. 若一条 paper reference 能解析到已有 paper 页面，通过 `tools/research_wiki.py add-citation` 写出 bibliographic 记录。

这种做法让 `/check` 下一轮不会报半吊子链接。也让回滚变简单：若某篇论文 ingest 被中止，直接撤销该论文的编辑就能把两侧同时撤销。

## `/ingest` 在此处不做的检查

`/ingest` 边写边写反向链接，但不会审计 wiki 中既有链接是否仍有反向。那是全图审计，属于 `/check`。不要在 ingest 过程中全量读 `wiki/` 去查已有的反向缺失 —— 时间与 token 成本都不小，而且与 `/check` 做重复工作。
