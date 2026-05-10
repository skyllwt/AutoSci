---
description: 扫描全 wiki 发现健康问题，生成分级修复建议报告（覆盖 runtime/schema/entities.yaml 中全部 entity 类型 + graph 一致性）
---

# /check

> 扫描全 wiki，发现结构、链接、字段、graph 的健康问题，生成分级修复建议。
> 覆盖 `runtime/schema/entities.yaml` 中声明的所有 entity 类型（papers, concepts, topics, people, ideas, experiments, methods, Summary, foundations），以及 graph edge / citation 一致性。重点检查包括：idea novelty-score 合理性、idea 失败原因完整性、experiment `linked_idea` 有效性。

## Inputs

- 全 wiki 目录（默认 `wiki/`）
- 可选：`--json` 标志（通过 tools/lint.py 输出 JSON 格式）
- 可选：`--fix` 标志（自动修复确定性问题）
- 可选：`--fix --dry-run`（预览修复但不执行）
- 可选：`--suggest` 标志（显示非自动修复问题的建议）

## Outputs

- Lint report（直接报告给用户）
- 可选写入文件：`wiki/outputs/lint-report-{date}.md`

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — 论文页面字段和链接
- `wiki/concepts/*.md` — 概念页面字段和链接
- `wiki/topics/*.md` — 方向页面字段和链接
- `wiki/people/*.md` — 人物页面字段和链接
- `wiki/ideas/*.md` — idea status、novelty_score、failure_reason、origin_gaps、target_venue
- `wiki/experiments/*.md` — experiment status、linked_idea、outcome
- `wiki/methods/*.md` — method type、source_papers、parent/child 链
- `wiki/Summary/*.md` — 综述页面字段
- `wiki/foundations/*.md` — foundations(终端 — 仅检查入链)
- `wiki/graph/edges.jsonl` — semantic graph edge 一致性检查
- `wiki/graph/citations.jsonl` — bibliographic citation 一致性检查
- `wiki/index.md` — 对照页面完整性

### Writes
- 不直接修改 wiki 内容（仅报告，除非指定 `--fix`）
- `wiki/log.md` — 通过 `tools/research_wiki.py log` 记录 lint 结果摘要

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。
设 `WIKI_ROOT=wiki/`。

### Step 1: 运行自动化 lint 工具

**默认模式（只报告）**：
```bash
python3 tools/lint.py --wiki-dir wiki/ --json
```

**自动修复模式**（用户指定 `--fix` 时）：
```bash
python3 tools/lint.py --wiki-dir wiki/ --fix --json
```
自动修复确定性问题（xref 反向链接补全、缺失字段填默认值），输出修复报告。

**预览模式**（用户指定 `--fix --dry-run` 时）：
```bash
python3 tools/lint.py --wiki-dir wiki/ --fix --dry-run --json
```
预览会修复什么，不实际执行。

解析 JSON 输出，获取所有自动检测到的 issues（及修复结果）。

### Step 2: 结构完整性（自动化覆盖）

自动化工具检查以下项目：

1. **Broken wikilinks**：`[[slug]]` 目标文件不存在
2. **Orphan pages**：无任何入链的页面
3. **必填字段缺失**（按 `runtime/schema/entities.yaml` 中声明的每种 entity）。权威源：`runtime.loader.REQUIRED_FIELDS`。当前集合：
   - papers: title, slug, tags, importance
   - concepts: title, tags, maturity, key_papers
   - topics: title, tags
   - people: name
   - methods: name, slug, type, tags
   - Summary: title, scope, key_topics
   - ideas: title, slug, status, origin, tags, priority
   - experiments: title, slug, status, linked_idea, hypothesis, tags
   - foundations: title, slug, domain, status

### Step 3: 字段值验证（自动化覆盖）

1. **Enum 值检查**（来源：`runtime.loader.VALID_VALUES`）：
   - papers.importance ∈ {1,2,3,4,5}
   - concepts.maturity ∈ {stable, active, emerging, deprecated}
   - ideas.status ∈ {proposed, in_progress, tested, validated, failed}
   - ideas.priority ∈ {1,2,3,4,5}
   - experiments.status ∈ {planned, running, completed, abandoned}
   - experiments.outcome ∈ {succeeded, failed, inconclusive}
   - methods.type ∈ {architecture, training, inference, evaluation, data, benchmark, system, optimization, prompting, protocol, other}
   - foundations.status ∈ {mainstream, historical}
2. **Idea novelty_score**（若存在）∈ [1, 5]（整数）
3. **Idea failure_reason**：status=failed 时必须非空（anti-repetition memory）
4. **Experiment linked_idea**：引用的 idea 页面必须存在

### Step 4: Cross Reference 对称性（自动化覆盖）

