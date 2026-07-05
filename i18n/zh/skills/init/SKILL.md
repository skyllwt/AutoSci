---
name: init
description: 基于用户素材与可选外部发现搭建 AutoSci，并完成最终论文集的消化
argument-hint: "[topic] [--no-introduction]"
---

# /init

> 从 `raw/` 搭建 wiki：先做确定性 prepare，再跑 planner-guided discovery；`raw/notes/` 与 `raw/web/` 可种下 provisional scaffold；论文消化走顺序 `/ingest`。

按需打开这些本地参考文件：

- `references/prepare-and-discovery.md` — prepare 流程、最终选择、fetch 与 source-manifest 规则
- `references/planner-policy.md` — planner 行为与 LLM 裁剪期望
- `references/parallel-ingest.md` — 可选的并行 ingest（通过 git worktree；仅在运行时支持并发子代理时使用；sandbox 环境跳过此参考）

## Inputs

- `topic`（可选）：研究方向关键词；当 `raw/` 已定义 seed set 时可省略
- `--no-introduction`（可选）：禁用外部发现；仅在用户明确要求时使用
- 用户自有素材：`raw/papers/`、`raw/notes/`、`raw/web/`

## Outputs

- `wiki/` 骨架与 provisional 页面（Summary、topics、ideas、concepts）
- `raw/tmp/` 与 `raw/discovered/` 预处理来源
- `/ingest` 产出的最终论文页面
- `.checkpoints/init-*.json` 清单，用于恢复与重放
- 更新后的 `wiki/index.md`、`wiki/log.md`、`wiki/graph/*`
- 重新生成的可视化产物：`wiki/.obsidian/graph.json`（按实体类型的 colorGroups）与 `wiki/canvases/*.canvas`（best-effort，见 Step 6）。交互式网页 Graph 视图由 `tools/serve.py`（SPA）提供服务，不再单独生成产物。

## Wiki Interaction

### Reads

- `raw/papers/`、`raw/notes/`、`raw/web/`
- `.checkpoints/init-prepare.json` 与 `.checkpoints/init-sources.json`，供 resume、planning 与 ingest 顺序使用
- `wiki/index.md` 以及已有 `wiki/topics/`、`wiki/ideas/`、`wiki/concepts/`、`wiki/methods/`，用于去重与 scaffold 对齐

### Writes

- `wiki/` scaffold 与 provisional 页面
- `raw/tmp/` 与 `raw/discovered/`
- `wiki/index.md`、`wiki/log.md`、`wiki/graph/*`
- `.checkpoints/init-prepare.json`、`.checkpoints/init-plan.json`、`.checkpoints/init-sources.json` 与 `init-session` checkpoint metadata

### Graph edges created

- `/init` 本身只在 provisional 页面需要时写入少量 scaffold 级别的 edges
- 论文驱动的 edges 全部委托给 `/ingest`

## Workflow

**前置条件**：当前目录为项目根，且包含 `wiki/`、`raw/`、`tools/`。设 `WIKI_ROOT=wiki/`。先解析一次 `PYTHON_BIN`，并在整个 `/init` 流程里复用它，确保运行时使用与 `setup.sh` 安装依赖时相同的解释器：

```bash
if   [ -x .venv/bin/python ];         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then PYTHON_BIN=.venv/Scripts/python.exe
else                                       PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: 初始化 wiki 结构

```bash
"$PYTHON_BIN" tools/research_wiki.py init wiki/
```

创建标准目录、`graph/`、`outputs/`、`index.md` 与 `log.md`。这里不要重复写第二条 init 日志。

### Step 2: 把本地输入 prepare 到 `raw/tmp/`

```bash
"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json
```

- 在运行 `prepare` 前，先读取每个本地 PDF，并把恢复 handoff 写入 `.checkpoints/init-pdf-titles.json`。格式既可以是 `{ "raw/papers/foo.pdf": "Recovered Paper Title" }`，也可以是在已知可信 arXiv ID 时写成 `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title", "arxiv_id": "2401.00001" } }`
- 使用 `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]` 做本地论文规范化
- 本地 PDF 的恢复顺序必须严格遵守：handoff 进来的 arXiv ID 或 filename/path 中的 arXiv ID -> agent 恢复出的标题经 Semantic Scholar 搜索 -> 抓取到的 arXiv 源码 -> synthetic `.tex`
- 如果 agent 已经提供了 PDF 标题，就把这个标题当作 prepare manifest 中的权威标题；fetched/source 标题仅作为显示用的 fallback metadata
- prepare 阶段禁止使用 PDF metadata 或 PDF body text 作为 arXiv-ID 线索
- arXiv ID 恢复成功后，优先使用抓取到的原始 TeX 源码，而不是 synthetic `.tex`
- prepare 子命令内部会委托到 `prepare_paper_source.py`；不要在 `/init` Step 2 单独调用 `prepare_paper_source.py`

