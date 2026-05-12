---
description: 基于 anchor 论文、topic 关键词或当前 wiki 状态，产出一份排好序的候选论文 shortlist，供用户或上游 skill 决定是否进一步 `/ingest`。当用户问 "接下来该读什么"、"找和这篇相似的论文"、"推荐相关工作"、"这个方向周围有什么" 时触发；`/ingest --discover` 也会内部调用本 skill。本身不 ingest，只提出候选。
argument-hint: "(--anchor <id> [--anchor <id>] [--negative <id>] | --topic <str> | --from-wiki | --venue <slug> --year <int>) [--limit N]"
---

# /discover

> 从四种 seed 模式之一产出一份排好序的候选论文 shortlist，附带每条候选的 rationale，呈现给用户或调用方 skill。`/discover` 绝不自动 ingest —— 它只负责提出候选，实际动作由 `/ingest` 负责。

按需打开下列本地参考文件：

- `references/seed-modes.md` —— 如何把用户的措辞映射到 anchor / topic / wiki / venue 模式，以及四者的选择规则
- `references/ranking-signals.md` —— `tools/discover.py` 的打分依据，以及为什么 discovery 不共享 `/init` 的 survey 偏好
- `references/wiki-dedup.md` —— 候选如何被过滤掉已 ingest 的论文，以及 dedup 边界

## Inputs

- `--anchor <id>`（可重复）：一或多个 anchor 论文 ID（优先 arXiv ID，也接受 S2 paperId）。驱动 **anchor 模式** —— 主要使用场景，包括 `/ingest` 后的 "接下来该读什么"。
- `--negative <id>`（可重复，可选）：希望推开的论文 ID。只在配合 `--anchor` 时有意义。
- `--topic "<str>"`：topic / query 字符串。驱动 **topic 模式** —— 相对 `/init` planner 更轻量的替代。
- `--from-wiki`：自动从 wiki 最近修改过的论文页派生 seed。驱动 **wiki 模式**。
- `--venue <slug>` + `--year <int>`：会议/venue 缩写与年份（如 `neurips` `2024`）。驱动 **venue 模式** —— 从该 venue/year 的论文列表中按与现有 wiki 的相关性排序。
- `--limit N`（可选，默认 10）：shortlist 最大长度。

`--anchor`、`--topic`、`--from-wiki`、`--venue` 四者必须恰好选一。

## Outputs

- `.checkpoints/discover-{seed-slug}-{YYYY-MM-DD}.json` —— 完整 shortlist payload，机器可读；seed slug 基于首个 anchor 或 topic 派生
- 给用户的 markdown 摘要，包含每条候选的 rationale
- `wiki/log.md` —— 仅 anchor/topic/wiki 运行通过 `tools/research_wiki.py log` 追加一行

`/discover` 除了 `log.md` 外不向 `wiki/` 写入任何内容，也不触碰 `raw/`。`from-venue` 更严格：它完全不写 `wiki/`，包括 `wiki/log.md`。是否把候选拉进 wiki 是调用方的决定（之后的 `/ingest`）。

## Wiki Interaction

### Reads

- `wiki/papers/*.md` —— frontmatter 中的 `arxiv`（或旧版 `arxiv_id`），用于与已 ingest 的论文做 dedup
- `wiki/papers/*.md` 修改时间 —— 用于 `--from-wiki` 模式下 anchor 选取
- `wiki/papers/*.md`、`wiki/concepts/*.md`、`wiki/topics/*.md` —— 标题与正文，用于 venue 模式的相关性打分

### Writes

- anchor/topic/wiki 运行：`wiki/log.md` —— 通过 `tools/research_wiki.py log` APPEND
- venue 运行：无

### Graph edges created

- 无。图变更属于 `/ingest`，不属于 `/discover`。

## Workflow

**前置条件**：工作目录包含 `wiki/`、`raw/`、`tools/`。一次解析 Python 解释器路径并复用：

