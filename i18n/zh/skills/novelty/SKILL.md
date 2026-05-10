---
description: 多源 novelty 验证：WebSearch + Semantic Scholar + wiki + Review LLM cross-verify，输出 novelty 评分与建议。可选 --write，把分数写回 idea 页面。
argument-hint: <idea-description-or-slug> [--quick] [--verbose] [--write]
---

# /novelty

> 对一个研究想法或方法进行多源 novelty 验证。搜索 WebSearch、Semantic Scholar、
> wiki 内已有工作和 arXiv 最新预印本，然后由 Review LLM 交叉验证，输出 novelty 评分（1-5）、
> 最相似已有工作、差异化要点和下一步建议。
> 可独立使用，也被 /ideate Phase 4 调用。

## Inputs

- `target`：以下之一：
  - idea 的自由文本描述（一段话或几句话）
  - wiki 中 ideas/ 页面的 slug（如 `sparse-lora-for-edge-devices`）
  - 论文标题或 arXiv URL（检查该论文方法的 novelty）
- `--quick`：快速模式，跳过 Review LLM cross-verify（Step 3），仅做搜索
- `--verbose`：输出完整搜索结果，不仅是摘要
- `--write`（可选，默认 **关闭**）：把得到的 `novelty_score` 持久化到 target frontmatter。**仅当 `target` 是 idea slug**（即 `wiki/ideas/{slug}.md` 存在）时生效。自由文本 target 与论文 novelty 检查无论是否带此 flag 都保持只读。视为用户可见参数 —— `/ideate` Phase 4 调用 `/novelty` 时显式传入；不得仅根据仓库状态推断。

## Outputs

- **Novelty Report**（输出到终端）：
  - Novelty Score（1-5）
  - 最相似的已有工作列表（top 3-5）
  - 与每个已有工作的差异化要点
  - Review LLM 交叉验证意见（除非 --quick）
  - 推荐行动：proceed / modify / abandon
- **idea 页面写入（仅当 `--write` 开启且 target 是 idea slug）**：通过 `tools/research_wiki.py set-meta` 更新 `wiki/ideas/{slug}.md` 的 `novelty_score` 字段。其他字段一律不动。

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — 搜索已有论文中是否有类似方法
- `wiki/concepts/*.md` — 检查概念重叠
- `wiki/methods/*.md` — 检查是否已有重叠的 method 实体
- `wiki/ideas/*.md` — 检查是否与已有 idea 重复（特别是 failed ideas 的 failure_reason）
- `wiki/graph/context_brief.md` — 获取全局上下文辅助搜索

### Writes
- `wiki/ideas/{slug}.md`（仅当 `--write` 开启且 target 是 idea slug）—— 设置 `novelty_score`，其余情况不写。
- `wiki/log.md`（仅当发生写入时）—— 追加 "novelty | wrote novelty_score=N to ideas/{slug}"。

### Graph edges created
- **无**。

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 提取方法签名

1. **若 target 是 slug**：读取 `wiki/ideas/{slug}.md`，提取 title、Hypothesis、Approach sketch
2. **若 target 是自由文本**：直接使用
3. **若 target 是 arXiv URL**：下载摘要，提取方法描述
4. 从 target 中提取「方法签名」——方法的核心要素：
   - **What**：做什么（任务/目标）
   - **How**：用什么方法（技术路线）
   - **Why novel**：声称的创新点
5. 生成 3-5 个核心关键词用于后续搜索

### Step 2: 多源搜索

并行执行以下搜索（使用 Agent tool 并发）：

**Source A — Web Search（5+ 查询）：**
1. 直接查询：`"<method-name>" + "<task>"` 精确短语搜索
2. 组件查询：`<component-1> + <component-2> + <domain>` 组件组合搜索
3. Survey 查询：`"survey" OR "review" + <task-area> + 2024 2025`
4. 竞品查询：`<alternative-approach> + <same-task>`
5. 最新查询：`<method-keywords> + arXiv + 2025 2026`

**Source B — Semantic Scholar + DeepXiv：**
```bash
python3 tools/fetch_s2.py search "<method-keywords>" --limit 20
python3 tools/fetch_deepxiv.py search "<method-keywords>" --mode hybrid --limit 20
```
合并两个来源的结果（按 arxiv_id 去重）。DeepXiv 的混合语义搜索能发现 S2 关键词搜索遗漏的语义相似工作。
- 对 top 5 结果获取详情和 TLDR：
```bash
python3 tools/fetch_s2.py paper <s2_id>
python3 tools/fetch_deepxiv.py brief <arxiv_id>
```
使用 DeepXiv brief 的 TLDR 辅助快速判断方法相似度。
**若 DeepXiv 不可用**：仅使用 S2 搜索（回退到原有行为）。

**Source C — Wiki 内部搜索：**
1. 扫描 `wiki/papers/` 所有页面的 Key idea 和 Method 段落
2. 扫描 `wiki/concepts/` 的 Definition 和 Variants 段落
3. 扫描 `wiki/ideas/` 的全部内容，特别关注：
   - status = failed 的 ideas 及其 failure_reason（anti-repetition）
   - status = proposed/in_progress 的 ideas（避免内部重复）
4. 读取 `wiki/graph/context_brief.md` 获取全局视角

**Source D — arXiv 近期预印本：**
- 使用 WebSearch 查询 `site:arxiv.org <method-keywords> 2025 2026`

### Step 3: Review LLM 交叉验证

（若 `--quick` 则跳过此步）

