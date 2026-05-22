---
description: 端到端研究编排器：idea 发现 → 实验设计 → 执行 → 判决 → 论文撰写，带人工门控和状态恢复
argument-hint: <research-direction-or-brief> [--auto] [--start-from stage1|stage2|stage3|stage3-collect|stage3-check|stage4|stage5] [--skip-paper] [--venue ICLR|NeurIPS|ICML|ACL|CVPR]
---

# /research

> 端到端研究编排器，将所有 skill 组合为完整的研究流程。
> Stage 0 (Bootstrap) + 5 个 Stage + 2 个 Human Gate，覆盖从空 wiki 到论文提交的全流程。
> **零摩擦入口**：wiki 为空时自动触发 Bootstrap（搜索 + auto-ingest 5 篇论文），无需手动 /init。
> 每个 Gate 和 Stage 保存进度到 `wiki/outputs/pipeline-progress.md`，支持跨 session 恢复。
>
> **Stage 3 为非阻塞设计**：实验部署后立即返回（`--auto` 模式自动设置 CronCreate 每 30 分钟监控），
> 实验全部完成后自动进入 Stage 4。可随时用 `/exp-status` 查看进度。
>
> `--auto` 模式跳过人工确认（自动选 top-1 idea），`--skip-paper` 只做研究不写论文。

## Inputs

- `direction`：研究方向描述或 `RESEARCH_BRIEF.md` 文件路径
  - 文本形式：一句话描述研究方向（如 "sparse LoRA for edge devices"）
  - 文件形式：结构化的 RESEARCH_BRIEF.md（含 domain、constraints、target venues）
- `--auto`（可选）：全自动模式，Gate 1 自动选 top-1 idea，Gate 2 自动继续，Stage 3b 自动 CronCreate
- `--start-from <stage>`（可选）：从指定 stage 恢复执行
  - 有效值：`stage1`、`stage2`、`stage3`、`stage3-collect`、`stage3-check`、`stage4`、`stage5`
  - `stage3-collect`：跳过 deploy，直接进入 Stage 3c（收集已部署实验的结果）
  - `stage3-check`：只检查实验状态（等同于 `/exp-status --pipeline {slug}`），不继续执行
  - 需要 `wiki/outputs/pipeline-progress.md` 存在
- `--skip-paper`（可选）：只做研究（Stage 1-4），不写论文（跳过 Stage 5），但仍执行 /exp-eval（Stage 4）
- `--venue`（可选）：目标会议（ICLR / NeurIPS / ICML / ACL / CVPR），传递给 /paper-plan

## Outputs

- **wiki 更新**（通过子 skill 委托）：ideas/、experiments/、methods/、outputs/、graph/
- **wiki/outputs/pipeline-progress.md** — 流水线进度快照（用于恢复）
- **wiki/outputs/PIPELINE_REPORT.md** — 完整流水线报告
- **paper/ 目录**（若未 --skip-paper）— 可提交的论文
- **wiki/log.md** — 每个 stage 追加日志

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — 全局上下文（传递给子 skills）
- `wiki/graph/open_questions.md` — 知识缺口（传递给 /ideate）
- `wiki/ideas/*.md` — Gate 1 选择、Stage 4 判决、Stage 5 论文规划
- `wiki/experiments/*.md` — Stage 3-4 状态检查
- `wiki/methods/*.md` — Stage 5 论文写作上下文
- `wiki/outputs/pipeline-progress.md` — --start-from 恢复状态
- `wiki/papers/*.md` — Stage 5 论文写作上下文

### Writes
- `wiki/outputs/pipeline-progress.md` — 每个 Gate 保存进度（委托写入 wiki 实体的操作由子 skill 完成）
- `wiki/outputs/PIPELINE_REPORT.md` — 最终报告
- `wiki/log.md` — 追加日志
- 其他 wiki 实体写入均通过子 skill 委托（不直接写入 ideas/experiments/methods/）

### Graph edges created
- 无直接创建 — 所有 graph edges 通过子 skill 代理（/ideate、/exp-design、/exp-eval 各自创建 edges）

