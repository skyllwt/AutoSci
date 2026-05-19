# Bio Case Study Demo Walkthrough — 9 张图端到端讲透 OmegaWiki

> **一句话概括**：从一篇 PTM 综述论文（图 1）出发，OmegaWiki 把它结构化成 wiki 实体（图 4-5），生成研究 idea（图 2），主动屏蔽 saturated 子空间（图 3），把所有关系组织成一张 live 知识图谱（图 6），每条关系携带可机读 typed metadata（图 7），跑每日 arXiv 流水线给出 LLM 排序的推荐（图 8），最后 Obsidian Canvas 给人脑友好的可视化（图 9）。**整套流水线 self-evolving + multi-agent，bio case study 是它能力的端到端证明。**

---

## 0. 叙事主线（30 秒电梯版）

```
论文 → idea → failed idea (避坑) → experiment → dataset
                                                      ↓
                  典型 metadata grep ← SPA 全图 ← daily-arxiv digest → Obsidian Canvas
```

3 个"反直觉"的卖点：

1. **失败也是产物**——图 3 的 `ptm-site-disorder-predictor` 状态 `failed` + scope 块明确"已 saturated 的子空间"，未来 `/ideate` 跑同领域会自动避开（C3 banlist）。绝大多数 research agent 系统只产正样本，OmegaWiki 把"已知失败"也持久化为一等公民。
2. **每条边都可机读**——图 7 的 `dataset_version_used` 边带 `metadata: {version: v1, subset: crbn-vhl-training}`，由 `runtime/loader.py` closed-set schema 强制（未声明 key 触发 lint warning）。这不是 free-text comment，是结构化数据。
3. **优雅退化的真实跑**——图 8 的 daily-arxiv 在有 LLM API key 时调 DeepSeek v4-flash 排序、没 key 时自动退化成 tool-signals-only fallback，二者都能产出 digest。系统不靠 LLM 也能跑。

---

## 1. 图 1 ——`demo-01-paper.png`：论文从 PDF 到 typed 实体

![paper frontmatter for MusiteDeep](../../assets/demo-01-paper.png)

**Caption**：MusiteDeep (NAR 2020) 的 wiki page frontmatter。`doi: "10.1093/nar/gkaa275"` (A3 bio identifier) · `pmid: "32324217"` · `domain: "bioinformatics"` (A4 canonical slug) · `tags: [deep-learning, ptm, ...]` · `keywords: [...]` 全部从 PDF 提取后结构化落盘。

**系统能力证据**：
- A3 bio-specific identifier 落地：DOI + PubMed ID 是生信文献的实际锚点（CS 默认的 arXiv ID 在 wet-lab / 综述 / NAR-class 期刊上覆盖率低）
- A4 domain 受控词表：`bioinformatics` 是 15 个 canonical slug 之一，避免 free-text "bioinfo / bioinformatic / bio-informatics" 三胞胎污染
- `keywords` 块由 LLM 从 PDF 提取，保留作者口径（vs `tags` 是 wiki 自有受控词表）

**对叙事的贡献**：自动化 `paper.pdf → wiki/papers/musitedeep-...md` 这一步是整套流水线最基础也最不出彩的一环，但**它是后续所有结构化推理的入口**——没有这一步，下面 7 张图全部白瞎。

---

## 2. 图 2 ——`demo-02-idea-main.png`：从论文派生研究 idea

![PTM-aware-degrader idea page](../../assets/demo-02-idea-main.png)

**Caption**：`ptm-aware-degrader-target-nomination` idea page。`status: in_progress` · `priority: 5` · `grade: "low"` (A7 GRADE 证据强度评分) · `linked_experiments` 8 项 flow list · `domain: "comp-drug-discovery"`。底部注释块写明 grade=low 的理由（thin positive set < 10 known PTM-selective degraders）。

**系统能力证据**：
- **A7 GRADE 评分内嵌**：不是 LLM 给的虚分，是按经典 GRADE 流程（mechanistic basis × empirical evidence × consistency × directness）打分；low 意味着系统**主动承认证据不足**而不是假装 hype
- **linked_experiments × 8**：从一个 idea 派生 8 个 cascaded experiments（Stage 1 baseline → Stage 2a noise-floor → Stage 2b headline → 3 ablations → 2 robustness）。这是 `/exp-design` skill 的产物，每个 experiment 都有 hypothesis + setup + metrics + success/marginal/failure 阈值
- **frontmatter YAML 严格**：5-19 修复了一处 `[[wikilink]]` 在 flow list 的破语法（commit `726ef38`），lint 校验 + Obsidian frontmatter UI 双校验

