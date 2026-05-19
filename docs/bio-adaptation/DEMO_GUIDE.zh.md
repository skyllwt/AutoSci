# Demo 静态图片制作详细操作指南

> 本文是 [`DEMO_PLAN.zh.md`](DEMO_PLAN.zh.md) §6 storyboard 的**静态图片版**替代方案（不录 GIF，全部用截图）。
>
> DEMO_PLAN 写于 2026-05-11（13 项 pilot 合并时）；本指南对齐 2026-05-12 会话结束时的状态（A 8/8 + A4、B 14/14 + infra、C 9/9、D 2/2 全部合并），caption 文案中"drafted/延后"的提法已更新为"live"。
>
> 如需英文镜像，告诉我，我同步建一份 `DEMO_GUIDE.en.md`。

## 0. 比赛上下文与本指南角色（2026-05-18 加注）

本指南原本是为 GitHub README 配图设计的"静态 8 图"方案。**自 2026-05-18 起**，团队报名了**第八届北京智源大会 · Agent for Science 创意大赛**（征集截止 2026-05-30）。比赛要求**五项交付**：① 基础信息 · ② ≤9 页英文 ICLR 模板技术报告 · ③ Poster 海报 · ④ 公开仓库 · ⑤ Demo 视频。

本指南的角色因此扩展为**多用途素材采集**，不再只服务 README：

| 用途 | 由本指南输出 | 备注 |
|---|---|---|
| GitHub README "Demo" 段 | 8 张 PNG 直接用 | 原始目标 |
| **Poster bio panel** | 图 4、图 6、图 7、（可选）图 9 提供 PTM-PROTAC 邻域素材 | 论文 §4 case study 同源 |
| **Demo 视频中段 bio reveal** | 图 4、图 6、图 7 是分镜原画；现场再补 1–2 段录屏 | §6 录屏脚本见 [`COMPETITION_NOTES.zh.md`](COMPETITION_NOTES.zh.md) §6.2 |
| **技术报告 §4 Domain Adaptation** | 图 5、图 6 嵌入 1.5–2 页 bio 章节 | 论文模板：https://www.overleaf.com/read/bvsdjzdttszt#4023ef |

bio 模块在比赛里的定位：**case study，不是分赛道**。主线由团队 PM 主导（科研 Agent · self-evolving · multi-agent），bio 在视频中段 20 秒 reveal、poster 占 1 个 panel、论文占 1.5–2 页。详细 framing 与 P0/P1/P2 优化清单见 [`COMPETITION_NOTES.zh.md`](COMPETITION_NOTES.zh.md)。

## 1. 最终交付物清单（8 张 PNG + 1 张可选）

下表新增 **用途** 列，标记每张图在哪些比赛产物里被使用 —— 截图时请用同一组高分辨率、同一主题，避免事后重截。

| # | 文件名 | 内容 | 时间预估 | 用途（README / Poster / Video / Paper §4）|
|---|---|---|---|---|
| 1 | `assets/demo-01-paper.png` | musitedeep paper frontmatter（A3 + A4 live） | 3 min | README · Paper |
| 2 | `assets/demo-02-idea-main.png` | PTM-aware degrader idea（A7 grade + 8 linked experiments） | 3 min | README · Poster · Paper |
| 3 | `assets/demo-03-idea-failed.png` | ptm-site-disorder failed idea（C3 banlist scope） | 3 min | README · Video（self-evolving reveal）|
| 4 | `assets/demo-04-experiment.png` | deepternary-baseline experiment（A5 + A6 + A8）—— **5-ID 复现块最高密度生物锤** | 5 min | README · **Poster · Video · Paper**（四投）|
| 5 | `assets/demo-05-dataset.png` | ternarydb dataset page（A1） | 2 min | README · Paper |
| 6 | `assets/demo-06-spa-graph.png` | SPA 全图，聚焦 PTM 邻域（14 bio edges live）| 5 min | README · **Poster · Video · Paper**（四投）|
| 7 | `assets/demo-07-spa-metadata.png` | typed metadata JSONL grep 输出（B-infra） | 3 min | README · **Video**（bio reveal 50-55s 替代镜头）|
| 8 | `assets/demo-08-digest.png` | terminal `bash demo/run-demo.sh` 输出 | 3 min | README · Video（hook 0-10s） |
| 9（可选） | `assets/demo-09-canvas.png` | Obsidian Canvas PTM 邻域知识图 | 8 min | Poster · Video（bio reveal 40-45s 替代镜头）|

总计 **30-40 分钟**（含一次性 setup）。

