---
description: Interactive API key configuration guide — checks current .env state and walks you through Semantic Scholar, DeepXiv, and Review LLM setup
---

# /setup

> Guides you through ΩmegaWiki's optional API key configuration.
> Reads your current `.env`, shows what is and isn't configured, and helps you
> set up each key with clear explanations of what it does and how to get it.
> Safe to re-run at any time — only updates keys you choose to configure.

## Inputs

- No arguments required
- Reads: `.env` (current configuration state)
- Reads: `config/setup-guide.md` (reference for what each key does)

## Outputs

- Updated `.env` with any newly configured keys
- A summary of current configuration status

## Wiki Interaction

### Reads
- None (setup runs before any wiki exists)

### Writes
- None (does not touch the wiki)

## Workflow

### Step 1: Read Configuration Reference

Read `config/setup-guide.md` to load the complete reference for all configurable keys,
including what each does, which skills use it, how to get it, and fallback behavior.

### Step 2: Detect Current Environment

Run the following to check what is already configured:

```bash
python3 -c "
import sys, os
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
keys = {
    'SEMANTIC_SCHOLAR_API_KEY': 'Semantic Scholar',
    'DEEPXIV_TOKEN':            'DeepXiv',
    'LLM_API_KEY':              'Review LLM (API key)',
    'LLM_BASE_URL':             'Review LLM (base URL)',
    'LLM_MODEL':                'Review LLM (model)',
}
for k, label in keys.items():
    v = os.environ.get(k, '').strip()
    print(f'SET:{k}' if v else f'UNSET:{k}')
"
```

Also detect the Python environment and `.venv` status:
```bash
ls .venv/ 2>/dev/null && echo "venv:present" || echo "venv:absent"
python3 --version
```

### Step 3: Show Configuration Status

Present a clear summary to the user, grouped by status:

```
ΩmegaWiki Configuration Status
================================
✓  ANTHROPIC_API_KEY      — managed by Claude Code (claude login)

Recommended:
✗  Semantic Scholar        — not set  (citation expansion 3x slower — get free key)

Optional:
✗  DeepXiv                 — not set  (semantic search unavailable)
✗  Review LLM              — not set  (cross-model review unavailable)
```

Ask the user: "Which would you like to configure? (You can skip any or all.)"

### Step 4: Configure Each Key (user-directed)

For each key the user wants to configure, follow the specific sub-flow below.
Always ask for user confirmation before writing to `.env`.

---

#### 4a: Semantic Scholar API Key

**Explain**: "Semantic Scholar gives citation data and paper search.
Used by /ingest, /init, /novelty, /ideate. Free to get.
**Recommended** — without it, /init runs 3x slower and citation-chain expansion is much less effective."

**Guide to get it**: "Go to https://www.semanticscholar.org/product/api and click 'Get API Key'. It's free."

**Ask**: "Do you have a Semantic Scholar API key? (paste it, or 'skip')"

**If provided**, write to `.env`:
```python
# Read current .env, update or append SEMANTIC_SCHOLAR_API_KEY=<value>
```
Use the Edit tool to update `.env`:
- If `SEMANTIC_SCHOLAR_API_KEY=` line exists (even empty), replace it
- Otherwise append `SEMANTIC_SCHOLAR_API_KEY=<value>`

---

#### 4b: DeepXiv Token

**Explain**: "DeepXiv enables semantic paper search, AI paper summaries (TLDR),
and trending paper detection. Used by /daily-arxiv, /novelty, /ideate, /ingest, /init.
Without it, those skills fall back to arXiv RSS + Semantic Scholar — everything still works."

**Offer three options**:
1. **Auto-register** (recommended, free, instant): Run the registration inline
2. **Paste existing token**: User provides their token
3. **Skip**: Configure later

