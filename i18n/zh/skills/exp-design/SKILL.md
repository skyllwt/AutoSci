---
description: 基于idea的实验设计（含迭代消融） — 方法候选生成（直接实现/混合融合/跨idea结合） → 基准选择 → 迭代消融（非线性：消融可触发方法简化与重新规划）→ 敏感度分析 → 主实验 → 可选泛化实验 → 中间量深度分析。在预实验评估后为idea设计完整实验套件时使用。
argument-hint: <idea-slug>
---

# /exp-design

> 为idea设计完整、非线性的实验套件。
> 本skill支持方法候选生成、带方法简化的迭代消融、敏感度分析和中间量深度分析。
> 消融循环是非线性的核心：消融结果将各因子分类为必要/贡献/边际/有害，边际/有害因子触发方法简化和重新规划（上限2次迭代）。

## Inputs

- `idea-slug`：要为其设计实验的idea（从 `wiki/ideas/{slug}.md` 读取）

## Outputs

- 实验wiki页面：`wiki/experiments/{exp-slug}.md` — 每个实验块一个页面（ablation、sensitivity、main、generalization、analysis），每个页面 `status: planned`，`linked_idea` 已设置
- 主设计文档：`experiments/designs/{slug}-master.md` — 各实验块的详细spec
- `wiki/graph/edges.jsonl` — 新的 `tested_by` 边：idea → 每个experiment
- `wiki/ideas/{slug}.md` — 更新的 `linked_experiments` 字段
- `wiki/graph/context_brief.md` — 重建
- `wiki/graph/open_questions.md` — 重建
- `wiki/log.md` — 追加日志条目
- **DESIGN_REPORT**（输出到终端） — 实验套件摘要、运行顺序、计算预算

## Wiki Interaction

### Reads
- `wiki/ideas/{slug}.md` — idea的假设、方法、风险、新颖性论点
- `wiki/ideas/*.md` — 其他idea（用于候选C跨idea结合，筛选已验证/通过预实验的idea）
- `experiments/pilot/{slug}/report.md` — 预实验评估结果（若存在）
- `wiki/papers/*.md` — 相关论文的baseline设置和方法细节
- `wiki/concepts/*.md` 和 `wiki/topics/*.md` — 通过idea的 `origin_gaps` 引用
- `wiki/methods/*.md` — idea所基于的可复用方法
- `wiki/experiments/*.md` — 已有实验（避免重复设计）
- `wiki/graph/context_brief.md` — 全局上下文
- `wiki/graph/open_questions.md` — 知识空白

### Writes
- `wiki/experiments/{exp-slug}.md` — 实验wiki页面（每个实验块一个，遵循entity schema）
- `experiments/designs/{slug}-master.md` — 主设计文档，含各块详细spec
- `wiki/ideas/{slug}.md` — 在 `linked_experiments` 中追加experiment slug
- `wiki/graph/edges.jsonl` — 添加 `tested_by` 边（idea → 每个experiment）
- `wiki/graph/context_brief.md` — 重建
- `wiki/graph/open_questions.md` — 重建
- `wiki/log.md` — 追加操作日志

### Graph edges created
- `tested_by`：idea → experiment（该idea正被此实验验证）。反向关系由experiment的 `linked_idea` frontmatter字段捕获，`xref.yaml` 将其反转为idea的 `linked_experiments` 列表。

## Workflow

**前置条件**：确认工作目录为wiki项目根目录（包含 `wiki/`、`raw/`、`tools/` 的目录）。

---

### Phase 1：加载上下文与验证前置条件

1. **读取idea页面**：加载 `wiki/ideas/{slug}.md`，提取 `## Motivation`、`## Hypothesis`、`## Approach sketch`、`## Novelty argument`、`## Risks` 以及frontmatter字段 `origin_gaps`、`tags`、`target_venue`、`priority`、`novelty_score`。

