---
description: 从已撰写的论文生成学术海报 —— 提炼章节为单页 HTML 海报,包含配图和段落间过渡
argument-hint: "[paper-dir] [--review] [--anonymous] [--no-figures] [--no-logos] [--no-refine]"
---

# /poster

> 从已撰写的论文生成学术 HTML 海报。读取 `paper/main.tex`、章节文件与图片;
> 构建 PaperX 兼容的 `dag.json` 中间格式;将每个章节提炼为 2–5 句话摘要;
> 选取代表性配图;渲染为自包含的 HTML 海报(三栏自适应布局)。

## Inputs

### 常用

- `paper_dir`(可选,默认 `paper/`):LaTeX 项目目录,需包含 `main.tex` 和 `sections/`
- `--review`(可选):调用 Review LLM 对生成的海报内容进行跨模型评审
- `--anonymous`(可选):强制将作者写为 "Anonymous",忽略 `\author{}`、`paper/.author_display.txt` 缓存以及 `--authors` flag
- `--no-figures`(可选):所有章节渲染为纯文本(适合文本密集型海报,或配图尚未准备好时)
- `--no-logos`(可选):跳过 affiliation / conference logo 询问,header 只显示 venue 文本
- `--no-refine`(可选):跳过 Step 5.5 critique-revise(默认会跑 1 轮)

### 进阶(脚本化使用;交互场景一般用不到)

- `--authors STR`:覆盖海报上的作者文本(例如 `--authors "Mingtian Yang, Co-Author"`)。一次性覆盖用;日常需求由 Step 0 Q1 的 `paper/.author_display.txt` 缓存自动处理。`--anonymous` 同时传入时仍以 `--anonymous` 为准。
- `--venue STR`:header 右块的 venue 文本(例如 `"NeurIPS 2026"`)。跳过 Step 0 的 venue 询问。
- `--affiliation-logo PATH` / `--conference-logo PATH`:logo 文件路径(PNG/JPG/PDF);各自跳过 Step 0 对应的询问。
- `--layout corners|stacked`(默认 `corners`):header 布局。`corners` = 单位 logo 左上 + 会议 logo 右上;`stacked` = 两个 logo 都叠在右侧 `.conf` 区,venue 文本在最上。
- `--auto-figures`:跳过 Step 2.5 的逐章节配图询问,直接为每章选择面积最大的候选图(旧的 "largest wins" 行为)。
- `--refine-iterations N`(默认 1,硬上限 2):Step 5.5 的迭代次数。`0` 等同于 `--no-refine`。文字密集且首轮可能无法收敛时,调到 2。

## Outputs

- `poster/dag.json` —— PaperX 兼容的中间格式(未来可被 `/slides`、`/pr` 复用)
- `poster/outline.html` —— 模板注入前的 `<section>` 块拼接结果
- `poster/poster.html` —— 最终自包含的 HTML 海报(浏览器打开即可;若需 PDF:**Cmd/Ctrl+P → 另存为 PDF**,打印设置见 Step 7 报告)
- `poster/poster.png` —— 2× CSS 尺寸的渲染截图(默认 2800×1800),见 Step 5b
- `poster/images/` —— 从 `paper/figures/` 复制/转换(PDF→PNG @ 200 DPI)而来的图片
- **POSTER_REPORT**(输出到终端)
- `wiki/log.md` —— 追加日志条目

## Wiki Interaction

### Reads
- `paper/main.tex` + `paper/sections/*.tex` + `paper/figures/` —— 论文源
- `wiki/outputs/paper-plan-*.md`(可选)—— 叙事线、配图计划、证据图
- `wiki/ideas/*.md`(可选)—— 假设、新颖性论证,用于海报开头
- `wiki/experiments/*.md`(可选)—— 关键数值与结果,用于结果区 callout
- `.claude/skills/shared-references/academic-writing.md` —— 去 AI 风格化规则

### Writes
- `poster/` 目录(完整列于 Outputs)
- `wiki/log.md` —— 追加

### Graph edges created
- 无(海报是展示产物,不是知识实体)

## Workflow

**前置**:确认 `paper/main.tex` 存在。否则报错:"先运行 /paper-draft"。

### Step 0: 交互式 header 配置

目标:收集 venue 文本与(可选的)两个 logo,用于海报 header 渲染。如果用户已通过 CLI flag 传入对应值,则静默跳过该项。

整个交互流程用 `AskUserQuestion` 做是/否/布局选择,自由文本(路径与 venue)直接读取下一条用户消息。

1. **作者** —— 论文级别的元数据,按下面的优先级解析:

   1. 传入 `--authors STR` flag → 用它,不问也不持久化。
   2. 传入 `--anonymous` flag → 强制 "Anonymous",不问也不持久化。
   3. `paper/.author_display.txt` 存在 → 用文件内容,不问。这是"问一次,以后复用"的缓存。未来 `/paper-draft` 会在写作阶段填这个文件;在那之前,`/poster` Step 0 维护它(见下)。
   4. dag.json 根节点 `content` (来自 `main.tex` 的 `\author{...}`) 非空且不是字面 "Anonymous" → 用它,不问。
   5. **否则(匿名稿且没有缓存的 display name)**:问用户。

   询问流程(只在第 5 条触发时进入):
   - 用 `AskUserQuestion`,选项:
     - `"Keep 'Anonymous' (double-blind submission)"`(Recommended)
     - `"Provide author names (I'll ask for the string)"`
   - 若选 "Provide author names":自由文本询问 *"海报上应显示什么作者字符串?例如 `Mingtian Yang, Co-Author Name`。回复字符串,或回复 `skip` 保留 'Anonymous'。"* 把下一条用户消息取作 authors 字符串。
   - **把答案持久化** 到 `paper/.author_display.txt`(单行,不要末尾换行)。下一次 `/poster` 跑时文件已存在 → step 0 Q1 静默跳过。用户想改的话,自己编辑或删除这个文件。
   - 两个分支("Keep Anonymous" 或 自定义字符串)都要持久化 —— 目标是 **除非用户主动删文件,否则不再被问**。