## Workflow

**前置**：
1. 确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）
2. 若 `--start-from` 指定，读取 `wiki/outputs/pipeline-progress.md` 恢复状态

### Step 0: 初始化

1. **解析输入**：
   - 若为文件路径：读取 RESEARCH_BRIEF.md，提取 direction、domain、constraints、target_venue
   - 若为文本：作为 direction，domain/constraints 留空
   - 生成 slug：`python3 tools/research_wiki.py slug "{direction}"`

2. **自动恢复检测**（无 `--start-from` 时）：
   - 若 `wiki/outputs/pipeline-progress.md` 存在 且 `status == running`：
     - 读取 direction、current_stage、started、slug
     - 使用 AskUserQuestion 提示用户选择：
       ```
       检测到未完成的 pipeline:
       方向: {direction}
       当前阶段: {current_stage}
       开始时间: {started}

       [1] 从 {current_stage} 继续（推荐）
       [2] 开始新的 pipeline（将覆盖旧进度）
       [3] 先查看实验状态（/exp-status --pipeline {slug}）
       ```
     - 若 --auto 或用户选 [1]：自动设 `--start-from {current_stage}`，继续执行
     - 若用户选 [2]：继续创建新 pipeline（覆盖旧进度文件）
     - 若用户选 [3]：调用 `/exp-status --pipeline {slug}` 后退出，不继续执行

3. **检查恢复**（有 `--start-from` 时）：
   - 若 `wiki/outputs/pipeline-progress.md` 存在：
     - 读取进度文件，恢复 idea_slug、experiment_slugs、stage3a_deployed、linked_idea_slugs、monitoring_cron_id
     - 跳转到指定 stage
   - 若进度文件不存在：报错退出，提示先运行完整流水线
   - **`--start-from stage3-check`**：等同于调用 `/exp-status --pipeline {slug}`，展示状态后退出
   - **`--start-from stage3-collect`**：跳过 Stage 3a+3b，直接进入 Stage 3c（收集已部署实验）

3. **创建进度文件** `wiki/outputs/pipeline-progress.md`：
   ```yaml
   ---
   slug: "{pipeline-slug}"
   direction: "{research direction}"
   status: running
   current_stage: stage1
   started: YYYY-MM-DD
   mode: auto|interactive
   skip_paper: true|false
   venue: "{venue}"
   idea_slug: ""
   experiment_slugs: []
   stage3a_deployed: []
   linked_idea_slugs: []
   iteration_count: 0
   ---
   ## Stage Log
   - Stage 0 (Bootstrap): skipped
   - Stage 1: pending
   - Gate 1: pending
   - Stage 2: pending
   - Stage 3a (Deploy): pending
   - Stage 3b (Await): pending
   - Stage 3c (Collect): pending
   - Stage 4: pending
   - Gate 2: pending
   - Stage 5: pending
   ```

4. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | started | direction: {direction} | mode: {auto|interactive}"
   ```

5. **Snapshot wiki 状态**（用于 Step Final 的 Growth Report）：
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   保存返回的 JSON 到内存变量 `maturity_before`。

### Stage 0: Bootstrap（wiki 为空时自动触发）

**触发条件**：运行 `python3 tools/research_wiki.py maturity wiki/ --json`，若 `level == "cold"` 且 `papers < 3`：自动进入 Bootstrap。否则跳过，直接进入 Stage 1。

1. **初始化 wiki 结构**（若未初始化）：
   ```bash
   python3 tools/research_wiki.py init wiki/
   ```

2. **搜索相关论文**（使用 Agent tool 并行 3 路搜索）：
   - DeepXiv：`python3 tools/fetch_deepxiv.py search "{direction}" --mode hybrid --limit 20`
   - Semantic Scholar：`python3 tools/fetch_s2.py search "{direction}" --limit 20`
   - arXiv：`python3 tools/fetch_arxiv.py`（使用 direction 关键词）
   - 若 DeepXiv 不可用：跳过，仅使用 S2 + arXiv

3. **合并排名 & 选取 top 5**：
   - 按 arxiv_id 去重
   - 排序优先级：DeepXiv relevance score > S2 citation count > recency
   - 取 top 5 篇（5 = cold→warm 最低门槛）

4. **逐一 auto-ingest**：
   ```
   Skill: ingest
   Args: "{arxiv_url_or_path}"
   ```
   每篇 ingest 后输出进度：`[{i}/5] Ingested: {paper_title}`

5. **重建派生数据**：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

6. **Bootstrap 报告**：
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   输出到终端：
   ```
   Bootstrap 完成：
   Papers: {N} | Concepts: {K} | Methods: {Mt} | Edges: {E}
   Maturity: cold → {new_level}
   继续进入 Stage 1: Idea Discovery...
   ```

7. **日志 + 进度更新**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | stage0-bootstrap | auto-ingested {N} papers | maturity: {level}"
   python3 tools/research_wiki.py set-meta \
     wiki/outputs/pipeline-progress.md current_stage stage1
   ```

