---
description: 实验判决门：Review LLM 独立评判实验结果 → 4 种判决路径 → 自动更新 linked idea 的 status / failure_reason 与 graph edges
argument-hint: <experiment-slug> [--auto]
---

# /exp-eval

> 将已完成实验的结果转化为 wiki 知识更新。
> Review LLM 作为 impartial judge（遵循 cross-model-review），独立评估实验结果对 linked idea 的 hypothesis 的影响。
> 4 种判决路径：supported → idea validated / partially_supported → 补充实验 /
> not_supported → idea failed / inconclusive → debug。
> 自动更新 linked idea 的 `status`、`failure_reason` 与 graph edges。

## Inputs

- `experiment`：wiki/experiments/ 中的 slug（status 必须为 `completed`）
- `--auto`（可选）：自动模式，不暂停等待用户确认 wiki 更新（用于 /research 调用）

## Outputs

- `wiki/ideas/{linked-idea}.md` — 更新 `status`、`failure_reason`、`date_resolved`
- `wiki/experiments/{slug}.md` — 填充 `## Idea updates` section（记录 linked idea 的 status 变化；旧名为 `## Claim updates`）
- `wiki/graph/edges.jsonl` — 新增 `supports` / `invalidates` 边（experiment → idea）
- `wiki/graph/context_brief.md` — 重建
- `wiki/graph/open_questions.md` — 重建
- `wiki/log.md` — 追加日志
- **VERDICT_REPORT**（输出到终端）— 判决结果、wiki 变更摘要、下一步建议

## Wiki Interaction

### Reads
- `wiki/experiments/{slug}.md` — 实验结果：`outcome`、`key_result`、`metrics`、完整 Results section、`linked_idea`
- `wiki/ideas/{linked-idea}.md` — linked idea 当前状态：`status`、`## Hypothesis`、`## Risks`
- `wiki/experiments/*.md` — 同一 `linked_idea` 的 sibling 实验（综合评估）
- `wiki/graph/context_brief.md` — 全局上下文
- `.claude/skills/shared-references/cross-model-review.md` — 审稿独立性原则

### Writes
- `wiki/ideas/{linked-idea}.md` — 更新 `status`、`failure_reason`、`date_resolved`
- `wiki/experiments/{slug}.md` — 填充 `## Idea updates` section
- `wiki/graph/edges.jsonl` — 新增 `supports` / `invalidates` 边（experiment → idea）
- `wiki/graph/context_brief.md` — 重建
- `wiki/graph/open_questions.md` — 重建
- `wiki/log.md` — 追加操作日志

### Graph edges created
- `supports`：experiment → idea（实验支持 idea 的 hypothesis）— verdict = supported 或 partially_supported
- `invalidates`：experiment → idea（实验否定 idea 的 hypothesis）— verdict = not_supported

## Workflow

**前置**：
1. 确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）
2. 确认实验 status == `completed`（未完成的实验不能评判）

### Step 1: 加载上下文

1. **读取实验页面** `wiki/experiments/{slug}.md`：
   - `outcome`（succeeded/failed/inconclusive）
   - `key_result`
   - `linked_idea` slug（必填；缺失则拒绝继续）
   - `metrics` 与完整 `## Results` section
   - `hypothesis`

2. **读取 linked idea** `wiki/ideas/{linked-idea}.md`：
   - 当前 `status`
   - `## Hypothesis`、`## Approach sketch`、`## Risks`、`## Novelty argument`

3. **加载 sibling 实验**（同一 `linked_idea`）：
   - Glob `wiki/experiments/*.md`，过滤 `linked_idea == 当前 idea`
   - 汇总它们的 outcome（判决要看完整证据组合，不是单个实验）

4. **读取全局上下文**：`wiki/graph/context_brief.md`

5. **读取 cross-model-review.md**：确认 Review LLM 独立性原则

### Step 2: Review LLM 判决（Cross-Model Verdict）

**遵循 cross-model-review.md**：不向 Review LLM 发送 Claude 的预判。

