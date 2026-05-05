---
description: 对 wiki 提问，综合检索相关页面后回答，好的回答可 crystallize 回 wiki
argument-hint: <question>
---

# /ask

> 对 wiki 知识库提问。LLM 读取 context_brief.md 获取全局上下文，检索相关页面，
> 综合回答并附带引用。好的回答可以 crystallize 回 wiki——写入 outputs/、创建新的
> concept 页面，或追加到已有的 idea/method/output 笔记上，让探索成果像 ingest 一样持续积累。

## Inputs

- `question`：自然语言问题（如 "LoRA 和 Adapter 的核心区别是什么？"）
- `--crystallize`（可选）：若指定，将回答 crystallize 回 wiki（默认仅回答不写入）
- `--format`（可选）：输出格式，默认 `markdown`，可选 `table` / `timeline` / `bullets`

## Outputs

- **始终**：终端输出综合回答（含 `[[slug]]` 引用）
- **若 crystallize**：
  - `wiki/outputs/{query-slug}.md` — 查询结果页面（默认 crystallize 目标）
  - 或 `wiki/concepts/{slug}.md` — 若回答揭示了新的跨论文概念
  - 或追加到已有的 `wiki/ideas/{slug}.md` / `wiki/methods/{slug}.md` / `wiki/outputs/{slug}.md` — 若回答为已有实体补充了新发现
  - 更新的 `wiki/graph/edges.jsonl`（crystallize 产生的关系）
  - 更新的 `wiki/index.md` 和 `wiki/log.md`

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — 全局压缩上下文（ideas, gaps, failed ideas, papers, edges）
- `wiki/index.md` — 页面目录，用于定位相关页面
- `wiki/graph/open_questions.md` — 开放问题，辅助判断问题是否涉及已知知识缺口
- `wiki/papers/*.md` — 与问题相关的论文页面
- `wiki/concepts/*.md` — 与问题相关的概念页面
- `wiki/methods/*.md` — 与问题相关的 method 页面
- `wiki/topics/*.md` — 与问题相关的 topic 页面
- `wiki/people/*.md` — 若问题涉及特定研究者
- `wiki/ideas/*.md` — 若问题涉及研究想法或 failed ideas
- `wiki/experiments/*.md` — 若问题涉及实验结果
- `wiki/Summary/*.md` — 若问题涉及领域全景

### Writes（仅 crystallize 模式）
- `wiki/outputs/{query-slug}.md` — CREATE（查询结果页面）
- `wiki/concepts/{slug}.md` — CREATE（新发现概念）或 EDIT（补充已有概念）
- `wiki/ideas/{slug}.md` / `wiki/methods/{slug}.md` / `wiki/outputs/{slug}.md` — EDIT（向已有页面追加新发现）
- `wiki/graph/edges.jsonl` — APPEND（crystallize 产生的关系）
- `wiki/graph/context_brief.md` — REBUILD（若 crystallize 创建了新页面）
- `wiki/graph/open_questions.md` — REBUILD（若 crystallize 创建了新页面）
- `wiki/index.md` — EDIT（若 crystallize 创建了新页面）
- `wiki/log.md` — APPEND

### Graph edges created（仅 crystallize）
- `output → paper`: `derived_from`（回答引用的论文）
- `output → concept`: `derived_from`（回答引用的概念）
- `output → idea` / `output → method`: `derived_from`（回答引用的 idea 或 method）
- `concept → paper`: `supports`（若新概念从论文中归纳）

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。
设 `WIKI_ROOT=wiki/`。

### Step 1: 加载全局上下文

1. 读取 `wiki/graph/context_brief.md`——获取 wiki 当前知识的压缩快照（ideas, gaps, papers, edges）
2. 读取 `wiki/graph/open_questions.md`——了解已知的开放问题和知识缺口
3. 若两者都不存在，先重建：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

### Step 2: 检索相关页面

1. 读取 `wiki/index.md`，基于 question 关键词匹配相关 slugs
2. 从 context_brief.md 中提取与 question 语义相关的 ideas、methods 和 papers
3. 按相关性排序，选取 top-K 页面（K ≤ 15，避免上下文过长）
4. 读取选中页面的完整内容
5. 若 question 涉及关系（如 "X 和 Y 的区别"），额外读取 `wiki/graph/edges.jsonl` 中连接 X 和 Y 的边

### Step 3: 综合回答

1. 基于收集的页面内容，综合回答用户问题
2. 回答要求：
   - **有引用**：每个关键论断必须附带 `[[slug]]` wikilink 指向来源页面
   - **有结构**：根据 `--format` 参数组织输出（markdown / table / timeline / bullets）
   - **识别不确定性**：对 wiki 中证据不足的部分明确标注 "wiki 中尚无充分证据"
   - **标注知识缺口**：若问题触及 open_questions.md 中的已知缺口，明确指出
   - **引用 idea 状态**：涉及 idea 时注明其 `status` 和 `novelty_score`
3. 若问题超出 wiki 当前知识范围，坦诚告知并建议：
   - 需要 ingest 哪些论文来填补
   - 可能的搜索方向（arXiv 关键词、Semantic Scholar 查询）

### Step 4: 评估 crystallize 价值

