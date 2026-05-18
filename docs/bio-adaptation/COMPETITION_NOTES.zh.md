# 智源 Agent for Science 大赛 — 生物分支作战备忘

> **Author**: Head of Bio Applications
> **Created**: 2026-05-18（征集截止 2026-05-30，剩 12 天）
> **配套**：[`DEMO_GUIDE.zh.md`](DEMO_GUIDE.zh.md) · [`REPORT.zh.md`](REPORT.zh.md) · [`CHECKPOINT-2026-05-12.zh.md`](CHECKPOINT-2026-05-12.zh.md) · [`CHANGELOG.zh.md`](CHANGELOG.zh.md)
>
> 本备忘的两个目的：
>
> 1. 让团队主线（**科研 Agent · self-evolving · multi-agent**）写到 paper / poster / 视频里时，bio 模块**不拆台**且**有视觉锤**
> 2. 列出 12 天内我能动手的 bio 局部优化（按 P0/P1/P2，每项含估时与演示用途）

## 1. 比赛事实卡（一屏看清）

| 项 | 内容 |
|---|---|
| **主办** | 第八届北京智源大会 · 「Agent for Science」创意大赛 |
| **关键日程** | 征集 2026-05-10 → **05-30** ·  评审 06-01→06-03 · 现场展示 06-12-13 · 大会报告 06-13 |
| **地点** | 北京中关村国际创新中心 |
| **主旨原话** | "查资料、做实验、写论文，**能干活、能落地、能复现**" |
| **评审** | 8 位国内外顶尖高校教授现场点评 |
| **奖励** | 优胜奖 + 惊喜奖 + 大会舞台公开宣讲 + 入围作品现场展示 |
| **资格** | 国内外在校学生 |
| **五项必交付** | ① 基础信息 · ② 技术报告（≤9 页英文，ICLR-改编模板）· ③ Poster 海报 · ④ 公开仓库（GitHub）· ⑤ Demo 视频 |
| **未指定** | 视频时长 / 格式 / 团队人数上限（按宽松解读）|
| **论文模板** | https://www.overleaf.com/read/bvsdjzdttszt#4023ef |

## 2. 主线三轴 × 生物锚点 — 故事 framing

> 主线由 PM/Lead 主导，生物模块在每轴提供"它真做了"的实证锚点。
> Bio 不开辟新故事线，**只为主线作证**。

### 2.1 Self-evolving × Bio

主线论点："Wiki 自我演化 —— 每跑一次实验，graph 自我扩张；每个失败 idea 进入下一轮 banlist。"

Bio 实证锚点：
- **`concepts.maturity` 9 状态机** (D2)：`hypothesis → contested → well-supported → consensus / falsified` —— 是 wiki 自身的认知演进维度
- **24 页 domain-slug 迁移** (A4)：bio 加了 15-slug `RECOGNISED_DOMAINS` 集合，9 个 free-text 变体已经被自动规范化为 7 个 canonical slug —— 不是 mock，是 16 commits 演进出来的实际状态
- **22 ideas 历经 4 状态流转**：11 validated / 2 failed / 9 in 其他状态 —— `failed` 是 /exp-eval 真实写入的，触发 /ideate 下轮 banlist 演进
- **14 个 bio edge types + 5 typed metadata schema** (B1-3 + B-infra)：从 0 到 14 是 12 个 pilot 累计扩展的"图模式"演化

### 2.2 Multi-agent × Bio

主线论点："25 个 specialized agents 协作完成研究闭环。"

Bio 实证锚点：
- **`/research` orchestrator** 是 explicit multi-agent runner：discovery → ingest → ideate → designer → runner → evaluator → writer → compiler
- **`/review` 跨模型 reviewer**：主模型 + DeepSeek v4-flash 独立评分 —— **跨模型一致性 = multi-agent 的硬证据**
- **`/novelty` 4-source 并行** (Source A-E)：WebSearch + Semantic Scholar + **PubMed E-utilities** + wiki + Review LLM cross-verify —— bio 是**唯一加 PubMed 通道**的 vertical，证明 multi-channel agent 框架支持 domain-specialized 行为
- **25+ skills 各司其职**：每个是带工具集 + system prompt 的 sub-agent；视频里相册式扫一遍 `.claude/skills/*.md` 列表即可成立 "multi-agent" framing

### 2.3 能复现 × Bio

主线论点："所有节点可复现、所有边可追溯证据。"

