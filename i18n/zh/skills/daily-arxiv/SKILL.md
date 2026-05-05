---
description: 每日从 arXiv 拉取新论文，过滤相关性，auto-ingest 高优先级论文，检测 SOTA 更新
argument-hint: "[--hours 24] [--max-ingest 5] [--dry-run]"
---

# /daily-arxiv

> 每日从 arXiv RSS 拉取新论文，基于 wiki 中的研究方向和概念自动判断相关性，
> 对高相关论文调用 /ingest 完整纳入 wiki，检测 SOTA 更新，生成 digest 日志。
> 支持 cron 调度自动执行，也可手动触发。

## Inputs

- `--hours N`：拉取最近 N 小时的论文（默认 24）
- `--max-ingest N`：单次最多 ingest 篇数（默认 5，防止 wiki 过载）
- `--dry-run`：仅生成 digest，不执行 ingest
- `--categories`：覆盖默认 arXiv 分类（默认 cs.LG cs.CV cs.CL cs.AI stat.ML）

## Outputs

- `raw/discovered/{slug}/` 或 `raw/discovered/{slug}.pdf` — 每篇 auto-ingest 论文对应的抓取原始来源
- `wiki/papers/{slug}.md` — 高相关论文页面（通过 /ingest 创建）
- 相应的 concepts/、people/、methods/ 页面（通过 /ingest 创建）
- 更新的 `wiki/topics/*.md` — SOTA tracker 标注（若检测到 SOTA 更新）
- 更新的 `wiki/graph/` — edges.jsonl, context_brief.md, open_questions.md（通过 /ingest 维护）
- 更新的 `wiki/index.md` 和 `wiki/log.md`

## Wiki Interaction

### Reads
- `wiki/topics/*.md` — 提取 Overview 关键词和 SOTA tracker，用于相关性判断和 SOTA 检测
- `wiki/concepts/*.md` — 提取 Definition 关键词，辅助相关性判断
- `wiki/index.md` — 检查论文是否已收录（按 arXiv URL 去重）
- `wiki/papers/*.md` — 检查 arxiv ID 是否已存在
- `wiki/graph/open_questions.md` — 优先 ingest 能填补知识缺口的论文

### Writes
- `wiki/papers/{slug}.md` — 通过 /ingest CREATE
- `wiki/concepts/{slug}.md` — 通过 /ingest CREATE/EDIT
- `wiki/people/{slug}.md` — 通过 /ingest CREATE/EDIT
- `wiki/methods/{slug}.md` — 通过 /ingest CREATE/EDIT（论文引入或复用的可命名方法）
- `wiki/topics/{slug}.md` — EDIT（SOTA tracker 标注）
- `wiki/graph/edges.jsonl` — 通过 /ingest APPEND
- `wiki/graph/context_brief.md` — REBUILD（最终一次）
- `wiki/graph/open_questions.md` — REBUILD（最终一次）
- `wiki/index.md` — 通过 /ingest EDIT
- `wiki/log.md` — APPEND

### Graph edges created
- 通过 /ingest 创建的所有 edges（paper → paper 关系、paper → concept、method → paper 等）

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。
设 `WIKI_ROOT=wiki/`。

### Step 1: 拉取 arXiv RSS + 热门论文

1. 运行 fetch_arxiv.py 获取新论文列表：
   ```bash
   python3 tools/fetch_arxiv.py --hours <hours> -o /tmp/arxiv_feed.json
   ```
2. 获取 DeepXiv 热门论文（过去 7 天）：
   ```bash
   python3 tools/fetch_deepxiv.py trending --days 7 --limit 20
   ```
   将热门论文合并到候选列表中（按 arxiv_id 去重），热门论文在后续评分中获得额外关注。
   **若 DeepXiv 不可用**：跳过此子步骤，仅使用 RSS 结果。
3. 解析结果，获取论文列表（title, abstract, authors, arxiv_url, arxiv_id, category）
4. **去重**：读取 `wiki/index.md`，跳过 arxiv URL 已在 wiki 中的论文。同时检查 `wiki/papers/` 目录下已有的 arxiv ID。
5. 若无新论文，直接跳到 Step 6 生成空 digest。

