# /init Prepare And Discovery

当 `/init` 需要 prepare 本地输入、选择最终论文集、或写出 `.checkpoints/init-sources.json` 时，打开此参考文件。

## Prepare 流程

- 执行 `"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`。
- prepare 本地 PDF 前，先尽量恢复可信标题，并把结果写入 `.checkpoints/init-pdf-titles.json`。格式既可以是 `{ "raw/papers/foo.pdf": "Recovered Paper Title" }`，也可以是在已知可信 arXiv ID 时写成 `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title", "arxiv_id": "2401.00001" } }`。
- `tools/init_discovery.py prepare` 必须把这些恢复出的标题和 ID 传给 `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]`。
- `tools/init_discovery.py prepare` 必须委托给同一个 helper 做本地论文规范化，并在已有预处理结果时复用现成的 `raw/tmp/` artifact。
- 本地 PDF 只允许采用这一条恢复顺序：handoff 进来的 arXiv ID 或 filename/path 中的 arXiv ID -> 在提供可信标题时经 Semantic Scholar 按标题恢复 -> 抓取到的 arXiv 源码 -> synthetic `.tex`。
- 如果 agent 已经提供了可信 PDF 标题，这个标题就是 prepared manifest 的 authoritative title。抓取到的 TeX 源码标题只能作为清洗后的 fallback metadata，不能覆盖 agent 标题。
- prepare 阶段不得把 PDF metadata 或正文文本当作 arXiv-ID hint。
- 恢复成功后，优先使用 `raw/tmp/papers/...-arxiv-src/` 下抓取到的原始 TeX 源码，而不是 synthetic `.tex`。
- 如果拿不到可信 PDF 标题，就省略 `--title`；如果也拿不到可信 arXiv ID，就省略 `--arxiv-id`；随后只允许走 filename/path arXiv-ID 恢复，然后直接回退到 synthetic `.tex`。metadata 或 filename 标题只用于显示。

## 来源优先级

- 本地来源优先级：原始本地 `.tex` > archive 解出的源码 `.tex` 或抓取到的 arXiv 源码目录 > 由 PDF 生成的 synthetic `.tex` > 原始 `.pdf`。
- notes/web 保持原始来源路径，`/init` 在 planning 阶段直接读取。
- 如果 handoff 进来的来源已经在 `raw/tmp/` 或 `raw/discovered/` 下，就把它视为 canonical path，不要再复制进 `raw/papers/`。
- 本地论文若存在 prepared 结果，其 `canonical_ingest_path` 必须指向 `raw/tmp/`；否则回退到原始 `raw/papers/...`。

## 最终选择与 Fetch

- `plan` 必须读取 `.checkpoints/init-prepare.json`，而不是重新扫描 `raw/`。
- 先 over-pick 一个 shortlist，再在 `fetch` 前显式裁成文档规定的最终范围。
- 默认保留所有可解析的用户论文，再用剩余名额选择 introduced 论文。
- 如果 seeded discovery 最终没有新增外部论文，也要继续用用户自带论文集往下走，而不是把它当成 fatal planner error。
- 如果用户已提供超过 10 篇可解析论文，则不再新增外部论文。
- 如果 `--no-introduction` 开启，最终论文集 = 所有可解析本地论文；即便如此也仍要运行 `fetch`（不给外部 ID），以写出 `.checkpoints/init-sources.json`。

执行：

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id> --id <candidate-id>
```

- `/init` 下载的论文只允许写入 `raw/discovered/`，绝不写入 `raw/papers/`。
- 若某篇候选已经由 prepared local source 覆盖，则禁止重复抓取。

## Source Manifest 合同

- `.checkpoints/init-sources.json` 是 Step 5 ingest 顺序的唯一真相源。
- 用户本地论文在 `init-sources.json` 中以 `origin=user_local` 记录，并在可用时带上 canonical prepared path。
- introduced 论文在 `init-sources.json` 中以 `origin=introduced` 记录，其 canonical path 位于 `raw/discovered/`。
- Step 5 必须原样消费 handoff 过来的 `canonical_ingest_path`。
