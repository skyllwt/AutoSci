---
description: 从 PAPER_PLAN 起草 LaTeX 论文：逐 section 从 wiki 取材撰写 + 生成 figures/tables + BibTeX 验证 + de-AI polish
argument-hint: <paper-plan-path> [--review] [--sections <section-numbers>]
---

# /paper-draft

> 从 /paper-plan 生成的 PAPER_PLAN.md 起草完整 LaTeX 论文。
> 逐 section 撰写：每个 section 从 wiki 读取 ideas/methods/experiments/papers/concepts 取材，
> 生成 LaTeX + figures + tables。BibTeX 从 DBLP/CrossRef 获取（遵循 citation-verification），
> 完成后执行 de-AI polish（遵循 academic-writing）。
> 可选逐 section Review LLM review。输出可编译的 paper/ 目录。

## Inputs

- `plan`：PAPER_PLAN.md 的路径（如 `wiki/outputs/paper-plan-sparse-lora-2026-04-08.md`）
- `--review`（可选）：启用逐 section Review LLM review
- `--sections`（可选）：只写指定 section（如 `--sections 3,4` 只写 Method + Experiments），用于增量撰写

## Outputs

- `paper/` 目录（在 wiki 项目根下）：
  - `paper/main.tex` — 主文件（include 各 section）
  - `paper/sections/introduction.tex`
  - `paper/sections/related_work.tex`
  - `paper/sections/method.tex`
  - `paper/sections/experiments.tex`
  - `paper/sections/conclusion.tex`
  - `paper/sections/appendix.tex`（若有）
  - `paper/figures/` — 生成的 figures（PDF/PNG）
  - `paper/tables/` — 独立 table 文件（可选）
  - `paper/math_commands.tex` — 共享数学符号定义
  - `paper/references.bib` — 验证的 BibTeX 条目
- `wiki/log.md` — 追加日志

## Wiki Interaction

### Reads
- `wiki/outputs/paper-plan-*.md` — PAPER_PLAN（章节大纲、evidence map、figure plan、citation plan）
- `wiki/ideas/*.md` — Hypothesis、Novelty argument、Approach sketch、Motivation、Risks、Lessons learned
- `wiki/methods/*.md` — Mechanism、Procedure、Assumptions、Tradeoff profile（支持 Method 撰写）
- `wiki/experiments/*.md` — Results、Analysis、key_result、metrics 数据
- `wiki/papers/*.md` — Method、Results、Related（作为引用内容和 baseline 参考）
- `wiki/concepts/*.md` — Definition、Intuition、Variants、Comparison（支持 Method 撰写）
- `wiki/topics/*.md` — Overview、Timeline、SOTA tracker、Open problems（支持 Introduction 上下文）
- `wiki/people/*.md` — 人名和机构（引用格式）
- `wiki/graph/edges.jsonl` — 关系图（构建论证逻辑链）
- `wiki/graph/open_questions.md` — 已知局限（写 Limitations 和 Future Work）
- `.claude/skills/shared-references/academic-writing.md` — 写作规范
- `.claude/skills/shared-references/citation-verification.md` — 引用纪律

### Writes
- `paper/` 目录（所有文件）
- `wiki/log.md` — 追加操作日志

### Graph edges created
- 无（paper-plan 已创建 derived_from 边）

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 初始化 Paper 目录

1. 读取 PAPER_PLAN.md，提取 venue、title、section 列表
2. 若 `paper/` 目录已存在：
   - 备份为 `paper.bak-{timestamp}/`
   - 提示用户确认覆盖
3. 创建目录结构：
   ```
   paper/
   ├── main.tex
   ├── math_commands.tex
   ├── references.bib
   ├── sections/
   └── figures/
   ```
4. 从 `templates/` 复制 venue 模板（若存在）：
   - `templates/{venue}.sty` 或 `templates/{venue}/`
   - 若无模板：使用通用 article class，在 main.tex 中注明需要替换为正式模板
5. 生成 `math_commands.tex`：
   - 从 wiki/methods/（`## Mechanism`、`## Procedure`）和 wiki/concepts/（`## Definition`、`## Intuition`）收集 notation
   - 统一符号定义（向量、矩阵、集合、常用运算符）
6. 生成 `main.tex` 骨架：
   ```latex
   \documentclass{article} % 替换为 venue template
   \input{math_commands}
   % packages
   \usepackage{booktabs,graphicx,amsmath,hyperref}

   \title{<title>}
   \author{} % 匿名提交时留空

   \begin{document}
   \maketitle
   \begin{abstract}
   % Step 3 生成
   \end{abstract}
   \input{sections/introduction}
   \input{sections/related_work}
   \input{sections/method}
   \input{sections/experiments}
   \input{sections/conclusion}
   \bibliography{references}
   \bibliographystyle{plain} % 替换为 venue 要求的 style
   % \input{sections/appendix} % 取消注释如需要
   \end{document}
   ```

