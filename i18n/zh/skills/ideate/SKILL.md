---
description: 多阶段研究 idea 生成管道：景观扫描 → 双模型脑暴 → 筛选与验证 → 写入 wiki → 预实验
argument-hint: "[research-direction-or-topic] [--max-ideas N] [--skip-validation] [--skip-pilot] [--auto]"
---

# /ideate

> 基于 wiki 知识库和外部搜索，通过 5 阶段管道生成高质量研究 idea。
> Phase 1 扫描研究景观（wiki + WebSearch + S2），Phase 2 双模型脑暴（Claude + Review LLM 独立生成），
> Phase 3 初步筛选 + 深度验证（可行性、novelty、review），Phase 4 将 ideas 写入 wiki（包括被淘汰的 ideas，记录原因作为 anti-repetition 记忆），
> Phase 5 对幸存 ideas 进行预实验（idea 页面已存在）并更新结果。

## Inputs

- `direction`（可选）：研究方向、关键词或具体问题描述。若不指定，则从 open_questions.md 自动选择最有价值的方向。
- `--max-ideas N`（可选，默认 3）：最终写入 wiki 的 idea 数量上限
- `--skip-validation`：跳过 Phase 3 步骤 2 深度验证（跳过 /novelty 和 /review，快速模式仅做初步筛选）
- `--skip-pilot`：跳过 Phase 5 预实验（快速模式，仅做 Phase 1-4）
- `--auto`：全自动模式，不暂停等待用户确认（用于 /research 调用）

## Outputs

- `wiki/ideas/{slug}.md` — 每个 idea 一个页面（status: proposed），包含 top ideas 和被淘汰的 ideas
- `wiki/graph/edges.jsonl` — 新增 idea → concept/topic 的关系边
- `wiki/graph/context_brief.md` — 重建后的压缩上下文
- `wiki/graph/open_questions.md` — 重建后的知识缺口图
- **IDEA_REPORT**（输出到终端）— 管道执行摘要、排名结果、novelty 评分

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — 全局上下文
- `wiki/graph/open_questions.md` — 知识缺口，驱动 idea 方向
- `wiki/ideas/*.md` — 已有 ideas，特别是 status=failed 的 ideas 及 failure_reason（banlist）
- `wiki/papers/*.md` — 已有论文方法和结果
- `wiki/concepts/*.md` — 技术概念，寻找跨领域组合机会
- `wiki/methods/*.md` — 可复用 method，圈定候选灵感来源
- `wiki/topics/*.md` — 研究方向地图，SOTA 和 open problems（含 `### Known gaps` 与 `### Methodological gaps`）
- `wiki/experiments/*.md` — 已有实验结果，避免重复

### Writes
- `wiki/ideas/{slug}.md` — 创建新 idea 页面
- `wiki/graph/edges.jsonl` — 添加 idea → concept/topic 的关系边（addresses_gap, inspired_by）
- `wiki/graph/context_brief.md` — 重建
- `wiki/graph/open_questions.md` — 重建
- `wiki/log.md` — 追加操作日志

### Graph edges created
- `addresses_gap`：idea → concept/topic（idea 针对的知识缺口 — `origin_gaps` 字段）
- `inspired_by`：idea → paper/method/concept（idea 的灵感来源）

## Workflow

**前置**：
1. 确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）
2. **检查 wiki 成熟度**：
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   根据 maturity level 调整后续行为：
   - **cold**：Phase 1 外部搜索扩展（WebSearch 查询从 5 增至 8，S2/DeepXiv limit 从 20 增至 30），
     跳过 wiki 内部上下文加载（为空无意义），标注 "cold-start mode: heavier external search"
   - **warm**：标准行为（当前默认）
   - **hot**：Phase 1 外部搜索缩减（WebSearch 查询从 5 降至 2，S2/DeepXiv limit 从 20 降至 10），
     Phase 3 gap_alignment_bonus 从 +2 提升到 +3，优先解决 topic / concept open-problem 章节中已经枚举的 gap
3. **Snapshot wiki 状态**（用于结束时的 Growth Report）：
   保存 maturity 返回的 JSON 到内存变量 `maturity_before`

