---
description: 用领域基础知识填充 wiki/foundations/，避免后续 /ingest 为教科书材料创建重复的 concept 页面
argument-hint: "[domain] [--add '概念名']"
---

# /prefill

> 将领域基础知识（奠基性方法、common practice、标准架构）作为稳定背景页面沉淀到 `wiki/foundations/`。
> Foundations 不再是终端节点：`grounded_in` 某 foundation 的 concept/method,以及 `contributes_to_foundation` 的 paper,都会反向写入该 foundation 的 `## Grounds concepts` / `## Grounds methods` / `## Contributed by papers` 正文区。foundation 也可带 `parent_topics`。页面保持精简 —— `/prefill` 只 seed 背景,这些反向区由 `/ingest` 和 `lint --fix` 填。

## Trigger

手动：`/prefill [domain]` 或 `/prefill --add "概念名"`。

## Inputs

- `domain`（位置参数，可选）：研究领域 — `general` / `NLP` / `CV` / `ML Systems` / `Robotics` 之一。未指定时从 `wiki/topics/` 标签推断；若 topics 为空则提示用户。
- `--add "<概念>"`：跳过 catalog，直接为单个概念建立 foundation。

## Outputs

- `wiki/foundations/{slug}.md` — 每个种子一页
- 更新的 `wiki/index.md`（由 `rebuild-index` 重生成 foundations 段落）
- `wiki/log.md` 一条记录

## Wiki Interaction

### 读取
- `wiki/topics/*.md` — 用于推断 domain（未指定时）
- `wiki/foundations/*.md` — 跳过已存在的 foundation（幂等）
- `.claude/skills/prefill/foundations-catalog.yaml` — 种子列表

### 写入
- `wiki/foundations/{slug}.md`（仅新建，从不覆盖）
- `wiki/index.md`（通过 `tools/research_wiki.py rebuild-index`）
- `wiki/log.md`（通过 `tools/research_wiki.py log`）

## Workflow

**前置条件**：当前目录包含 `wiki/`、`tools/`、`.claude/`。`WIKI_ROOT=wiki/`。

### Step 1: 确定 domain

1. 用户传入 `domain` → 直接使用。
2. 否则若处于 `--add` 模式 → 默认 `general`，除非用户额外指定。
3. 否则：读取 `wiki/topics/*.md` 的 frontmatter `tags`；若能识别出主导 domain 则用之，否则提示用户。

### Step 2: 加载种子

- **Catalog 模式**：读取 `.claude/skills/prefill/foundations-catalog.yaml`，取 `domains.{domain}` 下所有条目，并叠加 `domains.general` 的全部条目（general foundations 适用所有领域）。
- **`--add` 模式**：构造单一种子 `{slug: <slugified concept>, title: <concept>, summary: ""}`。Slug 用 `python3 tools/research_wiki.py slug "<concept>"` 生成。

对每个种子，若 `wiki/foundations/{slug}.md` 已存在则**跳过**（不覆盖、不警告）。

### Step 3: 从 Wikipedia 拉取背景

对每个剩余种子调用 `tools/fetch_wikipedia.py`：

```bash
python3 tools/fetch_wikipedia.py summary "<title>"
python3 tools/fetch_wikipedia.py sections "<title>"
python3 tools/fetch_wikipedia.py section "<title>" --index <N>   # 拉取相关章节
```

- summary 调用返回 `{title, extract, url}`。
- sections 调用返回 `[{index, line, level}, ...]` — 选取 `line` 包含 `Variants` / `Types` / `Architecture` / `History` / `Limitations` / `Applications` 的章节（大小写不敏感子串匹配）。
- 任意调用退出码为 `2` 表示**页面不存在** — 该种子回退到 LLM 知识，生成的 frontmatter 中 `source_url: ""`。

### Step 4: 组装 foundation 页面

按下方模板渲染。Wikipedia 来源的内容与 LLM 生成的内容需视觉上区分：纯 LLM 段落以 `(LLM analysis)` 标注。

```yaml
---
title: "{title}"
slug: "{slug}"
domain: "{domain}"
status: mainstream         # 已被取代的方法填 historical
aliases: []                # 列出 LLM 有把握的常见别名
first_introduced: "{Wikipedia summary 中能提取的年份，否则留空}"
date_updated: "{今天}"
source_url: "{Wikipedia URL，404 时留空}"
---

## Definition
{Wikipedia summary 首段，或 LLM 提供的定义。}

## Intuition
{基于定义的通俗解释。}

## Formal notation
{从 Wikipedia 提取的公式/记号；若无则由 LLM 补充并标注 `(LLM analysis)`。}

## Key variants
{从 Wikipedia "Variants" / "Types" / "Architecture" 章节提炼的列表。}

## Known limitations
{Wikipedia + LLM 综合判断。}

## Open problems
{LLM analysis (LLM analysis)}

## Relevance to active research
{LLM analysis (LLM analysis)}
```

每页写入 `wiki/foundations/{slug}.md`。

### Step 5: 刷新导航和日志

```bash
python3 tools/research_wiki.py rebuild-index wiki/
python3 tools/research_wiki.py log wiki/ "prefill | {N} foundations created for {domain}"
```

### Step 6: 报告

打印分组摘要：

```
## Prefill Report — {date}

**Domain**: {domain}
**Created**: {N}  **Skipped (already present)**: {M}

### mainstream
- foundations/gradient-descent — Gradient Descent
- ...

### historical
- foundations/recurrent-neural-networks — Recurrent Neural Networks
```

提醒用户：后续 `/ingest` 会与这些 foundation 去重，遇到匹配概念时创建 `[[foundation-slug]]` 链接而非新建 concept 页面。

## Constraints

- **foundation 不是 hub**：`/prefill` 只 seed 背景。唯一的外向字段是 `parent_topics`（foundation 明显归属某 topic 时设置）。不要臆造 `key_papers` / `related_concepts` 这类非 schema 字段。foundation 不再是终端节点 —— `## Grounds concepts` / `## Grounds methods` / `## Contributed by papers` 反向区已在模板里,由 `/ingest` + `lint --fix` 填,而非 `/prefill`。
- **从不覆盖**已存在的 `wiki/foundations/{slug}.md`（幂等）。
- **来源区分**：Wikipedia 内容与 LLM 内容必须在页面正文中视觉上区分。
- **catalog 是建议性的**：seed YAML 由人工维护、不完整，用户可无需改代码自行扩展。
- **仅写入 `wiki/foundations/`**：不会创建 `papers/`、`concepts/`、`topics/` 等目录下的页面。

## Error Handling

- **`wiki/foundations/` 不存在**：先运行 `python3 tools/research_wiki.py init wiki/`。
- **Wikipedia 404**：记录缺失页面，该种子回退 LLM 知识（`source_url: ""`）。
- **网络失败**：打印失败的种子，继续处理其余种子，不中断整个批次。
- **catalog 文件缺失**：报错并指向 `.claude/skills/prefill/foundations-catalog.yaml`。

## Dependencies

### 工具（通过 Bash）
- `python3 tools/fetch_wikipedia.py summary|sections|section|wikitext "<title>" [--index N]`
- `python3 tools/research_wiki.py slug "<title>"`
- `python3 tools/research_wiki.py rebuild-index wiki/`
- `python3 tools/research_wiki.py log wiki/ "<message>"`

### Catalog
- `.claude/skills/prefill/foundations-catalog.yaml`
