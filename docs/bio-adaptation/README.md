<div align="center">

<img src="../../assets/logo.png" width="160" alt="ΩmegaWiki Logo">

# ΩmegaWiki · bio-adaptation

### A bioinformatics-shaped DLC for LLM-Wiki / LLM-Wiki 的生信场景 DLC

**PTM-aware degrader · structural biology · ML for molecules**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Entity Types](https://img.shields.io/badge/Entity_Types-10_(vs_9)-green.svg)](#wiki-structure-differences)
[![Bio Edges](https://img.shields.io/badge/Bio_Edge_Types-14-purple.svg)](#wiki-structure-differences)
[![Skills](https://img.shields.io/badge/Skills-24-orange.svg)](#skills-differences)

[**English**](#english) · [**中文**](#chinese) · [upstream README](../../README.md) · [📷 demo gallery](DEMO.zh.md)

</div>

---

## Author / 作者

<div align="center">
<table>
  <tr>
    <td align="center" width="200">
      <img src="../../assets/DiChenyang_circle.jpg" width="100" alt="Di Chenyang"/>
      <br/><br/>
      <b>Di Chenyang</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2023</sub>
    </td>
  </tr>
</table>
</div>

> Bio-adaptation DLC built on top of upstream [ΩmegaWiki](../../README.md) by [DAIR Lab](https://cuibinpku.github.io/) at Peking University. /
> 本 DLC 在北京大学 [DAIR Lab](https://cuibinpku.github.io/) 团队的上游 [ΩmegaWiki](../../README.md) 之上做生信场景改造。

---

# <a id="english"></a>English

## Introduction

Upstream ΩmegaWiki defaults to a CS shape — `arxiv` is the primary paper ID, single dataset concept, experiment records get by with `model + dataset + hardware` only. That shape is efficient for ML paper workflows; it gets uncomfortable the moment you bring it to **bioinformatics / structural biology / drug discovery**: DOI and PMID are more universal than arXiv IDs, datasets need versioning, wet-lab vs in-silico experiments must be distinguishable, and cellosaurus / RRID / PDB version provenance must trace cleanly.

This DLC layers 12 schema + skill + tooling adaptations on top of upstream, **fully backwards-compatible** — an upstream wiki can pull this DLC without any migration. The wiki/ directory on this branch is **intentionally empty** (`.gitkeep` placeholders for each entity directory); after cloning, you build your own bio wiki from scratch via `/init` + `/ingest`.

**Who this DLC is for**:

- Researchers working on computational drug discovery / PROTAC / structure prediction / multi-omics
- People who want a research knowledge base that remembers *"which paths have been tried and which are dead-ends"*
- Research groups automating the paper → idea → experiment → paper loop

A demo gallery walks through the 9 capabilities end-to-end with screenshots from a sample PTM-aware degrader workflow: [📷 `DEMO.zh.md`](DEMO.zh.md).

## Updates

### Core differences from upstream

| | upstream ΩmegaWiki | bio DLC |
|---|---|---|
| **Entity types** | 9 | **10** (adds `datasets/`) |
| **Edge types** | 13 (CS citations + reasoning) | **+ 14 bio relations** (binds / phosphorylates / ubiquitinates / clinical_trial_for / fda_approved_for ...) |
| **Edge metadata** | free-text `evidence` field | **+ 5 closed-set typed schemas** (runtime-validated) |
| **Paper IDs** | `arxiv` only | **+ `doi` + `pmid` + `s2_id`** three-axis |
| **Experiment setup** | model / dataset / hardware | **+ 9 bio fields** (in_silico_or_wet · species · cell_line · assay_type · force_field · solvent_model · simulation_length · weight_version · random_seed_protocol) |
| **Experiment budget** | single `estimated_hours` | **+ 6 fields** (GPU-h · CPU-h · MD wall-clock-h · wet-lab USD · FTE-weeks · data NDA wait days) |
| **Reproducibility** | git commit hash | **+ 5-ID block** (RRID · Cellosaurus · Addgene · PDB versions · dataset versions) |
| **Idea rating** | `priority` 1-5 | **+ GRADE evidence strength** (low / moderate / high) |
| **Failed ideas** | only `status: failed` | **+ `scope:` block** — failure bans only the saturated subspace, leaves other subspaces open |
| **Concept maturity** | 4 enums (stable / active / emerging / deprecated) | **+ 5 bio enums** (consensus / well-supported / contested / hypothesis / falsified) |
| **Literature search** | Semantic Scholar | **+ PubMed E-utilities** (much higher coverage for bio literature) |
| **Lint** | `tools/lint.py` | **+ `tools/lint_bio.py`** (5 bio-specific cross-checks) |
| **Domain slugs** | free text | **15 canonical slugs** (`bioinformatics` · `comp-drug-discovery` · `protein-engineering` ...) |

Full changelog: [`CHANGELOG.zh.md`](CHANGELOG.zh.md) / [`CHANGELOG.en.md`](CHANGELOG.en.md). Full design + migration report: [`REPORT.zh.md`](REPORT.zh.md) / [`REPORT.en.md`](REPORT.en.md).

## Quick Start

This walks a new bio user through the full pipeline: setup → add papers → build wiki → generate ideas → design experiments → write paper. **The branch ships with an empty wiki** — every concrete bio entity you see in the demo gallery is something `/ingest` and `/ideate` produced from your own raw sources.

**Prerequisites**: Python 3.9+, Node.js 18+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

### 0. Clone + setup (shared with upstream)

```bash
git clone https://github.com/skyllwt/OmegaWiki.git -b dev-dcy-biology
cd OmegaWiki

chmod +x setup.sh && ./setup.sh            # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

cp .env.example .env                       # then edit: add LLM_API_KEY etc.
```

API keys you may want in `.env` (all optional; defaults degrade gracefully):

| Key | What it powers |
|-----|---|
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | Cross-model review LLM (DeepSeek / Qwen / OpenAI / etc., OpenAI-compatible) |
| `SEMANTIC_SCHOLAR_API_KEY` | S2 citation graph |
| `DEEPXIV_TOKEN` | DeepXiv semantic search |

### 1. Verify the DLC is installed

```bash
.venv/bin/python tools/lint.py             # base: 0 🔴 / 0 🟡 / N 🔵 (info)
.venv/bin/python tools/lint_bio.py         # bio: 0 🔴 / 0 🟡 / 0 🔵
```

A clean lint run on an empty wiki confirms schema + tooling are in place.

### 2. Add your bio papers

Drop your `.tex` or `.pdf` files into the `raw/` tree:

```bash
cp ~/path/to/papers/*.pdf raw/papers/        # main paper corpus
cp ~/path/to/notes/*.md   raw/notes/         # optional: intent notes / reading sketches
cp ~/path/to/saved/*.html raw/web/           # optional: saved blog posts / preprint pages
```

`raw/papers/` accepts `.tex` source or `.pdf`. The system handles both.

### 3. Bootstrap the wiki

Launch Claude Code, then run `/init`:

```
claude
> /init bioinformatics
```

`/init` scans `raw/`, kicks off bio-flavored `/ingest` (DOI / PubMed ID / Cellosaurus / PDB / UniProt three-axis auto-extraction), discovers related papers via S2 + PubMed, and populates `wiki/papers/`, `wiki/concepts/`, `wiki/people/`. After it returns, browse the result:

```bash
ls wiki/papers/                              # your paper pages
ls wiki/concepts/                            # auto-derived concepts
cat wiki/index.md                            # rebuilt catalog
.venv/bin/python tools/serve.py              # interactive graph @ http://localhost:8765/
```

### 4. Generate research ideas

```
> /ideate
```

The skill runs a 4-phase pipeline: landscape scan → dual-model brainstorm → first-pass filter → deep validation. Output lands in `wiki/ideas/` with `status` (`proposed` / `tested` / `validated` / `failed`), bio `grade` (low / moderate / high), and a `scope:` block for any failures so future `/ideate` runs avoid the same dead-end subspace.

Verify a novel idea before committing to experiments:

```
> /novelty <idea-slug>
```

This crosses 5 channels (WebSearch · Semantic Scholar · **PubMed E-utilities** · wiki dedup · Review LLM cross-verify) and writes a multi-source novelty score back to the idea page.

### 5. Design experiments

```
> /exp-design <idea-slug>
```

For each promising idea, `/exp-design` produces cascaded experiment blocks (baseline / validation / ablation / robustness) with the bio-required `setup` fields (`in_silico_or_wet` · `species` · `cell_line` · `assay_type` · `force_field` · `solvent_model` · `simulation_length` · `weight_version` · `random_seed_protocol`), the 6-field `estimated_cost` block (GPU-h / CPU-h / MD-wall-clock / wet-lab USD / FTE-weeks / data NDA wait), and the 5-ID `reproducibility` block (RRID / Cellosaurus / Addgene / PDB / dataset versions).

Run them, then evaluate:

```
> /exp-run <experiment-slug>              # local or remote-GPU execution
> /exp-eval <experiment-slug>             # verdict gate → auto-update graph
```

### 6. Write the paper

```
> /paper-plan <primary-idea-slug>
> /paper-draft wiki/outputs/paper-plan-<slug>-<date>.md
> /paper-compile paper/
```

`/paper-plan` builds an outline from the idea graph (evidence map + section plan + figure plan + citation plan, with mandatory Review LLM area-chair pass). `/paper-draft` writes the LaTeX section by section from wiki sources, generates figures, fetches BibTeX. `/paper-compile` produces the PDF + runs submission-readiness checks.

### 7. (Optional) Watch arXiv daily

```bash
bash demo/run-demo.sh                      # one-off run on demo/sample-feed.json
```

Wires up to GitHub Actions cron for daily arXiv tracking; LLM ranks new candidates against your wiki state. See [`examples/output/digest-sample.md`](../../examples/output/digest-sample.md) for a pre-rendered LLM-ranked output (no API call needed).

## <a id="skills-differences"></a>Skills (Differences)

Full 24-skill catalog is in the [upstream README](../../README.md#skills). This DLC modifies the prompts / defaults of 5 skills; **no new skills added, none removed**:

| Skill | What this DLC changes |
|---|---|
| `/ingest` | Adds a bio NER pre-pass: auto-extracts DOI, PubMed ID, Cellosaurus CVCL ID, PDB ID, UniProt accession from PDF / arXiv into frontmatter |
| `/ideate` | A failed idea's `scope:` block participates in ban judgment — only same-domain + same-data-regime gets blocked; cross-species / low-data / new-disease-area is let through |
| `/exp-design` | Default produces 4 statistical forms (bootstrap CI · stratified k-fold · LOO-CV · bio×tech replicates), auto-routed by `setup.in_silico_or_wet`; auto-fills 9 bio setup fields by setup type |
| `/novelty` | Adds **PubMed E-utilities** as a full-weight channel (much higher bio literature coverage than S2); for bio novelty runs, this is the primary channel |
| `/check` | Runs `tools/lint_bio.py` 5-check cross-validator on top of base lint |

`/paper-draft` also has a "result-first writing" bio-style adjustment (state results before method), but that is a prompt nudge rather than a structural difference.

## <a id="wiki-structure-differences"></a>Wiki Structure (Differences)

### New 10th entity: `datasets/`

```yaml
# wiki/datasets/<slug>.md (example structure — your own datasets will populate this)
---
slug: "<your-dataset-slug>"
maturity: active                              # active / archived / deprecated
access: public                                # public / on_request / restricted
aliases: []                                   # alternative names
versions:
  - version: "v1"
    released: ""
    url: ""
    n_entries: ""
    notes: ""
canonical_url: ""
license: ""
key_papers: []                                # back-references from papers using this dataset
date_updated: 2026-MM-DD
---
```

Downstream experiments reference a specific dataset via `setup.dataset: [[your-dataset-slug]]`. `tools/lint_bio.py` cross-checks `experiments.reproducibility.dataset_versions[].version` against `datasets/*.versions[].version` in both directions.

### 14 bio relation edge types

`runtime/schema/edges.yaml` registers — on top of upstream's 13 CS edges — these bio relations:

```
binds · targets_protein · degrades · phosphorylates · ubiquitinates ·
sumoylates · acetylates · methylates · glycosylates ·
wet_lab_validated · clinical_validated ·
clinical_trial_for · fda_approved_for ·
validates_in_species · dataset_version_used
```

Each edge may carry `confidence: high | medium | low` (upstream edges default to no confidence).

### 5 closed-set typed-metadata schemas

Edges can carry structured metadata, validated at load time by `runtime/loader.py::validate_edge_attributes`:

```yaml
# runtime/schema/edges.yaml (excerpt)
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

Undeclared keys → lint warning (with "known keys" hint). Required key missing → error. Type mismatch → rejected. The other 9 bio edges currently accept arbitrary metadata (forward-compatibility).

### Experiment page — 3 new blocks

```yaml
# wiki/experiments/*.md frontmatter (template shown; /exp-design fills these per-experiment)
setup:
  model: ""
  dataset: "[[your-dataset]] subset name"
  hardware: ""
  framework: ""
  in_silico_or_wet: ""                         # bio: new
  species: []                                  # bio: new
  cell_line: ""                                # bio: new
  assay_type: ""                               # bio: new
  force_field: ""                              # bio: new
  solvent_model: ""                            # bio: new
  simulation_length: ""                        # bio: new
  weight_version: ""                           # bio: new
  random_seed_protocol: ""                     # bio: new

estimated_cost:                                # bio: entirely new
  gpu_hours: 0
  cpu_hours: 0
  md_wallclock_hours: 0                        # MD billed separately
  wet_lab_usd: 0
  fte_weeks: 0
  dataset_access_lead_time_days: 0

reproducibility:                               # bio: entirely new
  rrid: []
  cellosaurus: []                              # cell line CVCL_[A-Z0-9]{4}
  addgene: []
  pdb_versions: []
  dataset_versions:                            # cross-checked with datasets/*.versions[]
    - dataset_slug: <your-dataset-slug>
      version: v1
      accessed_date: YYYY-MM-DD
```

### Idea page — GRADE + scope ban

```yaml
# wiki/ideas/<slug>.md
grade: low | moderate | high                   # bio: new — evidence-strength rating

# When status: failed, add a scope block so future /ideate runs only ban
# the saturated subspace, not the entire research direction:
scope:                                         # bio: new
  species: []                                  # the saturated species
  disease_area: []
  data_regime: high_data | low_data            # the saturated regime
```

When `/ideate` runs, new ideas go through scope-overlap validation: `scope.species ∩ banlist.species == ∅` → let through.

### `concepts.maturity` 9-enum dual scale

```yaml
# wiki/concepts/*.md
maturity: <one of>
  # upstream CS scale
  stable / active / emerging / deprecated
  # bio scale (new)
  consensus / well-supported / contested / hypothesis / falsified
```

Each concept picks one scale; **mixing is prohibited** (lint detects). The bio cognitive-progression axis (`hypothesis → contested → well-supported → consensus`, or `→ falsified`) is orthogonal to the CS engineering-maturity axis (`emerging → active → stable → deprecated`).

### Schema files at a glance

| File | upstream | bio DLC |
|---|---|---|
| `runtime/schema/entities.yaml` | 9 entity types | + `datasets:` block |
| `runtime/schema/edges.yaml` | 13 edge types | + 14 bio edges + 5 typed-metadata schemas |
| `runtime/schema/conventions.yaml` | CS conventions | + Phase/Stage disambiguation |
| `runtime/loader.py` | base validators | + `validate_edge_attributes` typed metadata |
| `tools/lint.py` | base 5 checks | unchanged |
| `tools/lint_bio.py` | _(new)_ | 5 bio cross-checks |

---

# <a id="chinese"></a>中文

## 介绍

upstream ΩmegaWiki 默认是 CS 形态——`arXiv` 是论文主 ID、单一 dataset 概念、实验记录里 `model + dataset + hardware` 三字段就够。这套形态在做 ML 论文工作流时高效；放到**生信 / 结构生物 / 药物发现**就处处别扭：DOI/PMID 比 arXiv ID 更主流、数据集要版本化、湿实验和干实验要明确区分、cellosaurus / RRID / PDB version 要可复现 trace。

本 DLC 在不破坏 upstream 工作流的前提下做了 12 项 schema + skill + tooling 改造，**全部向下兼容**——upstream wiki 直接 pull 本 DLC 不需要任何迁移。**本 branch 的 `wiki/` 目录是有意空置的**（每个实体目录只保留 `.gitkeep` 占位）；clone 后通过 `/init` + `/ingest` 从 0 开始建你自己的 bio wiki。

**这个 DLC 适合谁**：

- 在做计算药物发现 / PROTAC / 结构预测 / 多组学的科研人员
- 需要一个能记住"哪些路走过 / 哪些走不通"的研究知识库
- 想把"论文 → idea → 实验 → 论文"整个 loop 自动化的研究组

效果展示画廊（用一份 PTM-aware degrader 真实工作流截图走完 9 项能力）：[📷 `DEMO.zh.md`](DEMO.zh.md)。

## 更新

### 跟 upstream 的核心区别

| | upstream ΩmegaWiki | bio DLC |
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

完整 changelog: [`CHANGELOG.zh.md`](CHANGELOG.zh.md)。完整设计与迁移报告: [`REPORT.zh.md`](REPORT.zh.md) / [`REPORT.en.md`](REPORT.en.md)。

## Quick Start

这一段带新 bio 用户跑通完整流程：setup → 加论文 → 建 wiki → 生成 idea → 设计实验 → 写论文。**branch ship 时 `wiki/` 是空的**——demo gallery 里看到的每个 bio 实体都是 `/ingest` 和 `/ideate` 从你自己的 raw 源里产出的。

**前置**：Python 3.9+，Node.js 18+，[Claude Code](https://docs.anthropic.com/en/docs/claude-code)。

### 0. Clone + 一键 setup（与 upstream 共用）

```bash
git clone https://github.com/skyllwt/OmegaWiki.git -b dev-dcy-biology
cd OmegaWiki

chmod +x setup.sh && ./setup.sh            # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

cp .env.example .env                       # 然后编辑：加 LLM_API_KEY 等
```

`.env` 可选 key（不配也能跑，会优雅退化）：

| Key | 干什么 |
|-----|---|
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | Cross-model review LLM（DeepSeek / Qwen / OpenAI 等，OpenAI 兼容协议）|
| `SEMANTIC_SCHOLAR_API_KEY` | S2 citation graph |
| `DEEPXIV_TOKEN` | DeepXiv 语义检索 |

### 1. 验证 DLC 装好

```bash
.venv/bin/python tools/lint.py             # base: 0 🔴 / 0 🟡 / N 🔵 (info)
.venv/bin/python tools/lint_bio.py         # bio: 0 🔴 / 0 🟡 / 0 🔵
```

空 wiki 上 lint 全过表示 schema + 工具就位。

### 2. 加你的 bio 论文

把你的 `.tex` 或 `.pdf` 文件丢进 `raw/`：

```bash
cp ~/path/to/papers/*.pdf raw/papers/        # 主论文 corpus
cp ~/path/to/notes/*.md   raw/notes/         # 可选：阅读笔记 / intent 草稿
cp ~/path/to/saved/*.html raw/web/           # 可选：保存的 blog / preprint 页
```

`raw/papers/` 接受 `.tex` 源码或 `.pdf`，二者皆可。

### 3. 启动 wiki

启动 Claude Code 跑 `/init`：

```
claude
> /init bioinformatics
```

`/init` 扫描 `raw/`，触发 bio-flavored `/ingest`（DOI / PubMed ID / Cellosaurus / PDB / UniProt 三轴自动抽取），通过 S2 + PubMed 发现相关论文，最终在 `wiki/papers/`、`wiki/concepts/`、`wiki/people/` 落盘。完成后浏览：

```bash
ls wiki/papers/                              # 你的论文 page
ls wiki/concepts/                            # 自动派生的 concepts
cat wiki/index.md                            # 重建后的 catalog
.venv/bin/python tools/serve.py              # 浏览器看 @ http://localhost:8765/
```

### 4. 生成研究 idea

```
> /ideate
```

4-phase 流水线：landscape scan → 双模型 brainstorm → first-pass filter → deep validation。输出落在 `wiki/ideas/`，带 `status`（`proposed` / `tested` / `validated` / `failed`）、bio `grade`（low / moderate / high）、失败 idea 自带 `scope:` 块——下次 `/ideate` 只屏蔽已 saturated 的子空间，不屏蔽整个方向。

跑 idea 前验证新颖性：

```
> /novelty <idea-slug>
```

5 通道交叉（WebSearch · Semantic Scholar · **PubMed E-utilities** · wiki dedup · Review LLM cross-verify）写回多源 novelty 分数。

### 5. 设计实验

```
> /exp-design <idea-slug>
```

为每个有前景的 idea，`/exp-design` 产出 cascaded experiment blocks（baseline / validation / ablation / robustness），含 bio 必需 `setup` 字段（`in_silico_or_wet` · `species` · `cell_line` · `assay_type` · `force_field` · `solvent_model` · `simulation_length` · `weight_version` · `random_seed_protocol`），6-字段 `estimated_cost` 块（GPU-h / CPU-h / MD wall-clock / wet-lab USD / FTE-weeks / data NDA 等待），5-ID `reproducibility` 块（RRID / Cellosaurus / Addgene / PDB / dataset versions）。

跑 + 评估：

```
> /exp-run <experiment-slug>              # 本地或 remote-GPU 执行
> /exp-eval <experiment-slug>             # 判决 gate → 自动更新 graph
```

### 6. 写论文

```
> /paper-plan <primary-idea-slug>
> /paper-draft wiki/outputs/paper-plan-<slug>-<date>.md
> /paper-compile paper/
```

`/paper-plan` 从 idea graph 出发建大纲（evidence map + section plan + figure plan + citation plan，Review LLM area-chair pass 必跑）。`/paper-draft` 按节用 wiki 数据写 LaTeX、生成图、抓 BibTeX。`/paper-compile` 编译 PDF + 跑 submission-readiness 检查。

### 7.（可选）每日 arXiv 跟踪

```bash
bash demo/run-demo.sh                      # 在 demo/sample-feed.json 上一次性跑
```

可挂 GitHub Actions cron 每天跑；LLM 对新候选论文按 wiki 状态排序。预渲染输出：[`examples/output/digest-sample.md`](../../examples/output/digest-sample.md)（无 API key 也能 cat）。

## Skills（区别）

完整 24 skills 见 [主 README](../../README.md#skills)。本 DLC 影响以下 5 个 skill 的 prompt / 默认值，**没有新增 skill 也没有移除 skill**：

| Skill | bio DLC 的改动 |
|---|---|
| `/ingest` | 增加 bio NER pre-pass：自动从 PDF / arXiv 抽取 DOI、PubMed ID、Cellosaurus CVCL ID、PDB ID、UniProt accession 填入 frontmatter |
| `/ideate` | 失败 idea 的 `scope:` 块参与 ban 判定——同领域同 data_regime 才屏蔽，跨物种 / 低数据 / 新 disease_area 放行 |
| `/exp-design` | 默认产出 4 种统计方案（bootstrap CI · stratified k-fold · LOO-CV · bio×tech replicates），按 `setup.in_silico_or_wet` 自动路由；自动按 setup 类型补 9 bio 字段 |
| `/novelty` | 新增 **PubMed E-utilities** 作为满权重通道（生信文献覆盖率远高于 S2），bio 论文跑 novelty 时主要看这个 |
| `/check` | 在 base lint 之外额外跑 `tools/lint_bio.py` 5 项 cross-check |

`/paper-draft` 也有"result-first writing"的 bio 风格调整（先抛出结果再讲方法），但这是 prompt 微调，不算结构性区别。

## Wiki Structure（区别）

完整字段示例（YAML + closed-set schemas）见上面 **English § Wiki Structure (Differences)**。要点：

- **新增第 10 类实体 `datasets/`**：版本化、access 等级、aliases、下游 cross-check
- **新增 14 类生物关系边**：binds / phosphorylates / ubiquitinates / clinical_trial_for / fda_approved_for ... 每条带 confidence
- **5 种 closed-set typed-metadata schemas**：`dataset_version_used` · `clinical_trial_for` · `fda_approved_for` · `binds` · `validates_in_species`，runtime 强校验
- **实验 page 加 3 个新 block**：`setup` 增 9 bio 字段 + `estimated_cost` 6 字段 + `reproducibility` 5-ID 块
- **Idea page 加 GRADE + scope ban**：`grade: low|moderate|high` + 失败 idea 的 `scope:` 子空间标记
- **Concepts.maturity 9-enum 双轨制**：CS engineering 轴（stable/active/emerging/deprecated）+ bio 认知演进轴（consensus/well-supported/contested/hypothesis/falsified），不可混用

---

## Acknowledgments / 致谢

upstream ΩmegaWiki is built by the [DAIR Lab](https://cuibinpku.github.io/) team at Peking University (Weitong Qian · Beicheng Xu · Zhongao Xie · Bowen Fan · Guozheng Tang · Xinzhe Wu · Jiale Chen · Mingtian Yang). The bio-adaptation DLC adapts that foundation to bioinformatics scenarios.

upstream ΩmegaWiki 由北京大学 [DAIR Lab](https://cuibinpku.github.io/) 团队（Weitong Qian · Beicheng Xu · Zhongao Xie · Bowen Fan · Guozheng Tang · Xinzhe Wu · Jiale Chen · Mingtian Yang）构建。bio-adaptation DLC 在其上做生信场景改造。

## License

[MIT](../../LICENSE) — same as upstream / 与 upstream 一致。