### Phase 1: 景观扫描（Landscape Scan）

目标：构建目标领域的全面视角，包括已有工作、知识缺口和最新进展。

1. **加载 wiki 内部上下文**：
   - 读取 `wiki/graph/context_brief.md`（全局压缩上下文）
   - 读取 `wiki/graph/open_questions.md`（知识缺口列表）
   - 读取所有 `wiki/ideas/*.md`，提取：
     - status=failed 的 ideas → **banlist**（含 failure_reason）
     - status=proposed/in_progress 的 ideas → **active list**（避免重复）
   - 读取 `wiki/topics/*.md` 与 `wiki/concepts/*.md`：收集 `## Open problems` 下（包括 `### Known gaps` 与 `### Methodological gaps`）的 bullet → **gap candidates list**
   - 若 `direction` 指定，过滤与方向相关的子集

2. **外部搜索**（使用 Agent tool 并行）：
   - **WebSearch**：搜索目标方向最近 6 个月的论文和进展（3-5 个查询）
   - **Semantic Scholar**：
     ```bash
     python3 tools/fetch_s2.py search "<direction-keywords>" --limit 20
     ```
     对 top 5 高引论文获取详情
   - **DeepXiv 语义搜索**：
     ```bash
     python3 tools/fetch_deepxiv.py search "<direction-keywords>" --mode hybrid --limit 20
     ```
     对 top 5 高相关结果获取 TLDR 和关键词：
     ```bash
     python3 tools/fetch_deepxiv.py brief <arxiv_id>
     ```
     语义搜索补充 S2 关键词搜索可能遗漏的概念相关论文。
   - **DeepXiv 热门论文**：
     ```bash
     python3 tools/fetch_deepxiv.py trending --days 14
     ```
     热门论文指示社区关注热点，有助于发现趋势性 gap。
   - **arXiv 最新**：`site:arxiv.org <direction> 2025 2026`
   - **若 DeepXiv 不可用**：跳过 DeepXiv 搜索和 trending，仅依赖 S2 + WebSearch（回退到原有行为）。

3. **汇总景观报告**（内部使用，不写入 wiki）：
   - 当前 SOTA 方法及性能
   - 已知的 open problems / 未解决的 challenges
   - 最近的趋势和热点
   - wiki 中的知识缺口（from gap_map）
   - 被禁止的方向（from banlist）

### Phase 2: 双模型脑暴（Dual-Model Brainstorm）

目标：通过 Claude 和 Review LLM 独立生成 ideas，利用不同模型的视角差异获得多样性。

**遵循 `shared-references/cross-model-review.md`**：Claude 和 Review LLM 独立生成，不互相看到对方的结果。

1. **Claude 生成 6-10 个 ideas**：
   - 输入：景观报告 + wiki gaps + active list + banlist
   - **结构化生成路径** — 每个 idea 必须遵循以下四条路径之一：

     | 路径 | 名称 | 读取的 wiki 字段 | 产出形态 |
     |------|------|------------------|----------|
     | A | 景观驱动 (Landscape-driven) | `direction` + Phase 1 景观报告（不依赖已有方法） | "基于 topic/research 描述直接设计" |
     | B | 增量改进 (Incremental) | `wiki/methods/*.md` 中的 `method.limitations` | "在方法 M 上修复局限 L" |
     | C | 有机融合 (Combination) | 同 topic 下两个 method 的 `tradeoff_profile`（`wiki/methods/*.md`） | "组合 M1 + M2 的优势" |
     | D | 共性盲点 (Innovation) | 同 topic 下 N 个 method 的 `assumptions` 交集（`wiki/methods/*.md`） | "打破共有假设 P" |
     | E | 跨域迁移 (Cross-domain transfer) | 跨 topic 的 method 的 `mechanism` 相似度（`wiki/methods/*.md`） | "把机制 M 从领域 X 迁移到 Y" |

     对每条路径，先提取相关 wiki 字段，再生成 idea。每个 idea 必须声明来自哪条路径（A/B/C/D/E）。

   - 补充策略（在路径 A–E 之上叠加）：
     - 填补 gap_map 与 topic / concept open-problem 章节中的空白
     - SOTA 的已知 limitation → 改进方向
   - 每个 idea 包含：title、hypothesis（1-2 句）、approach sketch（3-5 句）、`origin_gaps`（idea 针对的 concept / topic slug）、estimated feasibility（高/中/低）、generation_path（A/B/C/D/E）

