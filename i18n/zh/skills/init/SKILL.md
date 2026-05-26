---
description: 基于用户素材与可选外部发现搭建 ΩmegaWiki，并用并行 `/ingest` 完成最终论文集的消化
argument-hint: "[topic] [--no-introduction]"
---

# /init

> 从 `raw/` 搭建 wiki：先做确定性 prepare，再跑 planner-guided discovery；`raw/notes/` 与 `raw/web/` 可种下 provisional scaffold；论文消化仍走并行 `/ingest` fan-out / fan-in。

按需打开这些本地参考文件：

- `references/prepare-and-discovery.md` — prepare 流程、最终选择、fetch 与 source-manifest 规则
- `references/planner-policy.md` — planner 行为与 LLM 裁剪期望
- `references/parallel-ingest.md` — worktree 隔离、子代理 prompt 合同、merge 与清理

## Inputs

- `topic`（可选）：研究方向关键词；当 `raw/` 已定义 seed set 时可省略
- `--no-introduction`（可选）：禁用外部发现；仅在用户明确要求时使用
- 用户自有素材：`raw/papers/`、`raw/notes/`、`raw/web/`

## Outputs

- `wiki/` 骨架与 provisional 页面（Summary、topics、ideas、concepts）
- `raw/tmp/` 与 `raw/discovered/` 预处理来源
- 并行 `/ingest` 产出的最终论文页面
- `.checkpoints/init-*.json` 清单，用于恢复与重放
- 更新后的 `wiki/index.md`、`wiki/log.md`、`wiki/graph/*`
- 重新生成的可视化产物：`wiki/.obsidian/graph.json`（按实体类型的 colorGroups）与 `wiki/canvases/*.canvas`（best-effort，见 Step 6）。交互式网页 Graph 视图由 `tools/serve.py`（SPA）提供服务，不再单独生成产物。

## Wiki Interaction

### Reads

- `raw/papers/`、`raw/notes/`、`raw/web/`
- `.checkpoints/init-prepare.json` 与 `.checkpoints/init-sources.json`，供 resume、planning 与 fan-out 使用
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
# 通过 git 找到项目根，让 worktree 中的 subagent 也能定位 .venv。
# .venv 被 gitignore，subagent 的 cwd 在 ../.worktrees/<branch>/ 时本地没有
# .venv——若不解析项目根，PYTHON_BIN 会回退到系统 python3，既丢失 .env 里的
# API key，也丢失安装的依赖（deepxiv-sdk 等）。
# git rev-parse --git-common-dir 无论 cwd 位于哪个 worktree 都返回主仓库的
# .git 目录；其父目录即项目根。
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi

if   [ -x "$PROJECT_ROOT/.venv/bin/python" ];         then PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -x .venv/bin/python ];                         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ];                 then PYTHON_BIN=.venv/Scripts/python.exe
else                                                       PYTHON_BIN=python3
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
- 如果 agent 已经提供了 PDF 标题，就把这个标题当作 prepared manifest 的 authoritative title；抓取源码里提取出的标题只能作为经过清洗后的 fallback metadata，不能反过来覆盖 agent 标题
- prepare 阶段不得把 PDF metadata 或正文文本当作 arXiv-ID hint
- metadata 或 filename 中的标题最多只是 provisional display label，不能当作可信 identity，也不能作为标题检索输入
- notes/web 保持原始来源路径，`/init` 在 planning 阶段直接读取
- 本地论文若存在 usable 的 prepared 结果，其 `canonical_ingest_path` 必须指向 `raw/tmp/`；否则回退到原始 `raw/papers/...`
- decode / 标题恢复 / arXiv 源码抓取失败时记录 warning，而不是中止 `/init`
- prepare 的细化决策树与来源优先级见 `references/prepare-and-discovery.md`

### Step 3: 生成 discovery plan、裁剪最终论文集，并写出 source manifest

