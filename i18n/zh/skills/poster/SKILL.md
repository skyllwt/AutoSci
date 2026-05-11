---
description: 从已撰写的论文生成学术海报 —— 提炼章节为单页 HTML 海报,包含配图和段落间过渡
argument-hint: "[paper-dir] [--review] [--anonymous] [--max-sections N]"
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

### Step 1: 构建 dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

若用户传入 `--anonymous`,在命令上加 `--anonymous`。

桥接工具生成三类节点:
- **Root**(`level: 0`):`name` 为论文标题,`content` 为作者,`edge` 为按顺序排列的章节名
- **Section**(`level: 1`):`name` 为章节标题,`content` 为完整正文,`visual_node` 为该章节引用的图片
- **Visual**(`level: 2`):`name` 为 markdown 图片引用,`content` 为 caption,`resolution` 为 `WxH`

### Step 2: 读取可选 wiki 上下文

若 `wiki/outputs/paper-plan-*.md` 存在,读取:
- venue 名称(用于海报右上角徽章)
- 叙事弧线与证据图
- 关联的 idea slug 列表

对每个 idea slug,读取 `wiki/ideas/<slug>.md` 取假设陈述与新颖性论证;读取关联的 `wiki/experiments/*.md` 取结果数值。这些信息为 Step 3 的提炼提供更丰富的上下文,但不是必须的。

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

对每个章节,使用以下提示词生成**唯一**一个 `<section class="section">` HTML 块(改写自 PaperX,Claude 直接执行此提示):

> **Prompt**: You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON has NO `visual_node` field and must be treated as authoritative.
>
> If a visual is available, you are also given IMAGE_SRC (e.g. `images/foo.png`) and ALT_TEXT (the caption).
>
> **Task**:
> 1. Write ONE concise paragraph summarizing ONLY the section's content for a scientific poster. Constraints: 2–5 sentences, factual, non-hallucinatory, no bullet lists, avoid starting with "This section". The summary must contain no more than 40 words and be written with strong logical coherence to minimize perplexity.
> 2. Output EXACTLY ONE HTML section block in the required template below. Output ONLY the HTML and nothing else.
>
> **Strict output rules**:
> - Output only ONE `<section class="section">...</section>` block.
> - Do NOT add markdown fences, explanations, or extra text.
> - The `<div class="section-bar">` must be the section title.
> - Replace the sample paragraph with your summary.
> - If a visual is provided AND IMAGE_SRC is non-empty, include exactly one `<div class="img-section">` with one `<img>` whose `src` is exactly IMAGE_SRC and `alt` is ALT_TEXT.
> - If no visual, do NOT output any img-section or img tag.
>
> **Required HTML template**:
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

按 `shared-references/academic-writing.md` 做去 AI 风格化(变换句首、避免 "leverage"/"comprehensive"/"delve" 等 AI 签名词)。从 `wiki/experiments/<slug>.md` 拉取关键数值,让结果具体可信。

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

若用户传入 `--anonymous`,在 inject-title 命令上加 `--anonymous`。

```bash
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
# Poster Report

## Source
- Paper: {title}
- Authors: {authors}
- Paper directory: {paper_dir}

## Generation
- Sections included: {N}/{total available}
- Figures embedded: {M}
- PDF→PNG conversions: {K}
- Review LLM: {invoked / skipped}

## Output
- poster/poster.html ← 浏览器打开
- poster/dag.json(中间产物,可被 /slides /pr 复用)

## Notes
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
- **`PIL`/Pillow 未安装**:图片分辨率无法计算,`dag.json` 的 visuals `resolution` 为空;poster_outline_prompt 的 "最高分辨率优先" 规则失效,Claude 按章节顺序选图。提示 `pip install Pillow`。
- **validate 失败**:把所有问题写入 stderr,不删除已有输出。用户改正 outline 后从 Step 5 继续。
- **Review LLM 不可用**:跳过 Step 6,在报告中标注,继续。

## Dependencies

### Tools(via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous]` —— 构建 dag.json
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` —— 注入 outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous]` —— 写入标题/作者
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