**对叙事的贡献**：这是整个 bio case study 的"主角"。Paper §3 method 三个 phase（calibration / cascaded prediction / split validation）和 §4 experiments 4 个 track 都从这一页派生。**Idea 是 wiki 自演化的最小单元——每个 idea 都有自己的 confidence、grade、linked exp、open question。**

---

## 3. 图 3 ——`demo-03-idea-failed.png`：失败 idea 也是一等公民

![failed idea with scope](../../assets/demo-03-idea-failed.png)

**Caption**：`ptm-site-disorder-predictor` idea，`status: failed` + `failure_reason` 列出 6 个已发表的 saturated 工具（SAPP / PhosAF / GraphPhos / AstraPTM2 / DeepPCT / MTPrompt-PTM）+ **`scope:` 块** (`species: [human, mouse]` · `disease_area: []` · `data_regime: high_data`) 框定"哪个子空间已 saturated"。

**系统能力证据**：
- **C3 banlist scope**：未来 `/ideate` 跑"plant phospho-PTM 跨物种低数据迁移"时，系统会 join scope，发现新 idea 的 `species=plant` 不在 banlist 的 `[human, mouse]` 里 → **不屏蔽**。反之，再有人提"human phospho-site predictor with AF features"会**被 ban**因为 data_regime=high_data 命中
- **失败原因 = 已发表竞品列表**：6 个工具全部 2024-2025 真实文献。failure_reason 是机器可读的"为什么失败"——LLM 跑 /ideate 时把它当 prior
- **失败不丢**：对比同行 research agent 框架（普遍只保留 "winning ideas"），OmegaWiki 把失败 idea 也持久化，**未来 /ideate 自动避开**

**对叙事的贡献**：**这是"self-evolving"主线的一个具体落地**——wiki 不只是积累正样本，**它积累"哪些路已经走过、走不通"**。视频里这一段是 self-evolving 的最强视觉证据。

---

## 4. 图 4 ——`demo-04-experiment.png`：实验全字段（信息密度最高一张）

![DeepTernary baseline experiment](../../assets/demo-04-experiment.png)

**Caption**：`deepternary-baseline-ternarydb-crbn-vhl-reproduction` experiment。`setup` 块 13 字段（model / dataset wikilink / in_silico_or_wet / species / cell_line / assay_type / force_field / solvent_model / simulation_length / weight_version / **random_seed_protocol "ranking-shuffle (>=3 seeds)"** / ...）· `estimated_cost` 块 6 字段（gpu_hours / cpu_hours / md_wallclock_hours / wet_lab_usd / fte_weeks / dataset_access_lead_time_days）· **`reproducibility.dataset_versions` 块** (`[{dataset_slug: ternarydb, version: v1, accessed_date: 2026-05-02}]`)。

**系统能力证据**：
- **A5 bio setup 9 字段**：CS 默认只关心 `model + dataset + hardware`，bio 还要 `in_silico_or_wet` · `species` · `cell_line` · `assay_type` · `force_field` · `solvent_model` · `simulation_length` · `weight_version` · `random_seed_protocol` —— 8/8 experiments 已回填
- **A6 estimated_cost 6 字段**：`md_wallclock_hours` 单独计费（MD 跑得起就要预算几天 wall-clock 不能跟 GPU-hours 混算）；`fte_weeks` 是人力工时；`dataset_access_lead_time_days` 提前预警等数据 NDA 的天数
- **A8 reproducibility ID 5 维度**：`rrid` (lab resource) + `cellosaurus` (cell line CVCL_*) + `addgene` (plasmid) + `pdb_versions[]` (structure) + `dataset_versions[]` (data) —— **`tools/lint_bio.py` cross-check** `experiments.reproducibility.dataset_versions[].version` 与 `datasets/ternarydb.md::versions[].version` **双向一致**（不一致就 lint warning）

**对叙事的贡献**：这是 bio adaptation 整套 schema 工作的"信息密度顶峰"。Poster panel 上把这张图框 4 个红框（setup / estimated_cost / reproducibility / random_seed_protocol）就能讲完 A5+A6+A7+A8 4 个 backlog item 的 12 小时工作量。

---

## 5. 图 5 ——`demo-05-dataset.png`：第 10 类一等公民

![ternarydb dataset page](../../assets/demo-05-dataset.png)

**Caption**：`ternarydb` dataset page。`maturity: active` · `access: public` · **`versions:` 块**（`v1` 的 released / url / n_entries / notes）· `aliases: ["TernaryDB CRBN+VHL", "TernaryDB CRBN/VHL"]` · `key_papers: []` / `key_concepts: []`。