2. **读取预实验结果**（若存在）：加载 `experiments/pilot/{slug}/report.md` 了解预实验结果。若预实验通过，可有信心地推进。若无预实验，谨慎推进并在设计文档中注明。

3. **加载相关wiki上下文**：
   - 读取 `wiki/graph/context_brief.md` 和 `wiki/graph/open_questions.md`
   - 从idea的 `origin_gaps` 读取引用的 `wiki/concepts/*.md` 和 `wiki/topics/*.md`
   - 从 `## Approach sketch` 的wikilinks读取引用的 `wiki/methods/*.md`
   - 读取 `linked_idea` 匹配的已有 `wiki/experiments/*.md`

4. **读取相关论文**：从 `wiki/papers/*.md` 中提取与idea相关的baseline设置和方法细节。

---

### Phase 2：方法候选生成

从idea生成2–3个方法候选。每个候选代表不同的实现策略：

- **候选A — 直接实现**：直接实现 `## Approach sketch` 中提出的方法
- **候选B — 混合/融合**：将idea的方法与已有方法（来自 `wiki/methods/`）结合，平衡性能和成本
- **候选C — 跨idea结合**：将此idea与另一个已验证或通过预实验的已有idea结合（检查 `wiki/ideas/` 中 `pilot_result: passed` 或 `status: validated` 的idea）。测试两个互补idea是否能产生叠加增益。

每个候选需记录：
- 核心机制/算法概述（2–4句话）
- 预期优势和风险
- 实现复杂度：低 / 中 / 高
- 计算成本估算（相对于baseline）

**向用户展示候选以供审查和选择。** 用户选择1–2个候选继续。若用户未选择，用更清晰的对比重新展示。

---

### Phase 3：基准与指标选择

> 选择benchmark，包括数据集、评测指标和基线方法。其中数据集和评测指标要选择领域内该方向公认的标准级别。

1. **确定基准**，基于：
   - idea的领域（NLP、CV、RL等）
   - 相关论文中使用的标准基准（来自 `wiki/papers/`）
   - 数据集可用性和计算约束

2. **选择数据集**：
   - 明确使用的数据集(需考虑任务适配性、规模、数据集规范程度)
   - 明确该数据集的组成结构及使用方法和规范

3. **选择指标**：
   - 主指标：衡量成功的单一最重要指标（如accuracy、F1、reward）
   - 辅助指标：补充指标（如延迟、内存、吞吐量）

4. **定义baselines**：列出所选候选需要比较的所有方法，包括：
   - 最相关论文中复现的baseline
   - 相关工作中的SOTA方法

5. **记录理由**：为什么这些基准和指标适合idea的假设。

---

### Phase 4：实验套件设计（非线性，含迭代）

本阶段设计所有实验块。消融循环（Step 4.6）是非线性的核心。

#### Step 4.1 — 设计消融实验

- 确定**消融因子**：方法中每个可独立开关的组件或假设
- 设计**消融矩阵**：测试哪些组合（通常：完整方法逐一去掉一个因子）
- 定义**收集的指标**：不仅是最终性能 — 还包括中间量（loss分量、梯度范数等），用于诊断每个因子为何重要
- 每个因子后续将被分类为：必要 / 贡献 / 边际 / 有害

#### Step 4.2 — 设计敏感度分析

- 确定**要扫描的超参数**：学习率、方法特有参数（如稀疏度、融合权重）、模型特有参数
- 定义**扫描范围和分辨率**：先粗后细
- 计划**增量执行**：先在子集上运行（更少步数、更小数据集），然后用缩小的范围做完整扫描

#### Step 4.3 — 设计主实验

- 所选方法候选 vs 所有baselines，在完整基准上
- 多seed（>= 3个seed用于方差估计）
- 完整训练预算
- 同时收集最终指标和中间量（用于Step 4.5的深度分析）

#### Step 4.4 — 设计泛化实验（可选）