> **新增素材**（不在本指南里，由 `COMPETITION_NOTES.zh.md` §5 P0 任务交付）：
> - `examples/output/bio-novelty-report.md` —— 视频锤 3（PubMed multi-source）
> - `examples/output/bio-ideate-banlist.md` —— 视频锤 5/6（scope-overlap + dose_response）
> - 这两份是终端输出文本，由我（Claude）写，不用截图。视频里直接 `cat` 显示即可。

## 2. Pre-flight（5 分钟）

### 2.1 截图工具（Windows 内置即可）

无需安装任何东西。用 **Windows Snipping Tool**：`Win + Shift + S` 截屏 → 自动复制到剪贴板 → 在 `mspaint` 或 Snip & Sketch 里粘贴 → 保存 PNG。

如需框选高亮 / 箭头标注，推荐 **ShareX**（`winget install ShareX`）—— 截屏后自动跳到带标注工具的编辑器，可加红框 / 箭头 / 文字。

### 2.2 生成 SPA 数据 + 启动 SPA（为图 6–7）

```bash
# 终端 1（后台跑）
.venv/bin/python tools/serve.py
# 默认 http://localhost:8765/
```

WSL2：Windows 浏览器开 `http://localhost:8765/`。

### 2.3 跑 daily-arxiv demo 一次（为图 8）

```bash
bash demo/run-demo.sh
# 把输出留在终端，准备截图
```

### 2.4（可选）生成 Obsidian Canvas（为图 9）

在 Claude Code 里执行 skill：

```
/visualize --canvas --focus ideas/ptm-aware-degrader-target-nomination --depth 2
```

然后 Obsidian 打开 `wiki/` 作为 vault，导航到 `wiki/canvases/*.canvas`。

## 3. 逐图操作

每张图请把**文件路径/窗口标题栏**保留在截图里（读者能看出来源）。

### 图 1 ——`demo-01-paper.png`（paper frontmatter）

**操作**：

1. VS Code 或文本编辑器打开 `wiki/papers/musitedeep-deep-learning-based-webserver-protein.md`
2. 折叠正文 / 滚动到 frontmatter 顶部
3. 截图覆盖 frontmatter 全部（约第 1–25 行）

**应包含字段**（读者一眼能看到）：

- `title:`、`venue: Nucleic Acids Research`、`year: 2020`
- `doi: "10.1093/nar/gkaa275"` ← A3
- `pmid: "32324217"` ← A3
- `domain: "bioinformatics"` ← A4 规范化 slug

**建议**：用 ShareX 在 doi / pmid / domain 三行画红框。

### 图 2 ——`demo-02-idea-main.png`（main idea page）

**操作**：

1. 打开 `wiki/ideas/ptm-aware-degrader-target-nomination.md`
2. 截图 frontmatter 全部 + 正文 `## Motivation` 前 2-3 行

**应包含字段**：

- `status: in_progress`
- `priority: 5`
- `grade: "low"` ← A7
- `linked_experiments:`（8 项 flow list，裸 slug；2026-05-19 从 `[[wikilink]]` 形式规范化以通过 Obsidian frontmatter 校验，详 commit `726ef38`）
- `domain: "comp-drug-discovery"` ← A4
- `tags: [...]`

**建议**：在 `grade` 和 `linked_experiments` 上画红框。

### 图 3 ——`demo-03-idea-failed.png`（failed idea + scope）

**操作**：

1. 打开 `wiki/ideas/ptm-site-disorder-predictor.md`
2. 截图 frontmatter 全部（scope 块务必入镜）

**应包含字段**：

- `status: failed`
- `failure_reason: "[filter] saturated by SAPP (2025), PhosAF (2024), ..."` ← C3 上下文
- `scope.species: [human, mouse]` ← **C3 关键**
- `scope.disease_area: []`
- `scope.data_regime: high_data` ← **C3 关键**

**建议**：把 `scope:` 块整体框出。Caption 配 "C3 banlist scope：植物 PTM / 跨物种低数据迁移不会被这条 failed idea 屏蔽"。

### 图 4 ——`demo-04-experiment.png`（experiment with bio fields）

**操作**：

1. 打开 `wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md`
2. 滚动到 setup + estimated_cost + reproducibility 都可见（可能需要适当折叠/缩小字体）
3. 截图覆盖 frontmatter

**应包含字段**：