2. **Review LLM 独立生成 4-6 个 ideas**（并行执行）：
   ```
   mcp__llm-review__chat:
     system: "You are a creative ML researcher brainstorming research ideas.
              Generate novel, concrete, and feasible ideas based on the given context.
              Each idea MUST follow one of the five structured generation paths below.
              For each idea, provide: title, hypothesis (1-2 sentences),
              approach sketch (3-5 sentences), feasibility assessment,
              and generation_path (A/B/C/D/E)."
     message: |
       ## Structured Generation Paths

       Each idea must follow exactly one of these paths:

       | Path | Name | Wiki input | Output form |
       |------|------|------------|-------------|
       | A | Landscape-driven | direction + landscape report (no dependency on existing methods) | "Design directly from topic/research description" |
       | B | Incremental | method.limitations | "Fix limitation L in method M" |
       | C | Combination | tradeoff_profile of two methods under same topic | "Combine strengths of M1 + M2" |
       | D | Innovation | Intersection of assumptions across N methods under same topic | "Break shared assumption P" |
       | E | Cross-domain transfer | mechanism similarity across different topics | "Transfer mechanism M from domain X to Y" |

       ## Research Landscape
       {landscape report from Phase 1 — gaps, SOTA, trends}

       ## Methods (for paths B–E)
       {wiki/methods/*.md — limitations, tradeoff_profile, assumptions, mechanism fields}

       ## Knowledge Gaps
       {gap_map entries}

       ## Banlist (DO NOT revisit these)
       {failed ideas with failure_reason}

       ## Active Ideas (avoid duplicating)
       {proposed/in_progress ideas}

       Generate 4-6 novel research ideas that address the gaps above.
       Focus on ideas that are: (1) genuinely novel, (2) feasible within 3-6 months,
       (3) directly address a knowledge gap.
       Each idea MUST declare its generation_path (A/B/C/D/E).
   ```

3. **合并与去重**：
   - 将 Claude 和 Review LLM 的 ideas 合并（10-16 个候选）
   - 去除高度相似的 ideas（方法核心相同的合并，保留更具体的版本）
   - 去除与 banlist 重叠的 ideas
   - 去除与 active list 高度重复的 ideas
   - 输出：8-12 个候选 ideas

### Phase 3: 筛选与验证（Filter & Validation）

目标：淘汰不可行或不够新颖的 ideas，然后深度验证幸存者。

**步骤 1 — 初步筛选**（对所有 8-12 个候选 idea 执行）：

1. **可行性检查**：
   - GPU/计算需求是否在合理范围内（参考 wiki 中已有 experiments 的 setup）
   - 数据可获取性（公开数据集 vs 私有数据）
   - 实现复杂度（能否在 3-6 个月内完成）
   - 标记为 feasibility: 高/中/低

2. **快速 novelty 筛查**（每个 idea 2-3 个 WebSearch）：
   - `"<idea-core-method>" + "<task>"` 精确搜索
   - `<component-1> + <component-2>` 组件组合搜索
   - 若找到高度相似的已发表工作 → 淘汰或标记

3. **wiki 对齐检查**：
   - idea 是否解决 gap_map 中的已知缺口？（+分）
   - idea 是否针对某个 concept 的 `## Open problems` 或某个 topic 的 methodological gap？（+分）
   - idea 是否基于 wiki 已有知识（papers / methods / concepts）构建？（+分）

4. **筛选决策**：
   - 淘汰条件：feasibility=低 AND novelty 筛查发现相似已发表工作
   - 淘汰条件：与 banlist 的 failure_reason 高度相关
   - 保留：feasibility >= 中 AND 未被淘汰
   - 输出：4-6 个幸存 ideas

**步骤 2 — 深度验证**（对幸存 ideas 执行；若 `--skip-validation` 则跳过）：