2. **Venue 文本** —— 若未传入 `--venue`:
   - 询问:*"海报 header 要显示什么 venue 文本?例如 `NeurIPS 2026`。回复文本,或回复 `skip` 留空。"*
   - 把下一条用户消息原文取作 venue。`skip`(不区分大小写)视为空。

3. **单位/实验室 logo** —— 若未传入 `--affiliation-logo` 且未传入 `--no-logos`:
   - 用 `AskUserQuestion` 询问,选项:`"Yes, I have a logo file"` / `"No, skip the affiliation logo"`。
   - 若选 yes:询问 *"单位 logo 文件路径?(PNG / JPG / PDF;相对路径或绝对路径都可以)"*。把下一条用户消息当作路径。校验文件存在;若不存在,提示错误后再询问一次,仍失败则按 skip 处理。

4. **会议/期刊 logo** —— 若未传入 `--conference-logo` 且未传入 `--no-logos`:
   - 流程同上(yes/no 用 `AskUserQuestion`,路径自由文本)。

5. **布局** —— 若至少一个 logo 被提供,且未传入 `--layout`:
   - 用 `AskUserQuestion` 询问,选项:
     - `"corners —— 单位 logo 左上、会议 logo 右上"`(Recommended)
     - `"stacked —— 两个 logo 叠在右侧 conf 区,venue 文本在上方"`
   - 若只有 venue 没有 logo:跳过布局询问(默认 `corners` 即可,只用 venue 文本槽)。

6. **配置摘要** —— 打印一行:
   - `Header config: authors='{...}', venue='{...}', affiliation={path|none}, conference={path|none}, layout={...}`

作者字符串通过 Step 5 的 `python3 tools/poster.py inject-title --authors "..."` 应用;venue 与 logo 通过 `python3 tools/poster.py inject-header` 应用。

### Step 1: 构建 dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

若用户传入 `--anonymous`,在命令上加 `--anonymous`。

桥接工具生成三类节点:
- **Root**(`level: 0`):`name` 为论文标题,`content` 为作者,`edge` 为按顺序排列的章节名
- **Section**(`level: 1`):`name` 为章节标题,`content` 为完整正文,`visual_node` 为该章节引用的图片
- **Visual**(`level: 2`):`name` 为 markdown 图片引用,`content` 为 caption,`resolution` 为 `WxH`

`wiki2dag.py` 保留论文中的:
- **数学公式**:`$…$`、`$$…$$`、`\(…\)`、`\[…\]` 原样进入章节内容,后续由海报 HTML 中的 KaTeX 渲染。`math_commands.tex` 里的宏会被展开,残留的 `\ensuremath{X}` 包装会被解包为 `$X$`,让 KaTeX 能识别。
- **引用** —— *默认丢弃*:`\citep{key}` / `\citet{...}` 标记被剥成空。基于对 CCF-A 海报的调研,实际会场上的海报通常不在正文里渲染 `[N]` 内联标注(没地方放参考文献列表)。如果你的海报样式确实需要它们,在 `wiki2dag.py build` 上加 `--citations` flag 可以恢复为 `[N]` / `[N, M]`(按首次出现顺序的 `bibkey → ordinal`)。未来支持参考文献页脚的样式可以默认开启。
- **表格**:`\begin{table}…\end{table}` envs(包括通过 `\input{tables/foo}` 内联的)被转为活的 HTML `<table class="poster-table">` 块,booktabs caption 渲染为 `<caption>`,`\multicolumn`、`\textbf`、`\emph`、`\textit`、`\texttt` 在 cell 层处理。Step 3 的 LLM 在 `SECTION_JSON.content` 中看到这段 HTML,必须**原样**插入到 summary 段落之后(见 Step 3)。fit() 算法会与正文文字一起缩放表格字号;若表格仍然溢出,Step 5.5 的 DOM 溢出探针会发现并要求修剪。
- **TikZ 图**:`\begin{figure}` envs 中含 `\begin{tikzpicture}` 但**没有** `\includegraphics{}` 的,通过 `tools/rasterize_latex.py`(pdflatex + pdftoppm)自动光栅化到 `paper/figures/_tikz_<sec>_<label>.png`。生成的 PNG 在桥接层眼里就是普通 visual node,Step 3 完全一样处理。若同一个 figure env 里**同时**有 `\includegraphics{}`,现有流水线优先(TikZ 跳过)。光栅化失败时 stderr 告警 + 丢弃该图,其它流程继续。跨次运行缓存 —— 删除 PNG 即强制重建。

### Step 2: 编译 WIKI_CONTEXT(可选)

目标:可选地用论文自己的规划产物(假设陈述、新颖性论证、关联 ideas/experiments 的关键数值)为 Step 3 的蒸馏提示词提供锚点。**始终告知用户当前发生了什么 —— 不要静默采用。**

**检测与透明度**:

- **不存在 plan 文件**:打印一行 —— `Step 2: 在 wiki/outputs/ 未找到 paper-plan-*.md —— Step 3 将在没有 WIKI_CONTEXT 的情况下运行。` 跳到 Step 2.5。

- **存在 plan 文件**:打印一行总结找到了什么,例如 `Step 2: 找到 wiki/outputs/paper-plan-2026-05-17.md(3 个 idea,2 个 experiment)。` 然后用 `AskUserQuestion`:
  - `"Yes —— 作为 WIKI_CONTEXT 锚点采用"`(推荐)
  - `"No —— 仅基于论文源蒸馏"`

若用户选 **Yes**:读取 plan 获取 venue、叙事弧线、关联 idea slug。对每个 idea slug,读取 `wiki/ideas/<slug>.md` 的假设(hypothesis)与新颖性论证;对每个关联的 `wiki/experiments/*.md`,读取 `outcome` 与 `key_result` 字段。按章节聚合成一个 `WIKI_CONTEXT` 字符串:

