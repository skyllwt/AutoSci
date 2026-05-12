---
description: 从已撰写的论文生成学术海报 —— 提炼章节为单页 HTML 海报,包含配图和段落间过渡
argument-hint: "[paper-dir] [--review] [--anonymous] [--max-sections N] [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked] [--no-logos]"
---

# /poster

> 从已撰写的论文生成学术 HTML 海报。读取 `paper/main.tex`、章节文件与图片;
> 构建 PaperX 兼容的 `dag.json` 中间格式;将每个章节提炼为 2–5 句话摘要;
> 选取代表性配图;渲染为自包含的 HTML 海报(三栏自适应布局)。

## Inputs

- `paper_dir`(可选,默认 `paper/`):LaTeX 项目目录,需包含 `main.tex` 和 `sections/`
- `--review`(可选):调用 Review LLM 对生成的海报内容进行跨模型评审
- `--anonymous`(可选):强制将作者写为 "Anonymous",忽略 `\author{}` 的实际内容
- `--max-sections N`(可选,默认 6):海报最多包含的章节数
- `--venue STR`(可选):海报右上方显示的会议/期刊文本(例如 `"NeurIPS 2026"`);若不提供,会交互式询问
- `--affiliation-logo PATH`(可选):单位/实验室 logo 文件路径(PNG/JPG/PDF),会被复制到 `poster/images/`
- `--conference-logo PATH`(可选):会议/期刊 logo 文件路径(PNG/JPG/PDF),会被复制到 `poster/images/`
- `--layout corners|stacked`(可选,默认 `corners`):header 布局。`corners` 把单位 logo 放在左上、会议 logo 放在右上;`stacked` 把两个 logo 都叠在右侧 `.conf` 区,venue 文本在最上
- `--no-logos`(可选):跳过所有 logo 询问,header 只显示 venue 文本

## Outputs

- `poster/dag.json` —— PaperX 兼容的中间格式(未来可被 `/slides`、`/pr` 复用)
- `poster/outline.html` —— 模板注入前的 `<section>` 块拼接结果
- `poster/poster.html` —— 最终自包含的 HTML 海报(浏览器打开即可)
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

1. **Venue 文本** —— 若未传入 `--venue`:
   - 询问:*"海报 header 要显示什么 venue 文本?例如 `NeurIPS 2026`。回复文本,或回复 `skip` 留空。"*
   - 把下一条用户消息原文取作 venue。`skip`(不区分大小写)视为空。

2. **单位/实验室 logo** —— 若未传入 `--affiliation-logo` 且未传入 `--no-logos`:
   - 用 `AskUserQuestion` 询问,选项:`"Yes, I have a logo file"` / `"No, skip the affiliation logo"`。
   - 若选 yes:询问 *"单位 logo 文件路径?(PNG / JPG / PDF;相对路径或绝对路径都可以)"*。把下一条用户消息当作路径。校验文件存在;若不存在,提示错误后再询问一次,仍失败则按 skip 处理。

3. **会议/期刊 logo** —— 若未传入 `--conference-logo` 且未传入 `--no-logos`:
   - 流程同上(yes/no 用 `AskUserQuestion`,路径自由文本)。

4. **布局** —— 若至少一个 logo 被提供,且未传入 `--layout`:
   - 用 `AskUserQuestion` 询问,选项:
     - `"corners —— 单位 logo 左上、会议 logo 右上"`(Recommended)
     - `"stacked —— 两个 logo 叠在右侧 conf 区,venue 文本在上方"`
   - 若只有 venue 没有 logo:跳过布局询问(默认 `corners` 即可,只用 venue 文本槽)。

5. **配置摘要** —— 打印一行:
   - `Header config: venue='{...}', affiliation={path|none}, conference={path|none}, layout={...}`

这些值在 Step 5 通过 `python3 tools/poster.py inject-header` 应用。

### Step 1: 构建 dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

若用户传入 `--anonymous`,在命令上加 `--anonymous`。

桥接工具生成三类节点:
- **Root**(`level: 0`):`name` 为论文标题,`content` 为作者,`edge` 为按顺序排列的章节名
- **Section**(`level: 1`):`name` 为章节标题,`content` 为完整正文,`visual_node` 为该章节引用的图片
- **Visual**(`level: 2`):`name` 为 markdown 图片引用,`content` 为 caption,`resolution` 为 `WxH`

