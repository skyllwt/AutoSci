# /ingest PDF 预处理

当 `/ingest` 接收到本地 `.pdf` 且需要转换成 prepared `.tex` 以便后续 ingest 时，打开此参考。INIT MODE 下跳过 —— `/init` 已经做过等价的批量预处理并交接了 canonical path。

## 为什么要做预处理

裸 PDF 作为 ingest 来源质量不佳：文本提取不稳定，公式与图表标题容易丢失，reference list 也经常不可靠。如果论文在 arXiv 上，把它解析到 arXiv ID 并抓取 TeX 源就能显著改善。即便没有 arXiv 源，我们也要把 PDF 统一规范成 synthetic `.tex`，让 `/ingest` 的其余步骤基于统一的输入形状运行。

这与 `tools/init_discovery.py prepare` 在 `/init` 批量处理本地 PDF 时执行的流水线是同一套 —— 此处是把它单篇、就地执行一遍。

## 恢复顺序

严格按此顺序执行，遇到第一个产出可信结果的步骤即停止。

1. **agent 先读 PDF 本身。**
   调用任何工具前，先打开 PDF 并记录：
   - 可信的论文标题（优先使用首页标题，不要用 PDF metadata —— 后者经常是错的）
   - 若首页或 header 明确印出 arXiv ID，也记录该 ID
   两者皆可为空。不要臆测。
2. **文件名 / 路径中的 arXiv ID 提取。**
   `prepare_paper_source.py` 本身会以正则匹配文件名或所在目录中的 arXiv ID，无需你自己做 —— 只要把 PDF 路径交给它即可。
3. **基于标题的 Semantic Scholar 查找。**
   仅当 agent 提供了可信标题时触发。由 `prepare_paper_source.py` 在传入 `--title` 后内部处理。
4. **arXiv 源抓取。**
   当 arXiv ID 已知（来自步骤 1 或 2），helper 将 TeX 源下载到 `raw/tmp/papers/.../<slug>-arxiv-src/` 并用它作为 prepared source。
5. **synthetic `.tex` fallback。**
   如果以上都无法匹配到 arXiv，helper 会在 `raw/tmp/` 下生成一份从 PDF 文本提炼的 synthetic `.tex`。该文件对 ingest 来说够用，但会被明确标记为 fallback。

## 调用

拿到（可能为空的）标题与 arXiv ID 后，执行：

```bash
"$PYTHON_BIN" tools/prepare_paper_source.py \
  --raw-root raw \
  --source <pdf-path> \
  [--title "<agent-recovered-title>"] \
  [--arxiv-id "<agent-recovered-arxiv-id>"]
```

- 只有 agent 确实可信才传 `--title`。不要把从 PDF metadata 或文件名派生的标题当作权威输入 —— helper 本身会对这些做 sanitize，若把它们当权威会污染 Semantic Scholar 查找。
- 只有 agent 从页面上读到 arXiv ID 才传 `--arxiv-id`。文件名中的 ID 由 helper 自动识别。
- 两者都不可信时，同时省略这两个参数。helper 会干净地 fallback。

helper 在 `raw/tmp/` 下写出一个 prepared 条目，并在 stdout 打印一份含 `prepared_path`、`title`、`arxiv_id` 与任何 warning 的 JSON 记录。后续 `/ingest` 步骤以 `prepared_path` 为来源。

## 标题权威性

当 agent 提供了可信标题时，该标题即是论文页面 `title` 字段的权威取值。从抓取到的 TeX 或 PDF metadata 中 sanitize 出来的标题只是 fallback 显示字符串，不得覆盖 agent 标题。这很重要：agent 标题是成功触发 S2 查找的那一个，如果让解析到的 TeX 标题覆盖它，会造成微妙的身份漂移。

## 输出

成功的预处理产出 `raw/tmp/` 下的一个 prepared source 条目：

- 若已抓到 arXiv 源：`raw/tmp/papers/<slug>-arxiv-src/` 目录，包含原始 `.tex` 树
- 否则：`raw/tmp/papers/<slug>.tex` synthetic 文件，由 PDF 文本提炼

从这一点开始，把 prepared 条目当作普通的用户提供的本地 `.tex` 对待即可。不要把 PDF 复制回 `raw/papers/`；原始 PDF 路径仍属用户自有产物。