（跳过时：直接进入 Phase 4: 写入 Wiki，所有幸存 ideas 默认 priority = 3）

1. **调用 /novelty `--write`**（逐个执行）：
   ```
   对每个幸存 idea：
   Skill: novelty
   Args: "<idea-slug>" --write
   ```
   `--write` 标志会把得到的 `novelty_score`（1-5）写入 idea frontmatter。记录该分数用于 IDEA_REPORT。

2. **调用 /review**（对 top ideas）：
   ```
   Skill: review
   Args: "<idea-full-description>" --difficulty hard --focus method
   ```
   记录 review score（1-10）和 weaknesses

3. **综合排名**：
   - 最终得分 = novelty_score × 2 + review_score + gap_alignment_bonus
   - gap_alignment_bonus：+2 若 idea 直接针对 gap_map 条目
   - 若 novelty_score <= 2 → 降级为「modify needed」
   - 若 review_score <= 4 → 降级为「major issues」

4. **验证后筛选**：
   - 淘汰 novelty_score <= 2 且 review_score <= 4 的 ideas
   - 输出：排名后的幸存者（通过初步筛选和深度验证）

5. **若 `--auto` 未设置**：在终端展示排名结果，等待用户确认或调整

### Phase 4: 写入 Wiki

将验证后的 ideas 写入 wiki（包括被淘汰的 ideas，记录淘汰原因）。

1. **写入 top ideas**（status: proposed）：
   对排名前 `--max-ideas` 个 ideas：
   ```bash
   # 生成 slug
   python3 tools/research_wiki.py slug "<idea-title>"
   ```
   创建 `wiki/ideas/{slug}.md`，**严格遵循 schema** — frontmatter 对齐 `runtime/schema/entities.yaml::ideas`，正文对齐 `runtime/templates/ideas.md.tmpl`：
   ```yaml
   ---
   title: "<idea 标题>"
   slug: "<idea-slug>"
   status: proposed
   origin: "ideate: <驱动该 idea 的 gap / open problem / 论文的简短描述>"
   origin_gaps: []           # [[concept-slug]] 或 [[topic-slug]] 列表 — 该 idea 针对的 concept / topic
   tags: []                  # 2-5 个主题标签（从 origin_gaps / direction 继承）
   target_venue: ""          # NeurIPS / ICLR / ICML / ACL / COLM — 未定时留空
   novelty_score: ""         # 1-5 — Phase 3 中 深度验证 由 /novelty --write 写入；否则留空
   priority: 3               # 1-5 — 见下方 Priority 计算
   pilot_result: ""          # 留空；预实验在 Phase 5 运行，结果由 /exp-pilot-eval 填入。
   linked_experiments: []    # 留空，由 /exp-design 创建 experiment 后填写
   date_proposed: YYYY-MM-DD
   date_resolved: ""         # 留空，validated/failed 时填写
   ---
   ```

   **Priority 计算**（把 Phase 3 验证信号映射到 1-5 分）：
   - 若 `--skip-validation`：默认 `priority = 3`（跳过 novelty/review 评分）
   - 否则从 `novelty_score`（/novelty 给出的 1-5）开始
   - `+1` 若 `gap_alignment_bonus > 0`（直接命中 gap_map 条目）
   - `-1` 若 `review_score <= 4`（major issues 降权）
   - Clamp 到 `[1, 5]`

   **正文结构**（必须与 `runtime/templates/ideas.md.tmpl` 严格一致 — 不要改名）：
   ```markdown
   ## Motivation
   哪个 gap / open problem / 论文限制驱动了这个 idea。用 `[[slug]]` 引用 wiki 页面。

   ## Hypothesis
   1-2 句话陈述可验证的命题。

   ## Approach sketch
   3-5 句描述提出的方法。任何借用现有工作的组件用 `[[paper-slug]]`、`[[method-slug]]` 或 `[[concept-slug]]` 标注。

   ## Novelty argument
   为何该 idea 真正新颖 —— /novelty 找到的最相近 prior work 是哪一项，差异维度在哪里。一段简短文字。

   ## Target venue
   计划投稿目标（如 NeurIPS 2026 / ICLR / ICML / ACL / COLM）。仍在打磨范围的 idea 可留空。

   ## Risks
   可行性评级（high/medium/low）+ top 2-3 风险。包含 /review 揭示的主要弱点。

   ## Pilot results
   （留空 — 由 /exp-pilot-run和/exp-pilot-eval 后填写）

   ## Lessons learned
   （留空 — 由 /exp-eval 在 idea 达到终态后填写）
   ```