```
mcp__llm-review__chat:
  system: "You are an impartial scientific judge evaluating whether experimental
           results support or refute a research hypothesis. Be rigorous and objective.
           Consider: statistical significance, effect size, experimental validity,
           potential confounds, and whether the results generalize beyond the
           specific setup tested."
  message: |
    ## Idea Hypothesis Under Test
    Title: {idea title}
    Hypothesis: {idea ## Hypothesis section}
    Novelty argument: {idea ## Novelty argument section}
    Current status: {idea status}

    ## Experiment
    Title: {experiment title}
    Hypothesis: {experiment hypothesis}
    Setup: {model, dataset, hardware, framework}
    Metrics: {metrics list}

    ## Results
    {full Results section from experiment page}

    ## Key Finding
    {key_result}

    ## Sibling Experiments on This Idea
    {summary of other experiments' outcomes that share the same linked_idea, if any}

    ## Your Task
    Provide your verdict:
    1. **Verdict**: One of: supported / partially_supported / not_supported / inconclusive
    2. **Evidence strength**: weak / moderate / strong
    3. **Idea status recommendation**: keep current / advance to validated / mark failed
    4. **Key reasoning**: 2-3 sentences explaining your verdict
    5. **Concerns**: Any methodological concerns or limitations
    6. **Suggested next steps**: What would strengthen or clarify this result?
```

记录 Review LLM 的判决。

### Step 3: Claude 综合评估

1. **独立形成 Claude 的判决**（在读取 Review LLM 判决后，Claude 也独立分析）：
   - 基于实验结果、idea 的 hypothesis，以及 sibling 实验的综合证据
   - 形成 Claude 自己的 verdict 和 idea status 建议

2. **综合两个判决**（遵循 cross-model-review.md composing rules）：
   - **两者一致**（verdict 相同）：采用该 verdict，高置信度
   - **两者不一致**：
     - 明确标注分歧
     - 取更保守的 verdict（supported > partially_supported > not_supported）
     - 在报告中详述分歧原因
   - **致命发现优先**：若任一方发现方法论问题（数据泄露、不公平比较），该发现优先

3. **确定最终判决**：verdict + evidence_strength + idea_status_change

### Step 4: 根据判决更新 Wiki

**若 `--auto` 未设置**：先展示判决结果和计划变更，等待用户确认。

#### 路径 A: SUPPORTED（实验支持 idea 的 hypothesis）

1. **更新 idea**：
   - 若 idea 只覆盖单一 hypothesis 且本实验是 主实验 块，把 idea 推进到 `validated`：
     ```bash
     python3 tools/research_wiki.py transition wiki/ideas/{linked-idea}.md --to validated
     ```
   - 否则保持 idea 当前生命周期状态（之前是 `tested` 就维持 `tested`；否则维持 `in_progress`）。

2. **添加 graph edge**：
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type supports --evidence "{key_result}"
   ```

3. **建议下一步**：`/paper-plan {linked-idea}` 或继续 ablation/robustness 实验

#### 路径 B: PARTIALLY_SUPPORTED（部分支持）

1. **更新 idea**：
   - 生命周期保持当前状态（`in_progress` 或 `tested`）

2. **添加 graph edge**：
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type supports --evidence "Partially supported: {limitation}"
   ```

3. **建议补充实验**：
   - 明确缺少什么证据
   - 建议用 `/exp-design --linked-idea {linked-idea}` 设计补充实验
   - 若 Review LLM 指出的 concern 可通过实验解决，具体建议实验方向

#### 路径 C: NOT_SUPPORTED（实验否定 idea 的 hypothesis）

1. **更新 idea**：
   - 推进到 `failed`：
     ```bash
     python3 tools/research_wiki.py transition wiki/ideas/{linked-idea}.md --to failed --reason "<具体原因>"
     ```
     `transition` 要求非空 `--reason`；把综合得到的失败原因传进来。`transition` 命令会自动写入 `failure_reason` 与 `date_resolved`。
   - 注意：`failure_reason` 是 anti-repetition memory —— 必须写出具体原因，不得是模糊的 "did not work"。

2. **添加 graph edge**：
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type invalidates --evidence "{failure_reason}"
   ```

3. **建议下一步**：
   - 分析失败原因
   - 考虑 pivot（新 idea 解决同一 gap，避开已知失败原因）
   - 建议 `/ideate` 生成替代方案

#### 路径 D: INCONCLUSIVE（结果不确定）

1. **不修改 idea status**：证据不足以做判断

2. **更新实验页面**：outcome 已为 inconclusive（/exp-run 设置）

3. **建议 debug**：
   - 数据问题？实现 bug？错误的 metric？
   - 方差过大？需要更多 seeds？
   - 实验设置与 idea 的 hypothesis 不对齐？

4. **idea status 不变**：保持当前状态

#### 所有路径通用

1. **更新实验页面的 `## Idea updates` section**（记录 linked idea 的更新；不再有独立的 claim 实体）：
   ```markdown
   ## Idea updates
   - **Verdict**: {supported/partially_supported/not_supported/inconclusive}
   - **Linked idea**: [[{linked-idea}]] status {old} → {new}
   - **Judge agreement**: {Claude and Review LLM agreed / disagreed on ...}
   - **Date**: YYYY-MM-DD
   ```