```bash
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  PYTHON_BIN=.venv/Scripts/python.exe
else
  PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: 选定 seed 模式

把用户请求映射到 `from-anchors`、`from-topic`、`from-wiki` 或 `from-venue` 之一。决策规则见 `references/seed-modes.md`，简版：

- 用户指明了一或多篇具体论文，或者这是 `/ingest --discover` 的后续 → **anchors**
- 用户给的是 topic / 方向 / 关键词 → **topic**
- 用户问开放式 "接下来读什么"，没有 anchor 也没有 topic → **wiki**
- 用户要求某个具体会议和年份的论文 → **venue**

如果用户同时提到 "不要这些"，在 anchor 模式下通过 `--negative` 传入。

### Step 2: 运行 discovery 工具

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <arxiv-id> [--id <arxiv-id>...] [--negative <id>...] \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

venue 模式下必须传 `--wiki-root`，以便工具根据现有内容计算相关性。若 wiki 过于稀疏，工具会明确报错而不是返回未个性化的列表。

或 topic / wiki 模式：

```bash
"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
```

anchor（与 wiki）模式每个 anchor 默认跑三个 S2 通道 —— `recommend` + `references` + `citations`。这正是 `/discover` 明显区别于 `/daily-arxiv` 的关键：references 带进 anchor 站在其肩膀上的 canonical 老论文，citations 带进高影响后续工作。只有在 API 成本成为硬约束时才考虑 `--no-citation-expand` 退回到只跑 recommend —— 质量退化会很明显。

工具内部处理候选抓取、wiki dedup、ranking，并写 checkpoint。始终传 `--wiki-root wiki`，否则已 ingest 论文会继续出现在 shortlist 中，浪费用户 review 时间。

topic 模式下若 S2 不可用，工具会继续用可用的通道产出；检查输出并向用户说明 degraded discovery。若全部通道失败，需明确报错而不是把空 shortlist 当作真实推荐返回。

### Step 3: 展示 shortlist

把 markdown 输出呈现给用户。每条候选要能让用户判断是否值得 ingest：

- 标题和 arXiv ID（或 S2 paperId fallback）
- 一行 rationale（工具已产出：anchor 命中数、influential citations、年份）
- 工具带出 TLDR 时一并展示（topic 模式常有；anchor 模式通常没有 —— recommendations endpoint 不返回 TLDR）

最后附一行 "next step" 提示：

```
如需 ingest：/ingest https://arxiv.org/abs/<arxiv-id>
```

不要自行 ingest。选择权归用户。

### Step 4: 日志

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki "discover | mode=<anchors|topic|wiki> | seed=<short-desc> | shortlist=<N>"
```

`from-venue` 跳过这一步；venue discovery 不能写 `wiki/` 或 `raw/`。

## Internal Callers

`/discover` 既供用户手动调用，也供其他 skill 作为子例程调用。

### 来自 `/ingest --discover`

`/ingest` 支持可选的 `--discover` flag（默认关闭）。开启时，`/ingest` 在最终 report 之后以刚 ingest 论文的 arXiv ID 作为单 anchor 调用 `/discover`，并把 shortlist 以 "接下来可能想 ingest 的相关论文" 段落附在 report 里。`/ingest` 不会从这份列表自动 ingest 任何东西。

### 来自 `/init`

`/init` **不调用** `/discover`。`/init` 的 planner（`tools/init_discovery.py plan`）有自己的打分策略，偏爱 survey、广覆盖、seed anchor —— 适合 bootstrap 场景。`/discover` 的 ranking 有意不同（不偏 survey；以 anchor 相似度 + influential citations 为主），替换进 `/init` 会稀释 shortlist 质量。两者保持独立。

## Constraints