Bio 实证锚点：
- **`experiments.reproducibility` 块** (A8)：每个 experiment 必填 `rrid / cellosaurus / addgene / pdb_versions / dataset_versions` —— 5 个 ID 维度
- **`tools/lint_bio.py` 闭环 cross-check**：`experiments[].reproducibility.dataset_versions[].version` ⇄ `datasets/[].versions[].version`，不一致即报警
- **5 个边类型 typed metadata closed-set schema 验证** (B-infra)：metadata key 越界 → `loader.py` 抛 `MetadataKeyError`
- **demo/run-demo.sh + sample-feed.json + digest-sample.md** 三件套已就位 —— reviewer git clone 后端到端跑通
- **1 条 live `dataset_version_used` 边**带 `metadata: {version: v1, subset: crbn-vhl-training}` —— `phase0-noise-floor → ternarydb`，全链路打通的最小存在证明

## 3. 五项交付物 × OmegaWiki 现状 × 生物分支可提供素材

| # | 交付物 | 团队主线现状 | 生物分支可贡献 | 拆台风险 |
|---|---|---|---|---|
| ① | 基础信息 + 价值简述 | README 现有素材 | 一句话：「bio adaptation backlog A+B+C+D 全部完结（39 pilots 累计 / 14 bio edges / 5 typed metadata schemas / 4 ID 维度复现）」 | 0 |
| ② | 技术报告 ≤9 页（ICLR-tmpl 英文）| 未开始 | **§4 Domain Adaptation Case Study — Computational Drug Discovery**（1.5–2 页：A1 dataset 一等公民 / B1-3 bio 边类型 / C9 PubMed 通道 / A8 复现块 / PTM-PROTAC anchor）| 0 |
| ③ | Poster 海报 | 未开始 | 1 个 bio panel：PTM-PROTAC degrader idea graph（PTM idea + 8 experiments + ternarydb + crbn 邻域）+ typed-metadata schema 小图 | 0 |
| ④ | 公开仓库 | 已开源 | bio 分支已合并入 main 路径；`tools/lint_bio.py` 单独可跑；`docs/bio-adaptation/` 自包含 | 0 |
| ⑤ | Demo 视频 | DEMO_GUIDE 当前是静态 8 图（poster / README 素材）| 视频里 bio 闪现节点 + 中段 reveal —— 见 §4 视觉锤 & §6 脚本 | 0 |

## 4. 视频里的生物视觉锤（眼前一亮清单）

> 每个 1–3 秒一闪而过，密度足够让评审在主线节奏不打断的前提下识别"这真的在做生物"。
> 按"识别度 × 拍摄成本"取舍，**TOP-7 优先入镜**。

| # | 视觉锤 | 拍摄载体 | 学界识别度 | 备注 |
|---|---|---|---|---|
| 1 | 14 bio edge types 在 SPA 全图里的边标签 | SPA 视口 | ★★★★★ | 含 `binds` / `ubiquitinates` / `dataset_version_used` / `clinical_trial_for` / `fda_approved_for` / `validates_in_species` |
| 2 | experiments frontmatter 同屏 `cellosaurus / addgene / rrid / pdb_versions / dataset_versions` 五个 ID 维度 | VS Code | ★★★★★ | DEMO_GUIDE 图 4，**最高密度生物锤** |
| 3 | `/novelty` 终端输出：`✓ PubMed: N hit \| ✓ Semantic Scholar: M \| ✓ wiki: K dupes` | 终端 | ★★★★ | 需新增 demo 输出，§5 P0-2 |
| 4 | typed metadata 行：`metadata: {version: v1, subset: crbn-vhl-training}` | 终端 (grep JSONL) | ★★★★ | DEMO_GUIDE 图 7 |
| 5 | `/ideate` banlist scope 拒/纳逻辑：`scope.species=[arabidopsis] vs current banlist=[human, mouse] → not blocked` | 终端 | ★★★ | 需新增 demo，§5 P0-3 |
| 6 | `/exp-design` dose_response block 输出：`[0.1, 1, 10, 100, 1000 nM] × 3 bio × 3 tech, ctrl: vehicle DMSO` | 终端 | ★★★★ | §5 P0-3 同一脚本 |
| 7 | `datasets/ternarydb.md` 的 versions 表 + key_papers | VS Code | ★★★ | DEMO_GUIDE 图 5 |
| 8 | `tools/lint_bio.py` cross-check 通过日志：🟢 `experiments[deepternary-baseline].reproducibility.dataset_versions[0].version 'v1' matches datasets/ternarydb.md::versions[0].version` | 终端 | ★★★ | 视频拍 P1-1 时附带 |