2. **更新 index.md**（若 idea status 变化）

3. **重建派生数据**：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

4. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-eval | {slug} → ideas/{linked-idea} | verdict: {verdict} | idea status: {old}→{new}"
   ```

5. **输出 VERDICT_REPORT 到终端**：
   ```markdown
   # Verdict Report: {experiment title}

   ## Verdict: {SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE}

   ## Judge Assessment
   | | Claude | Review LLM | Final |
   |---|-------|------|-------|
   | Verdict | {verdict} | {verdict} | {verdict} |
   | Idea status rec | {rec} | {rec} | {rec} |
   | Evidence strength | {strength} | {strength} | {strength} |

   ## Key Reasoning
   {2-3 sentences from Review LLM + Claude synthesis}

   ## Wiki Changes
   | Entity | Field | Before | After |
   |--------|-------|--------|-------|
   | ideas/{slug} | status | {old} | {new} |

   ## Graph Edges Added
   - experiments/{slug} → ideas/{linked-idea} (supports/invalidates)

   ## Concerns
   {methodological concerns from Review LLM}

   ## Next Steps
   - {path-specific suggestions}

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Ideas validated | {before} | {after} | +{delta} |
   | Ideas failed | {before} | {after} | +{delta} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {level} | {level} | {unchanged/upgraded} |
   （数据来自 Step 1 开始时和 Step 4 结束后分别调用 `python3 tools/research_wiki.py maturity wiki/ --json` 的对比。）
   ```

## Constraints

- **只处理 completed 实验**：status != completed 的实验拒绝处理，提示用 /exp-run 先完成。
- **`linked_idea` 必填**：拒绝评判任何 `linked_idea` 为空的实验（新 schema 强制要求；如果遇到这类页面，那是 refactor 之前的遗留物，必须先手动修复）。
- **审稿独立性**：严格遵循 cross-model-review.md，不向 Review LLM 发送 Claude 的预判。
- **`failure_reason` 必须具体**：not_supported 路径的 `failure_reason` 不能是空话（如 "实验失败"），必须写明具体原因。`transition --reason` 会拒绝空字符串。
- **idea 生命周期只前进**：`proposed → in_progress → tested → validated/failed`。使用 `tools/research_wiki.py transition`（而非直接改 frontmatter），让生命周期校验器跑起来。
- **graph edges 使用 tools/research_wiki.py**：不手动编辑 `edges.jsonl`。
- **保守原则**：当 Claude 和 Review LLM 判决不一致时，取更保守的判决。
- **综合所有 sibling 实验评估**：不仅看当前实验，还要参考同一 `linked_idea` 的其他实验。

## Error Handling

- **experiment 找不到**：提示用户检查 slug，列出 `wiki/experiments/` 中 status=completed 的候选。
- **experiment 未完成**：提示 status，建议先运行 `/exp-run {slug}` 或 `/exp-run {slug} --check`。
- **`linked_idea` 缺失**：拒绝继续；提示用户运行 `/edit` 设置实验的 `linked_idea`。
- **linked idea 页面不存在**：报告 dangling reference；拒绝更新 —— 建议先用 `/edit` 或 `/ideate` 创建该 idea 页面。
- **Review LLM 不可用**：降级为 Claude 单模型判决，在报告中标注「single-model verdict, cross-model verification unavailable」，建议用户稍后确认。
- **idea 已被其他实验修改**：在应用 transition 前重新读取最新状态；不要把更高生命周期状态退回到更低。
- **结果数据缺失**：若实验页面的 Results section 为空，提示用户先运行 `/exp-run {slug} --check`。

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to validated|failed [--reason "..."]` — 推进 idea 生命周期
- `python3 tools/research_wiki.py add-edge wiki/ ...` — 添加 graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建 query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建 gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### MCP Servers
- `mcp__llm-review__chat` — Step 2 Review LLM 独立判决

### Claude Code Native
- `Read` — 读取 wiki 页面
- `Glob` — 查找同一 `linked_idea` 的 sibling 实验
- `Edit` — 更新 wiki 页面

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM 独立性原则（必读）

### Called by
- `/research` Stage 4（判决与迭代阶段）
- 用户手动调用