2. **写入被淘汰的 ideas**（status: failed）：
   对 Phase 3 中被淘汰的 ideas，也用**上方同一模板**创建 `wiki/ideas/{slug}.md`，应用以下覆盖：
   - `status: failed`
   - `priority: 1`（被淘汰的 ideas 永远不会阻塞更高优先级的工作）
   - `date_resolved: YYYY-MM-DD`（今天）
   - `failure_reason: "[filter] <具体淘汰原因>"` — `[filter]` 前缀区分 Phase 3 筛选淘汰与 /exp-eval 的实验后失败。预实验失败（Phase 5）由 `/exp-pilot-eval` 直接写入已有的 idea 页面。
   - `## Motivation` 和 `## Hypothesis` 仍需填写（供未来 banlist 匹配）；`## Approach sketch` 可简略；`## Expected outcome` 和 `## Risks` 可说明淘汰原因
   - 这些 failed ideas 成为未来 ideate 的 banlist

3. **添加 graph edges**：
   ```bash
   # 对每个 idea：origin_gaps 中的每个 concept/topic 都加一条 addresses_gap 边
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{slug}" --to "concepts/{origin-gap-slug}" \
     --type addresses_gap --evidence "Generated by ideate"
   # ...gap 目标是 topic 时改为 topics/{origin-gap-slug}。

   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{slug}" --to "papers/{source-paper}" \
     --type inspired_by --evidence "Inspired by method in {paper-title}"
   ```

4. **重建派生数据**：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

5. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "ideate | {N} ideas proposed, {M} ideas filtered out | direction: {direction}"
   ```

6. **输出 IDEA_REPORT 到终端**：
   ```markdown
   # Idea Generation Report

   ## Pipeline Summary
   - Direction: {direction}
   - Phase 1: Scanned {N} external papers, {M} wiki gaps identified
   - Phase 2: Generated {X} candidates (Claude: {a}, Review LLM: {b})
   - Phase 3: {Y} survived filter & validation (from {X})
   - Phase 4: {K} ideas written to wiki

   ## Top Ideas (ranked)

   | Rank | Idea | Novelty | Review | Gap Align | Pilot | Status |
   |------|------|---------|--------|-----------|-------|--------|
   | 1 | [[slug]] | 4/5 | 7/10 | +2 | pass | proposed |
   | 2 | [[slug]] | 3/5 | 6/10 | +0 | pass | proposed |

   ## Filtered Out
   | Idea | Reason | Status |
   |------|--------|--------|
   | [[slug]] | 已有相似发表工作 | failed [filter] |
   | [[slug]] | 方法在预实验中发散 | failed [pilot] |
   | [[slug]] | GPU 需求过高 | failed [filter] |

   ## Suggested Next Steps
   - If --skip-pilot is not specified, run the pilot experiment for further screening.
   - Run `/exp-design {top-idea-slug}` to design experiments
   - Run `/novelty` on any idea before investing time

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Papers | {before} | {after} | +{delta} |
   | Methods | {before} | {after} | +{delta} |
   | Ideas | {before} | {after} | +{delta} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {before_level} | {after_level} | {unchanged/upgraded} |
   （仅展示 delta != 0 的行。数据来自前置 step 3 的 `maturity_before` 与此处重新调用 `maturity --json` 的对比。）
   ```

7. **若用户输入了 `--skip-pilot`则跳过预实验部分，否则记得向用户确定要进行预实验，并让用户选择幸存idea中需要进行预实验的idea**


### Phase 5: 预实验（Pilot Experiments）

（若 `--skip-pilot` 则跳过，管道在 Phase 4 后结束）

目标：对幸存的idea中**用户选择的**进行轻量级预实验，在投入完整实验前检测明显失败。

**按 `generation_path` 的预实验策略**：

| 路径 | 预实验方式 |
|------|-----------|
| A (景观驱动) | 基于 topic/research 描述直接实现提出的方法。在小规模 benchmark 上运行，验证 idea 可行且产生非退化输出。与简单 baseline 对比。 |
| B (增量改进) | 从原方法的论文 repo 出发，应用提出的修复并运行最小评估。与原方法对比验证局限是否被解决。 |
| C (有机融合) | 实现 M1 + M2 的组合版本。在小规模 benchmark 上运行，检查性能/成本 tradeoff 是否达到预期平衡（不被纯 M1 或纯 M2 支配）。 |
| D (共性盲点) | 在新设定下（共有假设 P 被打破时）运行现有方法。验证它们确实失败或退化，确认 gap 真实存在。 |
| E (跨域迁移) | 在目标领域实现迁移的机制。运行最小评估，检查机制是否兼容且产生非退化输出。 |

**Pilot Spec — 结构化输出**（GPU 资源充足时**可并行执行多个预实验**）：

写预实验代码前，为用户选择的idea 生成结构化 Pilot Spec 块并写入 `experiments/pilot/{slug}.yaml`。此 spec 是预实验代码生成的契约（类比 `/exp-design` 实验页面供 `/exp-run` 消费）。包含以下字段：

```yaml
# Pilot Spec for: {idea-slug}
pilot_spec:
  hypothesis: "<可测试命题>"
  approach_sketch: "<方法描述>"
  implementation:
    repo: "<基础代码 repo URL 或 'from-scratch'>"
    entry_point: "<主脚本>"
    modifications: "<具体代码改动>"
    files_to_create:
      - "<文件>: <用途>"
  setup:
    model: "<模型>"
    dataset: "<数据集>"
    hardware: "<GPU>"
    framework: "<PyTorch/JAX/TF>"
    batch_size: "<缩减的 batch size，通常为论文的 1/4 到 1/8>"
    max_steps: "<缩短的训练步数，完整步数的 10-30%>"
    learning_rate: "<lr>"
    seeds: "<种子数，预实验默认 1>"
    other_hparams: "<关键超参数>"
  metrics:
    - name: "<指标>"
      why: "<为什么用这个指标>"
  baseline:
    method: "<baseline 方法>"
    source: "<论文 repo 或 wiki slug>"
    expected_value: "<已知性能>"
  success_criterion:
    pass: "<量化条件>"
    fail: "<量化条件>"
    inconclusive: "<其他>"