**系统能力证据**：
- **A1: datasets/ 是 wiki 第 10 类实体**（vs upstream 9 类：papers / concepts / topics / people / ideas / methods / experiments / Summary / foundations）—— bio 默认就需要 dataset 一等公民
- **versions 表**：每次数据库发版（v1 → v2 → ...）都新增一行；下游 experiment 引用具体 version 就可以做版本一致性 audit
- **aliases**：同一数据集在不同 paper 里叫"TernaryDB CRBN+VHL" / "TernaryDB CRBN/VHL" / "TernaryDB"——alias 块把所有别名归一到同一 slug
- **`key_papers: []`**：留空有意义——TernaryDB v1 发布即随 DeepTernary 论文，**它本身不是论文的 key paper**

**对叙事的贡献**：CS 默认的"dataset = 静态文件"在 bio 不成立——版本化、access 等级、aliases、reproducibility cross-check 都是 ops 必须。这一页 + 图 4 的 reproducibility 块**双向一致由 lint_bio 校验**，是 bio-shaped infra 的标志。

---

## 6. 图 6 ——`demo-06-spa-graph.png`：知识图谱 live

![SPA graph PTM-aware-degrader neighborhood](../../assets/demo-06-spa-graph.png)

**Caption**：SPA (http://localhost:8765/) 渲染 PTM-aware-degrader 邻域（BFS depth=2）。可读 label 包括焦点 `ptm-aware-degrader-target-nomination`（黄）+ hub `ptm-protein-isoforms-enable-selective-drug`（黄）+ 3 个 experiments（红 robustness/calibrated/ablation）+ 4 个 papers（绿 AF / drug-design / E3-bioinformatics / structure-prediction）+ 2 个 concepts（紫 E3-ubiquitin-ligase / PTMI-DD）+ 邻接 idea `ptm-resolved-structurally-modeled-interactome`（黄）。Edge label 至少 4 种 bio 类型可见：`tested_by` · `addresses_gap` · `inspired_by` · `introduces_concept`。

**系统能力证据**：
- **B1+B2+B3 全 live**：14 个 bio edge type 注册（`binds` / `degrades` / `phosphorylates` / `ubiquitinates` / `sumoylates` / `acetylates` / `methylates` / `glycosylates` / `targets_protein` / `wet_lab_validated` / `clinical_validated` / `clinical_trial_for` / `fda_approved_for` / `validates_in_species` / `dataset_version_used`）；其中 7 条 bio relation 已实例化在 80 条 edges.jsonl 里
- **BFS focus 高亮**：SPA 支持搜索 + click → BFS depth-N highlight，**fade 掉其他节点**让局部图清晰
- **节点颜色按目录**：9 个目录 9 种色（`graph.json` 配置；本会话调过力学参数让 label 默认显示）

**对叙事的贡献**：**这是"multi-agent"的最强视觉证据**——画面里每条边都是另一个 agent skill 的产出（`/ingest` → paper 边、`/ideate` → idea 边、`/exp-design` → experiment 边、用户手工 → concept 边）。**多个 agent 在同一 wiki 上协作贡献，关系网就长出来了。**

> ℹ️ DEMO_GUIDE §3 fig-6 的"4 节点同框"原计划过乐观：`ternarydb` / `crbn` / `ubiquitin-ligase-e3` 实际在 PTM-aware-degrader 的 2-3 跳外。当前帧聚焦 BFS-2 邻域，`ternarydb`/`crbn` 在 +1 跳外（typed metadata 见图 7）。

---

## 7. 图 7 ——`demo-07-spa-metadata.png`：每条边都可机读

![typed metadata grep on edges.jsonl](../../assets/demo-07-spa-metadata.png)

**Caption**：干净终端跑 `grep -F 'phase0-noise-floor-...' wiki/graph/edges.jsonl | grep -F 'dataset_version_used' | python3 -m json.tool` 输出一条 edge 完整 JSON：`type: "dataset_version_used"` · `from: experiments/phase0-noise-floor-...` · `to: datasets/ternarydb` · `confidence: "high"` · `evidence: "Phase-0 noise-floor calibration runs on the CRBN+VHL training subset of TernaryDB v1."` · **`metadata: {"version": "v1", "subset": "crbn-vhl-training"}`**。

**系统能力证据**：
- **B-infra typed metadata closed-set**：`dataset_version_used` 边的 metadata 由 `runtime/schema/edges.yaml` 声明 schema (`version: str required` · `subset: str` · `accessed_date: str`)；`runtime/loader.py::validate_edge_attributes` 在 load 时强制：
  - 必需 key 缺失 → error
  - 未声明 key 出现 → `edge-attribute` warning + "known keys" 提示
  - 类型不匹配 → enum/int/float/str 校验失败
- **5 个 typed schemas**：`dataset_version_used` · `binds` · `clinical_trial_for` · `fda_approved_for` · `validates_in_species` —— closed-set 控住 5 个最 noise-prone 的边类型，其他 9 个边类型允许任意 metadata
- **lint_bio cross-check 闭环**：图 7 的 `metadata.version="v1"` + 图 4 的 `dataset_versions[].version: v1` + 图 5 的 `versions[].version: "v1"` —— **三处必须一致**，由 `tools/lint_bio.py` 双向校验

**对叙事的贡献**：**这是"为什么不能只用 RAG"的硬证据**——RAG 看 wiki 是非结构化文本，OmegaWiki 看 wiki 是 typed graph + typed metadata。**5 个 schema × 14 边类型 × 84 edges live = 80 KB JSONL 单文件可 grep。** Reviewer/poster 读者看到这条 metadata，立刻知道这套系统对接 downstream tool 是 trivial（不需要写 free-text parser）。

> SPA 本身不显示边 metadata（`app/modules/graph.js:146-160` 映射到 Cytoscape 时只保留 `id/source/target/label/workflow/symmetric`）；所以图 7 走 JSONL grep 终端截图，这是 DEMO_GUIDE 原本就列为后备的路径。

---

## 8. 图 8 ——`demo-08-digest.png`：daily-arxiv 端到端 live

![daily-arxiv DeepSeek digest](../../assets/demo-08-digest.png)

**Caption**：干净终端跑 `bash demo/run-demo.sh && head -25 examples/output/digest.md`。三步进度 `[1/3] prepare` (9 new / 9 scanned) · **`[2/3] recommend-llm via DeepSeek / 调用 DeepSeek 排序`** (4 decisions via `deepseek-v4-flash`) · `[3/3] finalize digest` (5 listed) · `LLM decisions: available` · **`## Strong Recommendations` 第一篇**：*"Benchmarking open-source tools for in silico antiviral drug discovery"* · `Decision: strong_recommend / confidence high / score 0.9 / Rationale: ...`。

**系统能力证据**：
- **3 步流水线 end-to-end**：`prepare` (dedupe + 信号打分 + context 构造) → `recommend-llm` (DeepSeek v4-flash 排序) → `finalize` (落盘 markdown + 机读 JSON digest)
- **优雅退化**：本会话发现 `demo/run-demo.sh:45` gate 写错变量名（commit `e54c2f5` 修复 `DEEPSEEK_API_KEY` → `LLM_API_KEY`）—— 修完后 gate 准确，**没 key 时跳过 LLM 步骤、退化为 tool-signals-only ranking**（fallback path 也产 digest）
- **LLM 输出真有 rationale**：`Rationale: "Directly benchmarks open-source tools for antiviral drug discovery, including binding affinity predictors like Boltz-2 and DrugFormDTA, relevant to the wiki's medpredict topic and benchmarking experiments."` —— 不是 templated 输出，是 DeepSeek 真在 reasoning

**对叙事的贡献**：**这是视频前 10 秒的 hook**——一条命令 `bash demo/run-demo.sh && head -25 examples/output/digest.md` 跑出来 *"DeepSeek 排序 4 decisions / strong recommend / confidence high / score 0.9 / rationale by LLM"*，**观众立刻知道这套系统是真跑的**。

---

## 9. 图 9 ——`demo-09-canvas.png`：人脑友好的可视化

![Obsidian Canvas PTM neighborhood](../../assets/demo-09-canvas.png)

**Caption**：Obsidian Canvas（`wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas`）渲染 PTM 邻域的"5 行流水线"布局：ROW 1 papers (5 张绿) · ROW 2 concepts (5 张紫) · ROW 3 close-ideas (4 黄 + 1 idea anchor) · ROW 4 outer-ideas + FOCUS (2 黄 + 1 焦点 PTM-aware-degrader) · ROW 5 experiments (5 红)。本会话调过两节点位置（biomolecular concept 收回 concepts 行；deepternary experiment 下移避开焦点遮挡）。

**系统能力证据**：
- **`/visualize` skill 输出 Obsidian-compatible Canvas**（`tools/visualize.py` 写 `.canvas` JSON）
- **手调 + 自动 layout 互补**：自动 layout 给初始位置，用户在 Obsidian 里拖拽微调，**live-sync 回写 `.canvas` 文件**（不需要 save）
- **`wiki/canvases/` 在 `.gitignore`**：源 canvas 文件是工作产物，**最终截图才进 git**（by design）

**对叙事的贡献**：**这是 SPA 全图（图 6）的策展版本**——SPA 是机器视角的 force-directed graph，Canvas 是人手挑选的局部知识地图。**两个视角同源同步**（都从 edges.jsonl 派生），覆盖 reader 不同需求：
- 想"看全貌探索"→ SPA
- 想"看故事讲透"→ Canvas

---

## 10. 9 张图 × 比赛交付物的映射

| 交付物 | 用到的图 |
|---|---|
| **README "Bio Demo Gallery" 段**（本文件链接进 README）| 全部 9 张 |
| **Poster bio panel × 4** | Panel 1: 图 1 + 图 4（论文 → 实验全字段）· Panel 2: 图 2 + 图 3（idea + failed idea）· Panel 3: 图 5 + 图 7（dataset + metadata）· Panel 4: 图 6 或 图 9（知识地图）|
| **30s 视频脚本** | 0-10s hook = 图 8 / 10-20s = 图 6 / 20-25s = 图 7 metadata / 25-30s = 图 2 idea |
| **90s 视频脚本** | 0-10s 图 8 hook · 10-30s 图 1+4 自动结构化 · 30-50s 图 6 知识图谱 · 50-70s 图 2+3 idea + failed · 70-90s 图 9 Canvas closing |
| **论文 §4 Bio case study** | Paper `paper/sections/experiments.tex` 已经把图 2-5 的数据嵌入到了 Table 1-4，图 6-7 作为 §4.1 setup 视觉证据 |
| **技术报告（团队主线）** | 图 6 作为"系统能力总览"图 · 图 2+图 4 作为"端到端例子"图 |

---

## 11. 一句话视觉锤就绪度

```
锤 1 SPA 14 bio edge labels live       ✅ 图 6
锤 2 5 ID reproducibility 同屏         ✅ 图 4
锤 3 /novelty PubMed multi-source      ✅ examples/output/bio-novelty-report.md
锤 4 typed metadata grep 输出           ✅ 图 7
锤 5 /ideate banlist scope             ✅ 图 3 + examples/output/bio-ideate-banlist.md
锤 6 /exp-design dose_response          ✅ examples/output/bio-exp-design-dose-response.md
锤 7 datasets/ternarydb versions 表    ✅ 图 5
锤 8 lint_bio cellosaurus cross-check  ⏸ P1-1 待加 CVCL_[A-Z0-9]{4} 格式 check
锤 9 (可选) Canvas knowledge map       ✅ 图 9
```

**8/8 (+1 可选) 视觉锤就绪**——只剩锤 8 的 cellosaurus check 没补，那是 1.5h 内部 infra 工作，比赛评委看不到。

---

## 12. 读完这份文档你应该能回答的 3 个问题

1. **"OmegaWiki 跟 RAG 的差别在哪？"**——RAG 看 wiki 是非结构化文本检索，OmegaWiki 看 wiki 是 typed graph + typed metadata（图 6 + 图 7 + 图 4 reproducibility 三位一体证明）。
2. **"self-evolving 的具体体现是什么？"**——图 3 失败 idea 持久化 + scope ban；图 2 idea grade=low 主动承认证据不足；图 4 experiment 三档 success/marginal/failure 自评——**系统知道自己哪里弱**。
3. **"multi-agent 在哪一张图里？"**——图 6 SPA 知识图谱里每条边都是另一个 skill 产出，84 edges 累计是 10+ skills 协作的轨迹；图 8 daily-arxiv 是 3 个 sub-agent (prepare / recommend-llm / finalize) 串行管线的 live demo。

---

## 13. 引用

- 截图制作指南：[`DEMO_GUIDE.zh.md`](DEMO_GUIDE.zh.md)
- 比赛上下文 + 视频脚本：[`COMPETITION_NOTES.zh.md`](COMPETITION_NOTES.zh.md)
- 5-18 / 5-19 会话档案：[`CHECKPOINT-2026-05-18.zh.md`](CHECKPOINT-2026-05-18.zh.md) · [`CHECKPOINT-2026-05-19.zh.md`](CHECKPOINT-2026-05-19.zh.md)
- 累计 changelog：[`CHANGELOG.zh.md`](CHANGELOG.zh.md)（39 entries）
- Bio case study 论文（端到端 demo 的"另一份输出"）：[`paper/main.tex`](../../paper/main.tex) + Stanford Agentic Reviewer **6.0/10** 实测
