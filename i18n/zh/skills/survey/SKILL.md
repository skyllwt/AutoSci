---
description: 从 wiki 知识生成论文 Related Work 章节：主题分组 → 叙事结构 → LaTeX 输出，遵循 citation-verification 和 academic-writing
argument-hint: <research-question-or-idea-slugs> [--format latex|markdown] [--max-papers 30]
---

# /survey

> 基于 wiki 已有知识，生成可直接用于论文的 Related Work 章节。
> 从 wiki/papers/、concepts/、topics/ 取材，按研究方向分组（非逐篇罗列），
> 每组以「与本文的区别」收尾。引用遵循 citation-verification.md，
> 写作遵循 academic-writing.md 的 Related Work 规则。
> 支持 LaTeX 和 Markdown 两种输出格式。

## Inputs

- `query`：以下之一：
  - 研究问题描述（自由文本，如 "parameter-efficient fine-tuning for LLMs"）
  - idea slugs 列表（从 wiki/ideas/ 中，用于围绕特定 ideas 组织相关工作）
  - PAPER_PLAN.md 路径（从中提取 Related Work section 定义）
- `--format`（可选，默认 `latex`）：输出格式
  - `latex`：`\cite{key}` 引用，可直接嵌入论文
  - `markdown`：`[[slug]]` wikilink 引用，用于 wiki 存档
- `--max-papers`（可选，默认 30）：最多引用的论文数量

## Outputs

- `wiki/outputs/related-work-{slug}-{date}.md` — Related Work 文本（归档）
- `wiki/graph/edges.jsonl` — derived_from 边（若新建 output）
- `wiki/log.md` — 追加日志
- **终端输出** — Related Work 正文（方便直接复制）

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — Problem & Context、Key idea、Experiment & Results、Related、My take
- `wiki/concepts/*.md` — Definition、Variants、Comparison、Known limitations
- `wiki/topics/*.md` — Overview、Timeline、Open problems、Seminal works
- `wiki/ideas/*.md` — Hypothesis、Motivation、origin_gaps（若输入为 idea slugs）
- `wiki/methods/*.md` — Mechanism、Procedure、source_papers（idea 引用的可复用方法）
- `wiki/index.md` — 内容目录，按 importance 筛选
- `wiki/graph/context_brief.md` — 全局上下文
- `wiki/graph/edges.jsonl` — 论文间语义关系（same_problem_as、similar_method_to、builds_on、challenges）
- `.claude/skills/shared-references/academic-writing.md` — Related Work 写作规则
- `.claude/skills/shared-references/citation-verification.md` — 引用纪律

### Writes
- `wiki/outputs/related-work-{slug}-{date}.md` — 归档文件
- `wiki/graph/edges.jsonl` — derived_from 边
- `wiki/log.md` — 追加操作日志

### Graph edges created
- `derived_from`：related-work output → source papers

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 定位相关知识

1. **解析输入**：
   - 若为自由文本：提取关键词，在 wiki/index.md 中匹配 tags 和 titles
   - 若为 idea slugs：读取每个 idea 的 `origin_gaps`（concepts/topics）→ 走到 `concepts.key_papers` 与 topic 的 seminal works 收集相关论文；同时读取 idea 的 `## Approach sketch` 引用的 methods，再从 `methods.source_papers` 拉论文
   - 若为 PAPER_PLAN 路径：读取 Related Work section 的 groupings 和 citations
2. **读取 wiki/graph/context_brief.md** 获取全局上下文
3. **读取 wiki/graph/edges.jsonl**：提取论文间语义关系（same_problem_as、similar_method_to、builds_on、challenges）
4. **生成候选论文列表**：
   - 从 index.md 按 importance 降序排列
   - 按 tags 和 domain 匹配度排序
   - 限制为 `--max-papers` 篇
5. **若候选论文 < 5 篇**：警告「相关论文不足，建议先 /ingest 更多论文」

### Step 2: 精读相关页面

对候选论文列表中的每篇论文：

1. 读取 `wiki/papers/{slug}.md`：重点读 Problem & Context、Key idea、Experiment & Results、My take
2. 读取该论文关联的 `wiki/concepts/*.md`：重点读 Definition、Variants、Comparison
3. 读取相关 `wiki/topics/*.md`：重点读 Timeline、Open problems

记录每篇论文的：
- 核心贡献（一句话）
- 方法类别（属于哪个研究方向）
- 与本文的关系（same problem / similar method / builds on / challenges）
- 局限性（从 Limitations 或 My take 提取）

### Step 3: 主题分组

遵循 `shared-references/academic-writing.md` 的 Related Work 规则：

1. **按研究方向分组**（非逐篇罗列）：
   - 从 wiki/topics/ 和 concepts/ 的分类中提取自然分组
   - 每组 3-8 篇论文
   - 分组标题描述研究方向（如 "Parameter-Efficient Fine-Tuning"），非单篇论文
