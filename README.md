<div align="center">

<img src="assets/autosci-logo.png" width="160" alt="AutoSci Logo">

# AutoSci

**Read, think, experiment, write, evolve — the AI research agent with memory that compounds across every project.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Powered_by-Claude_Code-d97706.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![arXiv](https://img.shields.io/badge/arXiv-2605.31468-b31b1b.svg)](https://arxiv.org/abs/2605.31468)
[![Status](https://img.shields.io/badge/status-internal_beta-orange.svg)](#️⃣-status--update)


</div>

---

## ⚠️ Status & Update

> **Thanks to everyone who's been trying AutoSci — the community response has been amazing!** AutoSci evolved from our earlier OmegaWiki prototype into what we're building toward: a next-generation research agent that can handle the full scientific lifecycle. We're actively testing and iterating on new features, and more capabilities are on the way. Jump in, break things, and tell us what you think — your feedback and ideas are what's shaping where this goes next. 🙏

> **🌿 Which branch?** [`main`](https://github.com/skyllwt/AutoSci/tree/main) is the **stable, lean** version. The **full system described in our [paper](https://arxiv.org/abs/2605.31468)** — SciMem · SciFlow · SciDAG · SciEvolve — lives on the [`paper`](https://github.com/skyllwt/AutoSci/tree/paper) branch (frozen as tag [`arxiv-v1`](https://github.com/skyllwt/AutoSci/tree/arxiv-v1)). Note that `paper` is a **research snapshot, not a finished product**: it's under active testing and iteration, and some capabilities described in the paper are still being implemented and refined.

---

## 📄 Paper

> ### [AutoSci: A Memory-Centric Agentic System for the Full Scientific Research Lifecycle](https://arxiv.org/abs/2605.31468)
>
> [![arXiv](https://img.shields.io/badge/arXiv-2605.31468-b31b1b.svg)](https://arxiv.org/abs/2605.31468) &nbsp;·&nbsp; [📄 **Read on arXiv →**](https://arxiv.org/abs/2605.31468)

If you find AutoSci useful in your research, please [cite our paper](#citation).

---

## 📌 Poster & Demo

<!--
  POSTER & VIDEO PLACEHOLDER
  Drop your files into assets/ and uncomment the blocks below:
    - Conference poster image  -> assets/poster.png   (or .jpg/.pdf)
    - Demo video               -> a YouTube/Bilibili link, or assets/demo.mp4 / assets/demo.gif
  GitHub READMEs cannot embed/play local .mp4 inline; for video, prefer either:
    (a) a clickable thumbnail linking to the hosted video, or
    (b) a short looping assets/demo.gif.
-->

<div align="center">
  <a href="assets/poster.png"><img src="assets/poster.png" width="760" alt="AutoSci conference poster"></a>
  <br/><sub><em>AutoSci poster — click to view full size.</em></sub>
</div>

<!-- DEMO VIDEO (uncomment and replace links/thumbnail once available)
<div align="center">
  <a href="https://your-video-url">
    <img src="assets/demo-thumbnail.png" width="640" alt="Watch the AutoSci demo">
  </a>
  <br/><sub><em>▶ Watch the AutoSci walkthrough.</em></sub>
</div>
-->

<div align="center">
  <a href="https://www.bilibili.com/video/BV19gVg6pEk6/">
    <img src="assets/demo-thumbnail.jpg" width="640" alt="▶ Watch AutoSci on Bilibili">
  </a>
  <br/><sub><em>▶ Watch the AutoSci demo on Bilibili</em></sub>
</div>

---

## 🆕 What's New

### 🛠️ 2026-05-19 · Experiment Overhaul

A possible usage process：`/ideate [research-direction-or-topic]`(You can use `--skip-pilot` to decide whether to conduct preliminary experiments) -> `/exp-design <idea-slug>`-> For each experimental block,recommended flow: `/exp-run <slug> [--env local|remote]` to deploy → `/exp-status` to monitor → `/exp-run <slug> --collect` to collect.->`/exp-eval <experiment-slug>`

✨ : New Skills
`/exp-pilot-run` — Pilot experiment execution: write code, deploy, monitor, collect raw results.
`/exp-pilot-eval` — Pilot result evaluation: read results, apply lenient verdict logic
These two skills are built into Phase5 of `/ideate`
🛠️ : Modified Skills
`/ideate`
5 structured generation paths (A-E) for both Claude and Review LLM.
Phase restructuring: Filter & Validation merged into Phase 3, Write Wiki moved to Phase 4.
Phase 5: Finish pilot design and workflow invocation
Your ideas will follow a clearer path, and a more reasonable screening mechanism will be established through pilot experiments.
`/exp-design`
A brand-new experimental design process:method candidate generation + 5 experiment block types + iterative ablation loop
`/exp-run`
Add the code decision gate, code optimization and config check

### 🎨 2026-05-18 · /poster — drafted paper → print-ready conference poster

Run `/poster` after `/paper-draft` + `/paper-compile` to turn your finished draft into a self-contained 1400×900 HTML poster and a print-quality PNG. Figures, booktabs tables, and math macros are extracted automatically from your LaTeX source; Claude walks you through picking which figures land in which sections and customizing the header (venue, affiliation logo). Export to PDF from your browser's print dialog. Pipeline adapted from [PaperX](https://github.com/yutao1024/PaperX) ([arXiv:2602.03866](https://arxiv.org/abs/2602.03866)).

<p align="center">
  <img src="assets/poster_demo_tikz_tables.png" alt="Example /poster output" width="720" />
</p>

### 🎯 2026-05-12 · /discover from a venue — "what should I read first from ICLR 2024?"

Run `/discover --venue iclr --year 2024` (or any conference/year) and get a personalized shortlist of papers from that venue, ranked by relevance to what's already in your wiki. Instead of scrolling a 7000-paper proceedings, you see the dozen that actually matter for your research direction, each with a rationale tied to topics and methods you already track. No new API keys, no ingest side-effects on your wiki — just a ranked reading list. Supports NeurIPS, ICLR, ICML, and other venues covered by [Paper Copilot](https://github.com/papercopilot/paperlists).

### 📰 2026-05-09 · Daily arXiv — fresh-paper recommendations, on demand or scheduled

Run `/daily-arxiv` for a one-off pass, or `/daily-arxiv setup` to schedule the same pipeline in GitHub Actions. The skill builds an evidence packet from arXiv + Semantic Scholar + DeepXiv, lets the LLM rank candidates against your wiki interests, and delivers a digest by e-mail. Explicit `--mode auto-ingest` calls `/ingest` for high-confidence picks; `inform` mode just notifies.

### 🌐 2026-05-06 · Knowledge Graph Visualization — browser + Obsidian

Your research graph now has two ways to explore:

- **Web UI** — run `python3 tools/serve.py`, open `http://localhost:8765/#/graph`. Click any node to highlight its neighborhood via BFS, filter by entity type or edge category, double-click to open the full page in the Reader.
- **Obsidian** — run `/visualize --obsidian` to generate a color-coded graph config, or `/visualize --canvas` to produce a force-layout Canvas with labeled semantic edges.

---

## Team

AutoSci is built by [DAIR Lab](https://cuibinpku.github.io/) at Peking University.

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
  <tr>
    <td align="center" width="165">
      <img src="assets/ChenyangDi_circle.png" width="90" alt="Chenyang Di"/>
      <br/><br/>
      <b>Chenyang Di</b>
      <br/>
      <sub>PKU</sub>
      <br/>
      <sub>Undergraduate · 2023</sub>
    </td>
  </tr>
</table>
<sub>...and more contributors who have shaped AutoSci along the way.</sub>
</div>

---

## What is AutoSci?

Scientific research has traditionally been **human-intensive**: researchers coordinate literature, ideas, experiments, manuscripts, and review responses across long project cycles. **AutoSci** is a memory-centric agentic system that automates the full research lifecycle — from paper ingestion to rebuttal — while maintaining structured persistent memory across projects and improving its own procedures over time.

<div align="center">
<img src="assets/fig-overview.png" width="820" alt="AutoSci system overview">
</div>

---

## 🔬 Works Produced with AutoSci

The following papers were generated end-to-end using AutoSci — from literature ingestion and idea generation to experiment execution and manuscript writing.

| Paper | Domain | PDF |
|-------|--------|-----|
| Agent-driven iterative optimization of Triton GPU kernels | GPU kernel optimization | [📄 PDF](assets/papers/gpu-kernel-optimization.pdf) |
| PTM-aware degrader target nomination via calibrated ternary-complex scoring | Biomedical drug discovery | [📄 PDF](assets/papers/protac-target-nomination.pdf) |
| Forced Honesty Dissociates Polite Speech from Motivated Cognition in LLM Attitude Ratings | LLMs as cognitive models | [📄 PDF](assets/papers/llm-positivity-bias-cognitive-models.pdf) |

**Have you used AutoSci in your own research?** We'd love to feature your work here — open a PR or drop us a message!

---

## Quick Start

**Prerequisites:** Python 3.9+, Node.js 18+

```bash
# 1. Clone
git clone https://github.com/skyllwt/AutoSci.git
cd AutoSci

# 2. Install Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# 3. One-click setup
chmod +x setup.sh && ./setup.sh        # Linux / macOS
# Windows (PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# setup creates a .venv for AutoSci; /init will use it automatically

# 4. Put your own papers in raw/papers/ (.tex or .pdf)
#    Optional: intent notes in raw/notes/, saved pages in raw/web/

# 5. Build your research memory and start a project
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
| `ANTHROPIC_API_KEY` | **Yes** (or use a third-party compatible API — see below) | `claude login` (automatic) | Powers all Claude Code skills |
| `CLAUDE_CODE_OAUTH_TOKEN` | Optional | `claude setup-token` | GitHub Actions Claude Code auth for Pro/Max users |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) (free) | Citation graph, paper search |
| `DEEPXIV_TOKEN` | Optional | `setup.sh` auto-registers | Semantic search, TLDR, trending |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | Optional | Any OpenAI-compatible API | Cross-model review; `/daily-arxiv` inform recommendations |

> **Don't have an Anthropic API key?** AutoSci runs on Claude Code, which supports any Anthropic-protocol-compatible provider — DeepSeek, Kimi, MiMo, GLM, and more. See the [LLM API Configuration](#llm-api-configuration--大模型-api-配置) section below for setup snippets.

> **Cross-model review**: AutoSci uses a second LLM as an independent reviewer for ideas, experiments, and paper drafts. Works with **any OpenAI-compatible API** — DeepSeek, OpenAI, Qwen, OpenRouter, SiliconFlow, etc. If not configured, skills still work in Claude-only mode.

---

## LLM API Configuration / 大模型 API 配置

AutoSci runs on **Claude Code**, which speaks the **Anthropic API** protocol. You can use Claude directly, or route Claude Code to any third-party provider that exposes an Anthropic-compatible endpoint by overriding a few environment variables.

AutoSci 基于 **Claude Code**,Claude Code 使用 **Anthropic API** 协议通信。你既可以直接使用 Claude,也可以通过覆盖几个环境变量,把 Claude Code 指向任意支持 Anthropic 协议的第三方供应商。

### Option A — Native Claude / 原生 Claude

```bash
claude login   # OAuth, no manual config / OAuth 登录,无需手动配置
```

### Option B — Third-party Anthropic-compatible API / 第三方 Anthropic 兼容 API

Pick a provider below, paste the snippet into `~/.claude/settings.json` (or the project's `.claude/settings.json`), and replace the `<...>` placeholder with your own API key. Model names and extra options follow each provider's official Claude Code docs.

从下方任选一个供应商,把对应配置粘贴到 `~/.claude/settings.json`(或项目的 `.claude/settings.json`),并把 `<...>` 占位符替换为你自己的 API key。模型名与额外选项均来自各供应商官方 Claude Code 文档。

<details>
<summary><b>MiMo / DeepSeek / Kimi / GLM 配置示例</b></summary>

#### MiMo (小米)

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.xiaomimimo.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-mimo-key>",
    "ANTHROPIC_MODEL": "mimo-v2.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "mimo-v2.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2.5"
  }
}
```

#### DeepSeek

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-deepseek-key>",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  }
}
```

#### Kimi (Moonshot)

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.moonshot.ai/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-moonshot-key>",
    "ANTHROPIC_MODEL": "kimi-k2.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k2.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-k2.5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-k2.5",
    "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-k2.5",
    "ENABLE_TOOL_SEARCH": "false"
  }
}
```

#### GLM (Z.AI)

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-zai-key>",
    "API_TIMEOUT_MS": "3000000"
  }
}
```

> Z.AI applies a default server-side model mapping, so no explicit `ANTHROPIC_MODEL` is needed.
> Z.AI 默认在服务端做模型映射,无需显式设置 `ANTHROPIC_MODEL`。

</details>

**Skip the Claude Code onboarding** / **跳过 Claude Code 初始引导**: when using a third-party key, create or edit `.claude.json` (`~/.claude.json` on macOS/Linux) and add `{ "hasCompletedOnboarding": true }`.

---

## Skills

AutoSci ships with 30+ slash commands spanning the full research lifecycle.

<details>
<summary><b>View all skills</b></summary>

### Phase 0: Setup
| Command | What it does |
|---------|-------------|
| `/setup` | Interactive API key configuration — checks `.env` state and walks through Semantic Scholar, DeepXiv, and Review LLM setup |
| `/reset` | Destructive cleanup — reset wiki state to a clean scaffold by scope (`wiki / raw / log / checkpoints / all`) |

### Phase 1: Knowledge Base
| Command | What it does |
|---------|-------------|
| `/prefill` | Seed `wiki/foundations/` with domain background so subsequent `/ingest` doesn't create duplicate concept pages for textbook material |
| `/init` | Bootstrap the wiki from your source files, with optional discovery, then ingest the final paper set in parallel |
| `/ingest` | Ingest a paper (local path or arXiv URL) — creates pages and builds all cross-references and graph edges |
| `/discover` | Build a ranked shortlist of candidate papers (anchor-driven, topic-driven, venue-filtered, or from wiki state) without ingesting |
| `/edit` | Add or remove raw sources, or update wiki content, per user request |
| `/ask` | Ask the wiki a question — retrieve and synthesize relevant pages, optionally crystallize the answer back into the wiki |
| `/check` | Scan the full wiki to detect health issues and produce a tiered fix-recommendation report |

### Phase 2: Ideation & Experiments
| Command | What it does |
|---------|-------------|
| `/daily-arxiv` | Run or schedule the daily arXiv recommendation feed; delivers a ranked digest by email with optional auto-ingest for high-confidence picks |
| `/ideate` | Multi-phase research idea generation: landscape scan → dual-model brainstorm → filter & validation → write to wiki → pilot |
| `/exp-pilot-run` | Pilot experiment execution — write code, deploy, monitor, collect raw results (called by `/ideate` Phase 5) |
| `/exp-pilot-eval` | Pilot result evaluation — read results, apply success criteria, update idea page (called by `/ideate` Phase 5) |
| `/novelty` | Multi-source novelty verification via WebSearch + Semantic Scholar + wiki + Review LLM; outputs novelty score and recommendations |
| `/review` | Cross-model review of any research artifact — outputs structured scores, wiki entity mapping, and improvement suggestions |
| `/exp-design` | Idea-driven experiment design with iterative ablation — method candidates → benchmark selection → sensitivity analysis → main experiment |
| `/exp-run` | Full experiment execution pipeline — prepare code → deploy → monitor → collect results |
| `/exp-status` | View the status of all running experiments; optionally auto-collect completed runs and advance the pipeline |
| `/exp-eval` | Experiment verdict gate — Review LLM independently judges results and auto-updates the linked idea's status and graph edges |
| `/refine` | Multi-round iterative improvement — repeatedly calls `/review`, parses feedback, applies fixes, and updates wiki until target score |

### Phase 3: Writing & Dissemination
| Command | What it does |
|---------|-------------|
| `/survey` | Generate a Related Work section from wiki knowledge — thematic grouping → narrative structure → LaTeX output |
| `/paper-plan` | Compile a paper outline from the idea graph — evidence map → narrative structure → section + figure + citation plan |
| `/paper-draft` | Draft a LaTeX paper from `PAPER_PLAN` — write each section from wiki sources, generate figures/tables, verify BibTeX |
| `/paper-compile` | LaTeX compile → PDF — latexmk compile + auto-fix + page count / anonymity / font checks + submission checklist |
| `/research` | End-to-end research orchestrator — idea discovery → experiment design → execution → verdict → paper writing with human gates |
| `/rebuttal` | Parse review comments → atomize concerns → map to wiki → stress-test with Review LLM → generate rebuttal |
| `/poster` | Generate an academic poster from a drafted paper — distill sections into a single-page HTML poster with figures |

### Utilities
| Command | What it does |
|---------|-------------|
| `/visualize` | Generate Obsidian graph configs and Canvas knowledge maps; the interactive web graph is served by `tools/serve.py` |

</details>

---

## Contributing

We welcome contributions and feedback — especially while we're in active iteration. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Community / 交流群

<img src="assets/wechat_group_3_new.png" width="240" alt="WeChat Group QR Code">

Scan to join the AutoSci WeChat group / 扫码加入微信交流群

## Citation

If you find AutoSci useful in your research, please cite our paper:

```bibtex
@misc{qian2026autosci,
      title={AutoSci: A Memory-Centric Agentic System for the Full Scientific Research Lifecycle}, 
      author={Weitong Qian and Beicheng Xu and Zhongao Xie and Bowen Fan and Guozheng Tang and Jiale Chen and Xinzhe Wu and Mingtian Yang and Chenyang Di and Jiajun Li and Lingching Tung and Peichao Lai and Yifei Xia and Ziyi Guo and Yanwei Xu and Yanzhao Qin and Shaoduo Gan and Xupeng Miao and Bin Cui},
      year={2026},
      eprint={2605.31468},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2605.31468}, 
}
```

## Acknowledgments

- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — the AI agent runtime that powers AutoSci
- The `/poster` pipeline is adapted from [PaperX](https://github.com/yutao1024/PaperX)

## License

[MIT](LICENSE) — use it, fork it, build on it.

## Star History

<div align="center">
<a href="https://star-history.com/#skyllwt/AutoSci&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=skyllwt/AutoSci&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=skyllwt/AutoSci&type=Date" />
    <img alt="AutoSci Star History Chart" src="https://api.star-history.com/svg?repos=skyllwt/AutoSci&type=Date" width="600" />
  </picture>
</a>
</div>


<div align="center">

**Built with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

If this project helps your research, give it a ⭐

</div>