### Step 3: Provisional notes/web 骨架与 planner

```bash
"$PYTHON_BIN" tools/init_discovery.py plan \
  [--topic "<topic>"] \
  --mode auto \
  --raw-root raw \
  --wiki-root wiki \
  --prepared-manifest .checkpoints/init-prepare.json \
  --allow-introduction <true|false> \
  --output-plan .checkpoints/init-plan.json
```

- 当用户没有提供 topic 时省略 `--topic`
- `--allow-introduction true`，除非用户显式传了 `--no-introduction`
- planner 通过 `.checkpoints/init-prepare.json` 读取本地上下文
- 可能会创建由 notes/web 驱动的 provisional `wiki/topics/`、`wiki/ideas/`、`wiki/concepts/` 页面
- 所有 notes/web 派生页面必须包含下列 exact provisional notice：`> ⚠️ **PROVISIONAL PAGE** — auto-generated from notes/web during /init. Does not (yet) cite a peer-reviewed source. Treat claims with caution.`
- planner 细节与选择策略见 `references/planner-policy.md`

### Step 4: 下载外部论文并写出 source manifest

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch \
  --raw-root raw \
  --plan-json .checkpoints/init-plan.json \
  --prepared-manifest .checkpoints/init-prepare.json \
  --output-sources .checkpoints/init-sources.json \
  --id <candidate-id> --id <candidate-id> ...
```

- 传入 plan shortlist 中的每个 external candidate ID（如果没有外部论文被选中，也仍然要传零个 --id 来写出 manifest）
- 外部论文下载到 `raw/discovered/`，绝不可下载到 `raw/papers/`
- fetch 子命令会写出 `.checkpoints/init-sources.json`，这是 Step 5 的唯一数据源
- source 选择优先级与 manifest schema 见 `references/prepare-and-discovery.md`

### Step 5: Ingest 论文

论文来源严格由 `.checkpoints/init-sources.json` 决定：

- `origin=user_local`：优先使用 `raw/tmp/` 下的 canonical prepared path，否则回退到 `raw/papers/...`
- `origin=introduced`：`raw/discovered/` 下的目录或 PDF

按 `shortlist_rank` **顺序**执行 `/ingest`，每次一篇：

- 每回合只 ingest 一个 source path
- 在 INIT MODE 下，严格使用 handed-off 的 `canonical_ingest_path`
- 跳过 `fetch_s2.py citations`
- 跳过 `fetch_s2.py references`
- 跳过 per-paper `rebuild-index`、`rebuild-context-brief`、`rebuild-open-questions`
- 跳过可能冲突的 topic 写入
- 每篇完成后把结果记入 checkpoint metadata（`checkpoint-set-meta wiki/ init-session ingest:<candidate_id> <status>`）
- 单篇失败时写 checkpoint、跳过该篇、继续其他论文

> **并行 ingest**（可选）：当运行时支持并发子代理且 `git worktree` 可用时，可使用 `references/parallel-ingest.md` 中的并行 fan-out / fan-in 工作流代替上述顺序循环。在 sandbox 环境中（`git worktree add`、并发子代理 session 或 `git merge` 不可用）不得尝试并行 ingest。

### Step 6: Rebuild、citation 回填、可视化与最终报告

所有论文 ingest 完成后：

```bash
"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/
"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix
```

接着通过 Semantic Scholar 回填 `cites` 边 —— `fetch_s2.py references` 在每篇 ingest 中都被跳过，必须在此处补回。best-effort：S2 故障不可阻塞 `/init`。

```bash
"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/ \
  || echo "WARN: citation backfill failed or partial; check stderr above" >&2
```

随后重新生成可视化产物（best-effort；visualize 失败不可阻塞 `/init`）。`generate-obsidian-config` 会从 `config/visualize.json` 重写 `wiki/.obsidian/graph.json`，让按实体类型的 colorGroups 与运行时配置保持同步。

```bash
"$PYTHON_BIN" tools/visualize.py generate-obsidian-config wiki/ \
  || echo "WARN: visualize generate-obsidian-config failed; run /visualize manually" >&2