2. **确定组间顺序**：
   - 从宏观到具体（大方向 → 子方向 → 最相关方法）
   - 或按时间线（早期奠基 → 发展 → 最新）
3. **确定组内顺序**：
   - 按年份升序（展现演进）
   - 重要论文详写（2-3 句），次要论文简写（1 句）
4. **标注每组与本文的关系**：
   - 每组结尾一句：「Unlike these approaches, our method...」或「We build upon X by...」

### Step 4: 生成段落

遵循 `shared-references/academic-writing.md`：

1. **每组一段或两段**：
   - 开头：该方向的背景和重要性
   - 中间：按组内顺序展开每篇论文的贡献
   - 结尾：与本文的定位关系（必须有）

2. **引用格式**：
   - `--format latex`：`\cite{key}`，key 从 citation-verification.md 的命名规则生成
   - `--format markdown`：`[[slug]]`

3. **写作规范**：
   - 不写平铺列表（"X did Y. Z did W."）
   - 每段有 topic sentence
   - 使用对比连接词（"While X focuses on..., Y addresses..."）
   - 不使用 AI 特征词汇（参考 academic-writing.md de-AI 列表）

4. **De-AI polish**：
   - 扫描并替换 AI 特征词汇
   - 变化 sentence openings
   - 移除 filler sentences

### Step 5: BibTeX 准备（仅 --format latex）

若输出格式为 LaTeX，遵循 `shared-references/citation-verification.md`：

1. 收集所有 `\cite{key}` 引用
2. 对每个 key，尝试获取 BibTeX：DBLP → CrossRef → S2
3. 已验证的：记录 BibTeX
4. 未验证的：标记 `[UNCONFIRMED]`
5. 输出 BibTeX 条目列表（可追加到 paper/references.bib）
6. 报告 citation coverage

### Step 6: 归档

1. **生成 slug**：
   ```bash
   python3 tools/research_wiki.py slug "<query-keywords>"
   ```

2. **写入归档文件**：
   创建 `wiki/outputs/related-work-{slug}-{date}.md`：
   ```yaml
   ---
   title: "Related Work: {topic}"
   type: related-work
   format: {latex|markdown}
   paper_count: {N}
   date_generated: YYYY-MM-DD
   ---
   ```
   正文为完整 Related Work 文本。
   若 latex 格式：附录包含 BibTeX 条目。

3. **添加 graph edges**：
   ```bash
   # output → 每篇引用的论文
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "outputs/related-work-{slug}-{date}" --to "papers/{paper-slug}" \
     --type derived_from --evidence "Cited in related work section"
   ```

4. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "survey | {topic} | {N} papers, {G} groups, format: {format}"
   ```

5. **终端输出**：完整 Related Work 正文 + citation coverage 统计

## Constraints

- **只引用 wiki 中已有论文**：不凭空编造引用。每个 `\cite{}` 或 `[[slug]]` 必须对应 wiki/papers/ 中的页面
- **按主题分组，非逐篇列表**：每段覆盖一个研究方向，非「Paper A did X. Paper B did Y.」
- **每组必须有定位句**：与本文的关系（结尾处说明区别或继承）
- **候选论文 < 5 篇时警告**：提示用户先 /ingest 更多论文
- **BibTeX 遵循 citation-verification.md**：不从 LLM 记忆生成（仅 --format latex）
- **de-AI polish 必选**：生成后必须执行 polish pass
- **归档到 outputs/**：不直接修改 wiki 的 papers/concepts/topics 页面
- **graph edges 使用 tools/research_wiki.py**：不手动编辑 edges.jsonl

## Error Handling

- **wiki 论文不足 3 篇**：报错，建议先 /ingest 足够数量的论文
- **无匹配论文**：扩大搜索范围（放宽 tag 匹配），若仍无则报错
- **BibTeX 获取全部失败**（latex 格式）：使用 [UNCONFIRMED] 占位，报告数量
- **PAPER_PLAN 格式不匹配**：忽略 plan 的分组建议，使用自动分组
- **slug 冲突**：追加日期后缀

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — 生成 slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — 添加 graph edge
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/fetch_s2.py search "<title>"` — BibTeX fallback（S2 搜索）

### MCP Servers
- 无（survey 不需要 Review LLM，可通过 /review --focus writing 单独审查）

### Claude Code Native
- `Read` — 读取 wiki 页面
- `Glob` — 查找 ideas、methods、concepts、topics、papers
- `WebFetch` — DBLP / CrossRef BibTeX 获取（仅 --format latex）

### Shared References
- `.claude/skills/shared-references/academic-writing.md` — Related Work 写作规则 + de-AI polish
- `.claude/skills/shared-references/citation-verification.md` — BibTeX 获取和 [UNCONFIRMED] 协议

### Called by
- `/paper-draft` Step 3（Related Work section 可委托此 skill）
- 用户手动调用