## 5. 12 天内的生物分支优化清单（P0/P1/P2）

> **0-拆台铁则**（每项改动须同时满足）：
>
> 1. 仅扩展，不破坏 `tools/lint.py` + `tools/lint_bio.py` clean
> 2. 仅写新 demo 输出 / 文档 / informational lint check，**不动 skill / schema 主干**
> 3. 失败能 `git reset` 单 commit 还原

### P0 — 必做（48 小时内，对视频 / poster / paper 直接增益）

| # | 项 | 估时 | 演示用途 | 拆台风险 | 谁做 |
|---|---|---|---|---|---|
| **P0-1** | README 增 "Bio Quick Tour" 段（14 edges / 9 setup fields / 5 typed metadata / 4 ID 维度 / 39 pilots）| 30 min | poster + GitHub 第一印象 + paper §4 抄稿 | 0 | Claude |
| **P0-2** | `examples/output/bio-novelty-report.md` 新建：对 ptm-aware-degrader idea 跑一次 `/novelty` 输出固化 | 1 h | 视频锤 3（PubMed multi-source）+ poster | 0 | Claude |
| **P0-3** | `examples/output/bio-ideate-banlist.md` 新建：scope-overlap 拒/纳两个 idea（一个 Arabidopsis PTM 通过 / 一个 human PTM site predictor 被 saturate 拒绝）的完整对话 | 45 min | 视频锤 5、6 | 0 | Claude |
| **P0-4** | `wiki/index.md` 加 "Bio coverage at a glance" 数字表 | 15 min | poster 数据点 + README 配图 | 0 | Claude |
| **P0-5** | 手工预排版 `wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas` 节点位置 | 30 min | DEMO_GUIDE 图 9 / 视频中段 bio reveal | 0 | User（Obsidian 拖拽）|

**合计 ~3.5 h**（其中 Claude 可承担 ~2.5h，user 0.5h）

### P1 — 推荐（如有余力，3–5 天窗口）

| # | 项 | 估时 | 演示用途 | 拆台风险 |
|---|---|---|---|---|
| **P1-1** | `tools/lint_bio.py` 加 1 项 informational check：`cellosaurus` ID 格式校验（`CVCL_[A-Z0-9]{4}`）+ 报告未声明 ID 的 experiments | 1.5 h | 视频锤 8 / paper §4 case study 一句 | 极低（informational tier 不阻断）|
| **P1-2** | `wiki/graph/edges.jsonl` 手工增 3 条 live bio 边：`lenalidomide→crbn (binds)` / `pomalidomide→multiple-myeloma (clinical_trial_for, phase=approved)` / `lenalidomide→FDA (fda_approved_for, year=2006)` | 1 h | 图 6 SPA 视觉更"bio"；让 B1/B2 多个边类型同屏 live | 极低（需对应 concepts/people 页存在）|
| **P1-3** | `demo/run-demo-bio.sh` 新建：串行跑 `/novelty` + `/ideate banlist` 对一个 bio claim → 输出固化为 `examples/output/bio-demo-output.md` | 1.5 h | 视频替代镜头 8（bio-flavored daily demo）| 0 |
| **P1-4** | 9 页技术报告 §4 Domain Adaptation 草稿 1.5 页（bio 部分），交团队主笔人合并 | 3 h | 论文 §4 一节完整 | 0 |

**合计 ~7 h**

### P2 — 锦上添花（看时间，可砍）

| # | 项 | 估时 | 演示用途 |
|---|---|---|---|
| **P2-1** | `docs/bio-adaptation/` 加 1 张 backlog heatmap PNG（A1-D2 完成度可视化）| 1.5 h | README + poster |
| **P2-2** | `/exp-eval` 输出补 bio `failure_taxonomy` 5 类（minimal prompt 改动：dataset-version-mismatch / species-mismatch / dose-range / negative-control-fail / cross-context-fail）| 2 h | self-evolving 故事补强 |

**合计 ~3.5 h**

## 6. 视频脚本骨架

> 比赛**未规定视频时长** —— 我给 30s 主线 + 90s 详版两种，团队拍视频时按需取舍。

### 6.1 30s 主线版（生物作为后半段的 "reveal"）