### Stage 1: Idea Discovery

调用 `/ideate`：

```
Skill: ideate
Args: "{direction}" --auto
```

**完成后**：
1. 读取生成的 ideas，按 pilot预实验结果和priority 排序
2. 更新 pipeline-progress：Stage 1 → completed，记录生成的 idea slugs
3. 追加日志

### Gate 1: 选择 Idea

**若 `--auto` 模式**：
- 自动选择 priority 最高（排名 top-1）的 idea
- 在终端输出选择结果，不等待确认

**若交互模式**：
- 列出所有生成的 ideas（slug、title、priority、novelty score\pilot result）
- 使用 AskUserQuestion 提示用户选择一个 idea（或输入 stop 停止）
- 若用户选择 stop：保存进度，终止流水线

**保存进度**：
- 更新 pipeline-progress：Gate 1 → passed，记录 idea_slug
- 更新选中 idea 的 status: proposed → in_progress

### Stage 2: Experiment Design

调用 `/exp-design`：

```
Skill: exp-design
Args: "{idea_slug}"
```

**完成后**：
1. 读取生成的 experiment slugs（从 wiki/experiments/ 中 linked_idea == idea_slug 的页面,以及根据exp-slug在experiments/designs/{slug}-master.md获取实验块详细spec）
2. 更新 pipeline-progress：Stage 2 → completed，记录 experiment_slugs

### Stage 3: Experiment Execution（非阻塞）

Stage 3 分为三个子阶段，允许实验在后台异步运行，不阻塞 session。

#### Stage 3a: Deploy All

按 run order（design中"ablation""sensitivity""main""generalization""analysis"）依次调用 `/exp-run {experiment_slug}`（默认 deploy 模式，Phase 1+2）：

```
Skill: exp-run
Args: "{experiment_slug}"
```

（**默认 deploy 模式**，Phase 1+2，部署后立即返回，不等待实验完成）

**每次部署后**：
- 记录部署结果（成功/失败）到内存
- 若 deploy 失败：记录到 pipeline-progress 中，在报告中标注警告（基线 deploy 失败时加强警告），但**继续部署其余实验**（不中止）

**全部部署完成后**，更新 pipeline-progress.md：
```bash
python3 tools/research_wiki.py set-meta \
  wiki/outputs/pipeline-progress.md current_stage stage3-await
python3 tools/research_wiki.py set-meta \
  wiki/outputs/pipeline-progress.md stage3a_deployed \
  "[{experiment_slug_1}, {experiment_slug_2}, ...]"
```
追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "research | stage3a | deployed {N} experiments | pipeline: {slug}"
```

#### Stage 3b: Await（非阻塞）

实验部署完毕后，计算 ETA、保存进度并结束当前 session。

1. 更新 pipeline-progress：
   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/outputs/pipeline-progress.md current_stage stage3-await
   ```
2. **计算各实验预计完成时间**：
   对每个已部署实验，读取 frontmatter 的 `started` 和 `estimated_hours` 字段：
   - `eta = started + estimated_hours`
   - `recommended_return = max(所有 eta) + 30 分钟缓冲，向上取整到最近整点或半点`