### Step 2: 生成 Figures 和 Tables

对 PAPER_PLAN 中 Figure Plan 的每个条目：

1. **Diagram 类型**（架构图等）：
   - 使用 TikZ 或 pgfplots 生成 LaTeX 原生图
   - 若过于复杂：生成 matplotlib Python 脚本 → 输出 PDF
   - 保存到 `paper/figures/{figure-name}.pdf`

2. **Plot 类型**(实验结果图)：
   - 从 `wiki/experiments/{slug}.md` 提取数据
   - 生成 matplotlib 脚本（遵循 academic-writing 的 figure 设计规范）：
     - Colorblind-safe palette
     - Font size >= 8pt
     - Error bars / confidence bands
     - Clear legend
   - 执行脚本生成 PDF：
     ```bash
     python3 paper/figures/plot_{name}.py
     ```
   - 保存到 `paper/figures/{figure-name}.pdf`

3. **Table 类型**：
   - 使用 booktabs 风格（toprule, midrule, bottomrule）
   - Best result bold, second-best underline
   - 直接嵌入 section .tex 文件（小表）或独立 `paper/tables/{name}.tex`（大表）

### Step 3: 逐 Section 撰写

对每个 section（按 PAPER_PLAN 的大纲顺序），若 `--sections` 指定则只写指定 section：

**3a. 收集素材**

从 PAPER_PLAN 的 section 定义中提取：
- 该 section 支撑的 ideas
- 对应的 wiki 页面列表
- 计划的 figures/tables
- 引用列表

