---
description: 从已撰写的论文生成学术海报 —— 提炼章节为单页 HTML 海报,包含配图和段落间过渡
argument-hint: "[paper-dir] [--review] [--anonymous] [--authors STR] [--max-sections N] [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked] [--no-logos] [--auto-figures] [--no-figures] [--no-refine] [--refine-iterations N]"
---

# /poster

> 从已撰写的论文生成学术 HTML 海报。读取 `paper/main.tex`、章节文件与图片;
> 构建 PaperX 兼容的 `dag.json` 中间格式;将每个章节提炼为 2–5 句话摘要;
> 选取代表性配图;渲染为自包含的 HTML 海报(三栏自适应布局)。

## Inputs

- `paper_dir`(可选,默认 `paper/`):LaTeX 项目目录,需包含 `main.tex` 和 `sections/`
- `--review`(可选):调用 Review LLM 对生成的海报内容进行跨模型评审
- `--anonymous`(可选):强制将作者写为 "Anonymous",忽略 `\author{}` 的实际内容或 `--authors`
- `--authors STR`(可选):覆盖海报上的作者文本(例如 `--authors "Mingtian Yang, Co-Author"`)。适用于论文 `\author{}` 因双盲投稿而留空但海报需要显示真实作者的情况。`--anonymous` 同时传入时仍以 `--anonymous` 为准。若两个 flag 都未传且解析出的作者为 "Anonymous",Step 0 会交互式询问。
- `--max-sections N`(可选,默认 6):海报最多包含的章节数
- `--venue STR`(可选):海报右上方显示的会议/期刊文本(例如 `"NeurIPS 2026"`);若不提供,会交互式询问
- `--affiliation-logo PATH`(可选):单位/实验室 logo 文件路径(PNG/JPG/PDF),会被复制到 `poster/images/`
- `--conference-logo PATH`(可选):会议/期刊 logo 文件路径(PNG/JPG/PDF),会被复制到 `poster/images/`
- `--layout corners|stacked`(可选,默认 `corners`):header 布局。`corners` 把单位 logo 放在左上、会议 logo 放在右上;`stacked` 把两个 logo 都叠在右侧 `.conf` 区,venue 文本在最上
- `--no-logos`(可选):跳过所有 logo 询问,header 只显示 venue 文本
- `--auto-figures`(可选):跳过 Step 2.5 的逐章节配图询问,直接为每章选择面积最大的候选图(旧的"largest wins"逻辑)
- `--no-figures`(可选):所有章节渲染为纯文本,不嵌入任何配图。适合文本密集型海报或配图尚未准备好时
- `--no-refine`(可选):跳过 Step 5.5 的截图驱动 critique-revise。默认会跑 1 轮 critique-revise
- `--refine-iterations N`(可选,默认 1,硬上限 2):Step 5.5 的迭代次数。`0` 等同于 `--no-refine`

## Outputs

- `poster/dag.json` —— PaperX 兼容的中间格式(未来可被 `/slides`、`/pr` 复用)
- `poster/outline.html` —— 模板注入前的 `<section>` 块拼接结果
- `poster/poster.html` —— 最终自包含的 HTML 海报(浏览器打开即可)
- `poster/poster.png` —— 2× CSS 尺寸的渲染截图(默认 2800×1800),见 Step 5b
- `poster/poster.refine{N}.png` —— Step 5.5 每轮迭代前的截图存档(`--refine-iterations ≥ 1` 且实际跑过 refine 时才会有)
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

1. **作者** —— 仅当未传入 `--authors` 且未传入 `--anonymous`,且论文的 `\author{}` 解析为空 / "Anonymous" 时触发(本步骤前先看 dag.json 根节点的 `content` 字段,或快速 grep `paper/main.tex` 里的 `\author{...}`)。否则静默跳过。
   - 用 `AskUserQuestion` 询问,选项:
     - `"Keep 'Anonymous' (double-blind submission)"`(Recommended)
     - `"Provide author names (I'll ask for the string)"`
   - 若用户选 "Provide author names":自由文本询问 *"海报上应显示什么作者字符串?例如 `Mingtian Yang, Co-Author Name`。回复字符串,或回复 `skip` 保留 'Anonymous'。"* 把下一条用户消息取作 authors 覆盖串,留给 Step 5。

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
- **数学公式**:`$…$`、`$$…$$`、`\(…\)`、`\[…\]` 原样进入章节内容,后续由海报 HTML 中的 KaTeX 渲染。
- **引用**:`\citep{key}` / `\citet{key1, key2}` 被替换为 `[N]` / `[N, M]`,编号通过遍历章节文件按首次出现顺序生成。找不到 key 时静默丢弃。
- **表格**:`\begin{table}…\caption{...}…\end{table}` 被替换为 `[Table: <caption text>]`,让 caption 流入正文。表体数据丢弃(1400×900 海报放不下整张表)。

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