- 在不同基准、数据集或设置上测试
- 验证方法的假设在主设置之外是否仍然成立
- 仅在idea的假设包含泛化声明时才包含
- 若包含，记录：与主实验有何不同，提供什么新洞察

#### Step 4.5 — 设计深度分析

- 确定**主实验中要记录的中间量**：
  - 梯度范数（逐层、逐组件）
  - 注意力模式或特征分布
  - loss分解（各loss项）
  - 任何能验证或否定方法核心假设的量
- 定义**分析脚本/可视化**，在实验完成后产出
- 这不是关于最终指标 — 而是理解方法*为什么*有效（或无效）
- 指定哪些量必须在实验*开始前*收集（instrumentation要求）

每个实验块应包含：
- `title`：描述性标题
- `linked_idea`：源idea slug（必需，schema要求）
- `hypothesis`：实验测试的具体假设
- `type`：ablation / sensitivity / main / generalization / analysis — 以tag形式记录
- `setup`：模型、数据集、硬件、框架
- `metrics`：评估指标列表
- `baseline`：比较基线
- `success_criterion`：明确的pass/fail标准（写在实验页面的 `## Procedure` 中）
- `estimated_gpu_hours`：预估计算时间
- `seeds`：随机种子数（建议 >= 3）

各块具体要求：

**消融**：
- 目的：隔离方法中每个独立因子的贡献
- 每次消融去掉一个因子，验证性能变化
- N个因子 → N次消融运行（加完整方法作为对照）
- 每次运行收集中间量（不只是最终指标）
- 成功标准：因子分类表（必要 / 贡献 / 边际 / 有害）
- 计算量：约等于主实验 × N个因子

**敏感度分析**：
- 目的：找到方法的最优超参数值
- 确定所有方法特有超参数（学习率、稀疏度、融合权重等）
- 定义扫描范围（先粗）和分辨率（网格或随机搜索）
- 增量执行：先在子集上运行，缩小范围，再完整扫描
- 成功标准：找到最优超参，有清晰的敏感度模式
- 计算量：中等（子集扫描便宜，完整扫描取决于参数数量）

**主实验**：
- 目的：在完整基准上验证idea的核心命题，与所有baselines比较
- 使用敏感度分析得到的最佳超参
- 多seed（>= 3个）保证统计可靠性
- 同时收集最终指标和中间量供深度分析使用
- 成功标准：相比baselines有统计显著的提升
- 计算量：最高（完整训练预算、多个seed、多个baseline）

**泛化实验**（可选）：
- 目的：验证方法在不同条件下是否成立
- 至少测试2个变化维度（不同数据集、模型大小、领域等）
- 使用主实验确定的最终方法和最佳超参
- 成功标准：在新设置上性能保持（无灾难性下降）
- 计算量：取决于变化维度数量

**深度分析**：
- 目的：通过检查中间量理解方法*为什么*有效（或无效）
- 输入：主实验中收集的日志和中间数据
- 产出可视化：梯度范数、注意力模式、loss分解等
- 成功标准：中间量证实（或否定）方法的核心假设
- 计算量：最小（事后分析，无需新的训练运行）

#### Step 4.6 — 迭代消融循环（非线性核心）

这是与线性实验设计的关键区别。初始消融结果后：

```
iteration = 0
while iteration < 2:
    运行消融实验（通过 /exp-run）
    根据结果分类每个消融因子：
      - 必要：   去掉后性能大幅下降（>10%）→ 保留
      - 贡献：   去掉后性能中等下降（3-10%）→ 保留
      - 边际：   去掉后效果可忽略（<3%）→ 候选移除
      - 有害：   去掉后性能提升 → 移除
    若发现任何边际或有害因子：
      简化方法：
        - 移除所有有害因子
        - 与用户讨论是否移除边际因子
      用减少后的因子集重新规划消融
      iteration += 1
    else:
      break  # 方法已清洁，进入主实验
```