读取所有相关 wiki 页面的对应部分：
- Introduction → wiki/ideas/{idea}.md（Hypothesis、Motivation、Novelty argument）+ wiki/topics/{topic}.md#Overview
- Related Work → wiki/papers/*.md#Related + wiki/concepts/*.md#Comparison
- Method → wiki/methods/{method}.md（## Mechanism + ## Procedure）+ wiki/concepts/{concept}.md（## Definition + ## Intuition）
- Experiments → wiki/experiments/*.md#Results + wiki/experiments/*.md#Analysis
- Conclusion → wiki/ideas/*.md#Lessons_learned + wiki/concepts/*.md#Open_problems + wiki/topics/*.md#Open_problems + wiki/graph/open_questions.md

**3b. 撰写 LaTeX**

遵循 `shared-references/academic-writing.md`：
- 按该 section 的 paragraph plan 撰写
- 插入 `\cite{key}` 引用（key 从 citation plan 映射）
- 插入 `\ref{fig:name}` / `\ref{tab:name}` 引用 figures/tables
- 使用 `math_commands.tex` 中定义的符号
- 每段以 topic sentence 开头
- Experiments section：idea-first 结构（"Our hypothesis is X. To verify, we..."）

**3c. De-AI Polish**

对每个撰写的 section 执行 de-AI polish（参照 academic-writing.md）：
1. 扫描并替换 AI 特征词汇（delve, leverage, utilize, comprehensive...）
2. 移除 excessive hedging
3. 变化 sentence openings（避免连续相同句式）
4. 移除 filler sentences（不增加信息的句子）
5. 确保 active voice 为主
6. 检查 notation consistency

**3d. 可选 Review LLM Review（--review）**

若启用 `--review`，对每个 section：

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher reviewing one section of a paper draft.
           Focus on: clarity, logical flow, idea-experiment alignment, notation consistency.
           Point out any remaining AI-sounding language patterns.
           Suggest specific rewrites for unclear passages."
  message: |
    ## Section: {section name}
    {LaTeX content}

    ## Ideas this section should support
    {ideas from the plan's idea list}

    ## Review this section for:
    1. Does it clearly support its target ideas?
    2. Is the writing clear and precise?
    3. Any AI-generated language patterns remaining?
    4. Is the notation consistent with other sections?
    5. Missing content that reviewers will expect?
```

根据 Review LLM 反馈修改 section（行内修改，不重写整个 section）。

### Step 4: 构建 Bibliography

遵循 `shared-references/citation-verification.md`：

1. 收集所有 section 中使用的 `\cite{key}` 引用
2. 对每个引用，从 PAPER_PLAN 的 citation plan 获取 BibTeX：
   - 已验证的：直接写入 `references.bib`
   - [UNCONFIRMED] 的：写入 `references.bib` 底部，带 `% [UNCONFIRMED]` 注释
3. 排除未引用的条目（不使用 `\nocite{*}`）
4. 验证 BibTeX 格式正确性（每条有 title, author, year）
5. 输出 bibliography 统计：
   ```
   references.bib: {N} entries, {M} verified, {K} [UNCONFIRMED]
   ```

### Step 5: 全文 Cross-Review

完成所有 section 后：

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher performing a final review of a complete paper draft.
           Focus on: cross-section coherence, idea-experiment thread (do the experiments back the central ideas?),
           narrative flow, notation consistency across sections, figure/table referencing.
           This is NOT a line-by-line review — focus on structural and argumentative issues."
  message: |
    ## Full Paper Draft
    {concatenated LaTeX of all sections}

    ## Evidence Map
    {from PAPER_PLAN}

    ## Review Focus
    1. Does the paper tell a coherent story from Introduction to Conclusion?
    2. Are all ideas from the plan adequately supported in the text?
    3. Is there notation inconsistency between sections?
    4. Are all figures/tables referenced and discussed?
    5. Any redundancy between sections?
    6. Overall readiness for submission (1-10)?
```

根据 Review LLM 反馈做最终调整。

### Step 6: 完成输出

1. 确认所有文件已写入 `paper/` 目录
2. 验证基本完整性：
   - 所有 `\input{sections/X}` 的文件存在
   - 所有 `\includegraphics{figures/X}` 的文件存在
   - 所有 `\cite{key}` 在 references.bib 中有对应条目
   - 所有 `\ref{label}` 有对应 `\label{label}`
3. 追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "paper-draft | drafted {venue} paper '{title}' | {N} sections, {M} figures, {K} citations ({V} verified)"
   ```
4. 输出到终端：
   ```markdown
   # Paper Write Complete

   ## Files
   - paper/main.tex (master file)
   - paper/sections/ ({N} section files)
   - paper/figures/ ({M} figure files)
   - paper/references.bib ({K} entries, {V_count} [UNCONFIRMED])
   - paper/math_commands.tex

   ## Status
   - Sections written: {list}
   - De-AI polish: applied
   - Review LLM review: {yes/no, if yes: overall score}
   - [UNCONFIRMED] citations: {count} (resolve before /paper-compile)

   ## Next Steps
   - Run `/paper-compile paper/` to compile and verify
   - Resolve [UNCONFIRMED] citations manually
   - Run `/refine paper/main.tex --focus writing` for further polish
   ```

## Constraints

- **每个 section 从 wiki 取材**：不凭空生成内容；每个技术陈述必须追溯到 wiki 页面
- **BibTeX 遵循 citation-verification.md**：从 DBLP/CrossRef/S2 获取，不从 LLM 记忆生成
- **de-AI polish 必选**：每个 section 写完后必须执行 polish pass，不可跳过
- **figures 遵循 academic-writing.md**：colorblind-safe、font size >= 8pt、vector format preferred
- **匿名提交**：不写作者名、机构、致谢（venue 匿名要求）
- **\nocite{*} 禁止**：只引用实际使用的条目
- **notation 一致性**：所有 section 使用 math_commands.tex 中的统一符号
- **已有 paper/ 目录备份后覆盖**：不直接覆盖，先备份
- **wikilink → \cite 转换**：PAPER_PLAN 中的 [[slug]] 在 LaTeX 中转换为 \cite{key}
- **tables 使用 booktabs**：不使用竖线和全网格

## Error Handling

- **PAPER_PLAN 找不到**：报错，建议先运行 /paper-plan
- **PAPER_PLAN 格式不完整**：列出缺失 section，建议重新运行 /paper-plan
- **wiki 页面找不到**（plan 引用的 idea/experiment/method/paper 不存在）：警告并跳过该引用，标注缺失
- **figure 生成失败**（matplotlib 错误）：输出占位符 `% TODO: generate figure {name}`，继续其他 section
- **BibTeX 全部获取失败**：使用 [UNCONFIRMED] 占位，在终端报告需要手动处理的数量
- **Review LLM 不可用**（--review 模式）：跳过 section review 和 cross-review，标注「unreviewed」
- **venue template 不存在**：使用通用 article class，在 main.tex 中注明
- **section 过长**（超过 plan 的 page budget）：警告，建议移至 appendix 或压缩

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/fetch_s2.py search "<title>"` — BibTeX fallback（S2 搜索）
- `python3` — 执行 matplotlib figure 脚本

### MCP Servers
- `mcp__llm-review__chat` — 逐 section review（可选，--review）+ 全文 cross-review（Step 5）

### Claude Code Native
- `Read` — 读取 wiki 页面和 PAPER_PLAN
- `Glob` — 查找 wiki 页面
- `Write` — 写入 paper/ 目录中的文件
- `Bash` — 执行 figure 脚本、创建目录
- `WebFetch` — DBLP / CrossRef BibTeX 获取

### Shared References
- `.claude/skills/shared-references/academic-writing.md` — 写作规范 + de-AI polish 规则 + figure 设计
- `.claude/skills/shared-references/citation-verification.md` — BibTeX 获取流程 + [UNCONFIRMED] 协议

### Called by
- `/research` Stage 5（论文写作阶段）
- 用户手动调用