| 时间 | 屏幕 | 画外音 |
|---|---|---|
| 0–5s | `tools/serve.py` 启动 → SPA 全图加载 | "这是 OmegaWiki —— 一个能自我演化的科研 Agent。" |
| 5–12s | `/ideate` → `/exp-design` → `/exp-run` → `/exp-eval` → `/paper-draft` 串行触发动画 | "25 个 specialized agent 协作完成一个完整研究闭环 —— 发现想法、设计实验、跑实验、写论文。" |
| 12–20s | graph 加 3 条新边动画 + ideas 状态从 `in_progress` → `validated` 闪现 | "每跑一次实验，知识图自我扩张；每写一篇论文，agent 自己产生下一批想法。" |
| 20–28s | 缩到 SPA bio 邻域（PTM idea + ternarydb + crbn + binding 边）→ experiments/deepternary frontmatter（cellosaurus / addgene / rrid 同屏 0.5s）| "并且，它真能做生物 —— PROTAC、PTM、binding pocket、Cellosaurus、PubMed cross-check。" |
| 28–30s | LOGO 黑底白字 "OmegaWiki — Agent for Science" + GitHub URL | — |

### 6.2 90s 详版（生物有专门 reveal 段 20s）

| 时间 | 段落 | 屏幕 | 画外音 |
|---|---|---|---|
| 0–10s | Hook | 跑 `demo/run-demo.sh`，digest 输出滚屏（含 q-bio.BM 推荐）| "每天早晨 8 点，OmegaWiki 自动从 arXiv 抓 q-bio.BM 和 cs.AI，给你 strong / maybe / skip 的科研 digest。" |
| 10–20s | Multi-agent reveal | `.claude/skills/*.md` 列表滚动 → 点 `/research` 自动调度 `/discover` → `/ingest` → `/ideate` → `/exp-design` | "25 个 specialized agent，每个带不同工具集和系统提示。/research 是 orchestrator，自动调度所有 agent 协作。" |
| 20–40s | Self-evolving reveal | (a) `/ingest` 一篇新 paper → graph 80→83 节点动画 / (b) 一个 idea 从 `in_progress` → `failed`，failure_reason 写入 → `/ideate` 下轮 banlist 自动 +1 / (c) `concepts.maturity: hypothesis` → `well-supported` 演进 | "每条新论文进入图谱、每个失败的实验更新 banlist、每个 idea 状态变迁 —— wiki 自己在成长。" |
| **40–60s** | **Bio reveal**（关键）| (a) 40-45s: SPA 缩到 PTM 邻域，bio edge labels 浮出 / (b) 45-50s: VS Code 切到 reproducibility 块（rrid + cellosaurus + addgene + pdb_versions + dataset_versions 全屏）/ (c) 50-55s: 终端跑 `/novelty` bio claim → 4 source verification 输出 / (d) 55-60s: 终端跑 `/ideate` 对 Arabidopsis PTM banlist scope-check 通过 | "生物模块是我们的 case study。每个实验记录 5 个 ID 维度，全部 lint 自动 cross-check。新假设跑 PubMed、Semantic Scholar、wiki、WebSearch 四路并行。scope overlap 算法让 human banlist 不会过度封禁植物 PTM 这种跨物种 idea。" |
| 60–80s | 闭环 reveal | `/exp-run` 跑 mock experiment → 结果写入 → `/exp-eval` verdict → idea status 自动更新 → `/paper-draft` 触发草稿 | "实验跑完，结果直接写回 idea 状态；想法 mature 之后，自动生成论文初稿。完整闭环，所有节点可复现，所有边可追溯证据。" |
| 80–90s | Outro | LOGO + GitHub URL + 团队名 | "OmegaWiki —— 让科研 Agent 真的能做科研。" |

### 6.3 录制注意（给拍视频的同事）

- **录屏工具**：Windows OBS Studio（免费，60fps 4K 输出）或 ShareX 录屏（轻量但 30fps 上限）
- **分辨率**：1920×1080 @ 60fps（B 站 / 智源大会现场都吃得下）
- **音频**：建议事后配音（Auphonic Web 免费降噪），现场录易混入键盘声
- **字幕**：英文字幕（评委含国外教授）+ 中文翻译可选
- **不要拍**：本机敏感路径（截前 `cd ~/OmegaWiki/` 并 `clear`）、`.env` 内容、API key
- **拍 bio reveal 时**：放慢节奏 0.5x —— 视觉锤要让评委看到识别，不是快闪

## 7. 给团队的 5 句话接口

> 团队其他成员（PM / 写论文 / 拍视频 / 做 poster）问 "bio 能给什么" 时，直接抄这 5 句：

