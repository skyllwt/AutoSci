# ΩmegaWiki Bio Fork —— 面向生信场景的改动总览

> **一句话**：upstream ΩmegaWiki 默认是 CS 形态（arXiv / GitHub repo / 单一 dataset 概念），本 fork 把它改造成可以承载真实生信工作流的形态——加了 dataset 一等公民、14 类生物关系边、湿/干实验区分、reproducibility ID 闭环、PubMed 检索通道、bio 专用 lint 等。**所有改动都向下兼容 upstream**，已有 wiki 不需要迁移。

驱动场景：[PTM-aware degrader target nomination](../../wiki/ideas/ptm-aware-degrader-target-nomination.md)（PROTAC 降解剂选靶的端到端流程），见 [DEMO_SUBMISSION.zh.md](DEMO_SUBMISSION.zh.md) 9 张图说清做了什么。

---

## 这个分支跟 upstream 有什么不同

| | upstream ΩmegaWiki | bio fork |
|---|---|---|
| 实体类型 | 9 类 | **10 类**（新增 `datasets/`）|
| 边类型 | 13 类（CS 引用 + 推理关系）| **+ 14 类生物关系**（绑定 / 磷酸化 / 泛素化 / 临床试验 / FDA 批准 ...）|
| 边的 metadata | free-text `evidence` 字段 | **+ closed-set typed schemas**（5 种边类型强 schema）|
| 论文 ID | `arxiv` 字段 | **+ `doi` + `pmid` + `s2_id`** 三轴 |
| 实验 setup | model / dataset / hardware | **+ in_silico_or_wet · species · cell_line · assay_type · force_field · solvent_model · simulation_length · random_seed_protocol** |
| 实验预算 | `estimated_hours` 单字段 | **+ 6 字段**（GPU-h · CPU-h · MD wall-clock-h · wet-lab USD · FTE-weeks · 数据 NDA 等待天数）|
| 实验复现 | git commit hash | **+ 5-ID 块**（RRID · Cellosaurus · Addgene · PDB versions · dataset versions）|
| Idea 评级 | `priority` 1-5 | **+ GRADE 证据强度**（low / moderate / high）|
| 失败 idea | 仅 `status: failed` | **+ `scope:` 块**（species / disease_area / data_regime）—— 未来 ideate 同子空间会避开，但其他子空间放行 |
| 概念成熟度 | 4 enum (stable / active / emerging / deprecated) | **+ 5 bio 评级**（consensus / well-supported / contested / hypothesis / falsified）|
| 文献检索 | Semantic Scholar | **+ PubMed E-utilities**（生信文献覆盖率远高于 S2）|
| Lint | base `tools/lint.py` | **+ `tools/lint_bio.py`**（5 项 bio cross-check）|
| 领域 slug | 自由文本 | **15 个受控词表**（如 `bioinformatics` · `comp-drug-discovery` · `protein-engineering`）|

---

## 10 个加进来的核心能力

### 1. Dataset 作为一等公民

新增 `wiki/datasets/` 目录，每个数据集一个 page，含 versions 表、访问等级、aliases。下游实验通过 `setup.dataset: [[ternarydb]]` 引用具体 dataset，由 lint 校验存在性。

```yaml
# wiki/datasets/ternarydb.md
---
slug: "ternarydb"
maturity: active
access: public
versions:
  - version: "v1"
    released: ""
    notes: "Release alongside DeepTernary (Nat. Commun. 2025) ..."
aliases: ["TernaryDB CRBN+VHL", "TernaryDB CRBN/VHL"]
---
```

### 2. 14 类生物关系边

`runtime/schema/edges.yaml` 注册了 14 类生物关系：

```
binds / targets_protein / degrades / phosphorylates / ubiquitinates /
sumoylates / acetylates / methylates / glycosylates /
wet_lab_validated / clinical_validated / clinical_trial_for /
fda_approved_for / validates_in_species / dataset_version_used
```

每条边可加 `confidence: high|medium|low`（CS 默认是无 confidence）。

### 3. 5 个 typed edge metadata schemas

边可携带 closed-set 结构化 metadata（不是 free-text comment），由 `runtime/loader.py` 在 load 时强校验：

```jsonl
# wiki/graph/edges.jsonl
{"from": "experiments/phase0-noise-floor-...",
 "to": "datasets/ternarydb",
 "type": "dataset_version_used",
 "confidence": "high",
 "metadata": {"version": "v1", "subset": "crbn-vhl-training"}}
```

5 种 schema 强约束：`dataset_version_used` · `binds` · `clinical_trial_for` · `fda_approved_for` · `validates_in_species`。未声明 key 触发 lint warning；必需 key 缺失直接报 error。

### 4. 实验 setup 加 9 bio 字段

```yaml
setup:
  model: "DeepTernary (released checkpoint, Nat. Commun. 2025)"
  dataset: "[[ternarydb]] CRBN+VHL test split"
  in_silico_or_wet: "in_silico"        # 干实验 / 湿实验 / 混合
  species: ["human"]                   # 物种
  cell_line: ""                        # 细胞系（湿实验用）
  assay_type: "scoring"                # 实验类型
  force_field: ""                      # MD 用力场
  solvent_model: ""                    # 溶剂模型
  simulation_length: ""                # MD 时长
  weight_version: "..."                # 模型 weights 版本
  random_seed_protocol: "ranking-shuffle (>= 3 seeds)"
```

### 5. 实验预算 6 字段

```yaml
estimated_cost:
  gpu_hours: 4
  cpu_hours: 0
  md_wallclock_hours: 0            # MD 单独计——跑 50 ns 要 8 小时 wall-clock 但不耗 GPU
  wet_lab_usd: 0
  fte_weeks: 0.25                  # 人力工时
  dataset_access_lead_time_days: 0 # 等数据 NDA / 申请期
```