```bash
"$PYTHON_BIN" tools/init_discovery.py plan [--topic "<topic>"] --mode auto --raw-root raw --wiki-root wiki --prepared-manifest .checkpoints/init-prepare.json --allow-introduction <true|false> --output-plan .checkpoints/init-plan.json
```

- `mode=seeded` 取决于 prepare manifest 中是否存在可解析本地论文；否则为 `bootstrap`
- `plan` 必须读取 `.checkpoints/init-prepare.json`，而不是重新扫描 `raw/`
- skill 层只保留定性 planner 策略：优先 relevance、freshness、connectivity 与 survey coverage
- 在 seeded 模式且 introduced 容量有限时，不要让偏旧且 citation 很高的 anchor 抢走太多名额
- 在 bootstrap 模式下，如果确实有助于覆盖面，可以保留一篇偏旧 canonical anchor
- 若 DeepXiv search 可用，要在工具打分里使用返回的 `relevance_score`，而不是只在文字里提一句
- 精确 ranking weights、shortlist 常量与 threshold 计算都属于 `tools/init_discovery.py`；把工具视为实现层唯一权威，不要在 LLM 推理里重述或覆盖这些常量
- 在 `fetch` 前读取 `.checkpoints/init-plan.json`，并把 over-picked 的 `shortlist` 明确裁成最终 **8-10** 篇
- 在 `fetch` 前必须给出明确的最终选择结果，至少包含 `shortlist_count`、`final_count` 与按 shortlist 顺序排列的最终 `candidate_id` 列表
- 若 `final_count` 不在 **8-10** 范围内，则必须先停止并修正最终选择，再执行 `fetch`；`--no-introduction` 或“用户已提供超过 10 篇可解析论文”除外
- 若传入 `--no-introduction`，只有在用户明确要求只使用本地论文时，才走这一分支；即便如此也仍要执行 `fetch`（不给外部 ID），以写出 `.checkpoints/init-sources.json`
- planner 行为、trim 期望与 source-of-truth 边界详见 `references/planner-policy.md`

然后执行：

```bash
"$PYTHON_BIN" tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id <candidate-id> --id <candidate-id>
```

- `/init` 下载的论文只允许写入 `raw/discovered/`，绝不写入 `raw/papers/`
- 若某篇候选已经由 prepared local source 覆盖，则禁止重复抓取
- `.checkpoints/init-sources.json` 是下游 ingest 顺序的唯一真相源

### Step 4: 在论文 ingest 前建立 scaffold 页面

创建一篇 `wiki/Summary/{area}.md`、若干 `wiki/topics/{slug}.md`，以及来自 notes/web 的 provisional `ideas/`、`concepts/`，必要时还包括 `methods/`。

规则：

- notes/web 对“用户意图”是权威，对“文献置信度”不是权威
- 每个 notes/web 派生页面都必须在 frontmatter 后立即写入这一行：

```markdown
Provisional note: seeded from raw/notes or raw/web during /init; pending validation from ingested papers.
```

- `topics/`：方向被明确提到或反复出现时创建
- `ideas/`：用户明确提出或强烈暗示研究方向 / 假设时创建
- `concepts/`：技术机制在 notes/web 中反复出现，或在 notes/web 与最终论文集中各出现至少一次时创建
- `methods/`：除非用户在 notes/web 中显式命名了一项可复用、可被引用的 method，否则 `/init` 不创建 `methods/`；把论文中的 method 推升为可复用 method 实体是 ingest 的职责
- `/prefill` 只是可选背景预填充，不属于 `/init`
- `/init` 不得直接创建 `people/` 页面，也不得自动创建 foundations

### Step 5: 通过 worktree 隔离并行 ingest 论文

本步骤的论文来源只能来自 `.checkpoints/init-sources.json`：

- `origin=user_local`：优先 ingest `raw/tmp/` 中的 canonical prepared `.tex`；prepare 失败时回退到原始 `raw/papers/...`
- `origin=introduced`：ingest `raw/discovered/` 中抓取到的目录或 PDF

并行 ingest 合同：

