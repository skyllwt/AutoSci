---
description: 通用多轮迭代改进：对任意研究制品反复调用 /review → 解析反馈 → 修复 → 更新 wiki，直到达标
argument-hint: <artifact-slug-or-path> [--max-rounds N] [--target-score N] [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /refine

> 通用多轮迭代改进循环，适用于任何研究制品（idea、proposal、experiment plan、paper draft）。
> 每轮调用 /review 获取结构化反馈 → 解析 actionable items → Claude 修复制品 → 更新 wiki 实体 →
> 重新 /review，直到评分达到目标分数或达到最大轮次。
> 输出改进历史和最终 review 评分。

## Inputs

- `artifact`：要改进的制品，以下之一：
  - wiki 页面的 slug（从 ideas/experiments/methods/outputs/ 中查找）
  - 文件路径（如 `wiki/outputs/paper-draft-v1.md`）
- `--max-rounds N`（可选，默认 4）：最大迭代轮次
- `--target-score N`（可选，默认 8）：目标 review 评分（1-10），达到后停止
- `--difficulty`（可选，默认 `hard`）：传递给 /review 的难度级别
- `--focus`（可选）：传递给 /review 的审查焦点

## Outputs

- **改进后的 artifact**（wiki 页面或文件，原地更新）
- **wiki 实体更新**（若 review 发现 idea/method 需加强或 gap 被识别）
- **REFINE_REPORT**（输出到终端）：
  - 每轮的评分变化轨迹
  - 累计修复的 issues 列表
  - 最终 review 评分和 verdict
  - 未解决的 issues（若有）

## Wiki Interaction

### Reads
- `wiki/ideas/*.md` — 若 artifact 是 idea
- `wiki/experiments/*.md` — 若 artifact 是 experiment plan
- `wiki/methods/*.md` — review 引用的 methods
- `wiki/papers/*.md` — review 引用的 papers
- `wiki/outputs/*.md` — 若 artifact 是 paper draft 或 output
- `wiki/graph/context_brief.md` — 传递给 /review 的全局上下文
- `wiki/graph/open_questions.md` — 检查是否有新 gap 需要记录

### Writes
- `wiki/ideas/{slug}.md` — 若 artifact 是 idea，修复 review 发现的问题
- `wiki/experiments/{slug}.md` — 若 artifact 是 experiment plan
- `wiki/methods/{slug}.md` — 若 review 指出 method 缺口（如 source_papers 缺失、Procedure 偏弱）
- `wiki/outputs/*.md` — 若 artifact 是 paper draft 或 output
- `wiki/graph/edges.jsonl` — 若修复过程中发现新关系
- `wiki/graph/context_brief.md` — 每轮结束后重建（若 wiki 有变更）
- `wiki/graph/open_questions.md` — 每轮结束后重建（若 wiki 有变更）
- `wiki/log.md` — 追加操作日志

### Graph edges created
- 视修复内容而定，可能添加：`supports`、`addresses_gap`、`inspired_by` 等

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 初始化

1. **定位 artifact**：
   - 若为 slug：按顺序在 `wiki/ideas/`、`wiki/experiments/`、`wiki/methods/`、`wiki/outputs/`、`wiki/papers/` 中查找 `{slug}.md`
   - 若为文件路径：直接读取
   - 记录 artifact 类型和路径
2. **读取当前内容**：加载 artifact 完整文本
3. **初始化追踪变量**：
   - `round = 0`
   - `score_history = []`
   - `fixed_issues = []`
   - `unresolved_issues = []`
   - `wiki_changes = []`

### Step 2: 迭代循环

重复以下步骤，直到满足终止条件：

**Round N（N = 1, 2, ..., max-rounds）：**

#### 2a. 调用 /review

```
Skill: review
Args: "<artifact-path-or-content>" --difficulty {difficulty} --focus {focus}
```

解析 review 输出，提取：
- `score`（1-10）
- `verdict`（ready / needs-work / major-revision / rethink）
- `weaknesses`（按 severity: critical / major / minor）
- `actionable_items`（排序列表）
- `wiki_entity_mapping`（ideas/methods needing strengthening, gaps identified）

#### 2b. 检查终止条件

- **达到目标分数**：`score >= target-score` → 终止，输出最终报告
- **连续两轮评分无提升**：`score_history[-1] == score_history[-2]` → 终止（已收敛）
- **达到最大轮次**：`round >= max-rounds` → 终止
- **verdict == ready**：→ 终止
- **verdict == rethink 且 round == 1**：→ 终止并建议重新设计（不在 rethink 级别的制品上反复迭代）

#### 2c. 分类 actionable items 并修复

对每个 actionable item 进行分类和处理：

**Category A — 方法/内容问题（Claude 直接修复）：**
- 方法描述不够具体 → 补充细节
- 缺少对比分析 → 添加与 baseline 的对比
- 论证逻辑不完整 → 补充推理步骤
- 表达不清晰 → 重写相关段落
- → 直接编辑 artifact 文件

**Category B — wiki 知识缺口（建议外部操作）：**
- idea 的 novelty 论证薄弱 → 建议重新运行 `/novelty`
- method 缺少 source_papers → 标记给 `/ingest` 复查
- 缺少相关工作引用 → 建议运行 `/ingest` 补充论文
- 需要实验验证 → 建议运行 `/exp-run`
- → 记录到 `unresolved_issues`，在报告中列出建议操作

**Category C — idea / method 更新（Claude 修复 wiki）：**
- review 指出 idea 的 `origin_gaps` 缺少某个 concept 链接 → 补上链接并写入反向 `linked_ideas`
- review 发现 method 缺少 parent/child 关系 → 修补 method 页面
- review 发现新的 gap → 记录到 gap_map（通过 rebuild）
- review 发现新的关系 → 添加 graph edge
- → 更新相关 wiki 页面，记录到 `wiki_changes`

**Category D — 超出范围（跳过）：**
- 需要新实验数据 → 无法在 refine 中解决
- 需要领域专家判断 → 标记为 unresolved
- → 记录到 `unresolved_issues`

#### 2d. 更新追踪

- `score_history.append(score)`
- `fixed_issues.extend(category_A_items + category_C_items)`
- `unresolved_issues.extend(category_B_items + category_D_items)`
- `wiki_changes.extend(category_C_changes)`
- `round += 1`

#### 2e. 重建派生数据（若 wiki 有变更）

若本轮有 wiki 变更（Category C）：
```bash
python3 tools/research_wiki.py rebuild-context-brief wiki/
python3 tools/research_wiki.py rebuild-open-questions wiki/
```

### Step 3: 最终报告

迭代结束后，生成 REFINE_REPORT：

```markdown
# Refine Loop Report: {artifact title}

## Summary
- **Artifact**: {slug or path}
- **Rounds**: {N} / {max-rounds}
- **Score trajectory**: {score_history, e.g., 5 → 6 → 7 → 8}
- **Final score**: {final_score}/10
- **Final verdict**: {verdict}
- **Termination reason**: {target reached / converged / max rounds / rethink}

## Issues Fixed ({count})

| Round | Issue | Severity | Fix applied |
|-------|-------|----------|-------------|
| 1 | 方法描述不够具体 | major | 补充了具体算法步骤 |
| 1 | idea novelty 论证薄弱 | major | 已标记 [[idea-slug]] 重跑 `/novelty` |
| 2 | 缺少 ablation 设计 | minor | 添加了 ablation 计划 |

## Wiki Changes Made

| Page | Change | Round |
|------|--------|-------|
| `wiki/methods/{slug}.md` | 补全缺失的 source_papers 链接 | 1 |
| `wiki/graph/edges.jsonl` | +1 edge (addresses_gap) | 2 |

## Unresolved Issues ({count})

| Issue | Severity | Suggested action |
|-------|----------|------------------|
| 缺少实验验证 | critical | Run `/exp-design {slug}` |
| 缺少对比论文 | major | Run `/ingest` for {paper-title} |

## Next Steps
- {based on verdict and unresolved issues}
```

追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "refine | {artifact-slug} | {N} rounds | score {initial}→{final} | verdict: {verdict}"
```

## Constraints

- **每轮必须有实质进展**：若连续两轮 score 无变化，必须终止（防止无限循环）
- **rethink 不反复迭代**：若首轮 verdict == rethink，直接终止并建议重新设计
- **wiki 修改限于 review 建议**：refine 只修改 review 明确建议修改的 wiki 实体，不主动扩大修改范围
- **unresolved issues 必须列出**：不能静默跳过无法在 loop 中解决的问题
- **保留改进历史**：score_history 和 fixed_issues 完整记录，不丢弃中间状态
- **review 参数透传**：--difficulty 和 --focus 透传给 /review，保持审查标准一致
- **artifact 原地更新**：修复直接修改原始文件，不创建副本

## Error Handling

- **artifact 找不到**：提示用户检查 slug 或路径，列出可能的候选页面
- **/review 调用失败**：重试一次，若仍失败则终止 loop，输出已完成的改进历史
- **wiki 写入失败**：记录错误，继续下一轮（wiki 变更降级为 unresolved）
- **首轮 score 已 >= target-score**：直接终止，输出报告（无需改进）
- **所有 issues 都是 Category B/D**：无法在 loop 中修复，终止并输出 unresolved issues 列表

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — 重建 query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — 重建 gap_map
- `python3 tools/research_wiki.py add-edge wiki/ ...` — 添加 graph edge（若需要）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### Skills（via Skill tool）
- `/review` — 每轮审查（核心依赖）

### Claude Code Native
- `Read` — 读取 artifact 和 wiki 页面
- `Edit` — 修复 artifact 内容
- `Glob` — 查找 artifact 和相关 wiki 页面

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — 通过 /review 间接依赖