```
[INTRODUCTION]
hypothesis: <来自 idea 的一句话>
novelty: <来自 idea 的一句话>

[EXPERIMENTS]
key_result: <来自 experiments 的关键数值>
outcome: <一句话总结>
```

若用户选 **No**:`WIKI_CONTEXT` 保持为空。

此字符串通过 Step 3 提示词中的 `{WIKI_CONTEXT}` 槽位传入。Step 3 提示词显式允许此槽位为空。

### Step 2.5: 配图选择

目标:决定每个被选中的章节应配哪张图(或无图)。在 `dag.json` 构建之后、LLM 提炼之前运行,使配图选择成为 Step 3 的*输入*,而不是让 LLM 猜。每张图都内联渲染在章节中;manifest 中的 ⚠ wide 标记仅作信息提示 —— 提醒比例极端的图在单列里可能被压扁,用户可以选其它图或跳过。

**章节选择**(优先级表,硬上限 6 个章节,保持 1400×900 下可读):

1. **Introduction**(摘要或第一节)
2. **Method**(方法/方案章节)
3. **主要结果**(Experiments / Replication / 主结果章节)
4. **次要结果 / 消融**(空间允许时)
5. **分析 / 讨论**(一个核心 insight)
6. **Conclusion**(简短结论)

**模式判定**:

- 传入 `--no-figures` → 模式 = `none`;所有章节渲染为纯文本,跳过所有询问。
- 传入 `--auto-figures` → 模式 = `auto`;为每章选面积最大的 visual(`resolution` 的 W×H),跳过所有询问。
- 否则 → 模式 = `interactive`,执行下面的 manifest + 询问。

**打印配图 manifest**(任何模式下都打印),示例:

```
Figure candidates per section:
  Abstract        — text only
  Introduction    — text only
  Method          — text only
  Experiments     — 2 candidates:
                    [a] layer_curves.png   2378x618  aspect 3.85  ⚠ wide
                    [b] bootstrap.png       974x612  aspect 1.59
  Discussion     — text only
  Conclusion     — text only
```

aspect 由 `resolution`(W×H)计算。⚠ wide 标记来自 dag.json 的 `wide` 字段(aspect ≥ 2.0 或 ≤ 0.5 时为 true)。

**交互流程**(仅模式 = `interactive`):

逐章节,按候选数与 wide 标记决定如何询问:

| 候选数 | Wide? | 行为 |
|---|---|---|
| 0 | — | 无图(不询问,静默) |
| 1 | any | 静默 inline 使用(manifest 已展示;若 `wide`,⚠ 标记即提示)。用户可重跑加 `--no-figures` 来移除。 |
| ≥2 | any | **询问 Q-Pick**(多选):*"Which figure(s) for {Section}?"* —— `AskUserQuestion` 配 `multiSelect: true`,选项:每个候选(标签包含 ⚠ wide 标记如适用) / `Let Claude decide (pick largest one)` / `No figure`。用户可选一张、多张或全部。 |

每次询问用 `AskUserQuestion`,选项数 ≤ 4。若某章节有 4 个以上候选,去掉 `Let Claude decide` 这一项以满足上限(用户已经在显式选了)。

**跟进:同一章节选了 ≥2 张时询问布局。** 用 `AskUserQuestion`(单选):

| 选项 | 行为 | 何时推荐 |
|---|---|---|
| `side-by-side` | 所有选中图都放进 **一个** `<div class="img-section">`;flex 布局自动水平平分宽度。 | 默认。3 列海报里最省空间。零 CSS 改动。 |
| `vertical-stack` | 每张图一个独立 `<div class="img-section">`,自上而下堆叠。每张图占满列宽。 | 单图细节重要时;但章节会很高,fit() 会更激进地缩小文字。 |
| `after-table` | 章节里**同时有** `<table class="poster-table">` 时使用,figures 横向并排,放在表格**之后**。 | 章节内容密;尊重论文阅读顺序。 |

HTML 模板已原生支持 `side-by-side` 与 `vertical-stack`(flex 布局 + 多个 `.img-section`)。`after-table` 只是放置变体,不是新 CSS 类。

所有决策做完后,打印一行汇总:

```
Figures chosen:
  Experiments → fig2.png + fig3.png (side-by-side)
  Method      → tikz_chain.png (inline)
  (其他章节:仅文字)
```

**决策记录**:用按章节显示名作 key 的内存 dict 保留选择:

```python
{
  "Experiments": {
    "figures": ["images/fig2.png", "images/fig3.png"],   # 列表,即使只 1 张
    "alts":    ["<caption fig2>",  "<caption fig3>"],    # 平行列表
    "layout":  "inline-multi-side",                       # 见下
  },
  "Method": {
    "figures": ["images/tikz_chain.png"],
    "alts":    ["<caption>"],
    "layout":  "inline",                                  # 单图场景
  },
  "Conclusion": {"figures": [], "alts": [], "layout": "none"},
  ...
}
```

`layout` 取值:
- `"none"` —— 章节仅文字,无图
- `"inline"` —— 一张图在一个 `.img-section` 中(向后兼容单图流程)
- `"inline-multi-side"` —— ≥2 张图放进**同一个** `.img-section`(flex 水平)
- `"inline-multi-stack"` —— ≥2 张图,每张一个 `.img-section`(垂直堆叠)
- `"inline-multi-after-table"` —— ≥2 张图横向并排,放在章节内容的 `<table class="poster-table">` **之后**

Step 3 会消费此 dict 填入每章节的提示词变量。

### Step 3: 提炼海报章节

加载 `poster/dag.json` 与 Step 2.5 的决策 dict。按顺序遍历被选中的章节节点。

对每个章节,准备下面提示词所需的变量。配图相关变量从 Step 2.5 的决策 dict 取,**不要**在这里重新算。

