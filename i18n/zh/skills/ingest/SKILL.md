---
description: 把一篇论文 ingest 进 wiki —— 建立 papers + concepts + people + claims 页面，并完成所有双向交叉引用与 graph edge。当用户说 "ingest"、"加入这篇论文"、丢 `.pdf` / `.tex` / arXiv URL 或要求把论文折叠进知识库时触发。
argument-hint: <local-path-or-arXiv-URL> [--discover] [--visualize]
---

# /ingest

把一篇论文转化成一组正确链接的 wiki 页面。`/ingest` 的职责是写出 well-shaped 的实体与正确的双向链接；语义层面的审计（反向链接对称性、dangling node、字段取值合规）留给 `/check`。

按需打开下列本地参考文件：

- `references/pdf-preprocessing.md` —— 直接 PDF 输入时的 arXiv-ID 恢复、tex 抓取、prepare-paper 交接流程
- `references/dedup-policy.md` —— concept / claim 的合并与新建决策规则，以及 `/ingest` 形状检查与 `/check` 语义审计的边界
- `references/cross-references.md` —— 正向/反向链接矩阵与 paper-to-paper edge 类型选择
- `references/init-mode.md` —— `/init` 的 manifest 交接与并行安全约束
- `references/error-handling.md` —— 来源解析、API 与 slug 冲突的 fallback

写 wiki 页面 frontmatter 字段去 `runtime/schema/entities.yaml`,正文章节顺序去 `runtime/templates/{kind}.md.tmpl`;`index.md`、`log.md`、`graph/` 形状去 `runtime/schema/conventions.yaml` 与 `runtime/schema/edges.yaml`。

## Inputs

- `source`：四种之一 —— arXiv URL（例如 `https://arxiv.org/abs/2106.09685`）、本地 `.tex`、本地 `.pdf`、或 `/init` 通过 `.checkpoints/init-sources.json` 交接的 `canonical_ingest_path`（见 `references/init-mode.md`）
- `--discover`（可选，默认 **关闭**）：在最终 report 之后调用 `/discover --anchor <this-paper's-arxiv-id>`，把 shortlist 作为 "接下来可能想 ingest 的相关论文" 附在 report 里。从不自动 ingest 推荐结果。INIT MODE 下自动跳过。视为用户可见参数：不得仅根据仓库状态擅自开启。
- `--visualize`（可选，默认 **关闭**）：在 Step 7 rebuild 之后通过 `tools/visualize.py generate-canvas` 重新生成 Canvas 可视化产物。INIT MODE 下自动跳过 —— 由上层 `/init` 在 fan-in 时统一处理可视化。视为用户可见参数：不得仅根据仓库状态擅自开启。（交互式网页 Graph 视图位于 SPA 的 `app/modules/graph.js`，由 `tools/serve.py` 服务，直接读取 `wiki/graph/`，不需要每次 ingest 单独重生成。）

## Outputs

- 一篇完整链接的论文页面及其关联实体（concepts、claims、people）
- 通过 `tools/research_wiki.py` 追加的 graph edges 与 citations
- 终端汇总报告（新增页面数、建议后续 ingest 的论文）

## Wiki Interaction

### Reads

- `wiki/index.md`，用于获取所有已存在 slug 与 tag
- `wiki/papers/*.md`，用于识别已 ingest 过的论文
- `wiki/concepts/*.md`、`wiki/foundations/*.md`，用于 dedup 匹配
- `wiki/claims/*.md`，用于 dedup 匹配
- `wiki/people/*.md`，用于识别已有作者
- `wiki/topics/*.md`，用于将论文归入已有 topic
- `wiki/graph/open_questions.md`，用于识别论文是否填补了已知 gap

### Writes

- `wiki/papers/{slug}.md` —— CREATE
- `wiki/concepts/{slug}.md` —— CREATE（新建）或 EDIT（追加 `key_papers`、aliases、variants）
- `wiki/claims/{slug}.md` —— CREATE（新建）或 EDIT（追加 `evidence` 条目）
- `wiki/people/{slug}.md` —— CREATE（仅当 importance ≥ 4）或 EDIT（追加 `Key papers`）
- `wiki/topics/{slug}.md` —— 只允许 EDIT，`/ingest` 不得 CREATE 新 topic
- `wiki/graph/edges.jsonl` —— 通过工具 APPEND
- `wiki/graph/citations.jsonl` —— 通过工具 APPEND
- `wiki/graph/context_brief.md` —— REBUILD（INIT MODE 下跳过）
- `wiki/graph/open_questions.md` —— REBUILD（INIT MODE 下跳过）
- `wiki/index.md` —— APPEND
- `wiki/log.md` —— 通过工具 APPEND
- `wiki/canvases/*.canvas` —— CREATE/OVERWRITE（仅当 `--visualize` 开启且非 INIT MODE）