### Step 2: 编译 WIKI_CONTEXT(可选)

若 `wiki/outputs/paper-plan-*.md` 存在,读取:
- venue 名称(用于 Step 5 的 `inject-header`,当用户未显式提供时作为默认值)
- 叙事弧线与证据图
- 关联的 idea slug 列表

对每个 idea slug,读取 `wiki/ideas/<slug>.md` 的假设(hypothesis)与新颖性论证;对关联的 `wiki/experiments/*.md`,读取 `outcome` 与 `key_result` 字段。把这些信息按章节聚合成一个 `WIKI_CONTEXT` 字符串:

```
[INTRODUCTION]
hypothesis: <来自 idea 的一句话>
novelty: <来自 idea 的一句话>

[EXPERIMENTS]
key_result: <来自 experiments 的关键数值>
outcome: <一句话总结>
```

此字符串通过 Step 3 提示词中的 `{WIKI_CONTEXT}` 槽位传入。若无 wiki 上下文,该槽位留空 —— 提示词显式允许此情况。

### Step 3: 选择并提炼海报章节

加载 `poster/dag.json`。跳过 root 与所有 visual 节点,只遍历 section 节点。

按以下优先级选取最多 `--max-sections` 个章节(默认 6):
1. **Introduction**(摘要或第一节)
2. **Method**(方法/方案章节)
3. **主要结果**(Experiments / Replication / 主结果章节)
4. **次要结果 / 消融**(空间允许时)
5. **分析 / 讨论**(一个核心 insight)
6. **Conclusion**(简短结论)

对每个选中的章节,选取最佳配图:从该章节的 `visual_node` 列表中,挑选 `resolution`(W×H 面积)最大的视觉节点。若章节没有 visual,则该 section 无图。

对每个选中的章节,先准备以下变量供提示词使用:

- `SECTION_JSON`:从 `poster/dag.json` 取该 section 节点,**去掉** `visual_node` 字段(visual 单独传入)。只保留 `name`, `content`, `level`。
- `HAS_VISUAL`:有分配 visual 时为 `true`,否则 `false`。
- `IMAGE_SRC`:例如 `images/layer_curves.png`,来自选中 visual 节点的 `name`(去掉 `![](...)` 外壳)。无 visual 时为空字符串。
- `ALT_TEXT`:选中 visual 节点的 `content`(caption)。无 visual 时为空。
- `WIKI_CONTEXT`(可选):Step 2 编译出的字符串。无 wiki 上下文时为空字符串。

调用如下提示词(逐字移植自 PaperX `poster_outline_prompt`,加入 `WIKI_CONTEXT` 扩展):

> You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON you see has NO `visual_node` field and must be treated as authoritative.
>
> SECTION_JSON:
> {SECTION_JSON}
>
> HAS_VISUAL: {HAS_VISUAL}
>
> If HAS_VISUAL is true, you are also given IMAGE_SRC and ALT_TEXT. The visual content MUST ONLY come from this provided IMAGE_SRC (do not invent or substitute any other image).
>
> IMAGE_SRC: {IMAGE_SRC}
> ALT_TEXT: {ALT_TEXT}
>
> WIKI_CONTEXT (optional, may be empty — use it ONLY to ground concrete numbers/claims, never to invent content not in the section):
> {WIKI_CONTEXT}
>
> **Task**:
> 1. Write ONE concise paragraph summarizing ONLY the section's content for a scientific poster. Constraints: 2–5 sentences, factual, non-hallucinatory, no bullet lists, avoid starting with "This section". The summary must contain no more than 40 words and be written with strong logical coherence and smooth transitions to minimize perplexity.
> 2. Output EXACTLY ONE HTML section block in the required template below. Output ONLY the HTML and nothing else.
>
> **Strict output rules**:
> - Output only ONE `<section class="section">...</section>` block.
> - Do NOT add markdown fences, explanations, or extra text.
> - The `<div class="section-bar">` must be the section title (use `SECTION_JSON.name`).
> - Replace the sample paragraph with your summary.
> - If HAS_VISUAL is true AND IMAGE_SRC is non-empty, include exactly one `<div class="img-section">` with one `<img>` whose `src` is exactly `IMAGE_SRC` and `alt` is `ALT_TEXT`.
> - If HAS_VISUAL is false OR IMAGE_SRC is empty, do NOT output any `<div class="img-section">` or `<img>` tag.
>
> **Required HTML template**(包含 img-section 变体):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRC" alt="ALT_TEXT" class="figure" />
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
  poster/poster.html