1. 判断回答是否值得写回 wiki（即使用户未指定 `--crystallize`，也给出建议）
2. Crystallize 值得的信号：
   - 回答综合了多篇论文的信息，形成了新的跨论文洞察
   - 回答揭示了一个 wiki 中尚未显式记录的概念
   - 回答为已有的 idea、method 或 output 笔记补充了新发现
   - 回答回应了 open_questions.md 中的一个已知缺口
3. Crystallize 不值得的信号：
   - 回答只是复述了单一页面的内容
   - 问题是简单事实查询（如 "LoRA 是哪年发表的？"）
   - 回答主要依赖推测而非 wiki 中的证据
4. 在回答末尾附带 crystallize 建议：
   ```
   💡 Crystallize 建议：[值得/不必要] — [原因]
   ```

### Step 5: Crystallize 回 wiki（若用户确认或指定了 --crystallize）

根据回答内容选择 crystallize 目标：

**Case A — 写入 outputs/（默认）：**
1. 生成 slug：`python3 tools/research_wiki.py slug "<query-summary>"`
2. 创建 `wiki/outputs/{query-slug}.md`：
   ```yaml
   ---
   title: ""
   slug: ""
   query: ""           # 原始问题
   source_pages: []    # 回答引用的所有页面 slugs
   date_created: YYYY-MM-DD
   ---
   ```
   正文为回答内容（保留 wikilinks）
3. 为每个引用的源页面添加 graph edge：
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ --from outputs/<slug> --to papers/<source-slug> --type derived_from --evidence "query answer"
   ```

**Case B — 创建新 concept：**
1. 若回答揭示了新概念：按 CLAUDE.md concept 模板创建 `wiki/concepts/{slug}.md`
2. maturity: emerging
3. key_papers: 从回答引用中提取
4. 添加 graph edges（concept → papers）
5. 在相关 paper 页面的 `## Related` 追加反向链接

**Case C — 向已有 idea、method 或 output 笔记追加发现：**
1. 若回答扩展了与已有实体相关的发现，向对应章节追加一段（带 `[[slug]]` 引用）：
   - `wiki/ideas/{slug}.md` → `## Lessons learned` 或 `## Pilot results`
   - `wiki/methods/{slug}.md` → `## Limitations` 或 `## Tradeoff profile`
   - `wiki/outputs/{slug}.md` → 正文末尾
2. 从被修改的页面向引用的 papers/concepts/methods 添加 graph edges（`derived_from`）
3. 不创建新实体；本 case 仅丰富已有实体

### Step 6: 更新导航与图谱（仅 crystallize）

1. **index.md**：在对应分类下追加新建页面条目
2. **log.md**：
   ```bash
   python3 tools/research_wiki.py log wiki/ "ask | <question-summary> | crystallized: <target-path>"
   ```
   若未 crystallize：
   ```bash
   python3 tools/research_wiki.py log wiki/ "ask | <question-summary> | answer-only"
   ```
3. **重建 graph 派生文件**（仅 crystallize 创建了新页面时）：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

### Step 7: 报告给用户

输出摘要，包含：
- 检索的页面数量和列表
- 回答（带引用和格式）
- 知识缺口标注（若有）
- Crystallize 建议或执行结果
- 后续建议（推荐 ingest 的论文、相关的 open questions）

## Constraints

- **不得虚构**：回答必须基于 wiki 中的实际内容，不得凭 LLM 预训练知识编造
- **引用必须存在**：每个 `[[slug]]` 必须指向 wiki 中实际存在的页面
- **raw/ 只读**：不得修改 `raw/` 下的文件
- **graph/ 仅通过 tools 维护**：不得手动编辑 `graph/` 下的文件
- **Crystallize 需确认**：除非用户显式指定 `--crystallize`，否则仅建议但不执行写入
- **上下文限制**：检索页面数量 ≤ 15，避免超出上下文窗口
- **idea 状态引用**：涉及 idea 时必须注明其 `status` 和 `novelty_score`
- **gap 标注**：若问题涉及 open_questions.md 中的已知缺口，必须明确指出
- **outputs/ frontmatter 必须包含 query 和 source_pages**：确保可追溯

## Error Handling

- **context_brief.md 不存在**：运行 `python3 tools/research_wiki.py rebuild-context-brief wiki/` 重建后重试
- **wiki 为空**：告知用户先运行 `/init` 或 `/ingest` 建立知识基础
- **无相关页面匹配**：坦诚告知 wiki 中无相关内容，建议搜索和 ingest 方向
- **crystallize slug 冲突**：追加数字后缀（如 `query-result-2`）
- **index.md 不存在**：运行 `python3 tools/research_wiki.py init wiki/` 初始化后重试

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — slug 生成
- `python3 tools/research_wiki.py add-edge wiki/ --from <id> --to <id> --type <type> --evidence "<text>"` — 添加 graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建压缩上下文
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建知识缺口地图
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/research_wiki.py init wiki/` — 初始化 wiki（fallback）

### Skills（via Skill tool）
- `/ingest` — 若建议用户补充知识时引用

### Shared References
- `.claude/skills/shared-references/citation-verification.md`（Phase 3 创建）