- `SECTION_JSON`:从 `poster/dag.json` 取该 section 节点,**去掉** `visual_node` 字段(visual 单独传入)。只保留 `name`, `content`, `level`。
- `LAYOUT`:`"none"` / `"inline"` / `"inline-multi-side"` / `"inline-multi-stack"` / `"inline-multi-after-table"` 之一,从 `decisions[section_name]["layout"]` 取。决定 HTML 模板分支。
- `IMAGE_SRCS`:图源列表,从 `decisions[section_name]["figures"]` 取(如 `["images/fig2.png", "images/fig3.png"]`)。`LAYOUT == "none"` 时为空列表。
- `ALT_TEXTS`:与 `IMAGE_SRCS` 一一对应的 caption 列表(`decisions[section_name]["alts"]`)。
- `WIKI_CONTEXT`(可选):Step 2 编译出的字符串(假设、新颖性、关键数值)。无 wiki 上下文时为空。

对每个章节调用下面的提示词(从 PaperX `poster_outline_prompt` 移植,扩展了 `LAYOUT` 与 `WIKI_CONTEXT`):

> You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON you see has NO `visual_node` field and must be treated as authoritative.
>
> SECTION_JSON:
> {SECTION_JSON}
>
> LAYOUT: {LAYOUT}    # one of "none" | "inline" | "inline-multi-side" | "inline-multi-stack" | "inline-multi-after-table"
>
> If LAYOUT is not "none", you are also given IMAGE_SRCS (a list of image paths) and ALT_TEXTS (parallel list of captions). The visual content MUST ONLY come from these provided sources (do not invent or substitute any other image). For single-figure layouts (`"inline"`), the lists each have length 1. For multi-figure layouts, length ≥ 2 and the order in the list is the order figures should appear in the rendered HTML (left-to-right for `*-side`, top-to-bottom for `*-stack`).
>
> IMAGE_SRCS: {IMAGE_SRCS}
> ALT_TEXTS: {ALT_TEXTS}
>
> WIKI_CONTEXT (optional, may be empty — use it ONLY to ground concrete numbers/claims, never to invent content not in the section):
> {WIKI_CONTEXT}
>
> **Task**:
> 1. Write ONE concise paragraph summarizing ONLY the section's content for a scientific poster. Constraints: 2–5 sentences, factual, non-hallucinatory, no bullet lists, avoid starting with "This section". The summary must contain no more than 40 words and be written with strong logical coherence and smooth transitions to minimize perplexity.
> 2. Output the HTML block for this section, choosing the template variant matching LAYOUT. Output ONLY the HTML and nothing else.
>
> **Strict output rules**:
> - Output only the HTML for one section (one `<section>` block).
> - Do NOT add markdown fences, explanations, or extra text.
> - The `<div class="section-bar">` must be the section title (use `SECTION_JSON.name`).
> - Replace the sample paragraph with your summary.
> - LAYOUT == `"none"`: output the section block with NO `<div class="img-section">`.
> - LAYOUT == `"inline"`: output the section block with exactly one `<div class="img-section">` containing one `<img>` whose `src` is `IMAGE_SRCS[0]` and `alt` is `ALT_TEXTS[0]`.
> - LAYOUT == `"inline-multi-side"`: output ONE `<div class="img-section">` containing all `<img>` tags in `IMAGE_SRCS` order; the template's flex layout splits them horizontally.
> - LAYOUT == `"inline-multi-stack"`: output MULTIPLE `<div class="img-section">` blocks, one per `<img>`, in `IMAGE_SRCS` order. Stacked top-to-bottom.
> - LAYOUT == `"inline-multi-after-table"`: same as `"inline-multi-side"` (one `.img-section` with all `<img>` tags) but place that `.img-section` AFTER the `<table class="poster-table">` block(s) inside `<div class="section-body">`. Useful when the section's table is the primary artifact and figures serve as visual support.
> - **TABLES**: if `SECTION_JSON.content` contains one or more `<table class="poster-table">…</table>` blocks, include EACH ONE verbatim (preserve the entire block byte-for-byte, including `<caption>`, `<thead>`, `<tbody>`, all `<tr>` / `<th>` / `<td>` tags and their attributes) inside `<div class="section-body">` AFTER your summary `<p>`. Do NOT paraphrase, restructure, or trim the table HTML. Exception — drop a table only if it is obviously too large for one column (> 5 columns AND > 6 rows) AND summarizing 2–3 key cells in prose would preserve the result; in that case, drop the table and call out the key numbers in your summary `<p>`.
>
> **Required HTML templates**(按 LAYOUT 选择对应变体):
>
> *LAYOUT = "none"*:
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline"* (single figure):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>     </div>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline-multi-side"* (≥2 figures, horizontal):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>       <!-- repeat for IMAGE_SRCS[2], etc. -->
>     </div>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline-multi-stack"* (≥2 figures, vertical):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>     </div>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>     </div>
>     <!-- one .img-section per figure -->
>   </div>
> </section>
> ```
>
> *With a table* — when `SECTION_JSON.content` contains
> `<table class="poster-table">`, insert the verbatim table block(s)
> after the summary `<p>`. Default placement order inside
> `<div class="section-body">`:
>   1. summary `<p>`
>   2. `<table class="poster-table">…</table>` (all tables, in source order)
>   3. `<div class="img-section">…</div>` (if LAYOUT requires figures)
>
> If LAYOUT is `"inline-multi-after-table"` the order is the same — the
> name is just a hint that the table is the primary artifact. Example:
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <table class="poster-table">…verbatim from SECTION_JSON.content…</table>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>     </div>
>   </div>
> </section>
> ```

按 `shared-references/academic-writing.md` 做去 AI 风格化(变换句首、避免 "leverage"/"comprehensive"/"delve" 等 AI 签名词)。从 `WIKI_CONTEXT` 拉取关键数值,让结果具体可信。

按选择顺序将所有块写入 `poster/outline.html`。

### Step 4: 添加章节间过渡句

对拼接后的 outline 应用以下提示词(改写自 PaperX):