### 会新增的 Graph edges

- `paper → concept`：`introduces_concept` / `uses_concept` / `extends_concept` / `critiques_concept`，并写 `confidence`
- `paper → foundation`：`derived_from`（foundation 是终端节点，无反向链接）
- `paper → claim`：`supports` / `contradicts`
- `paper → paper`：`same_problem_as` / `similar_method_to` / `complementary_to` / `builds_on` / `compares_against` / `improves_on` / `challenges` / `surveys`，并写 `confidence`
- bibliographic `paper → paper`：`graph/citations.jsonl` 中的 `cites`

`tools/research_wiki.py add-edge` 会拒绝缺少 confidence/evidence 的
paper-paper 与 paper-concept semantic edge，也会拒绝新写入 legacy
paper-to-concept 或 paper-to-paper 类型。

## Workflow

**前置条件**：工作目录下同时存在 `wiki/`、`raw/`、`tools/`。先解析一次 Python interpreter 并复用：

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

### Step 1: 解析来源

1. 如果 `/init` 交接了 `canonical_ingest_path`，进入 **INIT MODE** 并原样消费该路径，不要重新扫描 `raw/`。详见 `references/init-mode.md`。
2. 如果来源是 arXiv URL，先提取 arXiv ID；可用时通过 `"$PYTHON_BIN" tools/fetch_s2.py paper <arxiv-id>` 恢复标题，然后运行 `"$PYTHON_BIN" tools/init_discovery.py download --raw-root raw --arxiv-id <arxiv-id> --title "<title-or-arxiv-id>"`。后续从返回的 `canonical_ingest_path` 继续。该 helper 会先尝试 arXiv source，再 fallback 到 PDF；不要用 `fetch_arxiv.py` 处理单篇论文，因为它只用于 RSS。
3. 如果来源是本地 `.tex`，直接使用。
4. 如果来源是本地 `.pdf`，先走 `references/pdf-preprocessing.md` 的预处理流程，在 `raw/tmp/` 下生成 prepared `.tex`，再继续。

raw 持久化规则：已经在 `raw/discovered/`、`raw/tmp/`、`raw/papers/` 中的文件，不得被复制或重写到别的 raw 子目录。

### Step 2: 论文身份与 enrichment

1. 生成 paper slug：

   ```bash
   "$PYTHON_BIN" tools/research_wiki.py slug "<paper-title>"
   ```

2. 冲突检查：若 `wiki/papers/{slug}.md` 已存在且 arXiv ID 或标题一致，报告并退出；若不一致，按 `references/error-handling.md` 处理冲突。
3. 有 arXiv ID 时查询 Semantic Scholar：

   ```bash
   "$PYTHON_BIN" tools/fetch_s2.py paper <arxiv-id>
   ```

   用于填写 `venue`、`year`、`s2_id`、citation count，以及 `importance`（1-5）的评估依据。
4. 可选 DeepXiv enrichment，失败则静默跳过：

   ```bash
   "$PYTHON_BIN" tools/fetch_deepxiv.py brief <arxiv-id>
   "$PYTHON_BIN" tools/fetch_deepxiv.py head <arxiv-id>
   "$PYTHON_BIN" tools/fetch_deepxiv.py social <arxiv-id>
   ```

   `brief` 用于 seed Key idea；`head` 用于对照 tex 解析的章节结构；`social` 作为 importance 的辅助信号。

### Step 3: 写 paper 页面

打开 `runtime/schema/entities.yaml`(papers 段)看字段集,`runtime/templates/papers.md.tmpl` 看正文章节顺序。填写全部必需 frontmatter 字段;`cited_by` 本步骤留空,Step 5 再回填。

写入前对即将输出的 frontmatter 做一次**形状检查** —— 仅限以下范围：

- 每个必需字段都存在且非空
- `importance` ∈ {1,2,3,4,5}；claim 的 `status` 在合法集合内；concept 的 `maturity` 在合法集合内；claim 的 `confidence` ∈ [0,1]
- YAML 可解析

形状检查刻意保持狭窄：反向链接对称性、dangling node、跨实体一致性是 `/check` 的工作，不是本 skill 的。

