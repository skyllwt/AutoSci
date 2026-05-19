<div align="center">

<img src="../../assets/logo.png" width="160" alt="ΩmegaWiki Logo">

# ΩmegaWiki · bio-adaptation

### 把 LLM-Wiki 改造成可承载真实生信工作流的形态

**PTM-aware degrader · structural biology · ML for molecules**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Entity Types](https://img.shields.io/badge/Entity_Types-10_(vs_9)-green.svg)](#wiki-structure区别)
[![Bio Edges](https://img.shields.io/badge/Bio_Edge_Types-14-purple.svg)](#wiki-structure区别)
[![Skills](https://img.shields.io/badge/Skills-24-orange.svg)](#skills区别)

[English upstream](../../README.md) · [中文（本文档）](#介绍)

</div>

---

## 介绍

upstream ΩmegaWiki 默认是 CS 形态——`arXiv` 是论文主 ID、单一 dataset 概念、实验记录里 `model + dataset + hardware` 三字段就够、`claims/` 是证据账本。这套形态在做 ML 论文工作流时高效；放到**生信 / 结构生物 / 药物发现**就处处别扭：DOI/PMID 比 arXiv ID 更主流、数据集要版本化、湿实验和干实验要明确区分、cellosaurus / RRID / PDB version 要可复现 trace。

本 fork 在不破坏 upstream 工作流的前提下做了 12 项 schema + skill + tooling 改造，全部向下兼容——upstream wiki 直接 pull 本 fork 不需要任何迁移。驱动场景是 [PTM-aware degrader target nomination](../../wiki/ideas/ptm-aware-degrader-target-nomination.md)：从 PTMI-DD 综述出发，构建带 14 类生物关系的 typed graph，自动派生 22 个 idea（11 validated / 2 failed）和 8 个 cascaded experiments，最终喂给 `/paper-plan` + `/paper-draft` 产出 ICLR 8 页论文。

**这个 fork 适合谁**：

- 在做计算药物发现 / PROTAC / 结构预测 / 多组学的科研人员
- 需要一个能记住"哪些路走过 / 哪些走不通"的研究知识库
- 想把"论文 → idea → 实验 → 论文"整个 loop 自动化的研究组

---

## 更新

### 跟 upstream 的核心区别

| | upstream ΩmegaWiki | bio fork |
|---|---|---|
| **实体类型** | 9 类 | **10 类**（新增 `datasets/`）|
| **边类型** | 13 类（CS 引用 + 推理关系）| **+ 14 类生物关系**（绑定 / 磷酸化 / 泛素化 / 临床试验 / FDA 批准 ...）|
| **边 metadata** | free-text `evidence` 字段 | **+ 5 类 closed-set typed schemas**（runtime 强校验）|
| **论文 ID** | `arxiv` 字段 | **+ `doi` + `pmid` + `s2_id`** 三轴 |
| **实验 setup** | model / dataset / hardware | **+ 9 bio 字段**（in_silico_or_wet · species · cell_line · assay_type · force_field · solvent_model · simulation_length · weight_version · random_seed_protocol）|
| **实验预算** | `estimated_hours` 单字段 | **+ 6 字段**（GPU-h · CPU-h · MD wall-clock-h · wet-lab USD · FTE-weeks · 数据 NDA 等待天数）|
| **实验复现** | git commit hash | **+ 5-ID 块**（RRID · Cellosaurus · Addgene · PDB versions · dataset versions）|
| **Idea 评级** | `priority` 1-5 | **+ GRADE 证据强度**（low / moderate / high）|
| **失败 idea** | 仅 `status: failed` | **+ `scope:` 块**——失败只屏蔽 saturated 子空间，其他子空间放行 |
| **概念成熟度** | 4 enum（stable / active / emerging / deprecated）| **+ 5 bio 评级**（consensus / well-supported / contested / hypothesis / falsified）|
| **文献检索** | Semantic Scholar | **+ PubMed E-utilities**（生信文献覆盖率高于 S2）|
| **Lint** | `tools/lint.py` | **+ `tools/lint_bio.py`**（5 项 bio 专用 cross-check）|
| **领域 slug** | 自由文本 | **15 个受控词表**（`bioinformatics` · `comp-drug-discovery` · `protein-engineering` ...）|

### 当前 live 数据

- **wiki 实体**：11 papers · 25 concepts · 22 ideas（11 validated / 2 failed / 9 其他）· 8 experiments（全 in_silico）· 1 dataset · 1 topic · 16 people
- **knowledge graph**：84 条边，含 7 条 live bio relation（4 条带 typed metadata）
- **lint 状态**：base `0🔴 / 0🟡 / 11🔵`（info）+ bio `0🔴 / 0🟡 / 0🔵`
- **端到端论文**：[`paper/main.tex`](../../paper/main.tex)（ICLR 8p / 7962 words / 4 figs TikZ inline / 4 tables / 由同一 idea graph 自动派生）

完整 changelog: [`CHANGELOG.zh.md`](CHANGELOG.zh.md)（39 条 pilot entry）。完整设计文档与迁移表: [`REPORT.zh.md`](REPORT.zh.md) / [`REPORT.en.md`](REPORT.en.md)。

---

## Quick Start

**前置**：Python 3.9+，Node.js 18+，Claude Code（[安装](https://docs.anthropic.com/en/docs/claude-code)）。

```bash
# 1. Clone
git clone https://github.com/skyllwt/OmegaWiki.git
cd OmegaWiki

# 2. 一键 setup（与 upstream 共用）
chmod +x setup.sh && ./setup.sh        # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

# 3. 配 .env 加 API key（参考 .env.example）
#    SEMANTIC_SCHOLAR_API_KEY=...     (S2，可选)
#    DEEPXIV_TOKEN=...                (semantic search，可选)
#    LLM_API_KEY=... + LLM_BASE_URL=... + LLM_MODEL=...   (cross-model review，可选)

# 4. 验证 bio fork 已装好
.venv/bin/python tools/lint.py           # base: 0 🔴 / 0 🟡 / 11 🔵
.venv/bin/python tools/lint_bio.py       # bio: 0 🔴 / 0 🟡 / 0 🔵

# 5. 看 dataset 一等公民（upstream 没这一类）
cat wiki/datasets/ternarydb.md

# 6. 看带 9 bio 字段的实验页
cat wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md

# 7. 看 typed metadata 实例
grep dataset_version_used wiki/graph/edges.jsonl | python3 -m json.tool

# 8. 浏览器看知识图谱（搜 ptm-aware-degrader-target-nomination 看 PTM 邻域）
.venv/bin/python tools/serve.py          # http://localhost:8765/

# 9. 跑 daily-arxiv 流水线（DeepSeek 排序 9 篇候选论文）
bash demo/run-demo.sh                    # 需 LLM_* env 已配
cat examples/output/digest.md            # 看产出 digest

# 10. 在 Claude Code 里启动 bio 工作流
claude
# 输 /init bioinformatics  → 用 bio prefill 启动新 wiki
# 或 /ingest <paper.pdf>    → 自动 DOI/PMID/PubMed 三轴解析
```

跑 `bash demo/run-demo.sh` 缺 LLM key 时会优雅退化为 tool-signals-only ranking，仍产出 digest——系统不靠 LLM 也能跑。预渲染输出在 `examples/output/digest-sample.md` 可直接 cat 看长什么样。

---

## Skills（区别）

完整 24 skills 见 [主 README](../../README.md#skills)。本 fork 影响以下 5 个 skill 的 prompt / 默认值，**没有新增 skill 也没有移除 skill**：

| Skill | bio fork 的改动 |
|---|---|
| `/ingest` | 增加 bio NER pre-pass：自动从 PDF / arXiv 抽取 DOI、PubMed ID、Cellosaurus CVCL ID、PDB ID、UniProt accession 填入 frontmatter |
| `/ideate` | 失败 idea 的 `scope:` 块参与 ban 判定——同领域同 data_regime 才屏蔽，跨物种 / 低数据 / 新 disease_area 放行 |
| `/exp-design` | 默认产出 4 种统计方案（bootstrap CI · stratified k-fold · LOO-CV · bio×tech replicates），按 `setup.in_silico_or_wet` 自动路由；自动按 setup 类型补 9 bio 字段 |
| `/novelty` | 新增 **PubMed E-utilities** 作为满权重通道（生信文献覆盖率远高于 S2），bio 论文跑 novelty 时主要看这个 |
| `/check` | 在 base lint 之外额外跑 `tools/lint_bio.py` 5 项 cross-check |

`/paper-draft` 也有"result-first writing"的 bio 风格调整（先抛出结果再讲方法），但这是 prompt 微调，不算结构性区别。

---

## Wiki Structure（区别）

### 新增第 10 类实体：`datasets/`

```yaml
# wiki/datasets/ternarydb.md
---
slug: "ternarydb"
maturity: active
access: public                                # public / on_request / restricted
aliases: ["TernaryDB CRBN+VHL", "TernaryDB CRBN/VHL"]
versions:
  - version: "v1"
    released: ""
    url: ""
    n_entries: ""
    notes: "Release alongside DeepTernary (Nat. Commun. 2025)..."
canonical_url: ""
license: ""
key_papers: []                                 # 反向链接到使用此数据集的论文
date_updated: 2026-05-11
---
```

下游 experiment 通过 `setup.dataset: [[ternarydb]]` wikilink 引用具体 dataset。`tools/lint_bio.py` 校验 `experiments.reproducibility.dataset_versions[].version` 与 `datasets/*.versions[].version` 双向一致。

### 新增 14 类生物关系边

`runtime/schema/edges.yaml` 在 upstream 13 类（同问题 / 同方法 / 互补 / 构建于 / 比较 / 改进 / 挑战 / 综述 / 介绍概念 / 使用概念 / 扩展概念 / 批判概念 / 推理）之外注册：

```
binds · targets_protein · degrades · phosphorylates · ubiquitinates ·
sumoylates · acetylates · methylates · glycosylates ·
wet_lab_validated · clinical_validated ·
clinical_trial_for · fda_approved_for ·
validates_in_species · dataset_version_used
```

每条边可加 `confidence: high | medium | low`（upstream 边默认无 confidence）。

### Typed Edge Metadata（5 种 closed-set schemas）

边可携带结构化 metadata，由 `runtime/loader.py::validate_edge_attributes` 在 load 时强校验。当前 5 种 schema：

```yaml
# runtime/schema/edges.yaml （节选）
edges:
  dataset_version_used:
    metadata:
      version: { type: str, required: true }
      subset:  { type: str }
      accessed_date: { type: str }
  clinical_trial_for:
    metadata:
      nct_id: { type: str }
      phase: { type: enum, values: [0, 1, "1/2", 2, "2/3", 3, 4] }
      indication: { type: str }
      year: { type: int }
  fda_approved_for:
    metadata:
      indication: { type: str, required: true }
      year: { type: int }
      approval_kind: { type: enum, values: [standard, accelerated, breakthrough, fast-track] }
  binds:
    metadata:
      recruitment_ligand_class: { type: str }
      clinical_anchor: { type: str }
      kd_nM: { type: float }
  validates_in_species:
    metadata:
      species: { type: str, required: true }
      source_db: { type: str }
```

未声明 key 触发 lint warning（附 "known keys" 提示），必需 key 缺失直接报 error，类型不匹配拒绝。其他 9 类生物关系边暂时允许任意 metadata（向后兼容）。

### 实验 page 的 3 个新 block

```yaml
# wiki/experiments/*.md frontmatter
setup:
  model: "..."
  dataset: "[[ternarydb]] CRBN+VHL test split"
  hardware: "1 × A100 80GB"
  framework: "PyTorch + DeepTernary inference repo"
  in_silico_or_wet: "in_silico"                # bio 新增
  species: ["human"]                           # bio 新增
  cell_line: ""                                # bio 新增
  assay_type: "scoring"                        # bio 新增
  force_field: ""                              # bio 新增
  solvent_model: ""                            # bio 新增
  simulation_length: ""                        # bio 新增
  weight_version: "DeepTernary (Nat Commun 2025 checkpoint)"   # bio 新增
  random_seed_protocol: "ranking-shuffle (>=3 seeds)"          # bio 新增

estimated_cost:                                # bio 完全新增
  gpu_hours: 4
  cpu_hours: 0
  md_wallclock_hours: 0                        # MD 单独计——50 ns MD 耗 wall-clock 但不耗 GPU
  wet_lab_usd: 0
  fte_weeks: 0.25
  dataset_access_lead_time_days: 0

reproducibility:                               # bio 完全新增
  rrid: []                                     # lab resource RRID
  cellosaurus: []                              # cell line CVCL_[A-Z0-9]{4}
  addgene: []                                  # Addgene plasmid ID
  pdb_versions: []                             # 结构 PDB ID + release date
  dataset_versions:                            # 与 datasets/*.versions[] cross-check
    - dataset_slug: ternarydb
      version: v1
      accessed_date: 2026-05-02
```

### Idea page 的 GRADE 评级与 scope ban

```yaml
# wiki/ideas/ptm-aware-degrader-target-nomination.md
grade: low                                     # bio 新增：low / moderate / high
# bio-A7 (2026-05-11): GRADE = low — load-bearing premise (phospho-perturbation
# > noise floor) is empirically unverified. Mechanistic basis exists but thin
# positive set (<10 known PTM-selective experimental degraders) bounds evidence.

# wiki/ideas/ptm-site-disorder-predictor.md (status: failed)
failure_reason: "[filter] saturated by SAPP (2025), PhosAF (2024), GraphPhos (2025) ..."
scope:                                         # bio 新增
  species: [human, mouse]                      # 已 saturated 的物种
  disease_area: []
  data_regime: high_data                       # 已 saturated 的数据规模
```

跑 `/ideate` 时，新 idea 走 scope-overlap 校验：`scope.species ∩ banlist.species == ∅` 就放行。

### Concepts.maturity 9-enum 双轨制

```yaml
# wiki/concepts/*.md
maturity: <one of>
  # upstream CS scale
  stable / active / emerging / deprecated
  # bio scale（D2 新增）
  consensus / well-supported / contested / hypothesis / falsified
```

每个 concept 自选 scale，**禁止混用**（lint 检测）。bio 概念的认知演进维度（`hypothesis → contested → well-supported → consensus` 或 `→ falsified`）跟 CS 概念的工程成熟度（`emerging → active → stable → deprecated`）是两套正交的轴。

### 完整 schema 对照

| 文件 | upstream | bio fork |
|---|---|---|
| `runtime/schema/entities.yaml` | 9 entity types | + `datasets:` block |
| `runtime/schema/edges.yaml` | 13 edge types | + 14 bio edges + 5 typed-metadata schemas |
| `runtime/schema/conventions.yaml` | CS conventions | + Phase/Stage disambiguation (D1) |
| `runtime/loader.py` | base validators | + `validate_edge_attributes` typed metadata |
| `tools/lint.py` | base 5 checks | unchanged |
| `tools/lint_bio.py` | _(new)_ | 5 bio cross-checks |

---

## 兼容性 / 限制 / 下一步

**向下兼容**：所有新字段都是 optional + 有 default。upstream wiki 直接 pull 本 fork 不需要任何迁移。已有 CS 实验页 / idea 页 / concept 页都能继续 lint pass。

**当前限制**：
- 7 / 14 类生物关系边已 live（80 总边中 7 条 bio）；剩 7 类（degrades · phosphorylates · sumoylates · acetylates · methylates · glycosylates · wet_lab_validated）还在等使用场景
- 5 / 14 类边类型的 metadata schema 是 closed-set；其余 9 类暂时允许任意 metadata
- `lint_bio.py` 的 cellosaurus `CVCL_[A-Z0-9]{4}` 格式 check 待补
- 8 个实验全部 `status: planned`，paper §4 现有结果都带 [SIMULATED] 标记，等 GPU 跑通后替换

**正在做**：
- 补 cellosaurus 格式 check
- 加 3 条 live 生物关系边（lenalidomide-CRBN binds / thalidomide-CRBN binds / pomalidomide-CRBN binds）
- 给 PROTAC-DB / DegronMD / DeepTernary 等关键论文做 `/ingest`，把 paper/references.bib 的 7 个 [UNCONFIRMED] 引用降到 0
- v2 论文跑真实 GPU 实验替换 paper §4 现有的 [SIMULATED] 数字

---

## 引用本 fork

如果你在工作中用到了 bio fork 的 schema / lint / typed metadata 机制，欢迎引用：

```bibtex
@misc{omegawiki-bio-2026,
  author = {dcyukino and DAIR Lab},
  title  = {ΩmegaWiki / bio-adaptation: bioinformatics-shaped fork of LLM-Wiki},
  year   = {2026},
  url    = {https://github.com/skyllwt/OmegaWiki/tree/dev-dcy-biology}
}
```

---

## 致谢

upstream ΩmegaWiki 由北京大学 [DAIR Lab](https://cuibinpku.github.io/) 团队（Weitong Qian · Beicheng Xu · Zhongao Xie · Bowen Fan · Guozheng Tang · Xinzhe Wu · Jiale Chen · Mingtian Yang）构建。bio-adaptation fork 在其上做生信场景改造。