### Step 2.5: 配图选择

目标:决定每个被选中的章节应配哪张图(或无图)。在 `dag.json` 构建之后、LLM 提炼之前运行,使配图选择成为 Step 3 的*输入*,而不是让 LLM 猜。每张图都内联渲染在章节中;manifest 中的 ⚠ wide 标记仅作信息提示 —— 提醒比例极端的图在单列里可能被压扁,用户可以选其它图或跳过。

**章节选择**(优先级表同前,上限 `--max-sections`,默认 6):

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
| ≥2 | any | **询问 Q-Pick**: *"Which figure for {Section}?"* —— 选项:每个候选(标签包含 ⚠ wide 标记如适用) / `Let Claude decide (pick largest)` / `No figure`。 |

每次询问用 `AskUserQuestion`,选项数 ≤ 4。若某章节有 4 个以上候选,去掉 `Let Claude decide` 这一项以满足上限(用户已经在显式选了)。

所有决策做完后,打印一行汇总:

```
Figures chosen:
  Experiments → bootstrap.png (inline)
  (other sections: text only)
```

**决策记录**:用按章节显示名作 key 的内存 dict 保留选择:

```python
{
  "Experiments": {"figure": "images/bootstrap.png", "layout": "inline", "alt": "<caption>"},
  "Conclusion": {"figure": None, "layout": None, "alt": None},
  ...
}
```

Step 3 会消费此 dict 填入每章节的提示词变量。

### Step 3: 提炼海报章节

加载 `poster/dag.json` 与 Step 2.5 的决策 dict。按顺序遍历被选中的章节节点。

对每个章节,准备下面提示词所需的变量。配图相关变量从 Step 2.5 的决策 dict 取,**不要**在这里重新算。

- `SECTION_JSON`:从 `poster/dag.json` 取该 section 节点,**去掉** `visual_node` 字段(visual 单独传入)。只保留 `name`, `content`, `level`。
- `LAYOUT`:`"none"` 或 `"inline"`,从 `decisions[section_name]["layout"]` 取。决定 HTML 模板分支。
- `IMAGE_SRC`:例如 `images/layer_curves.png`,从 `decisions[section_name]["figure"]` 取。`LAYOUT == "none"` 时为空字符串。
- `ALT_TEXT`:从 `decisions[section_name]["alt"]` 取(caption)。`LAYOUT == "none"` 时为空。
- `WIKI_CONTEXT`(可选):Step 2 编译出的字符串(假设、新颖性、关键数值)。无 wiki 上下文时为空。

对每个章节调用下面的提示词(从 PaperX `poster_outline_prompt` 移植,扩展了 `LAYOUT` 与 `WIKI_CONTEXT`):

> You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON you see has NO `visual_node` field and must be treated as authoritative.
>
> SECTION_JSON:
> {SECTION_JSON}
>
> LAYOUT: {LAYOUT}    # one of "none" | "inline"
>
> If LAYOUT is "inline", you are also given IMAGE_SRC and ALT_TEXT. The visual content MUST ONLY come from this provided IMAGE_SRC (do not invent or substitute any other image).
>
> IMAGE_SRC: {IMAGE_SRC}
> ALT_TEXT: {ALT_TEXT}
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
> - LAYOUT == `"inline"`: output the section block with exactly one `<div class="img-section">` containing one `<img>` whose `src` is exactly `IMAGE_SRC` and `alt` is `ALT_TEXT`.
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
> *LAYOUT = "inline"*:
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