> **Prompt**: You are given an HTML-like poster outline of multiple `<section class="section">` blocks. Each section has a title in `<div class="section-bar">` and main text in the first `<p>` inside `<div class="section-body">`.
>
> Generate one bridging sentence per section from the FIRST up to the SECOND-TO-LAST. Place each at the END of that section's first `<p>` to lead into the NEXT section's topic.
>
> **Output**: a JSON array of strings. Length = (number_of_sections − 1). The i-th string bridges section i to section i+1. Each is one sentence (12–25 words), fluent academic English, no newlines.
>
> **Patterns** to prefer:
> - When the next section introduces/elaborates/substantiates a method or idea: "To introduce / elaborate on / substantiate \<next topic\>, we next present \<next title\>."
> - When the next section is experimental: "Next, we evaluate \<subject\> to demonstrate ..." or "We then conduct experiments on \<task\> to empirically validate ..."
> - Always reference the next section's topic without introducing new technical claims.

解析返回的 JSON 数组。对每个字符串,追加到对应章节的第一个 `<p>` 末尾。最后一个章节不加过渡句。

### Step 5: 构建海报

```bash
python3 tools/poster.py build \
  --template templates/poster/poster_template.html \
  --outline poster/outline.html \
  --output poster/poster.html

python3 tools/poster.py inject-title \
  --dag poster/dag.json \
  [--authors "{Step 0 收集到的 authors 覆盖串,或 --authors flag 的值}"] \
  poster/poster.html
```

`--anonymous` 已在 Step 1(`wiki2dag.py`)生效 —— `dag.json` 中的标题/作者已是最终值,`inject-title` 默认从那里读。当论文的 `\author{}` 因双盲投稿而留空但海报需要显示真实作者时,传入 `--authors` 覆盖。同时传入 `--anonymous` 时仍以 `--anonymous` 为准。

```bash
# 应用 Step 0 收集到的 venue 与 logo。用户跳过的项就不要传对应 flag。
python3 tools/poster.py inject-header \
  --venue "{Step 0 的 venue}" \
  [--affiliation-logo {path}] \
  [--conference-logo {path}] \
  --layout {corners|stacked} \
  poster/poster.html

python3 tools/poster.py inject-figures \
  --dag poster/dag.json \
  --paper-dir paper/ \
  --poster-dir poster/

python3 tools/poster.py validate poster/poster.html
```

`inject-figures` 直接拷贝 PNG/JPG,对 PDF 源使用 `pdftoppm` 以 200 DPI 转为 PNG。`validate` 检查每个 `<img src=...>` 能解析、标题非空、章节数 ≥ 3、不存在 `TODO`/`FIXME`/`[UNCONFIRMED]` 标记。

### Step 5b: 渲染 PNG

`validate` 通过后,把 HTML 海报渲染成 PNG,供用户预览,也作为后续 Step 5.5 critique-revise 的输入:

```bash
python3 tools/poster.py render poster/poster.html
```

产出 `poster/poster.png`,默认 2× CSS 像素(2800×1800)。用 `--scale {1,2,3}` 覆盖(1 = 快速预览,3 = 印刷质量)。

**渲染引擎**:优先 Playwright(Chromium),其次是系统浏览器的子进程兜底。Playwright 之所以首选,是因为它在截图前**等到特定事件触发**——`document.fonts.ready`、所有 `<img>` `load` 事件、`flow.scrollWidth` 连续 10 帧不变(即 fit() 收敛)。子进程路径用 `--virtual-time-budget=5000` 这种 wall-clock 超时,在 CDN 慢响应时可能在 Google Fonts / KaTeX 加载前就截图。这正是 PaperX 用的等待语义。

**安装 Playwright**(一次性,推荐):`pip install playwright && python -m playwright install chromium`。即使不装,`render` 也能走子进程路径;输出里会显示 `browser: chromium`(子进程)或 `browser: playwright-chromium`(首选)。

**子进程兜底的浏览器探测**:Chrome → Edge → Chromium → Firefox(最后兜底)。Chrome/Edge/Chromium 三者等价(同引擎、同 CLI flag)。Firefox 也能用,但有两个限制 —— 不支持 HiDPI 缩放(无论 `--scale` 传什么,PNG 都是 1×);也没有 `--virtual-time-budget` 等价物。退化到 Firefox 时 `render` 会向 stderr 打印警告。

**不支持 Safari** —— Safari 没有 headless CLI 截图 flag;接入需要 `safaridriver` + Selenium WebDriver。macOS 上只有 Safari 的用户可以 `brew install --cask google-chrome`(一行命令)解锁完整流程。

若找不到任何支持的浏览器,`render` 以平台对应的安装提示退出。HTML 海报本身在任何浏览器里都能打开 —— 用户依然可以 `open poster/poster.html`。

### Step 5.5: Critique-revise(截图 + DOM 溢出报告双驱动)

目标:用**程序化的溢出报告**(从渲染后的 DOM 取的 ground truth)结合**截图**(视觉上下文)来修订 HTML。DOM 报告是 fit() 和 LLM 都可能漏看的东西 —— 它精确测量每个叶子元素的 bottom / right 与 flow 边缘的差,精确报出任何 clipping。LLM **不能**在报告显示 clipping 的情况下声明收敛,必须修剪文字直到报告 ok。

自动应用,无用户交互。

**跳过条件**:
- 传入 `--no-refine` → 完全跳过。
- `--refine-iterations 0` → 等同 `--no-refine`。
- Step 5b 没产出 `poster/poster.png`(无可用 headless 浏览器)→ 警告后跳过。

**迭代次数**:由 `--refine-iterations N` 决定(默认 1,硬上限 2)。注意:收敛不再只看文字稳定,而是依赖溢出报告 —— 见下面的终止条件。

**单轮迭代流程**(i = 1..N):

