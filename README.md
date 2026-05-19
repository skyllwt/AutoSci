<div align="center">

<img src="assets/logo.png" width="180" alt="ΩmegaWiki Logo">

# ΩmegaWiki

### Karpathy's LLM-Wiki Vision, Fully Realized

**Your AI Research Platform — From Papers to Publications, Powered by [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

*From paper ingestion to publication — your research knowledge compounds, never decays.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Skills](https://img.shields.io/badge/Skills-24-purple.svg)](#skills)
[![Claude Code](https://img.shields.io/badge/Powered_by-Claude_Code-d97706.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Bilingual](https://img.shields.io/badge/i18n-EN_|_中文-orange.svg)](#bilingual-support)

[English](#what-is-ωmegawiki) | [中文](#中文)

</div>

---

## Team

ΩmegaWiki is built by [DAIR Lab](https://cuibinpku.github.io/) at Peking University — a fully agentic platform that automates the complete research pipeline, from knowledge ingestion to paper submission.

<div align="center">
<table>
  <tr>
    <td align="center" width="165">
      <a href="https://skyllwt.github.io/">
        <img src="assets/WeitongQian_circle.png" width="90" alt="Weitong Qian"/>
      </a>
      <br/><br/>
      <a href="https://skyllwt.github.io/"><b>Weitong Qian</b></a>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2023</sub>
    </td>
    <td align="center" width="165">
      <img src="assets/BeichengXu_circle.png" width="90" alt="Beicheng Xu"/>
      <br/><br/>
      <b>Beicheng Xu</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Ph.D. · 2023</sub>
    </td>
    <td align="center" width="165">
      <img src="assets/ZhongaoXie_circle.png" width="90" alt="Zhongao Xie"/>
      <br/><br/>
      <b>Zhongao Xie</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2025</sub>
    </td>
    <td align="center" width="165">
      <img src="assets/BowenFan_circle.png" width="90" alt="Bowen Fan"/>
      <br/><br/>
      <b>Bowen Fan</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2024</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="165">
      <img src="assets/GuozhengTang_circle.png" width="90" alt="Guozheng Tang"/>
      <br/><br/>
      <b>Guozheng Tang</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2024</sub>
    </td>
    <td align="center" width="165">
      <a href="https://brzgw555.github.io">
        <img src="assets/XinzheWu_circle.png" width="90" alt="Xinzhe Wu"/>
      </a>
      <br/><br/>
      <a href="https://brzgw555.github.io"><b>Xinzhe Wu</b></a>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2024</sub>
    </td>
    <td align="center" width="165">
      <img src="assets/JialeChen_circle.png" width="90" alt="Jiale Chen"/>
      <br/><br/>
      <b>Jiale Chen</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2024</sub>
    </td>
    <td align="center" width="165">
      <a href="https://morrowmind.live">
        <img src="assets/MingtianYang_circle.png" width="90" alt="Mingtian Yang"/>
      </a>
      <br/><br/>
      <a href="https://morrowmind.live"><b>Mingtian Yang</b></a>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2024</sub>
    </td>
  </tr>
</table>
</div>

---

## Bio-Adaptation Fork

> **ΩmegaWiki / bio-adaptation — PTM-aware degrader · structural biology · ML for molecules.** A bioinformatics-shaped fork of upstream ΩmegaWiki, driven through a real PTM-aware degrader nomination workflow and hardened against the CS-shaped assumptions that workflow surfaced.

<div align="center">
<img src="assets/demo.gif" width="800" alt="Bio-adaptation demo (≈50s walkthrough)">
<br>
<sub>30–60s walkthrough — lint sweep → SPA knowledge graph → DeepSeek ranking → final digest. Storyboard in <a href="docs/bio-adaptation/DEMO_PLAN.en.md">DEMO_PLAN.en.md</a>.</sub>
</div>

### What this fork changes

| | Upstream ΩmegaWiki | Bio-adaptation fork |
|---|---|---|
| **Domain shape** | CS / AI — arXiv-shaped papers, `claims/` ledger | Bioinformatics — DOI/PMID/bioRxiv first-class, `datasets/` as 10th entity type |
| **Evidence verbs** | `supports`, `contradicts`, `tested_by`, `invalidates` | + `wet_lab_validated`, `clinical_validated`, `mechanistic_basis`, `correlative`, `predicts`, optional GRADE |
| **Graph edges** | paper-paper, paper-concept, claim/experiment | + bio relations (`targets_protein`, `binds`, `degrades`, `phosphorylates`, `ubiquitinates`, …), validation/translation (`clinical_trial_for`, `fda_approved_for`), dataset-version provenance |
| **Experiment cost** | single `estimated_hours` | structured: `gpu_hours`, `cpu_hours`, `md_wallclock_hours`, `wet_lab_usd`, `fte_weeks`, `dataset_access_lead_time_days` |
| **Skill prompts** | CS examples | bio NER pre-pass in `/ingest`, MD/wet-lab budgeting in `/exp-design`, GRADE weighting in `/novelty`, result-first writing in `/paper-draft`, …  |
| **Worked example** | LLM papers, LoRA, flash-attention | 11 papers covering AlphaFold 2/3, PTM site prediction, E3 ligase platforms, geometric DL for molecules; 22 ideas (11 validated / 2 failed), 8 designed experiments, 80 graph edges |

Full per-item rationale and lint metrics across the migration: [`docs/bio-adaptation/REPORT.en.md`](docs/bio-adaptation/REPORT.en.md)（中文：[`REPORT.zh.md`](docs/bio-adaptation/REPORT.zh.md)）.

<div align="center">
<img src="assets/canvas-ptm-focus.png" width="800" alt="Obsidian Canvas — PTM-aware degrader neighborhood (23 nodes / 27 edges)">
<br>
<sub>PTM-aware degrader neighborhood — exported from <code>wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas</code>.</sub>
</div>

### Bio Quick Tour — 一眼看清生物适配做了什么

> **2026-05-12 backlog 完结快照**：A 8/8 (Schema) · B 14/14 + infra (Graph) · C 9/9 (Skills) · D 2/2 (Conventions) —— 累计 **39 pilots** 在 16 个 commit 内合并；lint 0 🔴 / 0 🟡 / 11 🔵 (base) + 0/0/0 (bio)。

| 维度 | 数量 | 内容 / live 证据 |
|---|---|---|
| **Wiki 实体类型** | **10** (vs upstream 9) | `datasets/` 是新增第 10 类一等公民；当前 1 个 dataset (`ternarydb`) live，含 versions 表 + `key_papers` 反向链接 |
| **Bio edge types 注册** | **14** | `binds` · `targets_protein` · `degrades` · `phosphorylates` · `ubiquitinates` · `sumoylates` · `acetylates` · `methylates` · `glycosylates` · `wet_lab_validated` · `clinical_validated` · `clinical_trial_for` · `fda_approved_for` · `validates_in_species` · `dataset_version_used` |
| **Bio edges live** | **7 条 / 5 类型** | 80 总边中 7 条 bio relation；含 `targets_protein` ×1 · `binds` ×2 · `ubiquitinates` ×1 · `validates_in_species` ×1 · `dataset_version_used` ×2 |
| **Typed metadata schemas** | **5** | `dataset_version_used` · `binds` · `clinical_trial_for` · `fda_approved_for` · `validates_in_species` —— closed-set + required keys + type checks，由 `runtime/loader.py` 在 load 时强制 |
| **Bio setup 字段** (`experiments.setup`) | **9** | `in_silico_or_wet` · `species` · `cell_line` · `assay_type` · `force_field` · `solvent_model` · `simulation_length` · `weight_version` · `random_seed_protocol` —— 8/8 experiments 已回填 |
| **Reproducibility ID 维度** (`experiments.reproducibility`) | **5** | `rrid` · `cellosaurus` · `addgene` · `pdb_versions[]` · `dataset_versions[]` —— `tools/lint_bio.py` 闭环 cross-check 与 `datasets/*.versions[]` 双向一致 |
| **Bio lint 检查** (`tools/lint_bio.py`) | **5** | dataset_version cross-check / domain slug 规范化 / setup 字段一致性 / cost 块完整性 / reproducibility ID 格式 |
| **Domain 受控词表** | **15 canonical slugs** | A4 把 9 个 free-text variants → 7 canonical slug（覆盖 24 页面），如 `bioinformatics` · `comp-drug-discovery` · `protein-engineering` |
| **Multi-source novelty channels** (`/novelty`) | **5** | WebSearch · Semantic Scholar · **PubMed E-utilities** (bio 独占满权重) · wiki dedup · Review LLM cross-verify |
| **`/exp-design` 统计默认值形态** | **4** | bootstrap CI · stratified k-fold · LOO-CV · bio×tech replicates —— 按 setup type 自动路由 |
| **`concepts.maturity` 状态机** | **9 enum** (D2 扩展自 4) | `hypothesis` → `contested` → `well-supported` → `consensus` / `falsified` 等 —— wiki 自身的认知演进维度 |

完整 backlog × pilot 表见 [`docs/bio-adaptation/CHANGELOG.zh.md`](docs/bio-adaptation/CHANGELOG.zh.md)（39 entries）。
比赛 (智源 Agent for Science) 上下文、视频脚本、P0-P2 优化清单见 [`docs/bio-adaptation/COMPETITION_NOTES.zh.md`](docs/bio-adaptation/COMPETITION_NOTES.zh.md)。

### 📷 Bio Demo Gallery — 9 张截图端到端讲透

完整 9 图 walkthrough（每张图 caption + 系统能力证据 + 对叙事贡献）：[**`docs/bio-adaptation/DEMO_WALKTHROUGH.zh.md`**](docs/bio-adaptation/DEMO_WALKTHROUGH.zh.md)

| | 主题 | 截图 |
|---|---|---|
| 图 1 | Paper frontmatter (DOI + PMID + domain) | [`assets/demo-01-paper.png`](assets/demo-01-paper.png) |
| 图 2 | Main idea (GRADE + 8 linked experiments) | [`assets/demo-02-idea-main.png`](assets/demo-02-idea-main.png) |
| 图 3 | Failed idea + C3 banlist scope | [`assets/demo-03-idea-failed.png`](assets/demo-03-idea-failed.png) |
| 图 4 | Experiment 全字段（setup + cost + reproducibility）| [`assets/demo-04-experiment.png`](assets/demo-04-experiment.png) |
| 图 5 | Dataset 第 10 类一等公民 + versions 表 | [`assets/demo-05-dataset.png`](assets/demo-05-dataset.png) |
| 图 6 | SPA 知识图谱 + 14 bio edge types | [`assets/demo-06-spa-graph.png`](assets/demo-06-spa-graph.png) |
| 图 7 | Typed metadata closed-set schema | [`assets/demo-07-spa-metadata.png`](assets/demo-07-spa-metadata.png) |
| 图 8 | daily-arxiv DeepSeek 排序 + digest | [`assets/demo-08-digest.png`](assets/demo-08-digest.png) |
| 图 9 | Obsidian Canvas 策展知识地图 | [`assets/demo-09-canvas.png`](assets/demo-09-canvas.png) |

Bio case study 完整论文（同一 idea graph 端到端产出，Stanford Agentic Reviewer 6.0/10）：[**`paper/main.tex`**](paper/main.tex)；规划见 [`wiki/outputs/paper-plan-ptm-aware-degrader-target-nomination-2026-05-19.md`](wiki/outputs/paper-plan-ptm-aware-degrader-target-nomination-2026-05-19.md)。

### Try the demo locally

```bash
# 0. clone, set up .venv (see Quick Start below for the full setup)
git clone https://github.com/skyllwt/OmegaWiki.git && cd OmegaWiki

# 1. lint the wiki — 0 🔴 / 0 🟡 / 11 🔵 informational
.venv/bin/python tools/lint.py

# 2. open the SPA knowledge graph (65 nodes / 80 edges)
.venv/bin/python tools/serve.py   # then visit http://127.0.0.1:8765/

# 3. run the daily-arxiv demo — DeepSeek ranks 9 candidate papers
bash demo/run-demo.sh             # writes examples/output/digest.md

# 4. pre-rendered output (no API call needed)
cat examples/output/digest-sample.md
```

Skipping step 3 because no DeepSeek key? `examples/output/digest-sample.md` is the verbatim output of a real LLM-ranked run on `demo/sample-feed.json` — no API quota consumed.

### See the pilot-merged bio features live

These commands prove the **2026-05-11 pilot merge (A1 minimal + A5 slice + A6)** is live in your local checkout:

```bash
# 1. Confirm datasets/ is the 10th entity type (was 9 in upstream)
.venv/bin/python -c "from runtime.loader import ENTITY_DIRS; print(len(ENTITY_DIRS), ENTITY_DIRS)"
# → 10 ['papers', 'concepts', 'topics', 'people', 'ideas', 'methods', 'experiments', 'Summary', 'foundations', 'datasets']

# 2. Inspect the first dataset page — version history, access tier, used-by experiments
cat wiki/datasets/ternarydb.md

# 3. See the wikilinked setup.dataset on one experiment, plain string on the seven siblings
grep -A1 "^setup:" wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md | tail -2
grep -A1 "^setup:" wiki/experiments/phase0-noise-floor-calibration-deepternary-ptm-perturbations.md | tail -2

# 4. See the structured cost block — note md_wallclock_hours separately accounted on the MD ablation
grep -A6 "^estimated_cost:" wiki/experiments/ablation-boltz2-ptm-vs-md-relaxed-route.md

# 5. Verify lint stays clean across the pilot merge
.venv/bin/python tools/lint.py
# → Lint: 0 🔴, 0 🟡, 11 🔵
```

For the full report (motivation, integration timeline, schema migration table, lint metrics, future work) see [**`docs/bio-adaptation/REPORT.en.md`**](docs/bio-adaptation/REPORT.en.md)（中文版：[`REPORT.zh.md`](docs/bio-adaptation/REPORT.zh.md)）.

---

## What is ΩmegaWiki?

Andrej Karpathy proposed LLM-Wiki: an LLM that **builds and maintains a persistent, structured wiki** from your sources — not a throwaway RAG answer, but compounding knowledge that grows smarter with every paper you feed it.

**ΩmegaWiki takes that idea and runs the full distance.** It's not just a wiki builder — it's a complete research lifecycle platform: from paper ingestion → knowledge graph → gap detection → idea generation → experiment design → paper writing → peer review response. All driven by 24 Claude Code skills, all centered on one wiki as the single source of truth.

Drop your `.tex` / `.pdf` files in a folder. Run one command. Get a fully cross-referenced knowledge base — and then use it to **generate novel research ideas, design experiments, write papers, and respond to reviewers**.

## Why Wiki-Centric, Not RAG?

| | RAG | ΩmegaWiki |
|---|---|---|
| **Knowledge persistence** | Rediscovered on every query | Compiled once, maintained forever |
| **Structure** | Flat chunk store | 9 typed entities with relationships |
| **Cross-references** | None — chunks are isolated | Bidirectional wikilinks + typed graph |
| **Knowledge gaps** | Invisible | Explicitly tracked, drive research |
| **Failed experiments** | Lost | First-class anti-repetition memory |
| **Output** | Chat answers | Papers, surveys, experiment plans, rebuttals |
| **Compounding** | No — same cost every query | Yes — each paper enriches the whole graph |

## Architecture

<div align="center">
<img src="assets/architecture.png" width="700" alt="ΩmegaWiki Architecture">
</div>

Every skill reads from and writes back to the wiki. Knowledge compounds — each new paper enriches the whole graph. Failed experiments aren't discarded; they become anti-repetition memory that prevents re-exploring dead ends.

## Quick Start

**Prerequisites:** Python 3.9+, Node.js 18+

```bash
# 1. Clone
git clone https://github.com/skyllwt/OmegaWiki.git
cd OmegaWiki

# 2. Install Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# 3. One-click setup
chmod +x setup.sh && ./setup.sh        # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# setup creates .venv for OmegaWiki
# the script does not keep your shell activated, but /init will use .venv automatically

# 4. Put your own papers in raw/papers/ (.tex or .pdf)
#    Optional: add intent notes to raw/notes/ and saved pages to raw/web/
#    /init and direct local /ingest will manage generated inputs under raw/discovered/ and raw/tmp/

# 5. Build your wiki
claude
# Then type: /init [your-research-topic]
```

<details>
<summary><b>Manual setup (Linux / macOS)</b></summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # Edit to add API keys
cp config/settings.local.json.example .claude/settings.local.json
```

</details>

<details>
<summary><b>Manual setup (Windows / PowerShell)</b></summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env          # Edit to add API keys
Copy-Item config\settings.local.json.example .claude\settings.local.json
```

Note: native Windows is supported for the local pipeline. Remote-GPU
experiments via `/exp-run --env remote` rely on `ssh`/`rsync`/`screen`
and are best run from WSL2 or Linux/macOS.

</details>

### API Keys

| Key | Required? | How to get | What it enables |
|-----|-----------|-----------|-----------------|
| `ANTHROPIC_API_KEY` | **Yes** | `claude login` (automatic) | Powers all Claude Code skills |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) (free) | Citation graph, paper search |
| `DEEPXIV_TOKEN` | Optional | `setup.sh` auto-registers | Semantic search, TLDR, trending |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | Optional | Any OpenAI-compatible API | Cross-model review |

> **Cross-model review**: ΩmegaWiki uses a second LLM as an independent reviewer for ideas, experiments, and paper drafts. Works with **any OpenAI-compatible API** — DeepSeek, OpenAI, Qwen, OpenRouter, SiliconFlow, etc. If not configured, skills still work in Claude-only mode.

## Skills

24 slash commands spanning the full research lifecycle:

### Phase 0: Setup

| Command | What it does |
|---------|-------------|
| `/setup` | First-time configuration (API keys, language, dependencies) |
| `/reset <scope>` | Destructive cleanup: `wiki \| raw \| log \| checkpoints \| all` |

### Phase 1: Knowledge Foundation

| Command | What it does |
|---------|-------------|
| `/prefill <domain>` | Optionally seed `foundations/` with background knowledge |
| `/init [topic]` | Bootstrap a full wiki from user raw sources plus optional discovery |
| `/ingest <source>` | Parse a paper → wiki pages + cross-references |
| `/discover` | Recommend ranked next-read papers from anchors, a topic, or the current wiki |
| `/edit <request>` | Add/remove sources or update wiki content |
| `/ask <question>` | Query the wiki, crystallize answers back |
| `/check` | Health scan: broken links, missing cross-refs, consistency |

### Phase 2: Research Pipeline

| Command | What it does |
|---------|-------------|
| `/daily-arxiv` | Auto-fetch & filter new arXiv papers (+ GitHub Actions cron) |
| `/ideate` | Multi-phase idea generation from cross-topic connections |
| `/novelty <idea>` | Multi-source novelty verification (web + S2 + wiki + review LLM) |
| `/review <artifact>` | Cross-model adversarial review for any research artifact |
| `/exp-design <idea>` | Claim-driven experiment + ablation design |
| `/exp-run <experiment>` | Implement + deploy + monitor (local or remote GPU) |
| `/exp-status` | Dashboard for running experiments; auto-collect results |
| `/exp-eval <experiment>` | Verdict gate → auto-update claims/ideas/graph |
| `/refine <artifact>` | Multi-round: produce → review → fix → re-review |

### Phase 3: Writing & Submission

| Command | What it does |
|---------|-------------|
| `/survey` | Generate Related Work from wiki knowledge |
| `/paper-plan <claims>` | Outline from claim graph + evidence matrix |
| `/paper-draft <plan>` | Draft LaTeX + figures, section by section |
| `/paper-compile <dir>` | Compile → PDF, auto-fix, verify page/anonymity |
| `/research <direction>` | End-to-end orchestrator with human gates |
| `/rebuttal <reviews>` | Parse reviewer comments → draft point-by-point responses |

## Wiki Structure

### 9 Entity Types

| Type | Directory | Purpose |
|------|-----------|---------|
| **Paper** | `papers/` | Structured summary with problem/method/results/limitations |
| **Concept** | `concepts/` | Cross-paper technical concept with variants and comparisons |
| **Topic** | `topics/` | Research direction map with SOTA tracker and open problems |
| **Person** | `people/` | Researcher profile with key papers and collaborators |
| **Idea** | `ideas/` | Research idea with lifecycle: proposed → tested → validated/failed |
| **Experiment** | `experiments/` | Full record: hypothesis → setup → results → claim updates |
| **Claim** | `claims/` | Testable claim with evidence list and confidence score |
| **Summary** | `Summary/` | Domain-wide survey across topics |
| **Foundation** | `foundations/` | Background knowledge (terminal: receives inward links, writes none) |

### Knowledge Graph

Semantic relationships are stored in `graph/edges.jsonl`; bibliographic paper citations are stored separately in `graph/citations.jsonl`.

Paper-paper semantic edges include `same_problem_as`, `similar_method_to`, `complementary_to`, `builds_on`, `compares_against`, `improves_on`, `challenges`, and `surveys`. Paper-concept edges use `introduces_concept`, `uses_concept`, `extends_concept`, and `critiques_concept`. Existing claim / experiment / idea / provenance edges remain available where appropriate.

All pages use **Obsidian `[[wikilink]]` format** — open `wiki/` in Obsidian for visual graph exploration.

## Automation

**GitHub Actions** runs `/daily-arxiv` at UTC 00:00 daily:

1. Add `ANTHROPIC_API_KEY` to repo **Settings → Secrets**
2. `.github/workflows/daily-arxiv.yml` fetches arXiv, runs ingestion, auto-commits

## Project Structure

```
OmegaWiki/
├── CLAUDE.md                    # Runtime schema & rules
├── wiki/                        # Knowledge base (LLM-maintained)
│   ├── papers/                  #   Structured paper summaries
│   ├── concepts/                #   Cross-paper technical concepts
│   ├── topics/                  #   Research direction maps
│   ├── people/                  #   Researcher profiles
│   ├── ideas/                   #   Research ideas (with lifecycle)
│   ├── experiments/             #   Experiment records
│   ├── claims/                  #   Testable research claims
│   ├── Summary/                 #   Domain-wide surveys
│   ├── foundations/             #   Background knowledge (terminal pages)
│   ├── outputs/                 #   Generated artifacts
│   ├── graph/                   #   Auto-generated: edges, context, gaps
│   ├── index.md                 #   Content catalog
│   └── log.md                   #   Chronological log
├── raw/                         # Source materials
│   ├── papers/                  #   User-owned .tex / .pdf files
│   ├── discovered/              #   /init and /daily-arxiv-downloaded external papers
│   ├── tmp/                     #   generated prepared local sidecars for /init and direct local /ingest
│   ├── notes/                   #   User-owned .md notes
│   └── web/                     #   User-owned HTML / Markdown
├── tools/                       # Deterministic Python helpers
│   ├── research_wiki.py         #   Wiki engine (20 CLI commands)
│   ├── init_discovery.py        #   /init prepare + plan + fetch helper
│   ├── discover.py              #   /discover candidate gathering, dedup, ranking
│   ├── lint.py                  #   Structural validation (10 checks)
│   ├── reset_wiki.py            #   Scoped destructive cleanup helper
│   ├── fetch_arxiv.py           #   arXiv RSS fetcher
│   ├── fetch_s2.py              #   Semantic Scholar API
│   ├── fetch_deepxiv.py         #   DeepXiv semantic search
│   ├── fetch_wikipedia.py       #   Wikipedia fetcher (used by /prefill)
│   └── remote.py                #   SSH ops for remote experiments
├── .claude/skills/              # 24 Claude Code skill definitions
├── i18n/                        # Bilingual: en/ (canonical) + zh/
├── config/                      # Configuration templates
├── mcp-servers/                 # Cross-model review server
└── .github/workflows/           # Daily arXiv cron
```


## Bilingual Support

ΩmegaWiki ships in English and Chinese:

```bash
./setup.sh --lang en   # English (default)
./setup.sh --lang zh   # 中文
```

---

## Roadmap

- [x] Wiki knowledge engine (20+ CLI commands, 9 entity types, semantic graph + citation layer)
- [x] 24 Claude Code skills (full research lifecycle)
- [x] Cross-model review (any OpenAI-compatible API)
- [x] Daily arXiv automation (GitHub Actions)
- [x] Remote GPU experiment support
- [x] Bilingual i18n (EN + ZH)
- [ ] Demo dataset (example wiki with pre-ingested papers)
- [ ] LaTeX venue templates (NeurIPS, ICML, ACL, etc.)
- [ ] Multi-user collaboration
- [ ] More language support

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🎁 Angel User Program / 天使用户计划

> **Limited time — free 15-day MiMo API credits for our earliest supporters.**
> **限时活动 — 为天使用户提供 15 天免费 MiMo API 额度。**

We're offering a batch of MiMo API credits to early supporters — use them with Claude Code to explore ΩmegaWiki, try out the skills, and help us iterate. ΩmegaWiki is still in its early stage and supports a wide range of feature extensions; we'd love for you to push it, explore new use cases, tell us what you'd like to see, and shape it alongside us.

**Haven't used Claude Code yet?** This is also your chance to get hands-on with one of the most capable agentic systems out there. You might just fall in love with it — and figure out how to reshape your research, your workflow, and the way you build things with AI, well before the people around you catch on.

我们为早期支持者提供一批 MiMo API 额度——用它在 Claude Code 里探索 ΩmegaWiki，体验各项 skill，并和我们一起打磨这个项目。ΩmegaWiki 仍处于早期阶段，同时支持非常丰富的功能拓展空间。我们希望你来用它、探索新的使用场景、告诉我们你想看到什么，和我们一起把它做得更强。

**还没用过 Claude Code？** 这也是一次近距离接触前沿 Agent 的机会——Claude Code 是目前最强的智能 agent 之一。你很可能会爱上它，并比身边的人更早一步摸索出：如何用 Claude Code 重塑你的研究、工作流，以及与 AI 协作的方式。

**Credits are valid through 2026-04-30. Credits are limited and the program may close once the current batch is exhausted.**
**额度有效期至 2026-04-30。名额有限，当前批次发放完毕后本计划可能随时关闭。**

> If you find ΩmegaWiki useful, starring the repo helps others discover it — but it's not a requirement for joining this program. / 如果你觉得 ΩmegaWiki 对你有帮助，欢迎 Star 本仓库帮助更多人发现它——但这并非参与本计划的条件。

### How to apply / 申请方式

Applications are currently handled manually via the community WeChat group due to limited quota. To apply, please join the WeChat group (QR code below) and contact the admin with:

- Your GitHub username
- A short description of your intended workflow / how you plan to use ΩmegaWiki
- (Optional) Any feedback or feature ideas you'd like to share

由于名额有限，本计划目前通过社群微信群人工受理申请。请扫描下方二维码加入微信群，并向管理员提供以下信息：

- 你的 GitHub 用户名
- 简要说明你计划如何使用 ΩmegaWiki（预期的工作流/使用场景）
- （可选）你希望分享的反馈或功能建议

We review applications based on fit with the project's current stage and the kind of feedback we're looking for — not on a first-come-first-served basis alone. / 我们会根据申请信息与项目当前阶段的契合度来审核，而非单纯按先后顺序。

### Config / 配置方式

**Step 1 — Point Claude Code at MiMo** / **第 1 步：把 Claude Code 指向 MiMo**

Drop the following into `~/.claude/settings.json` (or your project's `.claude/settings.json`):

将以下内容写入 `~/.claude/settings.json`（或项目的 `.claude/settings.json`）：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.xiaomimimo.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-personal-mimo-key>",
    "ANTHROPIC_MODEL": "mimo-v2.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "mimo-v2.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2.5"         
  }                                                       
}    
```

**Step 2 — Skip the Claude Code onboarding** / **第 2 步：跳过 Claude Code 初始引导**

Because you're using a third-party key (MiMo) instead of signing in via `claude login`, Claude Code's first-run onboarding flow won't complete automatically. Create or edit `.claude.json` to mark onboarding as done:

因为你用的是第三方 key（MiMo），不会走 `claude login` 的登录流程，Claude Code 首次启动的引导步骤不会自动完成。创建或编辑 `.claude.json`，手动标记引导已完成：

- macOS / Linux: `~/.claude.json`
- Windows: `<用户目录>\.claude.json`

```json
{
  "hasCompletedOnboarding": true
}
```

Then run `claude` as usual. That's it — zero extra setup.
保存后正常运行 `claude` 即可，零额外配置。

> **House rules / 使用约定**: Personal use only. Please don't share your key or run automated batch scripts — if any single key shows abuse patterns, we'll revoke it to protect other users. / **请仅限个人使用**，不要分享 key 或跑批量脚本。任何 key 出现异常用量会立即被回收，以保护其他用户。

---

## Community / 交流群

<img src="assets/wechat_group_1.png" width="240" alt="WeChat Group QR Code">

Scan to join the ΩmegaWiki WeChat group / 扫码加入微信交流群

## Acknowledgments

- **Andrej Karpathy** — for the LLM-Wiki concept that inspired this project
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — the AI agent runtime that powers ΩmegaWiki

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=skyllwt/OmegaWiki&type=Date)](https://star-history.com/#skyllwt/OmegaWiki&Date)

## License

[MIT](LICENSE) — use it, fork it, build on it.

---

## 中文

### 生信适配分支

> **ΩmegaWiki / bio-adaptation — PTM-aware degrader · 结构生物学 · ML for molecules。** 这是上游 ΩmegaWiki 的生信形态分支。我们用一次真实的 PTM-aware degrader 目标提名工作流把 wiki 跑通，并针对该工作流暴露出来的 CS-shaped 假设做了系统性硬化。

<div align="center">
<img src="assets/demo.gif" width="800" alt="生信适配 demo（约 50 秒走查）">
<br>
<sub>30–60 秒走查 —— lint 扫描 → SPA 知识图 → DeepSeek 排序 → 最终 digest。分镜见 <a href="docs/bio-adaptation/DEMO_PLAN.zh.md">DEMO_PLAN.zh.md</a>。</sub>
</div>

#### 这个 fork 改了什么

| | 上游 ΩmegaWiki | 生信适配 fork |
|---|---|---|
| **领域形状** | CS / AI —— arXiv 形态的论文、`claims/` 账本 | 生物信息 —— DOI / PMID / bioRxiv 一等公民，`datasets/` 成为第 10 种实体 |
| **Evidence 动词** | `supports`、`contradicts`、`tested_by`、`invalidates` | + `wet_lab_validated`、`clinical_validated`、`mechanistic_basis`、`correlative`、`predicts`，可选 GRADE 等级 |
| **Graph 边** | paper-paper、paper-concept、claim/experiment | + bio relation（`targets_protein`、`binds`、`degrades`、`phosphorylates`、`ubiquitinates`、…）、validation / translation（`clinical_trial_for`、`fda_approved_for`）、dataset-version provenance |
| **实验成本字段** | 单一 `estimated_hours` | 结构化：`gpu_hours`、`cpu_hours`、`md_wallclock_hours`、`wet_lab_usd`、`fte_weeks`、`dataset_access_lead_time_days` |
| **Skill prompt** | CS 风格示例 | `/ingest` 加入 bio NER 预扫；`/exp-design` 支持 MD / 湿实验预算；`/novelty` 用 GRADE 加权；`/paper-draft` 切换为 result-first 写法；… |
| **演示用例** | LLM 论文、LoRA、flash-attention | 11 篇论文覆盖 AlphaFold 2/3、PTM 位点预测、E3 ligase 平台、面向分子的几何深度学习；22 ideas、8 实验、73 graph 边 |

逐条理由和迁移过程中的 lint 数据：[`docs/bio-adaptation/REPORT.zh.md`](docs/bio-adaptation/REPORT.zh.md)（English：[`REPORT.en.md`](docs/bio-adaptation/REPORT.en.md)）。

<div align="center">
<img src="assets/canvas-ptm-focus.png" width="800" alt="Obsidian Canvas — PTM-aware degrader 邻域（23 节点 / 27 边）">
<br>
<sub>PTM-aware degrader 邻域 —— 由 <code>wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas</code> 导出。</sub>
</div>

#### 本地试一下

```bash
# 0. clone，配 .venv（完整安装步骤见下方"快速开始"）
git clone https://github.com/skyllwt/OmegaWiki.git && cd OmegaWiki

# 1. lint wiki —— 0 🔴 / 0 🟡 / 11 🔵（仅信息性提示）
.venv/bin/python tools/lint.py

# 2. 打开 SPA 知识图（63 节点 / 66 边）
.venv/bin/python tools/serve.py   # 然后访问 http://127.0.0.1:8765/

# 3. 跑 daily-arxiv demo —— DeepSeek 对 9 篇候选论文排序
bash demo/run-demo.sh             # 写入 examples/output/digest.md

# 4. 预渲染输出（无需调用 API）
cat examples/output/digest-sample.md
```

没有 DeepSeek key、想跳过第 3 步？`examples/output/digest-sample.md` 是真实 LLM 排序跑出来的输出（基于 `demo/sample-feed.json`），不消耗任何 API 配额。

#### 现场验证 pilot-merge 后的生信功能

下面这 5 条命令直接证明 **2026-05-11 pilot merge（A1 minimal + A5 切片 + A6）** 已在你本地 checkout 中 live：

```bash
# 1. 确认 datasets/ 是第 10 种实体类型（上游为 9 种）
.venv/bin/python -c "from runtime.loader import ENTITY_DIRS; print(len(ENTITY_DIRS), ENTITY_DIRS)"
# → 10 ['papers', 'concepts', 'topics', 'people', 'ideas', 'methods', 'experiments', 'Summary', 'foundations', 'datasets']

# 2. 查看第一个 dataset 页面：版本历史、access tier、被哪些实验使用
cat wiki/datasets/ternarydb.md

# 3. 看一个实验的 setup.dataset 是 wikilink，而它的 7 个 sibling 仍是裸字符串
grep -A1 "^setup:" wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md | tail -2
grep -A1 "^setup:" wiki/experiments/phase0-noise-floor-calibration-deepternary-ptm-perturbations.md | tail -2

# 4. 看结构化 cost 块——注意 md_wallclock_hours 在 MD 消融实验里单独计入
grep -A6 "^estimated_cost:" wiki/experiments/ablation-boltz2-ptm-vs-md-relaxed-route.md

# 5. 验证 lint 在 pilot merge 后仍干净
.venv/bin/python tools/lint.py
# → Lint: 0 🔴, 0 🟡, 11 🔵
```

完整 report（动机、整合时间线、schema 迁移表、lint 指标、后续工作）见 [**`docs/bio-adaptation/REPORT.zh.md`**](docs/bio-adaptation/REPORT.zh.md)（English：[`REPORT.en.md`](docs/bio-adaptation/REPORT.en.md)）。

---

### ΩmegaWiki 是什么？

Andrej Karpathy 提出了 LLM-Wiki 概念：让 LLM **构建并维护一个持久的、结构化的 wiki**，而不是一次性的 RAG 回答。知识持续积累，每一篇新论文都让整个知识图谱更强。

**ΩmegaWiki 将这个理念完整实现。** 它不仅是 wiki 构建器，更是完整的研究全流程平台：从论文摄入 → 知识图谱 → 缺口检测 → 想法生成 → 实验设计 → 论文写作 → 同行评审回复。24 个 Claude Code Skills 驱动，一个 wiki 作为唯一的知识中枢。

### 为什么选择 Wiki 而不是 RAG？

| | RAG | ΩmegaWiki |
|---|---|---|
| **知识持久性** | 每次查询都重新发现 | 编译一次，持续维护 |
| **结构** | 扁平的 chunk 存储 | 9 种实体类型 + 关系图 |
| **交叉引用** | 无 — chunk 彼此孤立 | 双向 wikilink + 类型化边 |
| **知识缺口** | 不可见 | 显式追踪，驱动研究方向 |
| **失败实验** | 丢失 | 一等公民，防止重复探索 |
| **输出** | 聊天回答 | 论文、综述、实验方案、审稿回复 |
| **复利效应** | 无 — 每次查询成本相同 | 有 — 每篇论文丰富整个图谱 |

### 快速开始

**前置条件：** Python 3.9+, Node.js 18+

```bash
git clone https://github.com/skyllwt/OmegaWiki.git && cd OmegaWiki

# 安装 Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# 一键配置
chmod +x setup.sh && ./setup.sh --lang zh        # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Lang zh
# setup 会为 OmegaWiki 创建 .venv
# 脚本不会把你当前 shell 永久激活，但 /init 会自动使用 .venv

# 把你自己的论文放入 raw/papers/（.tex 或 .pdf）
# 可选：把意图笔记放入 raw/notes/，网页存档放入 raw/web/
# /init 与直接本地 /ingest 会自动管理 raw/discovered/ 与 raw/tmp/ 下的生成内容
# 启动 Claude Code
claude
# 输入：/init [你的研究方向]
```

> **Windows 用户**：本地 pipeline 已原生支持。`/exp-run --env remote` 远程 GPU 实验依赖 `ssh`/`rsync`/`screen`，建议在 WSL2 或 Linux/macOS 下运行。

### API Key 说明

| Key | 必须？ | 获取方式 | 用途 |
|-----|--------|---------|------|
| `ANTHROPIC_API_KEY` | **是** | `claude login` | 驱动所有 Skill |
| `SEMANTIC_SCHOLAR_API_KEY` | 可选 | [semanticscholar.org](https://www.semanticscholar.org/product/api)（免费） | 引用图谱、论文搜索 |
| `DEEPXIV_TOKEN` | 可选 | `setup.sh` 自动注册 | 语义搜索、热门趋势 |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | 可选 | 任意 OpenAI 兼容 API | 跨模型评审 |

### 24 个 Skill 命令

| 命令 | 功能 |
|------|------|
| `/setup` | 首次配置（API key、语言、依赖） |
| `/reset` | 按范围销毁性清理：`wiki \| raw \| log \| checkpoints \| all` |
| `/prefill` | 可选地预填 `foundations/` 背景知识 |
| `/init` | 基于用户 raw 素材并按需做外部发现来搭建 wiki |
| `/ingest` | 消化论文，创建页面 + 交叉引用 |
| `/discover` | 从 anchor、topic 或当前 wiki 推荐排序后的下一批待读论文 |
| `/edit` | 增删 raw 或更新 wiki |
| `/ask` | 对 wiki 提问 |
| `/check` | wiki 健康检查 |
| `/daily-arxiv` | 每日 arXiv 新论文（CI 自动） |
| `/ideate` | 跨方向构思研究 idea |
| `/novelty` | 多源新颖性验证 |
| `/review` | 跨模型评审 |
| `/exp-design` | Claim 驱动实验设计 |
| `/exp-run` | 部署 + 监控实验 |
| `/exp-status` | 实验状态看板 |
| `/exp-eval` | 裁决 → 更新 claims |
| `/refine` | 多轮迭代改进 |
| `/survey` | 生成 Related Work |
| `/paper-plan` | Claim 图谱 → 论文提纲 |
| `/paper-draft` | 提纲 + wiki → LaTeX 草稿 |
| `/paper-compile` | 编译 → PDF，自动修复 |
| `/research` | 端到端研究编排器 |
| `/rebuttal` | 解析评审意见 → 逐条回复 |

---

<div align="center">

**Built with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

If this project helps your research, give it a ⭐

</div>