调用系统 headless 浏览器二进制做截图,产出 `poster/poster.png`,默认 2× CSS 像素(2800×1800),无新 Python 依赖。用 `--scale {1,2,3}` 覆盖(1 = 快速预览,3 = 印刷质量)。

**浏览器探测**:优先 Chromium 系(Chrome → Edge → Chromium),Firefox 作为兜底。Chrome/Edge/Chromium 三者等价(同引擎、同 CLI flag)。Firefox 也能用,但有两个限制 —— 不支持 HiDPI 缩放(无论 `--scale` 传什么,PNG 都是 1×);也没有 `--virtual-time-budget` 等价物(fit() / KaTeX / 字体加载可能在截图前还没收敛)。退化到 Firefox 时 `render` 会向 stderr 打印警告。

**不支持 Safari** —— Safari 没有 headless CLI 截图 flag;接入需要 `safaridriver` + Selenium WebDriver。macOS 上只有 Safari 的用户可以 `brew install --cask google-chrome`(一行命令)解锁完整流程。

若找不到任何支持的浏览器,`render` 以平台对应的安装提示退出。HTML 海报本身在任何浏览器里都能打开 —— 用户依然可以 `open poster/poster.html`。

### Step 5.5: Critique-revise(Claude 截图驱动)

目标:把 Step 5b 渲染出的截图喂给 Claude(多模态),做一次性的 critique-revise。捕捉 `validate` 抓不到的问题 —— HTML 中残留的 LaTeX、章节文字溢出、标题里的编号前缀、配图渲染异常等。自动应用,无用户交互。

**跳过条件**:
- 传入 `--no-refine` → 完全跳过。
- `--refine-iterations 0` → 等同 `--no-refine`。
- Step 5b 没产出 `poster/poster.png`(无可用 headless 浏览器)→ 警告后跳过。

**迭代次数**:由 `--refine-iterations N` 决定(默认 1,硬上限 2)。

**单轮迭代流程**(i = 1..N):