1. 确保 `poster/poster.png` 反映当前 `poster/poster.html`。若 HTML 自上次渲染后有改动,重跑 `python3 tools/poster.py render poster/poster.html`。
2. 运行 `python3 tools/poster.py check-overflow poster/poster.html --output raw/tmp/poster.overflow.json`(scratch 路径 —— `poster/` 里只放最终产物)。读取该 JSON。
3. **提前收敛(仅溢出报告路径)**:若 `i == 1` 且 `overflow.ok == true`,且认真比对截图后没看到任何明显的 LaTeX / 编码 / 编号问题(对自己应用下面 refinement 提示词里的强制 checklist),**可以**在这里就声明收敛:记录 `"converged after 0 iterations — DOM clean, no visible content issues"` 并退出。如果有**任何**疑虑就不要走这条捷径 —— 跑一轮 refinement 的成本远小于交付一张细节有问题的海报。
4. 在内存里快照 `pre_html = <当前 poster.html>` —— 用于后面的文字稳定性判定。
5. 读取 `poster/poster.png`(多模态)、`poster/poster.html`、以及 `raw/tmp/poster.overflow.json`(ground truth 的 clipping 报告)。
6. 应用下面的 refinement 提示词。把 overflow JSON 作为 prompt 的一部分传入 —— LLM 凭它**精确**知道哪些章节要 trim,而不是从截图里猜。用 Claude(会话内,已多模态)。**不要**用 `mcp__llm-review__chat`,它按 `mcp-servers/llm-review/server.py` 只接受文本。
7. 解析 LLM 输出:从第一个 ```` ```html ```` 围栏代码块里提取 HTML。
8. 把修订后的 HTML 写回 `poster/poster.html`,并快照为 `post_html`。
9. 重跑 `python3 tools/poster.py validate poster/poster.html`。若 validate 失败:停止,告诉用户具体问题,HTML 保留原样。
10. 重新渲染 `poster/poster.png`。重跑 `check-overflow --output raw/tmp/poster.overflow.json` → 更新报告。
11. **收敛检查(两个条件**都满足才算收敛**)**:
    - (a) 新的 overflow 报告 `ok == true`,且
    - (b) `pre_html` 与 `post_html` 在 `.flow` 区域字符差异 < 50。
    
    都满足:声明收敛(`"converged after {i} iteration(s) — DOM clean and prose stable"`)并退出。
    
    overflow.ok 仍为 false:下一轮**必须**继续 refine;即使 prose 稳定也不能停。LLM 没 trim 够。
    
    迭代预算用尽但 overflow.ok 还是 false:停止,清晰提示("Step 5.5 跑完 N 轮但仍有 DOM clipping —— 考虑 `--refine-iterations 2`,或在 `poster/outline.html` 里手动 trim 最长那节的文字"),HTML / PNG 留着给用户人工检查。

**为什么这么设计**:上一版让 LLM 看降采样的 PNG 后凭感觉声明收敛。列边缘的细微 clipping 被漏掉。DOM 溢出报告把"clipping 的检测"从 LLM 判断里拿出来 —— 现在 clipping 是测量值,不是猜测。LLM 的活变成专门**修复**报告里标出的东西,不再兼职决定"有没有要修的"。

**Refinement 提示词**(从 PaperX `poster_refinement_prompt` 移植;新增 overflow JSON 输入 + 强制 pre-flight checklist):

> You are an expert Academic Poster Designer and Web Developer. Your task is to refine an existing HTML poster based on its visual rendering (screenshot), the current HTML code, and a structured DOM overflow report.
>
> **INPUTS**:
> 1. **Current Poster Code (HTML)** — full poster.html
> 2. **Visual Render (PNG screenshot)** — poster.png attached via Read
> 3. **DOM Overflow Report (JSON)** — output of `tools/poster.py check-overflow`. This is **ground truth** about which elements are clipped. If `clipped` is non-empty, you MUST fix each entry.
>
> **MANDATORY PRE-FLIGHT CHECKLIST** — answer BEFORE generating any HTML. Write this as a fenced ```` ```json ```` block first; then below it, output the corrected HTML in a separate ```` ```html ```` block.
>
> ```json
> {
>   "overflow_report_ok": <true|false; copy from the report's "ok" field>,
>   "clipped_count":     <integer; the length of the report's "clipped" array>,
>   "col1_bottom_ok":    <true|false; from the screenshot, is the last text line in col 1 ≥ 10 px above the .poster bottom border AND fully readable?>,
>   "col2_bottom_ok":    <true|false; same check for col 2 — pay specific attention to any figure's x-axis label>,
>   "col3_bottom_ok":    <true|false; same check for col 3>,
>   "latex_leaks":       <list of strings; raw LaTeX patterns you found, e.g. ["\\textbf{x}", "\\citep{key}"] — empty list if none>,
>   "numbering_prefixes": <list of strings; section-bars with leading "1.", "A.", etc. — empty list if none>,
>   "will_revise":       <true|false; if ANY of the above signal a problem, this MUST be true and the HTML block below MUST contain trimming/fixes>
> }
> ```
>
> If `will_revise: false`, your HTML block may be identical to the input.
>
> If `will_revise: true`, the HTML block MUST contain real edits addressing each flagged issue. **Do not output unchanged HTML claiming you fixed it** — that's the failure mode this checklist exists to prevent.
>
> **TASKS** (apply only where flagged by the checklist):
>
> **Task 1: Fix LaTeX / encoding leaks** (when `latex_leaks` non-empty)
> - Replace raw LaTeX with HTML entities or Unicode (`\\textbf{x}` → `<strong>x</strong>`, `\\citep{key}` → `[N]`, `$d_S \\ge 10$` → `d_S ≥ 10`).
>
> **Task 2: Normalize section headers** (when `numbering_prefixes` non-empty)
> - Strip leading `1.`, `2.1`, `A.`, `E.`, `- `, etc. from `<div class="section-bar">` contents.
>
> **Task 3: Fix DOM-reported clipping** (when `overflow_report_ok: false`)
> - The JSON's `clipped` array names every offending element with its `section_title`, `tag`, `bottom_overflow_px`, and a content `preview`. For each clipped element, **trim the corresponding section's prose conservatively** (drop filler words, tighten sentences) until that element fits. Never delete claims, citations, or math expressions.
>
> **Task 4: Fix screenshot-only issues** (when any `colN_bottom_ok: false`)
> - The DOM check has tolerance; visually cramped content (line right against the border) may still pass `overflow.ok: true`. If the screenshot shows this, trim the relevant column's prose by 5–15 words.
>
> **Output requirements**:
> - First, the ```` ```json ```` checklist block (mandatory).
> - Then, the ```` ```html ```` block: complete, runnable HTML.
> - Preserve the CSS, the `<script>` fit algorithm, and font-related settings exactly. Only edit content inside `<section class="section">` and the title/authors slots.
>
> **HTML poster**:
> ```html
> {full content of poster/poster.html}
> ```
>
> **DOM Overflow Report**:
> ```json
> {full content of raw/tmp/poster.overflow.json}
> ```
>
> **Screenshot**:
> *(the contents of poster/poster.png attached via the Read tool — Claude reads it as an image)*

**终止条件**:
- **收敛(首选)**:overflow.ok=true 且 prose diff < 50 字符。正常退出。
- **达到迭代上限且 overflow.ok=true**:也算正常退出。
- **达到迭代上限但 overflow.ok=false**:停止并向用户告警 —— 预算不够清除全部 clipping。建议 `--refine-iterations 2`,或在 `poster/outline.html` 里手动 trim 最长那节的文字。
- **LLM 输出缺 JSON checklist 块** → 停止,告警("refinement LLM 未产出强制 pre-flight checklist"),HTML 保留原样。
- **LLM 输出缺 HTML 围栏块** → 停止,告警,HTML 保留原样。
- **修订后 validate 失败** → 停止,告诉用户具体问题,HTML 保留原样。
- **LLM 在 overflow.ok=false 的情况下声明 `will_revise: false`** → 告警("refinement LLM 忽略了 DOM clipping 报告"),若预算还有就继续下一轮,否则告警用户。

### Step 6: 可选 Review LLM 评审(`--review`)

若传入 `--review`,把海报 HTML 发给 Review LLM:

```
mcp__llm-review__chat
  system: "You are a senior researcher reviewing an academic poster.
           Evaluate: (1) Is the content hierarchy clear? (2) Are key results prominently placed?
           (3) Is each section self-contained and readable? (4) Is the visual balance good (text vs figures)?
           (5) Are transitions between sections logical? (6) Would a passerby understand the contribution in 30 seconds?"
  message: |
    ## Poster HTML
    {poster/poster.html 的完整内容}

    ## DAG
    {poster/dag.json 的完整内容}

    Review for: content completeness, text density, figure selection, narrative flow.
    Flag any section that is unclear, off-topic, or missing key context.
