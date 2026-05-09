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
| `CLAUDE_CODE_OAUTH_TOKEN` | Optional | `claude setup-token` | GitHub Actions Claude Code auth for Pro/Max users |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) (free) | Citation graph, paper search |
| `DEEPXIV_TOKEN` | Optional | `setup.sh` auto-registers | Semantic search, TLDR, trending |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | Optional | Any OpenAI-compatible API | Cross-model review; `/daily-arxiv` inform recommendations |

> **Cross-model review**: ΩmegaWiki uses a second LLM as an independent reviewer for ideas, experiments, and paper drafts. Works with **any OpenAI-compatible API** — DeepSeek, OpenAI, Qwen, OpenRouter, SiliconFlow, etc. If not configured, skills still work in Claude-only mode.

### Daily arXiv Recommendations

`/daily-arxiv` runs a one-off fresh-paper recommendation pass even before
automation is configured. To schedule the same pipeline in GitHub Actions, copy
`config/daily-arxiv.yml.example` to `config/daily-arxiv.yml`, then run
`/daily-arxiv setup`. The config stores non-secret preferences such as mode,
categories, caps, and schedule; SMTP/API credentials stay in `.env` or GitHub
Actions secrets. In CI inform mode, recommendations can use Claude Code auth
(`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`) or the OpenAI-compatible
`LLM_*` review model; auto-ingest still requires Claude Code.

> See [`docs/daily-arxiv-deployment.md`](docs/daily-arxiv-deployment.md) for
> the GitHub Actions setup checklist and symptom-keyed troubleshooting.

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
| `/daily-arxiv` | Run/manage a daily arXiv recommendation feed (+ optional GitHub Actions scheduler) |
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

**GitHub Actions** runs the `/daily-arxiv` recommendation pipeline at UTC 00:17 daily (08:17 Beijing time):

1. Add SMTP secrets to repo **Settings → Secrets** when e-mail delivery is enabled: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `DAILY_ARXIV_EMAIL_TO`
2. Optional inform-mode LLM recommendation: add `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` for Claude Code, or `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` for any OpenAI-compatible provider
3. `.github/workflows/daily-arxiv.yml` fetches arXiv, deduplicates against the wiki, builds a recommendation context, uploads artifacts, and sends the digest by SMTP

`auto-ingest` mode is explicit and requires Claude Code in CI, because plain API LLMs cannot invoke slash skills such as `/ingest`. Use manual dispatch with `send_email=false` for a dry run without SMTP secrets.

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
│   ├── discovered/              #   external papers from /init and explicit /daily-arxiv auto-ingest
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
| `CLAUDE_CODE_OAUTH_TOKEN` | 可选 | `claude setup-token` | Pro/Max 用户的 GitHub Actions Claude Code auth |
| `SEMANTIC_SCHOLAR_API_KEY` | 可选 | [semanticscholar.org](https://www.semanticscholar.org/product/api)（免费） | 引用图谱、论文搜索 |
| `DEEPXIV_TOKEN` | 可选 | `setup.sh` 自动注册 | 语义搜索、热门趋势 |
| `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | 可选 | 任意 OpenAI 兼容 API | 跨模型评审；`/daily-arxiv` inform 推荐 |

### 自动化

GitHub Actions 每天 UTC 00:17（北京时间 08:17）运行 `/daily-arxiv` 推荐 pipeline：拉取 arXiv、按 wiki 去重、构建 recommendation context、上传 artifacts，并可通过 SMTP 发送 digest 邮件。

启用邮件时，在 repo **Settings → Secrets** 添加：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_FROM`、`DAILY_ARXIV_EMAIL_TO`。

CI inform mode 可使用 `ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_OAUTH_TOKEN` 启动 Claude Code，也可使用 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 接入任意 OpenAI-compatible provider。`auto-ingest` 是显式模式，并且需要 Claude Code，因为普通 API LLM 不能调用 `/ingest` 这类 slash skill。手动触发时可设置 `send_email=false`，用于无 SMTP secrets 的 dry run。

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
| `/daily-arxiv` | 运行/管理每日 arXiv 推荐 feed（可选 CI 定时） |
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
