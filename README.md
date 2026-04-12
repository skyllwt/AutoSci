<div align="center">

<img src="assets/logo.png" width="180" alt="ΩmegaWiki Logo">

# ΩmegaWiki

### Karpathy's LLM-Wiki Vision, Fully Realized

**A wiki-centric full-lifecycle AI research platform powered by [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

*From paper ingestion to publication — your research knowledge compounds, never decays.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-2263_passing-brightgreen.svg)](#testing)
[![Skills](https://img.shields.io/badge/Skills-23-purple.svg)](#skills)
[![Claude Code](https://img.shields.io/badge/Powered_by-Claude_Code-d97706.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Bilingual](https://img.shields.io/badge/i18n-EN_|_中文-orange.svg)](#bilingual-support)

[English](#what-is-ωmegawiki) | [中文](#中文)

</div>

---

## What is ΩmegaWiki?

Andrej Karpathy proposed [LLM-Wiki](https://x.com/karpathy/status/1909372692069236775): an LLM that **builds and maintains a persistent, structured wiki** from your sources — not a throwaway RAG answer, but compounding knowledge that grows smarter with every paper you feed it.

**ΩmegaWiki takes that idea and runs the full distance.** It's not just a wiki builder — it's a complete research lifecycle platform: from paper ingestion → knowledge graph → gap detection → idea generation → experiment design → paper writing → peer review response. All driven by 23 Claude Code skills, all centered on one wiki as the single source of truth.

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

# 4. Put your papers in raw/papers/ (.tex or .pdf)

# 5. Build your wiki
claude
# Then type: /init <your-research-topic>
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

23 slash commands spanning the full research lifecycle:

### Phase 0: Setup

| Command | What it does |
|---------|-------------|
| `/setup` | First-time configuration (API keys, language, dependencies) |
| `/reset <scope>` | Destructive cleanup: `wiki \| raw \| log \| checkpoints \| all` |

### Phase 1: Knowledge Foundation

| Command | What it does |
|---------|-------------|
| `/prefill <domain>` | Seed `foundations/` with background knowledge (suggested before `/init`) |
| `/init <topic>` | Bootstrap a full wiki from `raw/` |
| `/ingest <source>` | Parse a paper → wiki pages + cross-references |
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

9 typed relationships stored in `graph/edges.jsonl`:

`extends` · `contradicts` · `supports` · `inspired_by` · `tested_by` · `invalidates` · `supersedes` · `addresses_gap` · `derived_from`

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
├── raw/                         # Source materials (read-only)
│   ├── papers/                  #   .tex / .pdf files
│   ├── notes/                   #   .md notes
│   └── web/                     #   HTML / Markdown
├── tools/                       # Deterministic Python helpers
│   ├── research_wiki.py         #   Wiki engine (20 CLI commands)
│   ├── lint.py                  #   Structural validation (10 checks)
│   ├── reset_wiki.py            #   Scoped destructive cleanup helper
│   ├── fetch_arxiv.py           #   arXiv RSS fetcher
│   ├── fetch_s2.py              #   Semantic Scholar API
│   ├── fetch_deepxiv.py         #   DeepXiv semantic search
│   ├── fetch_wikipedia.py       #   Wikipedia fetcher (used by /prefill)
│   ├── remote.py                #   SSH ops for remote experiments
│   ├── wiki_graph.py            #   Standalone knowledge graph traversal
│   ├── compile_context.py       #   Purpose-driven context compilation
│   ├── find_similar.py          #   Token Jaccard dedup search
│   └── wiki_lint.py             #   Cross-wiki structural lint
├── .claude/skills/              # 23 Claude Code skill definitions
├── i18n/                        # Bilingual: en/ (canonical) + zh/
├── config/                      # Configuration templates
├── tests/                       # 2263 tests
├── mcp-servers/                 # Cross-model review server
└── .github/workflows/           # Daily arXiv cron
```


## Standalone Tools

In addition to the main `research_wiki.py` engine and `lint.py` validator, four standalone CLI tools provide focused capabilities:

### wiki_graph.py — Knowledge Graph Traversal

BFS traversal, orphan detection, contradiction discovery, and wikilink seeding for `graph/edges.jsonl`.

```bash
python3 tools/wiki_graph.py wiki/ seed                          # Extract edges from wikilinks
python3 tools/wiki_graph.py wiki/ neighbors concepts/attention --depth 2
python3 tools/wiki_graph.py wiki/ find-contradictions
python3 tools/wiki_graph.py wiki/ orphans
python3 tools/wiki_graph.py wiki/ stats
python3 tools/wiki_graph.py wiki/ add-edge --from concepts/x --to papers/y --type supports
```

### compile_context.py — Purpose-Driven Context Compilation

Reads `index.md` trigger-to-page mappings and concatenates page content within a token budget. Useful for assembling focused context windows for LLM prompts.

```bash
python3 tools/compile_context.py wiki/ --list                   # Show available purposes
python3 tools/compile_context.py wiki/ --for session-close --budget 4000
```

Purposes are auto-derived from `## By Trigger` / `### <Heading>` sections in your `index.md`.

### find_similar.py — Semantic Dedup Search

Token Jaccard similarity search across wiki pages. Detects near-duplicates before creating new pages.

```bash
python3 tools/find_similar.py wiki/ "attention mechanism"
python3 tools/find_similar.py wiki/ "transformer" --type concepts
python3 tools/find_similar.py wiki/ "failed experiment" --threshold 0.5 --top 10
```

### wiki_lint.py — Cross-Wiki Structural Lint

Complements `lint.py` (entity-schema checks) with broader structural health checks: orphan pages, broken wikilinks, stale/ghost index entries, oversized pages, and duplicate filenames.

```bash
python3 tools/wiki_lint.py wiki/                                # Run all checks
python3 tools/wiki_lint.py wiki/ --fix                          # Auto-fix safe issues
python3 tools/wiki_lint.py wiki/ --max-lines 300 --json         # Custom threshold, JSON output
```

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

2263 tests covering all tools, skills, and shared references.

## Bilingual Support

ΩmegaWiki ships in English and Chinese:

```bash
./setup.sh --lang en   # English (default)
./setup.sh --lang zh   # 中文
```

---

## Roadmap

- [x] Wiki knowledge engine (20 CLI commands, 9 entity types, 9 edge types)
- [x] 23 Claude Code skills (full research lifecycle)
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

## Community / 交流群

<img src="assets/wechat-group.jpg" width="240" alt="WeChat Group QR Code">

Scan to join the ΩmegaWiki WeChat group / 扫码加入微信交流群

## Acknowledgments

- **[Andrej Karpathy](https://x.com/karpathy/status/1909372692069236775)** — for the LLM-Wiki concept that inspired this project
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — the AI agent runtime that powers ΩmegaWiki

## License

[MIT](LICENSE) — use it, fork it, build on it.

---

## 中文

### ΩmegaWiki 是什么？

Andrej Karpathy 提出了 [LLM-Wiki](https://x.com/karpathy/status/1909372692069236775) 概念：让 LLM **构建并维护一个持久的、结构化的 wiki**，而不是一次性的 RAG 回答。知识持续积累，每一篇新论文都让整个知识图谱更强。

**ΩmegaWiki 将这个理念完整实现。** 它不仅是 wiki 构建器，更是完整的研究全流程平台：从论文摄入 → 知识图谱 → 缺口检测 → 想法生成 → 实验设计 → 论文写作 → 同行评审回复。23 个 Claude Code Skills 驱动，一个 wiki 作为唯一的知识中枢。

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

# 把论文放入 raw/papers/（.tex 或 .pdf）
# 启动 Claude Code
claude
# 输入：/init <你的研究方向>
```

> **Windows 用户**：本地 pipeline 已原生支持。`/exp-run --env remote` 远程 GPU 实验依赖 `ssh`/`rsync`/`screen`，建议在 WSL2 或 Linux/macOS 下运行。

### API Key 说明

| Key | 必须？ | 获取方式 | 用途 |
|-----|--------|---------|------|
| `ANTHROPIC_API_KEY` | **是** | `claude login` | 驱动所有 Skill |
| `SEMANTIC_SCHOLAR_API_KEY` | 可选 | [semanticscholar.org](https://www.semanticscholar.org/product/api)（免费） | 引用图谱、论文搜索 |
| `DEEPXIV_TOKEN` | 可选 | `setup.sh` 自动注册 | 语义搜索、热门趋势 |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | 可选 | 任意 OpenAI 兼容 API | 跨模型评审 |

### 23 个 Skill 命令

| 命令 | 功能 |
|------|------|
| `/setup` | 首次配置（API key、语言、依赖） |
| `/reset` | 按范围销毁性清理：`wiki \| raw \| log \| checkpoints \| all` |
| `/prefill` | 预填 `foundations/` 背景知识（建议在 `/init` 之前运行） |
| `/init` | 从 raw/ 搭建完整 wiki |
| `/ingest` | 消化论文，创建页面 + 交叉引用 |
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