检查 `runtime/schema/xref.yaml` 中定义的所有双向链接规则：

| 正向链接 | 检查的反向链接 |
|----------|---------------|
| `papers ## Related → concepts` | `concepts.key_papers` 含 paper slug |
| `papers wikilink → people` | `people ## Recent work` 含 paper slug |
| `topics.key_people → people` | `people ## Research areas` 含 topic slug |
| `concepts.key_papers → papers` | `papers ## Related` 含 concept slug |
| `ideas.origin_gaps → concepts` | `concepts.linked_ideas` 含 idea slug |
| `ideas.origin_gaps → topics` | `topics.linked_ideas` 含 idea slug |
| `experiments.linked_idea → ideas` | `ideas.linked_experiments` 含 experiment slug |
| `methods.source_papers → papers` | `papers ## Related` 含 method slug |
| `methods.parent_methods ↔ methods.child_methods` | 互逆 |

### Step 5: Graph Edge 一致性（自动化覆盖）

1. **JSON 格式有效性**：每行都是合法 JSON
2. **必填字段**：每条 edge 有 from, to, type
3. **Edge type 合法性**：semantic edges 使用当前 endpoint-aware type set；旧 paper-paper / paper-concept 类型给出迁移 warning
4. **Edge confidence**：`/ingest` 写出的 paper-paper 与 paper-concept semantic edges 使用 `confidence: high|medium|low`
5. **Citation layer**：`graph/citations.jsonl` 使用 `type: cites`、合法 source/date、paper endpoints，且不写 confidence 字段
6. **Dangling nodes**：from/to 引用的 wiki 页面必须存在

### Step 6: 内容质量（LLM 辅助）

自动化工具可检测的：
1. importance=5 的论文无 concept 页引用
2. maturity=stable 的 concept 只有 1 篇 key_paper
3. topics 的 `## Open problems` 章节为空（同样标记空的 `### Known gaps` / `### Methodological gaps` 子章节）

LLM 额外判断（需要阅读内容）：
1. **Concept 近似重复检测**：扫描所有 concept 页面的 title + aliases，判断是否有语义相同/高度相似的概念对（如 "attention mechanism" 和 "self-attention"）。对疑似重复对输出合并建议。
2. **Method 近似重复检测**：在 `wiki/methods/*.md` 上做相同检测，对比 `name` + `tags` + `## Mechanism` 摘要。
3. 矛盾表述检测（不同页面对同一事实的描述不一致）
4. SOTA 记录超过 6 个月未更新
5. people 的 `## Recent work` 超过 6 个月未更新
6. Idea novelty_score 与 `## Novelty argument` 强度不匹配（低分 + 论证扎实，或高分 + 论证薄弱）
7. 高 priority idea 长期停留在 proposed 状态且无 `linked_experiments`

### Step 7: 生成报告

按优先级排序输出：

```
## Lint Report — YYYY-MM-DD

**Summary**: N 🔴, M 🟡, K 🔵

### 🔴 需立即修复
1. [file] — {issue description}

### 🟡 建议修复
1. [file] — {issue description}

### 🔵 可选优化
1. [file] — {issue description}
```

分类标准：
- **🔴 需立即修复**：broken links、missing required fields、invalid enum values、failed idea without failure_reason、invalid JSON in edges、novelty_score 越界
- **🟡 建议修复**：xref asymmetry、dangling graph edges、broken `linked_idea` 引用、unknown edge types
- **🔵 可选优化**：orphan pages、quality suggestions、empty sections

记录日志：
```bash
python3 tools/research_wiki.py log wiki/ "check | report: N 🔴, M 🟡, K 🔵"
```

## Constraints

- **默认只报告**：不带 `--fix` 时只报告不修复
- **`--fix` 仅修复确定性问题**：xref 反向链接补全、缺失字段填安全默认值。不确定的问题输出建议（`--suggest`），由用户手动批准
- **raw/ 只读**：不修改 `raw/` 下的文件
- **graph/ 只读**：lint 不修改 graph 文件，仅检查一致性
- **LLM 判断标注来源**：自动化检查和 LLM 判断在报告中明确区分
- **幂等**：多次运行产生相同结果（除非 wiki 内容变化）

## Error Handling

- **wiki/ 不存在**：报错并建议运行 `/init`
- **graph 文件不存在**：跳过缺失 graph 文件的检查，在报告中注明
- **部分目录缺失**：跳过缺失目录的检查，在报告中列出缺失目录

## Dependencies

### Tools（via Bash）
- `python3 tools/lint.py --wiki-dir wiki/ [--json] [--fix] [--dry-run] [--suggest]` — 自动化结构检查 + 修复（核心依赖）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/research_wiki.py stats wiki/` — 获取统计信息（可选，用于报告）
