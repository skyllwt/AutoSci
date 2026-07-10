# Deploying `/daily-arxiv` on GitHub Actions

This page is the operator's manual for running the daily arXiv pipeline on GitHub Actions. Read top-to-bottom for first-time setup; jump to **Troubleshooting** when a run fails.

## Setup

1. **Pick the decision runtime.** Set `runtime: codex` in
   `config/daily-arxiv.yml` for Codex, or leave `runtime: auto` to preserve
   Claude-first behavior. In a private repository, either mode prefers
   coding-plan account auth when `CODEX_AUTH_JSON` is configured, then falls
   back to API-key auth. Use `runtime: codex-account` or `runtime: codex-api`
   to require one path explicitly.

2. **Configure the selected agent auth.** For a coding-plan account in this
   private repository, store the local Codex auth file as a repository secret:
   ```bash
   gh secret set CODEX_AUTH_JSON < ~/.codex/auth.json
   ```
   Treat this secret like a password. The workflow restores it only under
   `$RUNNER_TEMP` and rejects account auth for non-private repositories.

   For Codex API-key auth:
   ```bash
   gh secret set OPENAI_API_KEY
   ```
   The workflow passes this secret only through
   [`openai/codex-action@v1`](https://github.com/openai/codex-action)'s
   `openai-api-key` input; do not add it to a job-level `env:` block.

   For Claude, pick one of:
   - `ANTHROPIC_API_KEY` — pay-as-you-go API; quota is independent of any subscription.
   - `CLAUDE_CODE_OAUTH_TOKEN` — Pro/Max subscription quota; generate with `claude setup-token`.

   Set it once with `gh secret set <NAME>`. The workflow is happy with either.

3. **Install the Claude Code GitHub App** on the repo at <https://github.com/apps/claude> only when using the Claude runtime. Codex does not require the Claude App.

4. **Mirror API keys to repo secrets.** These are required for the daily-cadence pipeline (anonymous-tier rate limits time the run out, they don't just slow it down):
   ```bash
   gh secret set SEMANTIC_SCHOLAR_API_KEY -b "$(grep ^SEMANTIC_SCHOLAR_API_KEY= .env | cut -d= -f2-)"
   gh secret set DEEPXIV_TOKEN            -b "$(grep ^DEEPXIV_TOKEN= ~/.env       | cut -d= -f2-)"
   ```
   `DEEPXIV_TOKEN` lives in `~/.env`, not the project `.env` — the SDK auto-registers there.

5. **Run `/daily-arxiv setup` once** in your local checkout. The skill auto-patches `.github/workflows/daily-arxiv.yml` to expose `SEMANTIC_SCHOLAR_API_KEY` and `DEEPXIV_TOKEN` to the Python prepare step (without these the secrets stay invisible to the runner and the daily run rate-limits out). Commit any resulting workflow change. If you can't run the slash skill, hand-add this under the `daily-arxiv:` job's `env:` block:
   ```yaml
   SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
   DEEPXIV_TOKEN:            ${{ secrets.DEEPXIV_TOKEN }}
   ```

6. **SMTP secrets**, if `email.enabled: true` in `config/daily-arxiv.yml`:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `DAILY_ARXIV_EMAIL_TO`.

7. **Verify with one manual dispatch** before relying on the cron. For the Codex inform path:
   ```bash
   gh workflow run daily-arxiv.yml --ref main \
     -f runtime=codex -f mode=inform -f send_email=false
   gh run watch
   ```

## What a good run looks like

- All workflow steps green.
- `digest.md` artifact populated under **Strong Recommendations**.
- E-mail digest in your inbox (if email is enabled).
- *Either* a new commit on `main` titled `daily-arxiv auto-ingest`, *or* the step summary line "no wiki/raw changes were detected" — depending on whether any candidate cleared the high-confidence gate that day. Both are valid.

## Troubleshooting

Match your failing-step error to a heading.

### `Could not fetch an OIDC token`

The workflow's `permissions:` block needs `id-token: write` only for the Claude runtime, because Claude's action exchanges an OIDC token for an app token. Codex account auth uses `CODEX_AUTH_JSON`; Codex API auth uses `OPENAI_API_KEY` through the Codex Action input.

### `App token exchange failed: 401 - Claude Code is not installed on this repository`

This only applies to `runtime=claude`. Install the Claude Code GitHub App on the repository: <https://github.com/apps/claude>. Selecting "Only select repositories" and adding just this repo is fine. For Codex, dispatch with `-f runtime=codex` and configure either `CODEX_AUTH_JSON` in a private repository or `OPENAI_API_KEY`.

### `runtime=codex-api requires the OPENAI_API_KEY repository secret`

Add the key with:

```bash
gh secret set OPENAI_API_KEY
```

Do not export it in the workflow's job-level environment. The Codex Action
starts the API proxy and receives the key through `openai-api-key`.

### `runtime=codex-account requires the CODEX_AUTH_JSON repository secret`

Create it from the local coding-plan login:

```bash
gh secret set CODEX_AUTH_JSON < ~/.codex/auth.json
```

This path only runs when GitHub reports the repository as private. Do not use
it for public repositories, and do not print or commit `auth.json`.

### Codex action completes, but `llm-decisions.json` is missing or invalid

The Codex path requires the checked-in
`.github/codex/llm-decisions.schema.json` and the action's structured-output
configuration. Confirm that the checkout step runs first and that the
Codex Action is not being skipped because `runtime` resolved to Claude or the
inform-only LLM. The action output is uploaded as `llm-decisions.json`.

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

`claude-code-action`'s `--max-turns` ceiling is too low for the work in one prompt. A single `/ingest` runs ~40–50 tool calls; the decision step adds a handful more. The workflow currently uses `--max-turns 100`, which fits one paper. If `max_auto_ingest > 1`, raise it proportionally. The Codex Action has the corresponding non-interactive run limits from the installed Codex CLI; keep `max_auto_ingest` small and ingest sequentially.

### `fatal: Authentication failed for 'https://github.com/<owner>/<repo>.git/'` (exit 128)

`actions/checkout@v4` installs an auth header in `.git/config`. An agent action may alter or clear it, so the commit step re-embeds the token in the remote URL before pushing:

```bash
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
git push
```

The step also needs `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` in its `env:` block.

### Pipeline finishes green, but no auto-ingest commit lands and no `wiki/papers/<slug>.md` is created

The Claude action's `--allowedTools` is missing `Skill` (and likely `TodoWrite` / `Agent`). Without `Skill`, Claude has no way to invoke the `/ingest` skill — but the prompt's structured output schema still gets filled in with `ingest_status: success`, so the failure is silent. Use:

```yaml
claude_args: |
  --max-turns 100
  --allowedTools "Read,Write,Edit,Bash,Skill,TodoWrite,Agent"
```

For Codex, the equivalent requirement is that the prompt invokes the repo's
`$ingest` skill and that the run uses `runtime=codex` with `mode=auto-ingest`.
The workflow rejects agent edits outside `.daily-arxiv/`, `wiki/`, and
`raw/discovered/` before writeback.

## Common errors

- **Whitespace in secrets.** `gh secret set X < <(claude setup-token)` and similar one-liners can capture banner text or trailing newlines. Sanitize before storing:
  ```bash
  TOKEN=$(claude setup-token | tr -d '[:space:]')
  printf '%s' "$TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN
  unset TOKEN
  ```
- **`DEEPXIV_TOKEN` lives in `~/.env`, not the project `.env`.** Easy to miss when writing a mirror script.
- **`gh run watch --exit-status` returns 0 on cancellation, not just success.** Confirm with `gh run view <id> --json conclusion`.
- **Job logs return HTTP 404 while the job is still running.** `gh api .../jobs/<id>/logs` only works after the job reaches a terminal state.
- **Pro/Max OAuth quota is shared.** The same token authenticates your local Claude Code session and CI's auto-ingest. Heavy local use can starve CI; if CI auth fails for hours, check whether you've been hammering Claude Code locally.