```

根据反馈编辑 `poster/outline.html` 并重新执行 Step 5。评审-修订循环最多 2 轮。

### Step 7: 日志与报告

```bash
python3 tools/research_wiki.py log wiki/ \
  "poster | generated poster for '{title}' | {N} sections, {M} figures | reviewed: {yes/no}"
```

打印 POSTER_REPORT:

```markdown
# 海报报告

## 来源
- 论文:{title}
- 作者:{authors}
- 论文目录:{paper_dir}

## 生成情况
- 包含章节:{N}/{可用总数}
- 配图选择模式:{interactive | auto | none}
- 嵌入配图:{M}
- PDF→PNG 转换:{K}
- Header:venue='{venue}', affiliation={path|none}, conference={path|none}, layout={corners|stacked}
- Critique-revise(Step 5.5):{k/N 轮已应用 | 第 k/N 轮收敛(无实质修改) | 已跳过(--no-refine) | 已跳过(无可用 headless 浏览器)}
- Review LLM(Step 6):{已调用 / 已跳过}

## 输出
- poster/poster.html ← 浏览器打开
- poster/poster.png ← 平面截图,2× CSS(默认 2800×1800)
- poster/dag.json(中间产物,可被 /slides /pr 复用)

## 导出 PDF
在 Chrome / Edge / Firefox 中打开 `poster/poster.html`,按 **Cmd+P**(macOS)
或 **Ctrl+P**(Win/Linux) → **另存为 PDF**。推荐打印设置:
- 方向:**横向**
- 纸张尺寸:**自定义 1400×900 px**(若不支持自定义,退回 Letter / A3 横向)
- 边距:**无**
- 缩放:**100%**(若 100% 溢出,改为"适应页面")
- 背景图形:**开启**(让蓝色 header 与 section bar 正常渲染)