3. 追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | stage3b | awaiting {N} experiments | latest eta: {YYYY-MM-DD HH:MM} | pipeline: {slug}"
   ```
4. 输出操作指引后**结束当前 session**：
   ```
   ✅ Stage 3a 完成：{N} 个实验已全部部署：

   实验                          环境            预计时长   预计完成
   ────────────────────────────  ────────────    ────────   ──────────────
   exp-foo-baseline              local           ~8h        明天 09:30
   exp-foo-validation            remote (gpu1)   ~6h        今天 23:00
   exp-foo-ablation              local           ~4h        今天 21:00

   ⏳ 最晚完成：明天 09:30（exp-foo-baseline）
   建议 明天 10:00 之后运行：

     /exp-status                              ← 确认所有实验完成
     /research --start-from stage3-collect    ← 收集结果并继续

   进度已保存至 wiki/outputs/pipeline-progress.md，当前 session 可以关闭。
   ```

#### Stage 3c: Collect（实验完成后触发）

**触发条件**：用户手动运行 `/research --start-from stage3-collect`

对每个已部署的 experiment（从 `stage3a_deployed` 列表读取）：
```
Skill: exp-run
Args: "{experiment_slug} --collect"
```

（collect 模式，Phase 3+4：检查完成状态并收集结果）

**每次 collect 后的决策**：
- 若 outcome == failed 且为 baseline experiment → **终止流水线**，报告基线无法复现
- 若 outcome == failed 且为 validation experiment → 记录失败，继续收集其余实验，进入 Stage 4 评估
- 若 outcome == inconclusive → 记录，继续

**全部 collect 完成后**：
- 更新 pipeline-progress：Stage 3 → completed
  ```bash
  python3 tools/research_wiki.py set-meta \
    wiki/outputs/pipeline-progress.md current_stage stage4
  ```
- 追加日志：
  ```bash
  python3 tools/research_wiki.py log wiki/ \
    "research | stage3c | collected {N} experiments | pipeline: {slug}"
  ```

- 更新linked idea 的 status: in_progress-> tested

- 继续进入 Stage 4

### Stage 4: Verdict & Iteration

对每个 completed experiment 调用 `/exp-eval`：

```
Skill: exp-eval
Args: "{experiment_slug}" --auto
```

**评估关联 idea 是否充分**：
1. 读取主要 linked idea（及任何辅助 idea）的最新状态
2. 判断是否需要迭代：
   - **充分**（主要 linked idea 已切换为 `validated`，或 ≥1 个支持性实验 `outcome=succeeded`）→ 进入 Gate 2
   - **不足**（idea 仍为 `proposed`或`in_progress`或`tested` 且所有关联实验都是 `failed`/`inconclusive`，或 idea 为 `failed`）→ 进入迭代

**迭代路径**（不足时，最多 1 次重试）：
1. 分析失败原因
2. 对相应的需要改进的实验块调用 `/refine` 改进 experiment plan：
   ```
   Skill: refine
   Args: "{experiment_plan_slug}" --max-rounds 2 --focus evidence
   ```
3. 对新增/修改的 experiments 重新执行 Stage 3 → Stage 4
4. 最多迭代 2 轮（防止无限循环），每个 stage 最多 1 次 auto retry

**完成后**：
- 更新 pipeline-progress：Stage 4 → completed，记录 linked_idea_slugs

### Gate 2: 确认 Paper Ready

**若 `--skip-paper`**：跳过 Gate 2 和 Stage 5，直接生成最终报告

**若 `--auto` 模式**：自动继续，进入 Stage 5

**若交互模式**：
- 展示 idea 状态摘要：
  ```
  Idea: {slug} | Status: {status} | Novelty: {novelty_score}
  Linked experiments: {count} ({succeeded}/{inconclusive}/{failed})
  ```
- 使用 AskUserQuestion 提示用户确认：ready for paper / need more experiments / stop here
- 若 "need more experiments"：返回 Stage 2 重新规划
- 若 "stop here"：保存进度，生成最终报告（不含论文）

**保存进度**：
- 更新 pipeline-progress：Gate 2 → passed

### Stage 5: Paper Writing

依次调用子 skills：/paper-plan → /paper-draft → /refine → /paper-compile

**5a. 调用 /paper-plan**：
```
Skill: paper-plan
Args: "{linked_idea_slugs}" --venue {venue}
```
（将 Stage 4 收集到的 validated idea slug(s) 传递给 /paper-plan）

**5b. 调用 /paper-draft**：
```
Skill: paper-draft
Args: "wiki/outputs/PAPER_PLAN.md" --review
```

**5c. 调用 /refine on Paper**：
```
Skill: refine
Args: "paper/main.tex" --max-rounds 3 --target-score 8 --focus writing
```

**5d. 调用 /paper-compile**：
```
Skill: paper-compile
Args: "paper/"
```

**完成后**：
- 更新 pipeline-progress：Stage 5 → completed, status: completed

### Step Final: Pipeline Report

生成 `wiki/outputs/PIPELINE_REPORT.md`：

```markdown
# Research Pipeline Report