1. **"bio 模块是 case study，不是分赛道。"**
    bio adaptation 用 39 个 pilot commit 把 generic loop 落地到一个 vertical（comp drug discovery）。在论文 §4 占 1.5–2 页，poster 占 1 个 panel，视频占中段 20s reveal。

2. **"能复现链路 bio 已经端到端打通。"**
    5 个 ID 维度（rrid / cellosaurus / addgene / pdb / dataset_version）+ typed metadata schema + lint cross-check + 1 条 live 示例边。任何 reviewer git clone 后跑 `tools/lint_bio.py` 验证。

3. **"PubMed 通道是 bio 独占的 vertical-specialization 证据。"**
    `/novelty` Source E 仅对 bio claim 给满权重，非 bio claim 仅辅助 —— 证明 multi-channel agent 框架支持 domain-specialized 行为。

4. **"PTM-PROTAC 是讲故事的 anchor。"**
    1 个 idea (`ptm-aware-degrader-target-nomination`) + 8 个 linked experiments + 1 个 dataset (`ternarydb`) + 多个 bio concepts (`crbn` / `ubiquitin-ligase-e3` / `lenalidomide`) 形成视觉锤，适合 SPA / canvas / poster panel 焦点。

5. **"bio 视频段 20s 够用，不喧宾夺主。"**
    见 §6.2，bio reveal 安排在 40–60s 这一关键段，前后用 multi-agent / self-evolving 主线包住，结尾归到"agent 真能做科研"主题。

## 8. 我的近期 todo（按时间排序）

| 日期 | 项 | 谁 |
|---|---|---|
| **2026-05-18 (today)** | 本备忘 + DEMO_GUIDE §0 比赛上下文段 | Claude（drafting） |
| 2026-05-19 | P0-1 → P0-4 全部完成（Claude 出 PR；user review） | Claude |
| 2026-05-19 (晚) | P0-5 canvas 手工排版（Obsidian 拖拽）| User |
| 2026-05-20 | 8 张静态图截图（VS Code + SPA + 终端）→ `assets/demo-*.png` | User |
| 2026-05-21 | P1-1（lint_bio cellosaurus check）+ P1-2（3 条 live 边）| Claude |
| 2026-05-22 | P1-3（`demo/run-demo-bio.sh`）+ P1-4 §4 论文草稿 | Claude |
| 2026-05-23 | 录视频（30s 主线版优先）| 团队拍视频同事，bio reveal 段我陪场 |
| 2026-05-25 | poster bio panel 出图 | bio + poster designer 同事 |
| 2026-05-27 | 论文 §4 合并 + 整体 review pass | Lead + Review LLM |
| **2026-05-30** | **提交截止** | 全员 |

## 9. 关键风险与缓解

| 风险 | 缓解 |
|---|---|
| 团队主线 self-evolving / multi-agent demo 没拍出来，bio reveal 撑不起 90s | bio 短版本（§6.1 30s 主线）单独录一遍，可作为独立 backup |
| bio 视觉锤评委不识别（非生物背景）| 字幕加 1 行解释："Cellosaurus / RRID = experiment-reagent ID standards" |
| 论文 §4 case study 被 9 页限制砍掉 | 把 §4 缩到 1 页，剩 0.5 页内容塞 appendix（ICLR-tmpl 通常允许）|
| 12 天周期 P1 来不及 | P0 全做完后 P1-3 (`demo/run-demo-bio.sh`) 是视频替代镜头唯一刚需，其它都可砍 |
| `wiki/canvases/*.canvas` 在评委本地 Obsidian 渲染异常 | poster panel 用静态 PNG（P0-5 输出），不依赖 Obsidian |

## 10. 链接索引

| 类别 | 路径 |
|---|---|
| 论文 Overleaf 模板 | https://www.overleaf.com/read/bvsdjzdttszt#4023ef |
| 比赛官方 URL | https://mp.weixin.qq.com/s/9NNz0H1oPloRUljnnW7hBw |
| Demo 制作指南 | [`DEMO_GUIDE.zh.md`](DEMO_GUIDE.zh.md) |
| 2026-05-12 backlog 完结快照 | [`CHECKPOINT-2026-05-12.zh.md`](CHECKPOINT-2026-05-12.zh.md) |
| 整体 report | [`REPORT.zh.md`](REPORT.zh.md) |
| 累计 changelog | [`CHANGELOG.zh.md`](CHANGELOG.zh.md) |
| backlog 原档 | [`../bioinformatics-adaptation-backlog.zh.md`](../bioinformatics-adaptation-backlog.zh.md) |
| Canvas focus | `wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas` |