- fan-out 前先 stash 无关脏文件，再把 `stash_ref`、`base_branch`、`base_commit` 写入 checkpoint metadata
- fan-out 前必须先提交刚创建的 scaffold 与 init manifests，确保 `BASE_COMMIT` 真的包含后续子代理要继承的页面、manifest 与 handoff metadata
- 创建 worktree 前先验证 `.gitattributes` 对 `wiki/log.md`、`wiki/graph/edges.jsonl`、`wiki/graph/citations.jsonl`、`wiki/index.md` 使用了 `merge=union`
- `/init` 的 worktree 模式必须运行在一个命名分支上，不能处于 detached HEAD
- 每个 worktree 都必须从 `BASE_COMMIT` 拉出，而不是复用已经签出的 `BASE_BRANCH`
- 子代理 prompt 只能使用**相对路径**，且子代理的 shell 工作目录必须是 worktree 路径（`$WT_PATH`），不能是主仓库根目录
- 只对一个 handoff 进来的 source path 执行 `/ingest`，不得绕过 `/ingest`
- 在 INIT MODE 下，必须原样消费 handoff 给它的 canonical path
- 跳过 `fetch_s2.py citations`
- 跳过 `fetch_s2.py references`
- 跳过每个子代理自己的 `rebuild-index`
- 跳过每个子代理自己的 `rebuild-context-brief`
- 跳过每个子代理自己的 `rebuild-open-questions`
- 跳过易冲突 topic 写入
- 子代理退出前必须在各自 worktree 内提交 ingest 结果，避免 fan-in 时 merge 到空 branch
- worktree 命令、merge 顺序、fan-in 与清理见 `references/parallel-ingest.md`

### Step 6: fan-in、rebuild 与最终报告

全部子代理完成后：

- 在 `BASE_BRANCH` 上按顺序 merge worktree branches
- concept / method 冲突默认保守合并，不要扩散 near-duplicate 页面
- 执行：

```bash
"$PYTHON_BIN" tools/research_wiki.py dedup-edges wiki/
"$PYTHON_BIN" tools/research_wiki.py dedup-citations wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki/ --fix
```

接着通过 Semantic Scholar 回填 `cites` 边 —— `fetch_s2.py references` 在每个 worktree 内被跳过（并发安全考虑），必须在此处串行补回。best-effort：S2 故障不可阻塞 `/init`。

```bash
"$PYTHON_BIN" tools/backfill_citations.py --wiki-dir wiki/ \
  || echo "WARN: citation backfill failed or partial; check stderr above" >&2
```

随后重新生成可视化产物（best-effort；visualize 失败不可阻塞 `/init`）。`generate-obsidian-config` 会从 `config/visualize.json` 重写 `wiki/.obsidian/graph.json`，让按实体类型的 colorGroups 与运行时配置保持同步 —— Obsidian 的图谱视图在 `colorGroups` 为空时显示为无色节点，所以这一步保证图谱在每次重建后仍然可读。交互式网页 Graph 视图是 SPA 的 `#/graph` 路由（由 `tools/serve.py` 服务）；本阶段不生成单独的 HTML 文件。

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

若 `stash_ref` 存在，在最后再 pop。若 stash pop 失败，保留 checkpoint 并在报告中说明。

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
- 所有论文 ingest 必须通过并行 `/ingest` 子代理执行
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
- **当前 checkout 处于 detached HEAD**：在 worktree fan-out 前停止，并要求用户先切换到或创建一个命名分支
- **stash pop 失败**：保留 checkpoint metadata，并给出手动恢复提示
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

### Skills

- `/ingest` — 每个子代理只 ingest 一篇论文，且运行在 INIT MODE
- `/visualize` — Step 6 fan-in 直接调用 `tools/visualize.py` 重新生成 Obsidian 颜色组与 Canvas（best-effort）；用户也可以稍后手动调用 `/visualize` 做 `--focus` 视图，或在改了 `config/visualize.json` 后重新渲染

### `init_discovery.py` 内部使用的外部 API

- Semantic Scholar
- DeepXiv（可选）
- arXiv 下载端点