- 循环退出后（最多2次迭代）：确定最终方法设计
- 在设计文档中记录完整的迭代历史（每次移除了什么、为什么、各迭代的结果）
- 此循环确定的方法将用于主实验（Step 4.3）

---

### Phase 5：构建运行顺序

按依赖关系排列实验，设置决策门：

```
Stage 0：消融（迭代1）
  └── 运行消融矩阵
  └── 分类因子 → 如需简化 → 重新运行（迭代2，最多2次）
  
Stage 1：敏感度分析（子集）
  └── 在小子集上运行以缩小超参数范围
  └── 门：若未找到合理超参 → 停止，重新考虑方法

Stage 2：主实验
  └── 最终方法 vs baselines，完整基准，多seed
  └── 门：相比baseline无提升 → 停止，通过深度分析诊断

Stage 3：泛化（可选）
  └── 仅在Step 4.4设计了泛化实验时执行
  └── 使用最终方法和最佳超参

Stage 4：深度分析
  └── 分析Stage 2中收集的中间量
  └── 产出诊断报告
```

估算总计算预算。生成含依赖关系的执行清单。

---

### Gate: 用户审查设计的实验模块和运行顺序

**在设计好实验模块，准备创建设计文档以及wiki页面之前，需向用户确认，申请用户手动检查设计的实验模块，确认后进入Phase6，否则需执行修改直到用户确认**

### Phase 6：写入设计文档

1. **创建主设计文档** `experiments/designs/{slug}-master.md`：
   ```markdown
   ---
   title: "实验设计: {idea-title}"
   slug: "{idea-slug}-design"
   status: planned
   linked_idea: "{idea-slug}"
   tags: ["exp-design"]
   date_planned: YYYY-MM-DD
   ---

   ## Idea摘要
   {idea假设和方法概述}

   ## 方法候选
   {候选表格及选择理由}

   ## 基准与指标
   {数据集、指标、baselines}

   ## 实验块

   ### 消融
   {消融因子、矩阵、指标}

   ### 敏感度分析
   {超参数、扫描范围}

   ### 主实验
   {方法 vs baselines，完整配置}

   ### 泛化（可选）
   {不同设置/基准}

   ### 深度分析
   {中间量、分析计划}

   ## 消融迭代历史
   {每次迭代记录：因子分类、简化操作}

   ## 运行顺序与预算
   {阶段依赖关系、预估GPU小时}

   ## 结果
   （/exp-run 后填写）
   ```

