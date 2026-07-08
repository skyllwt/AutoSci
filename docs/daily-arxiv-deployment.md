# Deploying Daily arXiv on GitHub Actions

This page is the operator's manual for the current GitHub Actions deployment path
for the daily arXiv pipeline. CI `inform` mode supports a Codex CLI recommender
first, then a legacy Claude Code Action recommender, then an OpenAI-compatible
Review LLM fallback. CI `auto-ingest` is still legacy Claude Code Action only
until the Codex writeback path is separately verified. Read top-to-bottom for
first-time setup; jump to **Troubleshooting** when a run fails.

## Setup

1. **Pick an inform-mode recommender auth secret.** Preferred:
   - `OPENAI_API_KEY` — Codex CLI API-key auth.
   - `CODEX_ACCESS_TOKEN` — Codex CLI access-token auth.

   Optional fallback:
   - `ANTHROPIC_API_KEY` — pay-as-you-go API; quota is independent of any subscription.
   - `CLAUDE_CODE_OAUTH_TOKEN` — Pro/Max subscription quota; generate with `claude setup-token`.
   - `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — OpenAI-compatible Review LLM fallback.

   Set secrets with `gh secret set <NAME>`. `CODEX_MODEL` can optionally override the Codex model used in CI.

2. **For auto-ingest only, configure legacy Claude Code Action auth.** Set either `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, then install the Claude Code GitHub App on the repo at <https://github.com/apps/claude>. The auth secret alone is not enough; the action needs an app installation to exchange OIDC for a usable token. Codex CI currently does not run `$ingest` or push wiki changes.

3. **Mirror API keys to repo secrets.** These are required for the daily-cadence pipeline (anonymous-tier rate limits time the run out, they don't just slow it down):
   ```bash
   gh secret set SEMANTIC_SCHOLAR_API_KEY -b "$(grep ^SEMANTIC_SCHOLAR_API_KEY= .env | cut -d= -f2-)"
   gh secret set DEEPXIV_TOKEN            -b "$(grep ^DEEPXIV_TOKEN= ~/.env       | cut -d= -f2-)"
   ```
   `DEEPXIV_TOKEN` lives in `~/.env`, not the project `.env` — the SDK auto-registers there.

4. **Run the daily-arxiv setup skill once** in your local checkout: `/daily-arxiv setup` in Claude Code, or `$daily-arxiv setup` in Codex for local configuration checks. The skill auto-patches `.github/workflows/daily-arxiv.yml` to expose `SEMANTIC_SCHOLAR_API_KEY` and `DEEPXIV_TOKEN` to the Python prepare step (without these the secrets stay invisible to the runner and the daily run rate-limits out). Commit any resulting workflow change. If you can't run the agent skill, hand-add this under the `daily-arxiv:` job's `env:` block:
   ```yaml
   SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
   DEEPXIV_TOKEN:            ${{ secrets.DEEPXIV_TOKEN }}
   ```

5. **SMTP secrets**, if `email.enabled: true` in `config/daily-arxiv.yml`:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `DAILY_ARXIV_EMAIL_TO`.

6. **Verify with one manual dispatch** before relying on the cron:
   ```bash
   gh workflow run daily-arxiv.yml --ref main
   gh run watch
   ```

## What a good run looks like

- All workflow steps green.
- `digest.md` artifact populated under **Strong Recommendations**.
- E-mail digest in your inbox (if email is enabled).
- *Either* a new commit on `main` titled `daily-arxiv auto-ingest`, *or* the step summary line "no wiki/raw changes were staged" — depending on whether any candidate cleared the high-confidence gate that day. Both are valid.

## Troubleshooting

Match your failing-step error to a heading.

### `Could not fetch an OIDC token`

The workflow's `permissions:` block must include `id-token: write` when the legacy Claude Code Action path is used. Required because the action exchanges an OIDC token for a Claude Code app token.

### `App token exchange failed: 401 - Claude Code is not installed on this repository`

Install the Claude Code GitHub App on the repository: <https://github.com/apps/claude>. Selecting "Only select repositories" and adding just this repo is fine.

### `Authentication failed: Invalid or expired token`

The auth secret value is malformed. Most often this is trailing whitespace from how it was piped into `gh secret set`. See the **Common errors** checklist below to re-set cleanly.

### `Rate limited, waiting 60s/120s/180s...` looping in `Prepare recommendation context`

The workflow needs `SEMANTIC_SCHOLAR_API_KEY` and `DEEPXIV_TOKEN` exposed as **environment variables** to the Python step, not just stored as secrets. Setting `gh secret set <KEY>` is half the work — the workflow's job-level `env:` block must also reference them:

```yaml
env:
  SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
  DEEPXIV_TOKEN:            ${{ secrets.DEEPXIV_TOKEN }}
```

Without these lines, the Python tool reads the env var as empty and runs in anonymous mode. With ~1000 daily candidates, the resulting backoff loop blows past any reasonable step budget.

### `Reached maximum number of turns (N)`

The legacy `claude-code-action` `--max-turns` ceiling is too low for the work in one prompt. A single ingest skill run takes roughly 40-50 tool calls; the decision step adds a handful more. The workflow currently uses `--max-turns 100`, which fits one paper. If `max_auto_ingest > 1`, raise it proportionally.

### `fatal: Authentication failed for 'https://github.com/<owner>/<repo>.git/'` (exit 128)

`actions/checkout@v4` installs an auth header in `.git/config`. Agent steps may alter it, so the commit step's `git push` can lose credentials. Re-embed the token in the remote URL before pushing:

```bash
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
git push
```

The step also needs `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` in its `env:` block.

### Pipeline finishes green, but no auto-ingest commit lands and no `wiki/papers/<slug>.md` is created

The action's `--allowedTools` is missing `Skill` (and likely `TodoWrite` / `Agent`). Without `Skill`, Claude has no way to invoke the ingest skill — but the prompt's structured output schema still gets filled in with `ingest_status: success`, so the failure is silent. Use:

```yaml
claude_args: |
  --max-turns 100
  --allowedTools "Read,Write,Edit,Bash,Skill,TodoWrite,Agent"
```

## Common errors

- **Whitespace in secrets.** `gh secret set X < <(claude setup-token)` and similar one-liners can capture banner text or trailing newlines. Sanitize before storing:
  ```bash
  TOKEN=$(claude setup-token | tr -d '[:space:]')
  printf '%s' "$TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN
  unset TOKEN
  ```
- **`DEEPXIV_TOKEN` lives in `~/.env`, not the project `.env`.** Easy to miss when writing a mirror script.
- **Codex inform mode only.** `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN` lets CI rank recommendations, but it does not enable CI auto-ingest. Auto-ingest still requires the legacy Claude Code Action auth path.
- **`gh run watch --exit-status` returns 0 on cancellation, not just success.** Confirm with `gh run view <id> --json conclusion`.
- **Job logs return HTTP 404 while the job is still running.** `gh api .../jobs/<id>/logs` only works after the job reaches a terminal state.
- **Pro/Max OAuth quota is shared.** The same token authenticates your local Claude Code session and CI's auto-ingest. Heavy local use can starve CI; if CI auth fails for hours, check whether you've been hammering Claude Code locally.