## 备注
- {警告项,如缺失图片、选中章节等}
```

## Constraints

- **不修改 `paper/` 源文件**:本 skill 对 LaTeX 源(`main.tex`、`sections/*.tex`、`figures/`、`references.bib`、`math_commands.tex`)只读。`paper/` 下允许写入的只有:(a) `paper/.author_display.txt`(Step 0 作者缓存);(b) `paper/figures/_tikz_<sec>_<label>.png`(Step 1 的 TikZ 光栅化缓存,见 Step 1 "TikZ 图")。`_tikz_` 前缀标识它们是从 `paper/sections/*.tex` 派生的产物;删除安全(下次运行重建)。其它输出全部写到 `poster/`。
- **不创建 wiki 实体或图边**:海报是展示产物,不进知识图。
- **复用已编译图**:不重新执行 `paper/figures/plot_*.py`,用户已运行过 `/paper-compile`。
- **遵循 `--anonymous`**:开启时,作者在 `dag.json` 与海报 header 中都写为 "Anonymous"。
- **章节数上限**:硬上限 6 个章节,保证 1400×900 下可读。章节按 Step 2.5 的优先级表选;论文章节数超过上限时,Related Work / Background / Appendix 优先被丢弃。
- **40 词摘要**:按 poster_outline_prompt,每章正文段在加过渡句前不超过 40 词。
- **强制去 AI 风格化**:按 `shared-references/academic-writing.md`。避开 "In this work" / "We propose" / "Our approach" 等签名开头,把 "leverage" 换成 "use","delve" 换成 "examine"。
- **严格模板注入**:`tools/poster.py build` 仅注入到 `<div class="flow" id="flow">...</div>` 之间,不修改模板的 CSS 与 fit 算法。
- **配图选择默认交互**:未传入 `--auto-figures` 也未传入 `--no-figures` 时,跑 Step 2.5 manifest + 询问流程。这些 flag 按 CLAUDE.md 规则 5 归用户所有 —— 不要替用户推断;不确定时,询问用户。
- **wide 图无特殊布局**:任何图都在 `<section>` 内 inline 渲染。visual 节点上的 `wide` 字段仅作信息提示 —— 用来在 manifest 中显示 ⚠ 标记,让用户选别的图或跳过过宽/过高的图。未来的图像生成 skill 预期会在源头解决比例问题,产出适配海报的图。

## Error Handling

- **`paper/main.tex` 不存在**:报错并提示 "先运行 /paper-draft 生成论文"。
- **`\input{sections/...}` 未找到章节**:列出搜索过的路径,提示检查 `main.tex` 是否使用了非标准的 section include。
- **没有图片引用**:文本-only 章节继续渲染;在 POSTER_REPORT 中给出警告。
- **`pdftoppm` 未安装**:PDF 图无法转 PNG;提示 `brew install poppler`(macOS)或 `apt install poppler-utils`(Linux)。海报仍能渲染但这些图会显示为 broken img。
- **嵌套图路径**(如 `paper/figures/exp1/foo.pdf`):桥接工具会扁平化为 `images/foo.png`,且图片解析只在 `paper/figures/` 顶层查找。若多个图片跨子目录同名,后者会覆盖前者。当前仅支持扁平的 `paper/figures/` 布局。
- **`PIL`/Pillow 未安装**:图片分辨率无法计算,`dag.json` 的 visuals `resolution` 为空;poster_outline_prompt 的 "最高分辨率优先" 规则失效,Claude 按章节顺序选图。提示 `pip install Pillow`。
- **validate 失败**:把所有问题写入 stderr,不删除已有输出。用户改正 outline 后从 Step 5 继续。
- **`render` 找不到可用浏览器**:打印对应平台的安装提示并继续(推荐 Chrome / Edge / Chromium;Firefox 作为兜底也可)。HTML 海报仍可用,只是少了 PNG。Step 5.5 critique-revise 也会跳过(无截图可参考)。Safari 不支持(没有 headless CLI)。
- **退化到 Firefox**:`render` 会向 stderr 打印警告(不支持 HiDPI 缩放,layout 可能尚未收敛)。输出仍能用,但比 Chrome/Edge 质量低。建议用户装一个 Chromium 系浏览器以获得最佳效果。
- **Refinement 输出格式异常(Step 5.5)**:若 LLM 没返回包含合法 `<section>` 与 `<h1 class="title">` 的 ```` ```html ```` 围栏,停止迭代,HTML 保留不变,告警提示。**不要**用残缺输出覆盖 HTML。
- **Review LLM 不可用**:跳过 Step 6,在报告中标注,继续。

## Dependencies

### Tools(via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous] [--citations]` —— 构建 dag.json;`--citations` 选择性恢复内联 `[N]` 标记(默认丢弃,海报上不渲染参考文献列表)
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` —— 注入 outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous] [--authors STR]` —— 写入标题/作者;`--authors` 覆盖 dag.json 中的作者字段,适用于源论文已匿名的情况
- `python3 tools/poster.py inject-header <poster.html> [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked]` —— venue 文本 + 可选 logo
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` —— 复制/转换图片
- `python3 tools/poster.py validate <poster.html>` —— 健康检查
- `python3 tools/poster.py render <poster.html> [--scale 1|2|3] [--output PATH]` —— HTML → PNG,走 headless 浏览器(优先 Chrome / Edge / Chromium,Firefox 兜底)
- `python3 tools/poster.py check-overflow <poster.html> [--output PATH]` —— 用 Playwright 查询渲染后的 DOM,产出 poster.overflow.json。Step 5.5 用它做 ground truth。
- `python3 tools/research_wiki.py log wiki/ "<message>"` —— 追加日志
- `pdflatex`(TeX Live)—— Step 1 的 TikZ 光栅化必需;`brew install --cask mactex` / `apt install texlive-full` 安装。需要 `tikz`、`pgfplots`、`standalone`、`booktabs`、`multirow`、`array`、`xcolor`、`amsmath`、`amssymb` 等包。若未安装,figure env 中没有 `\includegraphics{}` 的 TikZ 图会被 stderr 告警 + 丢弃,其余构建继续。
- `pdftoppm`(poppler)—— PDF → PNG @ 200 DPI(用于论文 PDF 图和 TikZ 光栅化产物)
- `pdfinfo`(poppler)—— PDF 页面尺寸,用于 resolution
- Playwright + Chromium(推荐,可选)—— `pip install playwright && python -m playwright install chromium`。启用事件驱动等待(字体/图片/fit 稳定)。若未安装会自动兜底。
- 系统 headless 浏览器(兜底)—— 自动探测顺序:Google Chrome → Microsoft Edge → Chromium → Firefox。Chrome/Edge/Chromium 完全等价;Firefox 只能在 1× 尺度渲染且无 sync-wait。Safari 不支持(无 headless CLI)。

### MCP Servers
- `mcp__llm-review__chat` —— 可选的跨模型评审(`--review`)

### Claude Code Native
- `Read` —— 读 .tex / dag.json / outline.html / poster.png(多模态)
- `Write` —— 写 outline.html
- `Edit` —— 给 outline.html 注入过渡句,或在 Step 5.5 写回修订后的 HTML
- `Bash` —— 调用 wiki2dag / poster / research_wiki

### Shared References
- `.claude/skills/shared-references/academic-writing.md` —— 去 AI 风格化规则
- `.claude/skills/shared-references/cross-model-review.md` —— Review LLM 协议(`--review` 时)

### Called by
- 用户手动调用
- 未来:`/research` Stage 5b(`/paper-compile` 之后)