正文章节：Problem、Key idea、Method、Results、Limitations、Open questions、My take、Related。

### Step 4: concept / claim / people

按 `references/dedup-policy.md` 执行。简要步骤：

1. 每个 concept / claim 候选都先调用对应的 `find-similar-*` 工具。
2. 默认合并到 top 结果。只有在工具返回无可用候选、且论文 importance 确实证明新建合理时，才新建页面。
3. 每写一条正向链接，同一 turn 内写入其反向链接。义务矩阵见 `references/cross-references.md`。
4. 仅当 importance ≥ 4 才允许新建 `wiki/people/{slug}.md`；否则只允许向已有作者页面追加。

### Step 5: paper-to-paper edge 与 `cited_by`

INIT MODE 下整步跳过 —— 由上层 `/init` 在 fan-in 时统一处理。

```bash
"$PYTHON_BIN" tools/fetch_s2.py references <arxiv-id>
"$PYTHON_BIN" tools/fetch_s2.py citations <arxiv-id>
```

- 对于 references 中 arXiv ID 或标题能解析到 `wiki/papers/{slug}.md` 的条目，在 `graph/citations.jsonl` 写一条 bibliographic `cites` 记录。
- 只有当原文给出清晰信号时，才在 `graph/edges.jsonl` 写 semantic paper-to-paper edge。选型规则见 `references/cross-references.md`。若没有能干净对应的语义关系，只保留 `cites` 记录。
- 对于 citations 中已在 wiki 的引用者，在本论文的 `cited_by` 追加引用者 slug。
- 在最终报告中列出未匹配的高引用 references，供用户决定是否后续 `/ingest`。

### Step 6: topic 与 index

1. 将论文的 domain 与 tags 对 `wiki/topics/*.md` 做匹配。对每个命中 topic：
   - importance ≥ 4 → 追加到 `## Seminal works`
   - importance < 4 → 按年份追加到 `## SOTA tracker` 或 `## Recent work`
   - 若论文直接回应了 topic 中列出的 open problem，在对应行上标注
2. `/ingest` 不得新建 topic 页面 —— topic 创建属于 `/init` 与 `/edit`。
3. 在 `wiki/index.md` 对应分类下追加新增或编辑过的条目。格式:每个 entity kind 是顶层 YAML 键(对应 `runtime/schema/entities.yaml`),其下挂 `- slug: <slug>`。

### Step 7: 日志与 rebuild

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki/ "ingest | added papers/<slug> | updated: <list>"
```

非 INIT MODE 下再执行：

```bash
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
```

### Step 7.5: 可选的可视化（仅当 `--visualize` 开启）

只有用户显式传 `--visualize` 时才执行本步。INIT MODE 下也一律跳过 —— `/init` 父流程在 fan-in 时统一重生成 Canvas，单个子代理不应重复执行从而引入并发写。

开启后，重新生成 Canvas（best-effort；visualize 失败不应让 `/ingest` 失败）：

```bash
"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/ \
  || echo "WARN: visualize generate-canvas failed; run /visualize manually" >&2