"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/ \
  || echo "WARN: visualize generate-canvas failed; run /visualize manually" >&2
```

报告中必须分开列出：

- 通过 `raw/tmp/` prepared path ingest 的用户论文
- 因 prepare 失败而回退到原始 `raw/papers/` 的用户论文
- `raw/discovered/` 中的 introduced 论文
- 由 notes/web 种下的 provisional 页面
- `/ingest` 新建的页面
- `/ingest` 更新过的页面
- 被跳过或失败的论文
- 可视化刷新状态

## Constraints

- 不得仅根据仓库状态推断 `--no-introduction`。只有当用户明确要求禁用外部发现时，才可使用它。
- `raw/papers/`、`raw/notes/`、`raw/web/` 是用户自有输入
- `raw/tmp/` 与 `raw/discovered/` 是生成型 handoff 区；直接本地 `/ingest` 也可以在 `raw/tmp/` 下准备可复用的 local sidecar
- `/init` 只能把外部论文写到 `raw/discovered/`；`/init` 与直接本地 `/ingest` 可以把生成的 prepared local source 写到 `raw/tmp/`
- `/prefill` 是可选背景预填充，不属于 `/init`
- 只有 `/prefill` 可以自动创建 foundations
- `/init` 不得直接创建 `people/` 页面
- notes/web 派生页面必须包含上面的 exact provisional notice
- 对 concept 合并与 method 抽取，论文证据永远高于 notes/web
- Step 5 必须读取 `.checkpoints/init-sources.json`，不得临时扫描目录
- 精确的 planner 常量属于 `tools/init_discovery.py`，不属于重复写在 skill 文档中的常量

## Error Handling

- **`raw/papers/` 无可解析论文**：自动切换到 bootstrap 模式
- **`raw/notes/` 与 `raw/web/` 为空**：跳过 provisional seeding，继续
- **prepare 阶段的 PDF decode 失败**：保留本地来源，把 warning 记入 `.checkpoints/init-prepare.json`，必要时回退到原始路径
- **没有恢复出可信 PDF 标题**：省略 `--title`，只允许走 filename/path arXiv-ID 恢复，然后直接回退到 synthetic `.tex`；metadata 或 filename 标题只用于显示
- **`raw/notes/` 或 `raw/web/` 中检测到中文内容**：继续执行，但要保留 planner warning，说明 note/web 提取与排序可能更不可靠，并把 rankings 与 provisional 页面视为较低置信度
- **S2 或 DeepXiv 不可用**：planner 使用剩余来源并继续执行；把 warning 保留在 checkpoint plan 中，并在最终报告里注明 discovery 降级
- **某篇外部论文下载失败**：保留其余最终论文集，报告失败项
- **单篇 ingest 失败**：写 checkpoint，跳过该篇，继续其他论文，并在最终报告中列出
- **可视化重生成失败**：警告并继续，绝不让 `/init` 失败。用户可单独跑 `/visualize --canvas` 排查，或直接通过 `python tools/serve.py` 浏览 SPA Graph 视图

## Dependencies

### Tools（via Bash）

- `"$PYTHON_BIN" tools/research_wiki.py init wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py checkpoint-set-meta wiki/ init-session <key> <value>`
- `"$PYTHON_BIN" tools/research_wiki.py checkpoint-save/load/clear wiki/ init-session ...`
- `"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"`
- `"$PYTHON_BIN" tools/visualize.py generate-obsidian-config wiki/`
- `"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/`
- `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"]`
- `"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`
- `"$PYTHON_BIN" tools/init_discovery.py plan [--topic "<topic>"] --mode auto --raw-root raw --wiki-root wiki --prepared-manifest .checkpoints/init-prepare.json --allow-introduction <true|false> --output-plan .checkpoints/init-plan.json`
- `"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id>`
- `"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix`
- `"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/`

### Skills

- `/ingest` — 每次只 ingest 一篇论文，且运行在 INIT MODE
- `/visualize` — Step 6 直接调用 `tools/visualize.py` 重新生成 Obsidian 颜色组与 Canvas（best-effort）；用户也可以稍后手动调用 `/visualize` 做 `--focus` 视图，或在改了 `config/visualize.json` 后重新渲染

### `init_discovery.py` 内部使用的外部 API

- Semantic Scholar
- DeepXiv（可选）
- arXiv 下载端点