## Stage Summary
| Stage | Status | Duration |
|-------|--------|----------|
| Stage 0: Bootstrap | completed/skipped | ... |
| Stage 1: Idea Discovery | completed | ... |
| Gate 1: Idea Selection | passed | ... |
| Stage 2: Experiment Design | completed | ... |
| Stage 3a: Deploy Experiments | completed | ... |
| Stage 3b: Await (async) | completed | ... |
| Stage 3c: Collect Results | completed | ... |
| Stage 4: Verdict | completed | ... |
| Gate 2: Paper Ready | passed | ... |
| Stage 5: Paper Writing | completed | ... |

## Selected Idea
- **Idea**: [[{idea_slug}]] — {idea title}
- **Priority**: {N}
- **Novelty score**: {score}

## Idea Trail
| Idea | Initial Status | Final Status | Novelty (start → end) |
|------|----------------|--------------|------------------------|
| [[{slug}]] | proposed | validated | 3 → 4 |

## Experiment Results
| Experiment | Outcome | Key Result |
|-----------|---------|------------|
| [[{slug}]] | succeeded | {result} |

## Iteration History
- Total iterations: {N}
- Reason for iteration: {idea evidence insufficient / ...}

## Deliverables
- Ideas: +{N} created, {N} validated
- Experiments: +{N} created, {N} completed
- Methods: +{N} created/updated
- Graph edges: +{N}
- Paper: paper/main.pdf (if applicable)

## Wiki Growth (pipeline total)
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Papers | {N} | {N} | +{N} |
| Methods | {N} | {N} | +{N} |
| Ideas | {N} | {N} | +{N} |
| Experiments | {N} | {N} | +{N} |
| Edges | {N} | {N} | +{N} |
| Maturity | {level} | {level} | {status} |
| Coverage | {%} | {%} | +{%} |
（数据来自 Step 0 step 5 的 `maturity_before` 与此处重新调用 `maturity --json` 的对比。仅展示 delta != 0 的行。）

## Next Steps
- {recommendations based on remaining gaps or unresolved issues}
```

追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "research | completed | idea: {slug} | linked ideas: {N} updated | paper: {yes/no}"
```

更新 pipeline-progress：status: completed

## Constraints

- **编排器不直接修改 wiki 实体，不嵌入子 skill 逻辑**：所有 wiki 修改通过子 skill 委托完成，pipeline 只负责协调，通过 Skill tool 调用
- **Gate 和 Stage 必须保存进度**：每个 Gate 和 Stage 完成/进入等待时必须保存 pipeline-progress.md
- **Stage 3a 部署失败不中止**：deploy 失败时记录警告继续部署，不提前终止（baseline collect 失败时才终止）
- **baseline collect 失败终止**：Stage 3c collect 结果，baseline outcome == failed 时终止流水线
- **Stage 3b 结束 session**：Stage 3b 完成后当前 session 结束，不继续等待实验
- **最多 2 轮迭代**：Stage 4 迭代最多 2 轮，防止无限循环
- **--auto 不跳过计算**：auto 模式跳过人工确认，但不跳过任何计算步骤
- **--skip-paper 仍执行 Stage 4 /exp-eval**：即使不写论文，也要完成 idea/experiment 更新
- **子 skill 参数透传**：将 domain、--venue 等参数正确传递给子 skill
- **日志记录每个 Stage**：每个 Stage 完成后追加 log.md 审计日志
- **不重复执行已完成 stage**：--start-from 跳过已完成的 stages
- **进度文件在 wiki/outputs/pipeline-progress.md**：统一位置，便于发现和恢复
- **自动恢复优先**：无 --start-from 且有未完成 pipeline 时，默认提示用户恢复而不是重新开始