### Step 2: 构建相关性上下文 + DeepXiv 增强

1. 读取 `wiki/topics/*.md`，提取每个 topic 的：
   - Overview 段落中的核心关键词
   - Open problems / Research gaps 列表
   - SOTA tracker 的当前最佳结果
2. 读取 `wiki/concepts/*.md`，提取每个 concept 的：
   - Definition 段落中的关键术语
   - tags 列表
3. 读取 `wiki/graph/open_questions.md`，获取当前知识缺口列表
4. 合成一份「研究方向摘要」（≤ 2000 字符），包含：核心 topics、活跃 concepts、待填补的 gaps
5. **DeepXiv TLDR 增强**（可选）：对每篇新论文，获取 AI 摘要和关键词以提升评分质量：
   ```bash
   python3 tools/fetch_deepxiv.py brief <arxiv_id>
   ```
   使用返回的 `tldr` 和 `keywords` 补充原始 abstract，帮助 LLM 更精准判断相关性。
   **若 DeepXiv 不可用**：仅使用 RSS 原始 title + abstract 进行评分（回退到原有行为）。

### Step 3: 相关性打分

对每篇新论文，基于标题和摘要 vs 研究方向摘要，LLM 判断相关性：

| 分数 | 含义 | 处理方式 |
|------|------|----------|
| 3 | 高度相关：核心方向的重要进展 | 自动 ingest |
| 2 | 中度相关：值得关注但非核心 | 列入 digest，不自动 ingest |
| 1 | 弱相关：仅供参考 | 折叠列出 |
| 0 | 不相关 | 跳过 |

**加分规则**（可将 2 分提升至 3 分）：
- 论文直接回应 open_questions.md 中的某个知识缺口 → +1
- 论文的 benchmark 可能刷新 SOTA tracker → +1（上限 3 分）

**批量打分**：将所有论文的 title+abstract 一次性提交 LLM，按 JSON 返回分数。避免逐篇调用。

### Step 4: 自动 Ingest 高优先级论文（支持断点续传）

1. 筛选相关性 = 3 的论文，按以下优先级排序：
   - 填补 gap_map 缺口的论文优先
   - 引用量高的论文优先（若 abstract 中提到 SOTA 结果）
2. 加载 checkpoint（若存在则跳过已完成的）：
   ```bash
   python3 tools/research_wiki.py checkpoint-load wiki/ "daily-arxiv-{date}"
   ```
3. 取前 `--max-ingest` 篇（默认 5）。对每篇选中的论文：
   - 先把原始来源下载到 `raw/discovered/`：
     ```bash
     python3 tools/init_discovery.py download --raw-root raw --arxiv-id <arxiv_id> --title "<title>"
     ```
   - 把返回的 `canonical_ingest_path`（位于 `raw/discovered/`）传给 `/ingest`，不要直接传裸 arXiv URL
   - /ingest 会完成完整的 wiki 纳入流程（paper + concepts + people + methods + cross-refs + graph）
   - 每篇成功后记录 checkpoint：
     ```bash
     python3 tools/research_wiki.py checkpoint-save wiki/ "daily-arxiv-{date}" "{arxiv_id}"
     ```
   - 失败则标记并继续：
     ```bash
     python3 tools/research_wiki.py checkpoint-save wiki/ "daily-arxiv-{date}" "{arxiv_id}" --failed
     ```
4. 若 `--dry-run`，同时跳过 `raw/discovered/` 下载与实际 ingest，仅在 digest 中标记「would ingest」
5. 全部完成后清理 checkpoint：
   ```bash
   python3 tools/research_wiki.py checkpoint-clear wiki/ "daily-arxiv-{date}"
   ```

### Step 5: SOTA 检测与更新

1. 对每篇已 ingest 的论文（Step 4 产出），检查其 Results 中的 benchmark 数字
2. 将 benchmark 与 `wiki/topics/` 中对应 topic 的 `## SOTA tracker` 对比
3. 若论文结果优于当前 SOTA 记录：
   - 在对应 topic 页面的 `## SOTA tracker` 追加/更新条目：
     ```
     - **{benchmark_name}**: {score} ← [[{paper-slug}]] ({year}) [previously: {old_score}]
     ```
   - 标记该 topic 的 `sota_updated` 为今天日期