```

**预实验要求**：
- **减小 batch size**：使用能产生有意义梯度的最小 batch size（通常为论文报告 batch size 的 1/4 到 1/8）
- **缩短训练**：训练到前中期（完整训练步数的 10-30%），非完整收敛
- **目标**：检测明显的退化或失败，而非追求 SOTA
- **对比**：始终包含 baseline（路径 A 用简单默认 baseline，路径 B 用原方法，路径 C 用纯 M1/M2，路径 D 用现有方法，路径 E 用目标领域 SOTA）
- **success_criterion**：必须是量化可判定的条件

**通过 `/exp-pilot-run` 运行预实验**：

用户选择的幸存 idea 写入 Pilot Spec 到 `experiments/pilot/{slug}.yaml` 后：

```
Skill: exp-pilot-run
Args: "{idea-slug}"
```

`/exp-pilot-run` 读取 Pilot Spec，写入预实验代码到 `experiments/pilot/code/{slug}/`，运行实验，返回 PILOT_REPORT：
- **Results**：指标值 vs baseline（mean ± std）
- **Details**：完成步数、运行时间、日志路径

**通过 `/exp-pilot-eval` 评估预实验结果**：

`/exp-pilot-run` 返回 PILOT_REPORT 后，评估结果并更新 idea 页面（已在 Phase 4 创建）：

```
Skill: exp-pilot-eval
Args: "{idea-slug}"
```

`/exp-pilot-eval` 读取预实验结果，应用判定逻辑（宽松阈值——目的是检测明显失败，非衡量最终性能），更新 idea 页面：
- **Pass**：设置 `pilot_result: "pass — ..."`，status 不变
- **Fail**：设置 `failure_reason: "[pilot] ..."`，status 转为 `failed`，同时设置`pilot_result: "fail — ..."`
- **Inconclusive**：设置 `pilot_result: "inconclusive — needs full experiment"`，status 不变

**若 `--auto` 未设置**：在终端展示预实验结果，对边界情况等待用户确认

**所有预实验完成后**：输出最终 IDEA_REPORT（见 Phase 4 Step 6）
## Constraints

- **wiki cold 时自动切换 cold-start mode**：外部搜索扩展（WebSearch 8 查询，S2/DeepXiv limit 30），不阻塞执行
- **所有 idea 必须有 wiki 依据**：每个 idea 至少引用 2 个 wiki 页面（paper / concept / method / topic）
- **必须加载 banlist**：Phase 1 必须读取 failed ideas 的 failure_reason，Phase 2/3/4 必须检查重叠
- **Review LLM 独立性**：Phase 2 中 Review LLM 不看 Claude 的 idea 列表（cross-model-review.md）
- **被淘汰的 ideas 也写入 wiki**：status=failed + failure_reason，作为 anti-repetition 记忆
- **不凭空编造**：所有 ideas 必须基于 wiki 已有知识或外部搜索结果推导，不编造不存在的论文或方法
- **slug 唯一性**：创建前检查 wiki/ideas/ 中是否已存在相同 slug
- **graph edges 使用 tools/research_wiki.py**：不手动编辑 edges.jsonl

## Error Handling

- **wiki 为空**：正常执行外部搜索（Phase 1 Source B/C/D），但跳过 wiki 内部上下文，提示用户先建立知识库
- **WebSearch 不可用**：跳过外部搜索，仅基于 wiki 内部知识生成（降级模式，在报告中标注）
- **Semantic Scholar API 不可用**：跳过 S2 搜索，依赖 DeepXiv + WebSearch 补偿
- **DeepXiv API 不可用**：跳过 DeepXiv 搜索和 trending，依赖 S2 + WebSearch（回退到原有行为）
- **Review LLM 不可用**：Phase 2 仅用 Claude 生成（无双模型多样性，在报告中标注）
- **/novelty 失败**：Phase 3 中单个 idea 的 novelty 失败时，标注「novelty unverified」继续
- **/review 失败**：Phase 3 中 review 失败时，标注「unreviewed」继续，建议用户手动 /review
- **预实验失败**：标记为 failed 并在 failure_reason 中加 `[pilot]` 前缀，其余 ideas 继续
- **所有预实验都失败**：idea 页面已存在（Phase 4 已写入），报告建议用户查看预实验日志并调整方案
- **slug 冲突**：若 wiki/ideas/ 中已存在相同 slug，追加数字后缀（如 `sparse-lora-v2`）
- **所有 ideas 都被淘汰**：仍写入 wiki（status: failed），报告中建议用户扩大搜索方向或 /ingest 更多论文

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py maturity wiki/ --json` — 检查 wiki 成熟度 + Growth Report
- `python3 tools/research_wiki.py slug "<title>"` — 生成 slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — 添加 graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建 query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建 gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/fetch_s2.py search "<query>" --limit 20` — Semantic Scholar 搜索
- `python3 tools/fetch_deepxiv.py search "<query>" --mode hybrid --limit 20` — DeepXiv 语义搜索
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — 获取论文 TLDR
- `python3 tools/fetch_deepxiv.py trending --days 14` — 热门论文趋势

### Skills（via Skill tool）
- `/novelty` — Phase 3 深度 novelty 验证
- `/review` — Phase 3 跨模型审查
- `/exp-pilot-run` — Phase 5 预实验执行
- `/exp-pilot-eval` — Phase 5 预实验结果评估与 idea 页面更新

### MCP Servers
- `mcp__llm-review__chat` — Phase 2 Review LLM 独立脑暴

### Claude Code Native
- `WebSearch` — Phase 1 外部搜索、Phase 3 快速 novelty 筛查、Phase 5 预实验验证
- `Agent` tool — Phase 1 并行搜索、Phase 2 并行脑暴

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Phase 2 Review LLM 独立性原则