## Error Handling

- **pipeline-progress 不存在但指定 --start-from**：报错，提示先运行完整流水线
- **pipeline-progress 损坏或格式异常**：尝试从 wiki 当前状态推断进度（读取 ideas/experiments 状态），恢复到最近的 Gate
- **子 skill 调用失败**：记录错误到 pipeline-progress，报告失败的 stage，建议 --start-from 恢复
- **所有 ideas 生成失败**：终止流水线，建议用户调整 research direction
- **所有实验 deploy 失败**：终止流水线（Stage 3a），生成失败报告，建议检查 GPU/SSH 配置
- **Stage 3c baseline collect 失败**：终止流水线，报告基线无法复现，建议重新 /exp-design
- **所有实验 collect 失败（其他非 baseline）**：进入 Stage 4 评估（以失败为证据）
- **Gate 用户选择 stop**：保存进度到 pipeline-progress，生成部分报告
- **RESEARCH_BRIEF.md 格式错误**：降级为纯文本 direction，忽略结构化字段
- **wiki 为空（无 papers/concepts）**：自动触发 Stage 0 Bootstrap（搜索 + auto-ingest 5 篇论文）
- **迭代后 idea 证据仍不足**：在报告中标注 "idea evidence insufficient after max iterations"，由用户决定是否继续
- **用户选择查看状态（自动恢复检测 [3]）**：调用 `/exp-status --pipeline {slug}` 后退出，不继续执行新流水线

## Dependencies

### Skills（via Skill tool）
- `/ingest` — Stage 0 Bootstrap auto-ingest
- `/ideate` — Stage 1 idea 发现
- `/exp-design` — Stage 2 实验设计
- `/exp-run` — Stage 3a（deploy 模式）和 Stage 3c（--collect 模式）
- `/exp-status` — 用户手动查看实验进度，`--auto-advance` 可在所有完成时自动触发 Stage 4
- `/exp-eval` — Stage 4 判决
- `/refine` — Stage 4 迭代 + Stage 5 论文改进
- `/paper-plan` — Stage 5 论文规划
- `/paper-draft` — Stage 5 论文撰写
- `/paper-compile` — Stage 5 论文编译

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "{title}"` — 生成 pipeline slug
- `python3 tools/research_wiki.py set-meta <path> <field> <value>` — 更新 pipeline-progress 字段
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/research_wiki.py maturity wiki/ --json` — 检查 wiki 成熟度（Stage 0 触发条件 + Growth Report）
- `python3 tools/research_wiki.py init wiki/` — 初始化 wiki 结构（Stage 0）
- `python3 tools/fetch_deepxiv.py search "{query}" --mode hybrid --limit 20` — DeepXiv 语义搜索（Stage 0）
- `python3 tools/fetch_s2.py search "{query}" --limit 20` — Semantic Scholar 搜索（Stage 0）
- `python3 tools/fetch_arxiv.py` — arXiv RSS 搜索（Stage 0）

### MCP Servers
- 无直接 MCP 调用 — 所有 Review LLM 交互通过子 skill 间接使用

### Claude Code Native
- `Read` — 读取 pipeline-progress、wiki 页面、RESEARCH_BRIEF
- `Write` — 写入 pipeline-progress、PIPELINE_REPORT
- `Glob` — 查找 experiments、ideas、methods
- `Skill` — 调用子 skills（核心能力）
- `AskUserQuestion` — Gate 和自动恢复检测的用户交互