- `setup.dataset: "[[ternarydb]] ..."` ← A5 wikilink
- `setup.in_silico_or_wet: "in_silico"` ← A5 full
- `setup.species: ["human"]`
- `setup.assay_type: "scoring"`
- `setup.random_seed_protocol: "ranking-shuffle (>= 3 seeds)"` ← C6
- `estimated_cost: { gpu_hours: 4, ... }` ← A6
- `reproducibility.dataset_versions: [{dataset_slug: ternarydb, version: v1, accessed_date: ...}]` ← **A8 关键**

**建议**：这是 bio 信息密度最高的一张，可以分两栏标注：左 setup bio 字段、右 reproducibility。

### 图 5 ——`demo-05-dataset.png`（dataset page）

**操作**：

1. 打开 `wiki/datasets/ternarydb.md`
2. 截图 frontmatter + `## Overview` 前几行

**应包含字段**：

- `title: "TernaryDB"`
- `access: "public"`
- `maturity: "stable"`
- `versions: [{version: "v1", released: ..., notes: ...}]`
- `key_papers: [...]`（可能为空 list，没关系）

**建议**：caption "A1 第 10 类实体：dataset 一等公民，版本表通过 lint_bio.py 与实验 reproducibility.dataset_versions cross-check"。

### 图 6 ——`demo-06-spa-graph.png`（SPA 全图）

**操作**（2026-05-19 修订 —— 原计划"4 节点同框"基于过乐观拓扑假设，`ternarydb` 实际在 PTM-aware-degrader 2 跳外、`crbn`/`ubiquitin-ligase-e3` 在 3 跳外，硬塞同帧会缩到 label 不可读）：

1. 浏览器开 `http://localhost:8765/`
2. 左侧搜索框输 `ptm-aware-degrader-target-nomination`，点搜索结果让节点居中 + BFS 高亮邻居（`app/modules/graph.js:53,350`）
3. BFS 深度 = **2**：一跳直邻 + 二跳邻居入镜（5 inspiring papers + 5 close ideas + 5 experiments 经由 `ptm-protein-isoforms-enable-selective-drug` hub）
4. 滚轮放大到 label 可读（节点名约 12-14px）
5. 截图浏览器视口（不必含 URL 栏，但要让读者看出是 web app）

**建议**：caption "PTM-aware-degrader idea hub @ BFS depth 2：4 papers / 3 experiments / 2 concepts / 2 邻接 ideas 全在视野；14 个 bio edge labels live（`tested_by` / `addresses_gap` / `inspired_by` / `introduces_concept` 在画面里都能读）。`ternarydb` 与 `crbn` 在 +1 跳外（typed metadata 见图 7）。"

### 图 7 ——`demo-07-spa-metadata.png`（typed metadata via JSONL）

> **2026-05-18 验证**：SPA **不显示**边 metadata —— `app/modules/graph.js:146-160` 把边映射到 Cytoscape 时只保留 `id/source/target/label/workflow/symmetric`，`metadata/evidence/confidence/date` 全被丢弃；且没有 edge `tap`/`hover` 处理器。所以图 7 直接走 JSONL 终端截图（DEMO_GUIDE 原本就把这条列为后备）。

**操作**：

1. 干净终端 `clear`
2. 跑：

```bash
grep -F 'phase0-noise-floor-calibration-deepternary-ptm-perturbations' wiki/graph/edges.jsonl \
  | grep -F 'dataset_version_used' \
  | python3 -m json.tool
```

3. 截图终端窗口（包含命令本身 + pretty-printed JSON 输出）

**应展示**：

- 边类型 `dataset_version_used`
- 端点 `experiments/phase0-noise-floor-... → datasets/ternarydb`
- `confidence: high`
- `metadata: {"version": "v1", "subset": "crbn-vhl-training"}` ← **关键**

**建议**：caption "B-infra typed metadata：closed-set schema 验证（loader.py 校验 required key + type），未声明 key 触发 lint warning；lint_bio cross-checks `metadata.version` 与 `datasets/ternarydb.md::versions[].version`"。

### 图 8 ——`demo-08-digest.png`（daily-arxiv 输出）

**前置**（2026-05-19 加注）：`demo/run-demo.sh` 跑 LLM 排序需要 `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` 三个环境变量都在 `.env` 或 `~/.env` 里就位（与 Review LLM 共用一套配置）。原脚本 `:45` 处 gate 写成 `DEEPSEEK_API_KEY` 是过时变量名，commit `e54c2f5` 已修。验证：`grep -E "^LLM_(API_KEY|BASE_URL|MODEL)=" .env` 应输出 3 行。

**操作**：