将以下信息提交 Review LLM 进行独立判断：

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher assessing the novelty of a proposed method.
           Be rigorous: if the method is essentially a recombination of known techniques
           with minor changes, score it low. Only score 4-5 if there is a genuinely new
           insight or formulation."
  message: |
    ## Proposed Method
    {method signature from Step 1}

    ## Existing Similar Work Found
    {top 5 similar works from Step 2, with title + one-line summary}

    ## Questions
    1. Is this method genuinely novel, or a minor variation of existing work?
    2. What is the closest existing work and what's the real difference?
    3. Novelty score 1-5 with justification.
    4. If score <= 2, what modification could increase novelty?
```

### Step 4: 生成 Novelty Report

综合 Step 2 搜索结果和 Step 3 Review LLM 意见，生成结构化报告：

```markdown
# Novelty Report: {idea title}

## Score: {1-5}/5 — {label}

| Score | Label | 含义 |
|-------|-------|------|
| 1 | Published | 已有高度相似的发表工作 |
| 2 | Very Similar | 存在非常相似的方法，仅细节差异 |
| 3 | Incremental | 在已有工作基础上有明确的增量贡献 |
| 4 | Novel Combination | 创新性地组合已有技术，产生新 insight |
| 5 | Fundamentally New | 提出全新范式或 formulation |

## Closest Prior Work

1. **{title}** ({year}) — {一句话描述相似之处}
   - 差异：{本方法与之的关键区别}
   - Wiki 链接：[[slug]]（若存在）
2. ...

## Review LLM Assessment
{Review LLM 的独立判断摘要}

## Anti-repetition Check
- Wiki 中已有 failed ideas：{列出相关 failed ideas 及 failure_reason}
- Wiki 中已有 in_progress ideas：{列出可能重叠的 ideas}

## Recommendation
- **{proceed / modify / abandon}**
- 理由：{一段话}
- 若 modify：建议的差异化方向：{具体建议}
```

**评分规则（综合判断）：**
- Claude 搜索结果 和 Review LLM 意见取较低分（保守原则）
- 若 wiki 中存在 failed idea 且 failure_reason 与本 idea 相关 → 降 1 分
- 若 wiki 中存在 in_progress idea 高度重叠 → 标记为 abandon（内部重复）

### Step 5: 持久化分数（仅当 `--write` 开启且 target 是 idea slug）

若 target 是自由文本或 paper slug，或未传 `--write`，整步跳过。否则：

```bash
python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md novelty_score {N}
python3 tools/research_wiki.py log wiki/ "novelty | wrote novelty_score=${N} to ideas/${slug}"
```

`{N}` 是上面综合规则得到的 1-5 整数。若 `set-meta` 报错（例如该字段在旧 schema 页面里不存在），将错误输出在报告中，不要静默吞掉。

## Constraints

- **默认只读**：未传 `--write` 时，novelty check 只输出终端报告，不修改 wiki 任何内容。
- **`--write` 是唯一持久化路径**：开启时只写 `novelty_score` 与 `wiki/log.md`。不得修改 idea 页面其他字段（status、priority、正文章节等）。
- **`--write` 对非 idea target 无效**：target 是自由文本或 paper slug 时，忽略 `--write`，仍输出只读报告。
- **保守评分**：宁可低估 novelty 也不高估，避免在已有工作上浪费精力
- **必须检查 failed ideas**：wiki/ideas/ 中 status=failed 的 ideas 是重要的 anti-repetition 信号
- **搜索覆盖面**：至少 5 个不同的 WebSearch 查询 + Semantic Scholar + wiki 内部搜索
- **Review LLM 独立性**：提交给 Review LLM 时不包含 Claude 自己的 novelty 判断，让 Review LLM 独立评估
- **引用真实来源**：报告中列出的所有 prior work 必须是真实存在的（WebSearch/S2 返回的），不得编造

## Error Handling

- **WebSearch 不可用**：跳过 Source A 和 D，仅依赖 S2 + wiki 搜索，在报告中注明覆盖面不足
- **Semantic Scholar API 不可用**：跳过 S2 部分，依赖 DeepXiv + WebSearch 补偿
- **DeepXiv API 不可用**：跳过 DeepXiv 部分，依赖 S2 + WebSearch（回退到原有行为）
- **Review LLM 不可用**：跳过 Step 3，报告标注「Review LLM cross-verify unavailable, single-model assessment only」
- **Wiki 为空**：正常执行外部搜索，wiki 内部搜索部分标注「wiki empty」
- **idea slug 不存在**：提示用户检查 slug，列出 wiki/ideas/ 中的可用 slugs

## Dependencies

### Tools（via Bash）
- `python3 tools/fetch_s2.py search "<query>" --limit 20` — Semantic Scholar 关键词搜索
- `python3 tools/fetch_s2.py paper <s2_id>` — 获取论文详情
- `python3 tools/fetch_deepxiv.py search "<query>" --mode hybrid --limit 20` — DeepXiv 语义搜索
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — 获取论文 TLDR 辅助相似度判断
- `python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md novelty_score <1-5>` — 仅当 `--write` 开启且 target 是 idea slug
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 写入时追加日志

### MCP Servers
- `mcp__llm-review__chat` — Review LLM 交叉验证（Step 3）

### Claude Code Native
- `WebSearch` — 多查询 web 搜索（Step 2 Source A + D）
- `Agent` tool — 并行执行多源搜索（Step 2）

### Shared References
- `.claude/skills/shared-references/cross-model-review.md`（Phase 2 创建，Review LLM 独立性原则）