```

`--anonymous` 已在 Step 1(`wiki2dag.py`)生效 —— `dag.json` 中的标题/作者已是最终值,`inject-title` 仅读取。

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
- 嵌入配图:{M}
- PDF→PNG 转换:{K}
- Header:venue='{venue}', affiliation={path|none}, conference={path|none}, layout={corners|stacked}
- Review LLM:{已调用 / 已跳过}

## 输出
- poster/poster.html ← 浏览器打开
- poster/dag.json(中间产物,可被 /slides /pr 复用)

## 备注
- {警告项,如缺失图片、选中章节等}
```

## Constraints

- **不修改 `paper/`**:本 skill 对论文源是只读的,所有输出写入 `poster/`。
- **不创建 wiki 实体或图边**:海报是展示产物,不进知识图。
- **复用已编译图**:不重新执行 `paper/figures/plot_*.py`,用户已运行过 `/paper-compile`。
- **遵循 `--anonymous`**:开启时,作者在 `dag.json` 与海报 header 中都写为 "Anonymous"。
- **章节数上限**:硬上限 `--max-sections`(默认 6),保证 1400×900 下可读。
- **40 词摘要**:按 poster_outline_prompt,每章正文段在加过渡句前不超过 40 词。
- **强制去 AI 风格化**:按 `shared-references/academic-writing.md`。避开 "In this work" / "We propose" / "Our approach" 等签名开头,把 "leverage" 换成 "use","delve" 换成 "examine"。
- **严格模板注入**:`tools/poster.py build` 仅注入到 `<div class="flow" id="flow">...</div>` 之间,不修改模板的 CSS 与 fit 算法。

## Error Handling

- **`paper/main.tex` 不存在**:报错并提示 "先运行 /paper-draft 生成论文"。
- **`\input{sections/...}` 未找到章节**:列出搜索过的路径,提示检查 `main.tex` 是否使用了非标准的 section include。
- **没有图片引用**:文本-only 章节继续渲染;在 POSTER_REPORT 中给出警告。
- **`pdftoppm` 未安装**:PDF 图无法转 PNG;提示 `brew install poppler`(macOS)或 `apt install poppler-utils`(Linux)。海报仍能渲染但这些图会显示为 broken img。
- **嵌套图路径**(如 `paper/figures/exp1/foo.pdf`):桥接工具会扁平化为 `images/foo.png`,且图片解析只在 `paper/figures/` 顶层查找。若多个图片跨子目录同名,后者会覆盖前者。当前仅支持扁平的 `paper/figures/` 布局。
- **`PIL`/Pillow 未安装**:图片分辨率无法计算,`dag.json` 的 visuals `resolution` 为空;poster_outline_prompt 的 "最高分辨率优先" 规则失效,Claude 按章节顺序选图。提示 `pip install Pillow`。
- **validate 失败**:把所有问题写入 stderr,不删除已有输出。用户改正 outline 后从 Step 5 继续。
- **Review LLM 不可用**:跳过 Step 6,在报告中标注,继续。

## Dependencies

### Tools(via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous]` —— 构建 dag.json
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` —— 注入 outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous]` —— 写入标题/作者
- `python3 tools/poster.py inject-header <poster.html> [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked]` —— venue 文本 + 可选 logo
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` —— 复制/转换图片
- `python3 tools/poster.py validate <poster.html>` —— 健康检查
- `python3 tools/research_wiki.py log wiki/ "<message>"` —— 追加日志
- `pdftoppm`(poppler)—— PDF → PNG @ 200 DPI
- `pdfinfo`(poppler)—— PDF 页面尺寸,用于 resolution

### MCP Servers
- `mcp__llm-review__chat` —— 可选的跨模型评审(`--review`)

### Claude Code Native
- `Read` —— 读 .tex / dag.json / outline.html
- `Write` —— 写 outline.html
- `Edit` —— 给 outline.html 注入过渡句
- `Bash` —— 调用 wiki2dag / poster / research_wiki

### Shared References
- `.claude/skills/shared-references/academic-writing.md` —— 去 AI 风格化规则
- `.claude/skills/shared-references/cross-model-review.md` —— Review LLM 协议(`--review` 时)

### Called by
- 用户手动调用
- 未来:`/research` Stage 5b(`/paper-compile` 之后)