1. 一个干净的终端（`clear`）
2. 跑 **`bash demo/run-demo.sh && echo && head -25 examples/output/digest.md`** —— `run-demo.sh` 本身不打印 digest 内容，串个 `head` 把 `## Strong Recommendations` 第一段一起呈现
3. 等到 `Decision: strong_recommend / confidence high / score X.X` 行出现
4. 截图整个终端窗口（命令首行 + 3-step progress + Summary + 第一篇 strong recommendation）

**建议**：用深色背景终端（更显专业）。Caption "live daily-arxiv：9 篇 q-bio.BM mock feed → DeepSeek v4-flash 排序（N decisions）→ strong/maybe/skip digest（score + rationale by LLM）。第 2 步缺 LLM_API_KEY 时优雅退化为 tool-signals-only fallback —— 见 `demo/run-demo.sh:45` 的 gate。"

### （可选）图 9 ——`demo-09-canvas.png`（Obsidian Canvas）

**操作**：

1. Obsidian 打开 `wiki/` 作为 vault（WSL Linux 端原生跑：`~/bin/obsidian /home/yukino/OmegaWiki/wiki`，详 `CHECKPOINT-2026-05-18.zh.md` §3.3）
2. 导航到 `wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas`（由 `/visualize --canvas --focus ideas/ptm-aware-degrader-target-nomination --depth 2` 生成，5 行流水线布局 v2，2750×1900）
3. 手动微调节点位置消除遮挡（拖拽 live-sync 到 `.canvas` 文件，但 `wiki/canvases/` 在 `.gitignore` 里，本地工作产物不进 git；最终截图进 git）
4. 截图整个 canvas 视口 → `assets/demo-09-canvas.png`（已存在，commit `31e8cfe`）

## 4. 截图素养（让图看起来专业）

1. **窗口尺寸**：建议截图 1600×1000（或 1400×900），分辨率一致
2. **字体**：VS Code 字号 14 或更大，行高 1.5；终端 14pt
3. **主题**：全部用同一主题（全亮色 or 全暗色，别混）
4. **空白边距**：窗口标题栏保留 ——让读者知道这是个真实的 IDE / 浏览器
5. **高亮**：用红框圈关键字段，不要红框堆得太密（每张图最多 2-3 个红框）
6. **不需要打码**：这些都是开源 wiki，无敏感信息

## 5. 后处理（批量压缩）

WSL 下：

```bash
# 装 pngquant（轻量）
sudo apt install pngquant
# 批量压（原地覆盖）
for f in assets/demo-*.png; do
    pngquant --quality=85-95 --skip-if-larger --output "$f" "$f" --force
done
ls -lh assets/demo-*.png
# 目标:每张 < 500 KB,总 < 4 MB
```

Windows 主机直接用 [TinyPNG.com](https://tinypng.com/) 拖进去也行 ——免安装。

## 6. 提交

```bash
git add assets/demo-*.png
git commit -m "$(cat <<'EOF'
docs(demo): add 8-panel static-screenshot demo set

Static images covering bio-adaptation deliverables:
01 paper frontmatter (A3 doi/pmid + A4 domain slug)
02 idea page (A7 grade + linked_experiments)
03 failed idea (C3 banlist scope: species + data_regime)
04 experiment page (A5 setup bio fields + A6 cost + A8 reproducibility)
05 dataset page (A1 ternarydb + versions list)
06 SPA full graph (B1/B2/B3 live edges)
07 SPA edge tooltip (B-infra typed metadata)
08 daily-arxiv digest terminal output

Total size after pngquant: ~XX MB.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## 7. 在 README 里展示这些图

我可以在你截好图后，帮你改 README.md 的 "See it live" 段（或新增一个 "Demo" 段），用 markdown 把 8 张图按顺序贴入，每张配一句 caption + 一行 backlog 节标识。要的话拍完图来找我。

## 速查清单

```text
□ 启动 SPA: .venv/bin/python tools/serve.py
□ (可选) /visualize --canvas --focus ideas/ptm-aware-degrader-target-nomination --depth 2
□ 截 8 张图:
    01 papers/musitedeep                      (frontmatter)
    02 ideas/ptm-aware-degrader-target-...    (main idea)
    03 ideas/ptm-site-disorder-predictor      (failed + scope)
    04 experiments/deepternary-baseline-...   (setup+cost+repro)
    05 datasets/ternarydb                     (versions list)
    06 SPA 全图                                (浏览器视口)
    07 SPA 边 tooltip                          (typed metadata)
    08 终端 bash demo/run-demo.sh             (digest 输出)
    [09 Obsidian canvas]                      (可选)
□ pngquant 压缩 → assets/demo-*.png
□ git add + commit
□ 改 README 添加 demo section(找我或自己写)
```
