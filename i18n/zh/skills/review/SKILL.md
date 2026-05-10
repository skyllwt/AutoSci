---
description: 通用跨模型审查：Review LLM 对任意研究制品进行独立评审，输出结构化评分、wiki 实体映射与改进建议
argument-hint: <artifact-path-or-slug> [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /review

> 对任意研究制品（idea、proposal、experiment plan、paper draft、method）进行跨模型审查。
> 使用 Review LLM 作为独立审稿人，输出结构化评分、可操作的改进建议，以及与 wiki 实体的映射
> （哪些 ideas/methods 需要加强，哪些 gaps 被发现）。
> 支持三种难度级别（standard / hard / adversarial）和四种审查焦点。
> 可独立使用，也被 /ideate、/refine、/exp-design 调用。

## Inputs

- `artifact`：要审查的制品，以下之一：
  - wiki 页面的 slug（如 `sparse-lora-for-edge-devices`，从 ideas/experiments/methods/ 中查找）
  - 文件路径（如 `wiki/outputs/paper-draft-v1.md`）
  - 自由文本（直接粘贴的 proposal 或 idea 描述）
- `--difficulty`（可选，默认 `standard`）：
  - `standard`：单轮审查，给出结构化反馈
  - `hard`：多轮对话（最多 3 轮），Claude 对每个 weakness 进行 rebuttal
  - `adversarial`：多轮对话（最多 3 轮），Review LLM 额外尝试找致命缺陷，模拟最严苛的审稿人
- `--focus`（可选，默认全面审查）：
  - `method`：聚焦方法设计的正确性、创新性、可行性
  - `evidence`：聚焦证据是否充分、实验是否严谨、idea/method 是否得到充分支撑
  - `writing`：聚焦表达清晰度、结构组织、论证逻辑
  - `completeness`：聚焦是否遗漏关键内容（相关工作、ablation、baseline）

## Outputs

- **Review Report**（输出到终端）：
  - Overall Score（1-10）
  - Strengths（优点列表）
  - Weaknesses（缺点列表，按严重程度排序）
  - Questions（审稿人的疑问）
  - Actionable Suggestions（可操作的改进建议，按优先级排序）
  - Wiki Entity Mapping（哪些 ideas/methods 需要加强，哪些 gaps 被发现）
  - Verdict：`ready` / `needs-work` / `major-revision` / `rethink`
- 若 `--difficulty >= hard`：额外包含多轮对话记录和最终修正后的评分
- 该 skill **不直接修改 wiki**，但会输出建议的 wiki 更新列表

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — 查找制品引用的论文，验证引用正确性
- `wiki/concepts/*.md` — 理解制品涉及的技术概念
- `wiki/methods/*.md` — 检查制品依赖的 methods 当前状态
- `wiki/experiments/*.md` — 查找相关实验结果
- `wiki/ideas/*.md` — 如果审查的是 idea，检查其上下文
- `wiki/graph/context_brief.md` — 获取全局上下文
- `wiki/graph/open_questions.md` — 对照 gap map 检查完整性
- `.claude/skills/shared-references/cross-model-review.md` — 审稿独立性原则

### Writes
- **无**。Review 是只读查询操作。
  - 审查结果输出到终端，由用户或调用方（如 /refine）决定是否应用。

### Graph edges created
- **无**。

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 加载上下文

1. **解析 artifact**：
   - 若为 slug：按顺序在 `wiki/ideas/`、`wiki/experiments/`、`wiki/methods/`、`wiki/papers/`、`wiki/outputs/` 中查找 `{slug}.md`
   - 若为文件路径：直接读取
   - 若为自由文本：直接使用
2. **确定 artifact 类型**：idea / experiment / method / paper-draft / proposal / other
3. **加载相关 wiki 上下文**：
   - 读取 `wiki/graph/context_brief.md` 获取全局视角
   - 读取 `wiki/graph/open_questions.md` 获取知识缺口列表
   - 根据 artifact 类型，加载相关 wiki 页面：
     - idea → 其 origin_gaps（concepts/topics）、相关 papers
     - experiment → 其 linked_idea、相关 experiments
     - method → 其 source_papers 和 parent_methods
     - paper-draft → 其引用的所有 wiki 页面
4. **读取 cross-model-review.md**：确认 Review LLM 独立性原则
5. **构建 reviewer system prompt**（根据 --focus）：

   **Base prompt（所有 focus）：**
   ```
   You are a senior ML researcher reviewing a research artifact.
   Be thorough, specific, and constructive. For every weakness, suggest a concrete fix.
   Score on a 1-10 scale where:
   - 1-3: Fundamental flaws, not salvageable in current form
   - 4-5: Significant issues but core idea may have merit
   - 6-7: Solid work with clear areas for improvement
   - 8-9: Strong work, minor issues only
   - 10: Exceptional, publication-ready
   ```

   **Focus-specific additions：**
   - `method`：额外要求评估 technical correctness, novelty of approach, feasibility, comparison to alternatives
   - `evidence`：额外要求评估 experimental rigor, statistical significance, idea-evidence alignment, missing controls
   - `writing`：额外要求评估 clarity, logical flow, notation consistency, figure quality, related work coverage
   - `completeness`：额外要求评估 missing baselines, missing ablations, missing datasets, missing related work, reproducibility

   **Adversarial addition（仅 adversarial 模式）：**
   ```
   Additionally: actively search for fatal flaws. A fatal flaw is anything that,
   if true, would make the entire contribution invalid (incorrect proof, data leakage,
   unfair comparison, published prior work). If you find one, flag it clearly.
   ```

### Step 2: Review LLM 首轮审查

**遵循 cross-model-review.md**：不向 Review LLM 发送任何 Claude 的预判。

```
mcp__llm-review__chat:
  system: {reviewer system prompt from Step 1}
  message: |
    ## Artifact to Review
    {artifact full text}

    ## Context from Knowledge Base
    {relevant wiki context: related ideas/methods with status, related experiments, gap map entries}

    ## Review Instructions
    Please provide:
    1. **Strengths** (3-5 bullet points)
    2. **Weaknesses** (ranked by severity, each with a concrete suggestion to fix)
    3. **Questions** (things that are unclear or need clarification)
    4. **Score** (1-10 with one-sentence justification)
    5. **Verdict**: ready / needs-work / major-revision / rethink
    6. **Idea-/method-level feedback**: For each idea or method referenced in the artifact, assess whether the evidence/justification is sufficient. List any ideas or methods that need stronger support.
    7. **Knowledge gaps identified**: Any open questions or missing knowledge that would strengthen this work.
```

记录 Review LLM 返回的 `threadId`（用于 Step 3 多轮对话）。

### Step 3: 多轮对话（hard / adversarial 模式）

若 `--difficulty` 为 `standard`，跳过此步。

**对 Review LLM 的每个 weakness 进行回应**（最多 3 轮）：

**Round N（N = 1, 2, 3）：**

1. Claude 分析 Review LLM 的 weaknesses，对每个 weakness 分类：
   - **可反驳（rebuttal）**：Claude 有充分理由或 wiki 证据反驳 → 写出 rebuttal
   - **承认（acknowledge）**：weakness 确实存在 → 承认并提出修复方案
   - **需要更多信息（clarify）**：weakness 基于误解 → 提供澄清

2. 将 Claude 的回应发送给 Review LLM：
   ```
   mcp__llm-review__chat-reply:
     threadId: {from Step 2}
     message: |
       Thank you for the review. Here are my responses:

       {for each weakness: rebuttal / acknowledgment / clarification}

       Please re-evaluate considering these responses. Update your score if warranted.
       If --difficulty == adversarial: Also, please try harder to find any remaining
       fatal flaws I may have missed.
   ```

3. Review LLM 回应新的评估和修正后的评分

4. 若 Review LLM 的评分变化 < 0.5 且无新 weakness → 停止对话（收敛）
5. 若已达 3 轮 → 停止对话

### Step 4: 结构化输出

综合 Step 2 + Step 3 结果，生成结构化 Review Report：

```markdown
# Review Report: {artifact title}

## Meta
- **Artifact type**: {idea / experiment / method / paper-draft / proposal}
- **Difficulty**: {standard / hard / adversarial}
- **Focus**: {method / evidence / writing / completeness / 全面}
- **Reviewer**: Review LLM（在 `.env` 中配置）
- **Rounds**: {1 for standard, N for hard/adversarial}

## Score: {final score}/10 — {verdict}

| Verdict | 含义 |
|---------|------|
| ready | 可直接使用或提交 |
| needs-work | 有明确的改进点，修复后可用 |
| major-revision | 核心部分需要重大修改 |
| rethink | 基本方向可能有问题，需重新考虑 |

## Strengths
1. {strength 1}
2. {strength 2}
...

## Weaknesses (by severity)

### Critical
- {weakness}: {具体描述} → **Fix**: {具体修复建议}

### Major
- {weakness}: {具体描述} → **Fix**: {具体修复建议}

### Minor
- {weakness}: {具体描述} → **Fix**: {具体修复建议}

## Questions
1. {question}
...

## Wiki Entity Mapping

### Ideas / methods needing stronger support
| Entity | Signal | Issue | Suggested action |
|--------|--------|-------|------------------|
| [[idea-slug]] | novelty_score 2/5 | Novelty argument is thin | Run /novelty rerun |
| [[method-slug]] | source_papers sparse | Missing source paper backing | Ingest the missing paper, then rerun /check |

### Knowledge gaps identified
| Gap | Related to | Suggested action |
|-----|-----------|------------------|
| {描述} | [[slug]] | /ingest, /exp-run, or /query |

### Suggested wiki updates
- `wiki/ideas/{slug}.md`: add risk factor from review
- `wiki/methods/{slug}.md`: tighten Tradeoff profile / Limitations
- `wiki/graph/open_questions.md`: will be updated on next rebuild

## Dialogue History (hard/adversarial only)

### Round 1
**Review LLM**: {summary of initial review}
**Claude**: {summary of rebuttals/acknowledgments}

### Round 2
**Review LLM**: {updated assessment}
...

## Actionable Items (ranked)
1. [CRITICAL] {action item}
2. [MAJOR] {action item}
3. [MINOR] {action item}
```

## Constraints

- **审稿独立性**：严格遵循 `shared-references/cross-model-review.md`，不向 Review LLM 泄露 Claude 的预判
- **不修改 wiki**：review 只输出建议，不直接修改任何 wiki 页面。wiki 修改由调用方（如 /refine）执行
- **score 必须有 justification**：不接受没有理由的分数
- **weakness 必须有 fix**：每个 weakness 必须附带具体的、可操作的修复建议，不接受空洞批评
- **entity-level mapping 必须**：输出必须包含 Wiki Entity Mapping 部分，将 review 发现映射到具体 wiki 实体（ideas、methods 等）
- **adversarial 模式必须搜索致命缺陷**：如已发表的完全相同工作、证明错误、数据泄露等
- **多轮对话最多 3 轮**：防止无限循环，若 3 轮后仍未收敛则以当前状态输出
- **引用 wiki 页面时使用 [[slug]]**：所有对 wiki 页面的引用使用 wikilink 语法

## Error Handling

- **artifact 找不到**：提示用户检查 slug 或路径，列出可能的候选页面
- **Review LLM 不可用**：降级为 Claude 自我审查模式，报告标注「single-model review, cross-model verification unavailable」，建议用户稍后用 Review LLM 重新审查
- **wiki 为空**：正常执行审查，但 Wiki Entity Mapping 部分标注「wiki empty, no entity mapping available」
- **artifact 太长**：若超过 Review LLM 上下文窗口，按 section 分段审查，最后合并
- **Review LLM 返回无效响应**：重试一次，若仍无效则使用 Claude 自审降级方案
- **多轮对话中 Review LLM 不收敛**：3 轮后强制结束，输出最后一轮的评分和总结

## Dependencies

### Tools（via Bash）
- 无直接工具调用（review 不需要确定性工具）

### MCP Servers
- `mcp__llm-review__chat` — Review LLM 首轮审查（Step 2）
- `mcp__llm-review__chat-reply` — Review LLM 多轮对话（Step 3）

### Claude Code Native
- `Read` — 读取 artifact 和 wiki 页面
- `Glob` — 查找 artifact 对应的 wiki 页面

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — 审稿独立性原则（必读）

### Called by
- `/ideate` Phase 4（审查 top ideas）
- `/refine` 每轮迭代（审查当前版本）
- `/exp-design --review`（审查实验计划）