- **不自动 ingest**：`/discover` 产出 shortlist 就结束。即便被 `/ingest --discover` 调用，调用方也只是呈现结果，最终 ingest 由用户决定。
- **不向 `wiki/` 写内容**：paper 页、concept、method、graph edge 全都属于 `/ingest`。anchor/topic/wiki 运行可以追加 `wiki/log.md`；`from-venue` 完全不能写 `wiki/`。
- **不写 `raw/`**：`/discover` 不下载论文。用户选定某个候选后，再手动 `/ingest <arxiv-url>`。
- **始终对 wiki 做 dedup**：必须传 `--wiki-root wiki`，否则已 ingest 论文会污染 shortlist，这是最常见的低质量失败模式。
- **ranking 是 discovery 专属**：不要复用或复制 `tools/init_discovery.py` 的打分函数。两者目标不同 —— `/init` 要宽覆盖与基础面；`/discover` 要相关的 *next reads*。见 `references/ranking-signals.md`。
- **三通道 anchor 抓取**：anchor 模式默认对每个 anchor 同时跑 S2 `recommend` + `references` + `citations`。砍掉 citation 通道（`--no-citation-expand`）会让结果退化为偏最新的语义聚类，和 `/daily-arxiv` 严重重合。除非 API 成本成为硬约束，否则保留三个通道。见 `references/ranking-signals.md`。
- **部分 S2 endpoint 字段较扁平**：`/citations`、`/references`、`/recommendations/*` 拒绝嵌套 selector —— 没有 `authors.hIndex`，没有 `tldr`。`/paper/{id}` 和 `/paper/search` 接受，所以 topic 模式的候选带完整 enrichment；anchor 模式下只从 citations/references/recommend 进来的候选没有。这是 S2 的真实约束，不是 bug。
- **rate limit**：anchor 模式每个 anchor 最多三次 S2 调用（recommend + references + citations）。默认 recs 每 anchor 拉 50 条、references/citations 各 30 条。多 anchor 时调用量成倍增长；有 API key（1 req/sec）时三 anchor 约 10 秒。

## Error Handling

- **所有 seed 通道都失败**：明确报错、不写 shortlist，也不记录成功日志。
- **S2 不可用但 DeepXiv 可用（topic 模式）**：仅用 DeepXiv 继续；在 report 中注明 degraded。
- **S2 对某个 anchor 返回零推荐**：保留其他 anchor 的结果继续；若所有 anchor 都返回零，视为整体失败。
- **`--from-wiki` 找不到可用 anchor**（`wiki/papers/` 为空或全部缺少 `arxiv_id`）：告诉用户 wiki 过于稀疏，建议改用 topic 模式（或跑 `/init`）。
- **`from-venue` wiki 过于稀疏**（从 wiki 提取到的有效词太少）：明确报错，建议先 ingest 一些论文或改用 topic 模式。venue 模式依赖现有 wiki 内容计算相关性，没有内容时排名将失去意义。
- **anchor ID 非法或未知**：S2 会返回 404；在 report 中暴露该坏 ID，并用剩余 anchor 继续。

## Dependencies

### Tools（via Bash）

- `"$PYTHON_BIN" tools/discover.py from-anchors --id <id> [--id <id>...] [--negative <id>...] --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-venue --venue <slug> --year <int> --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki "<message>"`

### Skills

- `/ingest` —— 通过 `--discover` flag 调用；也是用户对选中候选执行的动作
- `/init` —— 独立 planner，不调用 `/discover`

### External APIs

- Semantic Scholar —— recommendations (`/recommendations/v1/papers/forpaper/{id}`, `POST /recommendations/v1/papers/`)、search、paper detail（通过 `tools/fetch_s2.py`）
- DeepXiv —— topic 模式下的 search 辅助通道（通过 `tools/fetch_deepxiv.py`，可选，失败时优雅降级）
- Paper Copilot —— 公开 GitHub raw JSON（`papercopilot/paperlists`），用于 venue/year 论文列表。不使用 live-site 抓取，也不把数据集 vendor 进仓库。Venue normalization 应保留来源中已有的 title、abstract、TLDR、keywords / primary area / topic、track、status、citations、ratings、reviews 与论文 URL 等相关性字段。