2. **创建experiment wiki页面** — 每个实验块一个页面（遵循 `runtime/schema/entities.yaml` 和 `runtime/templates/experiments.md.tmpl`）：
   ```bash
   python3 tools/research_wiki.py slug "<experiment-title>"
   ```
   创建 `wiki/experiments/{slug}.md`，严格遵循 `runtime/schema/entities.yaml::experiments` 和 `runtime/templates/experiments.md.tmpl` — 以下每个frontmatter字段必须存在（即使为空），因为 `/exp-run` 后续使用 `tools/research_wiki.py set-meta` 更新，而 `set-meta` 拒绝创建不存在的字段：
   ```yaml
   ---
   title: ""
   slug: ""
   status: planned
   linked_idea: "{idea-slug}"   # 必需（schema要求）。通过xref.yaml反向链接到 wiki/ideas/{idea-slug}.md::linked_experiments。
   hypothesis: ""
   tags: []                     # 标明类型：["ablation"]、["sensitivity"]、["main"]、["generalization"] 或 ["analysis"]
   setup:
     model: ""
     dataset: ""
     hardware: ""
     framework: ""
   metrics: []
   baseline: ""
   outcome: ""                  # /exp-run Phase 4 前留空 — succeeded | failed | inconclusive
   key_result: ""               # /exp-run Phase 4 前留空
   date_planned: YYYY-MM-DD
   date_completed: ""           # /exp-run Phase 4 前留空
   run_log: ""                  # /exp-run Phase 2 前留空
   started: ""                  # /exp-run Phase 2 前留空（ISO时间戳，通过set-meta设置）
   estimated_hours: 0           # /exp-run Phase 2 前为0（通过set-meta设置）
   remote:                      # 整块必须存在，以便 /exp-run --env remote 通过Edit填充子字段
     server: ""
     gpu: ""
     session: ""
     started: ""
     completed: ""
   ---
   ```

   各块类型的正文section：

   **消融**（`tags: ["ablation"]`）：
   - `## Objective` — 测试哪些因子，消融揭示方法的什么特性
   - `## Setup` — 消融矩阵（因子组合）、模型、数据集、硬件、超参数
   - `## Procedure` — 逐步执行：运行每个因子组合，收集指标和中间量
   - `## Results`（/exp-run 后填写）— 因子分类表：必要 / 贡献 / 边际 / 有害
   - `## Analysis`（/exp-run 后填写）— 哪些因子应移除，迭代历史
   - `## Follow-up` — 若发现边际/有害因子：简化方法并重新消融（迭代2）；若全部必要/贡献：进入主实验

   **敏感度分析**（`tags: ["sensitivity"]`）：
   - `## Objective` — 扫描哪些超参数，最优范围是什么
   - `## Setup` — 扫描范围和分辨率、模型、数据集、硬件
   - `## Procedure` — 逐步执行：先在子集上运行，缩小范围，再完整扫描
   - `## Results`（/exp-run 后填写）— 最佳超参数值、性能曲线
   - `## Analysis`（/exp-run 后填写）— 敏感度模式，推荐用于主实验的值
   - `## Follow-up` — 将最佳超参传递给主实验

   **主实验**（`tags: ["main"]`）：
   - `## Objective` — 此实验证明idea相对于baselines的什么结论
   - `## Setup` — 方法 vs 所有baselines，完整基准，多seed（>=3），敏感度分析的最佳超参
   - `## Procedure` — 逐步执行计划，含明确成功标准；收集中间量供深度分析使用
   - `## Results`（/exp-run 后填写）— 指标对比表（方法 vs baselines），统计显著性
   - `## Analysis`（/exp-run 后填写）— 方法为何有效/失败，中间量分析
   - `## Follow-up` — 应急计划：成功/失败后分别怎么做

   **泛化实验**（`tags: ["generalization"]`，可选）：
   - `## Objective` — 测试什么泛化声明
   - `## Setup` — 与主实验不同的基准/数据集/设置
   - `## Procedure` — 用最终方法和最佳超参在新设置上运行
   - `## Results`（/exp-run 后填写）— 新设置 vs 主设置的性能
   - `## Analysis`（/exp-run 后填写）— 方法是否泛化？
   - `## Follow-up` — 若失败：识别哪个假设不成立

   **深度分析**（`tags: ["analysis"]`）：
   - `## Objective` — 分析哪些中间量，验证什么假设
   - `## Setup` — 数据来源（主实验日志）、可视化规格
   - `## Procedure` — 运行分析脚本，产出图表和诊断表
   - `## Results`（/exp-run 后填写）— 图表、表格、关键观察
   - `## Analysis`（/exp-run 后填写）— 中间量是否证实了方法的假设？
   - `## Follow-up` — 若假设未证实：识别问题所在

3. **添加graph edges**：
   ```bash
   # 每个experiment页面，idea → experiment
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{idea-slug}" --to "experiments/{exp-slug}" \
     --type tested_by --evidence "Designed by /exp-design"
   ```

4. **更新idea页面**：在 `wiki/ideas/{slug}.md` 的 `linked_experiments` 中追加所有experiment slug。

6. **重建派生数据**：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

7. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-design | 为idea {slug}设计了{N}个实验 | linked_idea: {slug}"
   ```

8. **输出DESIGN_REPORT到终端**：
   ```markdown
   # 设计报告: {idea-slug}

   ## 目标Idea
   - Idea: [[idea-slug]]
   - 假设: {hypothesis}

   ## 方法候选
   | # | 候选 | 类型 | 复杂度 | 是否选中 |
   |---|------|------|--------|----------|
   | A | {name} | 直接实现 | {低/中/高} | {是/否} |
   | B | {name} | 混合/融合 | {低/中/高} | {是/否} |
   | C | {name} | 跨idea结合 | {低/中/高} | {是/否} |

   ## 基准
   - 主要: {benchmark} | 指标: {metric}
   - Baselines: {列表}

   ## 实验块
   | # | 实验 | 类型 | GPU小时 | 阶段 |
   |---|------|------|---------|------|
   | 1 | [[slug]] | 敏感度 | {N} | 0 |
   | 2 | [[slug]] | 消融 | {N} | 1 |
   | 3 | [[slug]] | 主实验 | {N} | 2 |
   | 4 | [[slug]] | 泛化 | {N} | 3 |

   ## 消融迭代
   - 计划迭代次数: {N}（最多2次）
   - 因子: {列表及分类}

   ## 运行顺序
   Stage 0: 敏感度 → Stage 1: 消融 → Stage 2: 主实验 → Stage 3: 泛化 → Stage 4: 深度分析

   ## 预算
   - 总预估: {N} GPU小时

   ## 下一步
   - 运行 `/exp-run [[sensitivity-slug]]` 开始Stage 0
   ```

## Constraints

- **每个experiment必须引用一个idea**：`linked_idea` 是schema必需的。若无idea页面，拒绝设计 — 指示用户先运行 `/ideate`。
- **不重复创建experiment**：创建前扫描 `wiki/experiments/*.md` 中已有相同 `linked_idea` + `hypothesis` 的实验。
- **不覆盖已有设计文件**：若 `experiments/designs/{slug}-master.md` 已存在，覆盖前询问用户。
- **方法候选必须有依据**：不凭空编造方法 — 所有候选必须源自idea页面内容。
- **消融循环上限2次**：防止无限循环。2次迭代后用当前设计定稿。
- **敏感度扫描必须增量**：先子集，后完整扫描。
- **深度分析必须预先规划**：在实验*开始前*指定要收集的中间量 — 这是instrumentation，不是事后分析。
- **Graph edges通过tools/research_wiki.py**：不要手动编辑 `edges.jsonl`。
- **至少3个seed**：需要统计可靠性的实验（主实验）必须指定 >= 3个随机seed。
- **成功标准必须量化**：每个实验块需要具体的pass/fail数值。

## Error Handling

- **Idea页面未找到**：报告错误，建议先运行 `/ideate`。
- **无预实验结果**：警告用户，继续但在设计文档中注明信心降低。
- **用户未选择任何方法候选**：用更清晰的对比重新展示，要求明确选择。
- **基准不可用**：建议替代方案，由用户决定。
- **消融循环达到2次迭代**：用当前设计定稿，在报告中注明剩余的边际因子。
- **类似experiment已存在**：列出已有实验，询问用户是添加还是跳过。
- **计算预算不足**：缩减泛化实验范围，在报告中注明实际分配。

## Dependencies

### Skills (via Skill tool)
- `/exp-run` — 执行设计好的实验
- `/exp-pilot-eval` — 前置条件：预实验评估应在正式设计前完成

### Tools (via Bash)
- `python3 tools/research_wiki.py slug "<title>"` — 生成slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — 添加graph edge
- `python3 tools/research_wiki.py set-meta ...` — 更新frontmatter字段
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建上下文
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建知识空白
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### Claude Code Native
- `Read` — 读取wiki页面
- `Write` — 创建设计文档和实验页面
- `Glob` — 查找已有实验
- `AskUserQuestion` — 方法候选选择

### Called by
- `/ideate`（预实验评估后）
- 用户直接调用