### 6. 实验复现 5-ID 闭环

```yaml
reproducibility:
  rrid: []                  # 实验室资源 RRID
  cellosaurus: []           # 细胞系 CVCL_[A-Z0-9]{4}
  addgene: []               # Addgene plasmid ID
  pdb_versions: []          # 结构 PDB ID + release date
  dataset_versions:
    - dataset_slug: ternarydb
      version: v1
      accessed_date: 2026-05-02
```

`tools/lint_bio.py` 双向校验：`experiments.reproducibility.dataset_versions[].version` 与 `datasets/*.versions[].version` 一致；不一致就 lint warning。

### 7. Idea GRADE 评级

`grade: low|moderate|high` 字段标证据强度（不是 LLM 自吹的 priority，按经典 GRADE 框架：mechanistic basis × empirical evidence × consistency × directness）。

```yaml
# wiki/ideas/ptm-aware-degrader-target-nomination.md
grade: low
# bio-A7 (pilot 2026-05-11): GRADE = low — load-bearing premise
# (phospho-perturbation > noise floor) is empirically unverified...
```

### 8. C3 banlist scope —— 失败 idea 不全屏蔽

失败 idea 加 `scope:` 块标"哪个子空间已 saturated"，未来 `/ideate` 跑同领域时按 scope join 决定是否屏蔽：

```yaml
# wiki/ideas/ptm-site-disorder-predictor.md (status: failed)
failure_reason: "[filter] saturated by SAPP (2025), PhosAF (2024), ..."
scope:
  species: [human, mouse]
  disease_area: []
  data_regime: high_data
```

跑"plant PTM 跨物种低数据迁移"时，scope.species ∩ {plant} = ∅ → 不屏蔽。

### 9. PubMed 检索通道

`/novelty` 默认 5 通道交叉验证（WebSearch / Semantic Scholar / **PubMed E-utilities** / wiki dedup / Review LLM）；PubMed 在生信文献覆盖率远高于 S2。

```bash
.venv/bin/python tools/fetch_pubmed.py search "PROTAC ternary complex prediction"
```

### 10. bio lint —— 5 项 cross-check

`tools/lint_bio.py` 在 base lint 之外加：
- `dataset_versions[]` 与 `datasets/*.versions[]` cross-check
- `domain` 字段必须在 15 canonical slug 内
- `experiments.setup` 9 bio 字段一致性（in_silico_or_wet=wet 时 cell_line 必填等）
- `estimated_cost` 6 字段完整性
- reproducibility ID 格式（cellosaurus CVCL_[A-Z0-9]{4} 等）

---

## 快速尝试

```bash
git clone https://github.com/skyllwt/OmegaWiki.git
cd OmegaWiki

# 1. 看 dataset 一等公民
cat wiki/datasets/ternarydb.md

# 2. 看带 9 bio 字段的实验页
cat wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md

# 3. 看 typed metadata 实例
grep dataset_version_used wiki/graph/edges.jsonl | python3 -m json.tool

# 4. 跑 base lint + bio lint
.venv/bin/python tools/lint.py        # base: 0 🔴 / 0 🟡 / 11 🔵
.venv/bin/python tools/lint_bio.py    # bio: 0 🔴 / 0 🟡 / 0 🔵

# 5. 浏览器看知识图谱
.venv/bin/python tools/serve.py
# → http://localhost:8765/，搜 ptm-aware-degrader-target-nomination

# 6. 跑 daily-arxiv 流水线
bash demo/run-demo.sh   # 需 .env 配 LLM_API_KEY + LLM_BASE_URL + LLM_MODEL
```

---

## 深入阅读

| 文档 | 内容 |
|---|---|
| [`DEMO_SUBMISSION.zh.md`](DEMO_SUBMISSION.zh.md) | 9 张截图端到端讲透 bio fork（简洁版）|
| [`DEMO_WALKTHROUGH.zh.md`](DEMO_WALKTHROUGH.zh.md) | 同上详细版（含系统能力证据 + 视频脚本映射）|
| [`REPORT.zh.md`](REPORT.zh.md) / [`REPORT.en.md`](REPORT.en.md) | 完整 bio adaptation 报告（动机 / 时间线 / schema 迁移 / lint 指标 / future work）|
| [`CHANGELOG.zh.md`](CHANGELOG.zh.md) | 39 个 pilot 改动逐项 changelog |
| [`../../paper/main.tex`](../../paper/main.tex) | 同一 idea graph 喂给 `/paper-plan` + `/paper-draft` 产出的 ICLR 8 页论文 |

---

## 兼容性 / 限制 / 未来

**向下兼容**：所有新字段都是 optional + 有 default。upstream wiki 直接 pull 本 fork 不需要任何迁移。

**当前限制**：
- 7 类生物关系边已 live（80 条总边里 7 条 bio），剩 7 类还在等使用场景；
- typed metadata 5 种 schema closed，其余 9 边类型暂时允许任意 metadata；
- bio lint 第 5 项 cellosaurus 格式 check 待实现；
- 8 个实验全部 `status: planned`，跑通后会替换 paper §4 现有的 [SIMULATED] 标记。

**正在做**：
- 加 cellosaurus CVCL ID 格式 check
- 补 3 条 live 生物关系边（lenalidomide-CRBN binds 等）
- 给 PROTAC-DB / DegronMD / DeepTernary 等论文做 ingest，把 7 个 [UNCONFIRMED] 引用降到 0
- v2 论文跑真实 GPU 实验替换模拟数据