```

`--obsidian` 不在这里重新生成 —— `wiki/.obsidian/graph.json` 是项目级静态配置，只有在 `config/visualize.json` 调色板变化时才需要重写；那种情况下手动跑 `/visualize --obsidian`。

### Step 8: 汇报

输出一个紧凑 summary：新建的页面、编辑的页面、新增的 graph edge、发现的 contradiction（如有）、尚未 ingest 的高引用 references（后续 `/ingest` 建议）。末尾一行：

```
Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges
```

### Step 9: 可选的 discovery（仅当 `--discover` 显式开启）

如果用户没有显式传 `--discover`，跳过本步骤。INIT MODE 下也一律跳过 —— 是否在 fan-in 之后跑 discovery，是 `/init` 父流程的决定，不是单个子代理的决定。

开启时，用刚 ingest 论文作为单 anchor 调用 `/discover`：

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <arxiv-id-of-this-paper> \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

把 markdown 输出附在 report 下一个 "接下来可能想 ingest 的相关论文" 小节里。**不要**自动 ingest 列表里的任何东西 —— 由用户挑选。若 discovery 失败（S2 故障、所有通道返回空），在 report 里一行说明并继续 —— discovery 失败不应让一次成功的 `/ingest` 也算失败。

## Constraints

- `raw/papers/`、`raw/notes/`、`raw/web/` 归用户所有且只读。直接本地 `/ingest` 可在 `raw/tmp/` 下新增 prepared sidecar；直接 arXiv ingest 可把源归档写到 `raw/discovered/`。INIT MODE 下 `raw/` 全部只读。
- `wiki/graph/` 由工具维护。仅通过 `tools/research_wiki.py` 修改。
- slug 始终来自 `tools/research_wiki.py slug`，不得手写。
- 每一条正向链接必须在同一 turn 内写入其反向链接 —— 这是 wiki 的双向链接不变量。唯一例外是指向 `wiki/foundations/` 的链接，foundations 是终端节点。
- 在 INIT MODE 下，不要向已有页面（由 sibling worktree 或 scaffold 创建的）写入反向链接。只通过 `tools/research_wiki.py add-edge` 记录关系；上层 `/init` 在 fan-in 时统一回填反向链接。
- 来源优先级：`.tex` > `.pdf` > vision API fallback。只要有可用 `.tex`，就不从 PDF ingest。
- ingest 对新实体保守：
  - importance < 4：每篇论文最多 **1** 个新 concept、**1** 个新 claim
  - importance ≥ 4：每篇论文最多 **3** 个新 concept、**2** 个新 claim
  - 超出上限的候选，必须合并到最接近的 `find-similar-*` 结果，或整体跳过交给 `/check` 标记。规则与理由：`references/dedup-policy.md`。
- `/ingest` 只对自己写出的内容做形状检查（必需字段、枚举取值、YAML 可解析），到此为止。反向链接对称性、dangling node、完整语义审计属于 `/check`，不要在本 skill 内重复实现。
- 必须假设有其他 `/ingest` 在并行 worktree 中同时运行 —— 批量 ingest 已在路线图上。所有对共享文件（`graph/edges.jsonl`、`graph/citations.jsonl`、`index.md`、`log.md`）的写入必须经过 `tools/research_wiki.py` 或采用 append-only 语义。详见 `references/init-mode.md`。
- INIT MODE 下跳过 `fetch_s2.py citations`、`fetch_s2.py references`，以及 `rebuild-*` 命令 —— 由上层 `/init` 在 fan-in 后统一运行。
- INIT MODE 下也跳过 Step 7.5 的可视化重生成（无论 `--visualize` 是否开启）；由上层 `/init` 在 fan-in 时统一调用 visualize，避免 sibling worktree 间的并发写。

## Error Handling

详见 `references/error-handling.md`。要点：来源解析按 tex → PDF → vision API → 报告用户的顺序 fallback；S2 不可用时 `importance` 默认取 3 并跳过 citation 回填；DeepXiv 不可用时静默跳过 enrichment；slug 冲突追加数字后缀。

## Dependencies

### Tools（via Bash）

- `"$PYTHON_BIN" tools/research_wiki.py slug "<title>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-concept wiki/ "<title>" --aliases "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-claim wiki/ "<title>" --tags "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py add-edge wiki/ --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`
  - paper-paper 与 paper-concept semantic edge 必须带 `--confidence high|medium|low`。
- `"$PYTHON_BIN" tools/research_wiki.py add-citation wiki/ --from papers/<citing> --to papers/<cited> --source semantic_scholar`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/`
- `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]`
- `"$PYTHON_BIN" tools/init_discovery.py download --raw-root raw --arxiv-id <id> --title "<title-or-id>"` —— 单篇论文下载到 `raw/discovered/`，优先 arXiv source，fallback 到 PDF
- `"$PYTHON_BIN" tools/fetch_s2.py paper|citations|references <arxiv-id>`
- `"$PYTHON_BIN" tools/fetch_deepxiv.py brief|head|social <arxiv-id>`
- `"$PYTHON_BIN" tools/discover.py from-anchors --id <arxiv-id> --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown` —— 仅当 `--discover` 开启
- `"$PYTHON_BIN" tools/visualize.py generate-canvas wiki/` —— 仅当 `--visualize` 开启且非 INIT MODE

### Shared References

- `.claude/skills/shared-references/citation-verification.md`

### Skills

- `/init` —— 通过 INIT MODE 并行调用 `/ingest` 子代理
- `/check` —— 在 `/ingest` 完成后审计 wiki，负责所有 `/ingest` 故意不做的语义检查
- `/discover` —— 可选后续，当 `--discover` 开启时运行；产出用户可能想接着 ingest 的相关论文 shortlist

### External APIs

- Semantic Scholar（via `tools/fetch_s2.py`）
- DeepXiv（via `tools/fetch_deepxiv.py`，可选；不可用时自动降级）
- arXiv（源下载）