**For option 1 — auto-register**, run:
```bash
python3 -c "
import sys, json
from uuid import uuid4
try:
    import requests
except ImportError:
    print('ERROR: requests not installed', file=sys.stderr)
    sys.exit(1)

suffix = uuid4().hex[:10]
payload = {
    'sdk_secret': 'UuZp0i83svQU7_naUEexczc-X3NWv7lvNkD8e3sPyng',
    'name': f'deepxiv_{suffix}',
    'email': f'{suffix}@example.com',
}
try:
    resp = requests.post('https://data.rag.ac.cn/api/register/sdk', json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)

if not result.get('success'):
    print(f'ERROR: {result.get(\"message\", \"unknown\")}', file=sys.stderr)
    sys.exit(1)

token = result.get('data', {}).get('token', '')
daily_limit = result.get('data', {}).get('daily_limit', 1000)
if not token:
    print('ERROR: no token in response', file=sys.stderr)
    sys.exit(1)

print(token)
print(f'daily_limit:{daily_limit}', file=sys.stderr)
"
```
stdout → token value; stderr → human-readable status (pass through, don't suppress).

If registration succeeds, write the token to `.env`. If it fails, show the error and
offer to let the user paste a token manually instead.

---

#### 4c: Review LLM

**Explain**: "The Review LLM connects ΩmegaWiki to a second AI model for independent
adversarial review. It's used by /review, /novelty, /ideate, /paper-plan, /paper-draft,
/rebuttal, /refine, /exp-eval, /exp-design, and /daily-arxiv inform recommendations.
Works with any OpenAI-compatible API.
Without it, those skills skip the cross-model review step (everything still works)."

**Present the provider table** from `config/setup-guide.md` (Key 3 section).

**Clarify what 'OpenAI-compatible' means** if the user asks: any API that accepts
`POST /chat/completions` with `{"model": "...", "messages": [...]}` in the OpenAI format.

**Ask for**:
1. `LLM_BASE_URL` — e.g. `https://api.deepseek.com/v1`
2. `LLM_API_KEY` — their API key for that provider
3. `LLM_MODEL` — model name, e.g. `deepseek-chat`

**Validate format**: Base URL should start with `http://` or `https://` and end with `/v1`
(or similar path). If it looks wrong, ask for confirmation before writing.

**Write all three** to `.env` once the user confirms.

**After writing**: Remind the user that the Review LLM MCP server starts when Claude Code
launches and reads `.env` at that time — changes take effect after restarting Claude Code.

---

#### 4d: arXiv Categories (only if user asks)

This key has a sensible default (`cs.LG,cs.CV,cs.CL,cs.AI,stat.ML`). Only configure
it if the user explicitly asks, or if their research area is clearly outside ML/AI.

---

### Step 5: Verify Configuration

After the user finishes configuring, run the verification check from `config/setup-guide.md`:

```bash
python3 -c "
import sys, os
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
keys = ['SEMANTIC_SCHOLAR_API_KEY', 'DEEPXIV_TOKEN', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for k in keys:
    v = os.environ.get(k, '').strip()
    print(f'SET   {k}' if v else f'UNSET {k}')
"
```

Show a final summary. For any keys still not set, briefly note what they unlock
and that the user can run `/setup` again anytime to add them.

### Step 6: Next Steps

If this is a fresh install (no `wiki/` directory):
```
Configuration done. Next:
  • Put your own papers in raw/papers/ (.tex or .pdf)
  • Optional: add intent notes to raw/notes/ and saved pages to raw/web/
  • /init and direct local /ingest will manage generated inputs under raw/discovered/ and raw/tmp/
  • Run: /init [your-research-topic]
```

If `wiki/` already exists:
```
Configuration updated. Restart Claude Code for Review LLM changes to take effect.
```

## Constraints

- **Never overwrite existing non-empty values** without asking the user first
- **Never expose the full key value** in output — show only the first 8 characters + `...`
- **Write only to `.env`** — never to `~/.env` or other locations
- **No wiki reads or writes** — this skill runs before the wiki may exist
- **Skip gracefully**: if the user says "skip all", show the status summary and exit cleanly

## Error Handling

- **`.env` not found**: Inform the user that `setup.sh` was not run yet. Offer to create `.env` from `.env.example`:
  ```bash
  cp config/.env.example .env
  ```
  Then continue with configuration.

- **`config/setup-guide.md` not found**: Proceed using the information in this SKILL.md directly.

- **DeepXiv registration fails** (network error, server error): Show the error message clearly,
  offer to let the user paste a token manually, or skip.

- **Python environment issue** (`tools/_env.py` not found): Note that `.venv` may not be active,
  but still read `.env` directly using shell or Python file I/O to check current state.

## Dependencies

### Tools (via Bash)
- `python3 -c "import _env; ..."` — read current `.env` state
- `python3 -c "import requests; ..."` — DeepXiv auto-registration HTTP call

### Files Read
- `config/setup-guide.md` — complete reference for all configurable keys
- `.env` — current configuration (read + write)

### Files Written
- `.env` — updated with newly configured keys (via Edit tool)

### No MCP servers, no wiki, no external skills called