1. 确保 `poster/poster.png` 反映当前 `poster/poster.html`。若 HTML 自上次渲染后有改动,重跑 `python3 tools/poster.py render poster/poster.html`。
2. 存档当前截图:`cp poster/poster.png poster/poster.refine{i-1}.png`(方便用户 diff 每轮的变化)。
3. 在内存里快照 `pre_html = <当前 poster.html>` —— 用于 step 8 的收敛判定。
4. 读取 `poster/poster.png`(用 Read,Claude 多模态读图)与 `poster/poster.html`(Read)。
5. 应用下面的 refinement 提示词。用 Claude(会话内,已多模态)。**不要**用 `mcp__llm-review__chat`,它按 `mcp-servers/llm-review/server.py` 只接受文本。
6. 解析 LLM 输出:从第一个 ```` ```html ```` 围栏代码块里提取 HTML。
7. 把修订后的 HTML 写回 `poster/poster.html`,并快照为 `post_html`。
8. **收敛检查**(在 validate / 重新渲染之前):归一化 `pre_html` 与 `post_html` —— 去掉静态 `<head>` 块(它永不变化)、合并空白,然后只在 `<div class="flow" id="flow">…</div>` 区域内计算字符级对称差。若差异 **小于 50 个字符**(即 LLM 没做实质修改),声明收敛:
   - 记录结果为 `"converged after {i} iteration(s) — no material changes"`。
   - 跳过下面的 step 9–10(无需 re-validate / re-render,磁盘上的 PNG 已与 HTML 一致)。
   - **即使迭代预算 `N` 还有剩余**,也退出迭代循环。
9. 重跑 `python3 tools/poster.py validate poster/poster.html`。若 validate 失败:停止迭代,告诉用户具体问题,HTML 保留原样供人工检查。
10. 重新渲染 `poster/poster.png`,供下一轮(或作为最终渲染)。

**收敛 stop 的意义**:实际跑下来,当上游流程(Step 3 + Step 4)已经产出干净的文本(没有 LaTeX 漏出、没有编号前缀),step 5 的 LLM 没什么可改的。如果没这道收敛闸,第二轮迭代仍会触发一次 LLM 调用,代价不小但收益接近零。50 字符的阈值容忍空白/标点的微小差异,同时仍能捕获有意义的文字修订或 LaTeX 清理。

**Refinement 提示词**(从 PaperX `poster_refinement_prompt` 移植,加了一个截图驱动的 layout 任务):

> You are an expert Academic Poster Designer and Web Developer. Your task is to refine an existing HTML poster based on its visual rendering (screenshot) and the current code. Output ONLY the full, valid, and corrected HTML code inside a single fenced ```` ```html ```` code block.
>
> I will provide:
> 1. **Current Poster Code (HTML)**
> 2. **Visual Render (PNG screenshot)**
>
> **TASKS**:
>
> **Task 1: Fix LaTeX / encoding leaks**
> - Scan the HTML for raw LaTeX that did not render (e.g., `$d_S \ge 10$`, `\textbf{...}`, `\citep{...}`, `\ref{fig:...}`).
> - Replace with HTML entities or Unicode (e.g., `d_S ≥ 10`, `<strong>...</strong>`, `[N]`, "Fig. 1").
> - Remove garbled characters from math-rendering failures.
>
> **Task 2: Normalize section headers**
> - Find all `<div class="section-bar">` elements.
> - Strip leading numbering / alphabetic prefixes / meaningless punctuation (e.g. `1.`, `2.1`, `A.`, `E.`, `- `).
> - Keep only the core title text.
>
> **Task 3: Fix visible layout issues (from the screenshot)**
> - If any section's text overflows its column (visible in screenshot): shorten the prose conservatively. Never delete claims; trim filler words.
> - If a `<div class="img-section">` figure renders cropped, distorted, or breaks the column flow: leave the structure intact (do not delete) but you may add `style="max-height: 280px"` to the `<img>` or wrap text differently.
> - If a section is visually empty (just the title bar with no body text): leave a `<p>(content pending)</p>` placeholder, do NOT remove the section.
>
> **Output requirement**:
> - Return the **complete, runnable HTML** wrapped in a single fenced ```` ```html ```` code block.
> - Preserve the existing CSS layout exactly. Do NOT modify font-related settings (font-family, font-size, font-weight beyond what the template already defines).
> - Do NOT modify the existing `<script>` block (the fit algorithm) or the `<style>` block.
> - Only edit content inside `<section class="section">` elements and the `<h1 class="title">` / `<div class="authors">` if needed.
>
> **HTML poster**:
> ```html
> {full content of poster/poster.html}
> ```
>
> **Screenshot**:
> *(the contents of poster/poster.png attached via the Read tool — Claude reads it as an image)*

**终止条件**:
- **收敛**(正常的提前退出):LLM 的修订在 `.flow` 区域差异 < 50 字符 —— 见上面 step 8。无论预算剩余多少,退出循环。
- **达到 iteration 上限**:`i == N`。完成,进入 Step 6。
- **LLM 输出里没有 ```` ```html ```` 围栏** → 停止,HTML 保留原样,记录警告。
- **围栏里没有 `<section>` 或缺 `<h1 class="title">`** → 停止,HTML 保留原样,记录警告。
- **修订后 validate 失败** → 停止,告诉用户具体问题,HTML 保留原样供人工检查。

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
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous]` —— 构建 dag.json
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` —— 注入 outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous] [--authors STR]` —— 写入标题/作者;`--authors` 覆盖 dag.json 中的作者字段,适用于源论文已匿名的情况
- `python3 tools/poster.py inject-header <poster.html> [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked]` —— venue 文本 + 可选 logo
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` —— 复制/转换图片
- `python3 tools/poster.py validate <poster.html>` —— 健康检查
- `python3 tools/poster.py render <poster.html> [--scale 1|2|3] [--output PATH]` —— HTML → PNG,走 headless 浏览器(优先 Chrome / Edge / Chromium,Firefox 兜底)
- `python3 tools/research_wiki.py log wiki/ "<message>"` —— 追加日志
- `pdftoppm`(poppler)—— PDF → PNG @ 200 DPI
- `pdfinfo`(poppler)—— PDF 页面尺寸,用于 resolution
- Headless 浏览器(系统二进制)—— `render` 用来截图。自动探测顺序:Google Chrome → Microsoft Edge → Chromium → Firefox(兜底)。Chrome/Edge/Chromium 完全等价;Firefox 只能在 1× 尺度渲染且无 sync-wait。Safari 不支持。

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