4. 若检测到 SOTA 更新，在 digest 中高亮标注

### Step 6: 生成 digest 并写入 log

1. 重建 graph 派生文件（仅当有 ingest 时）：
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

2. 追加 digest 到 `wiki/log.md`：
   ```bash
   python3 tools/research_wiki.py log wiki/ "daily-arxiv | {N_ingested} ingested, {N_relevant} relevant / {N_total} total"
   ```

3. 在 log.md 的当日条目下方追加详细 digest：
   ```markdown
   ### 高优先级（已 ingest）
   - [[paper-slug]] — {title}（{one-line insight}）

   ### 值得关注（相关性 = 2）
   - {title} — {arxiv_url} — {one-line summary}

   ### Trending This Week（来自 DeepXiv）
   - {title} — {arxiv_id} — {tweets} tweets, {views} views

   ### SOTA 更新
   - {topic}: {benchmark} 新纪录 by [[paper-slug]]

   <details>
   <summary>弱相关（{K} 篇）</summary>

   - {title} — {arxiv_url}

   </details>
   ```

### Step 7: 报告给用户

输出摘要：
- 扫描论文总数 / 去重后数量
- 各相关性等级分布
- 已 ingest 论文列表（含 slug 链接）
- SOTA 更新列表（若有）
- 建议手动 ingest 的论文（相关性 = 2 中最值得关注的 top 3）
- 下次运行时间提示

## Constraints

- **只 ingest 相关性 >= 3 的论文**：其余留给用户判断，不自动创建 wiki 页面
- **每次最多 ingest `--max-ingest` 篇**（默认 5）：防止 wiki 单次过载
- **`/daily-arxiv` 对 raw/ 严格只读，只有 auto-ingest 论文可写入 `raw/discovered/`**：不得写入 `raw/papers/`、`raw/tmp/`、`raw/notes/` 或 `raw/web/`
- **graph/ 仅通过 tools 维护**：不得手动编辑 `graph/` 下的文件
- **双向链接**：通过 /ingest 保证
- **去重必须严格**：按 arxiv_url 和 arxiv_id 双重检查
- **批量打分**：一次 LLM 调用完成所有论文打分，不逐篇调用
- **digest 保持简洁**：详情查看具体 papers 页面，digest 每条论文最多一行
- **log.md append-only**：通过 `python3 tools/research_wiki.py log` 追加

## Error Handling

- **DeepXiv API 不可用**：回退到纯 RSS 模式（原有行为）。Trending 小节从 digest 中省略，评分仅用 RSS 原始数据。在报告中注明 DeepXiv 不可用。
- **RSS 拉取失败**：报告网络错误，建议用户检查网络后重试。不修改 wiki。
- **部分 ingest 失败**：已完成的 ingest 保留，失败的论文在报告中标记，建议用户手动 `/ingest <url>`。
- **wiki 目录不存在**：提示用户先运行 `/init` 初始化。
- **空 RSS 结果**：正常情况（假期、周末论文少），生成空 digest，不报错。
- **SOTA 对比失败**：benchmark 格式不匹配时跳过，在报告中注明。

## Dependencies

### Skills（via Skill tool）
- `/ingest` — 完整的论文纳入流程（Step 4 调用）

### Tools（via Bash）
- `python3 tools/fetch_arxiv.py --hours <N> -o <path>` — 拉取 arXiv RSS
- `python3 tools/fetch_deepxiv.py trending --days 7 --limit 20` — 获取热门论文
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — 获取论文 TLDR 和关键词
- `python3 tools/init_discovery.py download --raw-root raw --arxiv-id <id> --title "<title>"` — 将选中的论文下载到 `raw/discovered/`
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建压缩上下文
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建知识缺口地图
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### External APIs
- arXiv RSS（via tools/fetch_arxiv.py）
- DeepXiv API（via tools/fetch_deepxiv.py，可选，不可用时 graceful fallback）

### Scheduling
- 可通过 CronCreate 设置每日自动执行：
  ```
  CronCreate: schedule "/daily-arxiv" daily at 08:00
  ```
