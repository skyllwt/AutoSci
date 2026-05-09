# ΩmegaWiki — Configuration Guide

> This file is read by the `/setup` skill to guide users through API key configuration.
> It describes each optional key: what it does, which skills use it, how to get it,
> and what happens when it is not set.

---

## How Configuration Works

All API keys live in the project-root `.env` file (created by `setup.sh` from `.env.example`).
Python tools load this file automatically on startup via `tools/_env.py` — no manual `export` needed.
Claude Code itself does not read `.env`; only the Python tools do.

The `/setup` skill checks which keys are currently set, explains each one, and writes values
directly into `.env` using the Edit tool.

---

## Key 1: Semantic Scholar API Key

| Field | Value |
|-------|-------|
| `.env` variable | `SEMANTIC_SCHOLAR_API_KEY` |
| Required? | No (optional, strongly recommended) |
| Free? | Yes — instant approval, no credit card |

**What it does**: Gives access to Semantic Scholar's paper database — citation counts,
reference graphs, author metadata, and keyword search.

**Which skills use it**:
- `/ingest` — citation count, importance scoring for ingested papers
- `/init` — discover related papers by topic and citation chain
- `/novelty` — keyword search to find prior work
- `/ideate` — find high-citation papers in a research area
- `/daily-arxiv` — enrich arXiv papers with citation data

**Without this key**: All skills still work, but S2 API calls are rate-limited to
1 request per 3 seconds (vs. 1 per second with a key). For large `/init` runs with
many papers, this can add 10–20 minutes.

**How to get it**:
1. Go to https://www.semanticscholar.org/product/api
2. Click "Get API Key" (free, instant approval, no credit card)
3. Copy the key (format: a long alphanumeric string)

**Format**: Long alphanumeric string, e.g. `abc123def456...`

---

## Key 2: DeepXiv Token

| Field | Value |
|-------|-------|
| `.env` variable | `DEEPXIV_TOKEN` |
| Required? | No (optional) |
| Free? | Yes — auto-registration available |

**What it does**: Enables semantic paper search (BM25 + vector hybrid), AI-generated
paper summaries (TLDR), progressive reading, and trending paper detection.

**Which skills use it**:
- `/daily-arxiv` — trending papers, TLDR for scoring
- `/novelty` — semantic search to find similar work
- `/ideate` — landscape scan, trending papers
- `/ingest` — TLDR, paper structure analysis
- `/init` — semantic paper discovery

**Without this key**: Skills fall back to arXiv RSS + Semantic Scholar only.
All skills still work; semantic search and TLDR features are unavailable.

**How to get it** (choose one):
- **Option A — Auto-register**: Claude Code can register a free token automatically.
  Just say "auto-register" and it will call the registration API and save the token.
- **Option B — Manual**: Go to https://data.rag.ac.cn/register

**Auto-registration details** (for Option A):
- Endpoint: `POST https://data.rag.ac.cn/api/register/sdk`
- Payload: `{"sdk_secret": "UuZp0i83svQU7_naUEexczc-X3NWv7lvNkD8e3sPyng", "name": "deepxiv_<random>", "email": "<random>@example.com"}`
- Response: `{"success": true, "data": {"token": "<token>", "daily_limit": 1000}}`
- Free tier: 1,000 requests/day. For higher limits, contact tommy@chien.io

**Note on Python 3.9**: The `deepxiv_sdk` package uses type hint syntax (`tuple[X | None]`)
that requires Python 3.10+. On Python 3.9, import will fail. Use the inline HTTP request
approach above instead of `from deepxiv_sdk.cli import auto_register_token`.

**Format**: Alphanumeric token string

---

## Key 3: Review LLM (three variables)

| Field | Value |
|-------|-------|
| `.env` variables | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` |
| Required? | No (optional) |
| Free? | Depends on provider |

**What it does**: Connects ΩmegaWiki to a second LLM (independent of Claude) for
adversarial cross-model review. The reviewer independently critiques research artifacts
without seeing Claude's prior analysis, improving review quality.

**Which skills use it**:
- `/review` — general-purpose cross-model review
- `/novelty` — second-opinion on novelty assessment
- `/ideate` — dual-model brainstorm + independent filter
- `/exp-eval` — verdict gate on experiment results
- `/exp-design` — review experiment plan
- `/paper-plan` — review paper outline (mandatory gate)
- `/paper-draft` — review each section
- `/rebuttal` — stress-test rebuttal responses
- `/refine` — review in multi-round improve cycle
- `/daily-arxiv` — inform-mode recommendation in CI when Claude Code is unavailable

**Without these keys**: Skills skip the cross-model review step and proceed with
Claude-only analysis or deterministic fallback. Everything still works, but you
lose the independent second-opinion. The `/review` skill will note that
cross-model review is unavailable.

**Works with any OpenAI-compatible API**:

| Provider | LLM_BASE_URL | Example LLM_MODEL |
|----------|-------------|-------------------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| OpenRouter | `https://openrouter.ai/api/v1` | any model slug |
| Qwen (DashScope) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | see their docs |
| Local (Ollama) | `http://localhost:11434/v1` | `llama3.2` |

**How to set up**:
1. Choose a provider and get an API key from them
2. Note the base URL and model name from the table above
3. Set all three variables in `.env`
4. Restart Claude Code (the MCP server re-reads `.env` on startup)

**Optional**: `LLM_FALLBACK_MODEL` — fallback model if the primary fails (defaults to `LLM_MODEL`)

**Reviewer independence principle** (from `shared-references/cross-model-review.md`):
Never share Claude's analysis with the Review LLM before it gives its independent assessment.
The value of cross-model review comes from genuine independence.

---

## Key 4: arXiv Categories (optional)

| Field | Value |
|-------|-------|
| `.env` variable | `ARXIV_CATEGORIES` |
| Required? | No |
| Default | `cs.LG,cs.CV,cs.CL,cs.AI,stat.ML` |

**What it does**: Controls which arXiv subject categories `/daily-arxiv` monitors.

**Format**: Comma-separated category codes. Full list: https://arxiv.org/category_taxonomy

**Examples**:
- ML/AI focus: `cs.LG,cs.CV,cs.CL,cs.AI,stat.ML`
- Systems focus: `cs.DC,cs.AR,cs.PF,cs.OS`
- Theory focus: `cs.CC,cs.DS,cs.LO,math.CO`

---

## Configuration Verification

After setting keys, verify they are loaded correctly:

```bash
# Check which keys are set in .env
source .venv/bin/activate && python3 -c "
import _env, os
keys = ['SEMANTIC_SCHOLAR_API_KEY', 'DEEPXIV_TOKEN', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for k in keys:
    v = os.environ.get(k, '')
    status = '✓ set' if v else '✗ not set'
    print(f'{status}  {k}')
"
```

After adding `LLM_*` variables, restart Claude Code so the MCP server picks them up.
