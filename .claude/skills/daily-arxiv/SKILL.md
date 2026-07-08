---
name: daily-arxiv
description: Run or manage the daily arXiv recommendation feed. Use for one-off fresh-paper recommendations, scheduled GitHub Actions setup/status/disable, email digests, and explicit high-confidence auto-ingest through the ingest skill.
argument-hint: "[setup|status|disable] [--mode inform|auto-ingest] [--hours 24] [--categories <cat...>] [--max-recommendations 10] [--max-auto-ingest 1] [--send-email true|false]"
---

# /daily-arxiv / $daily-arxiv

> Run or manage the daily paper recommendation feed. Bare `/daily-arxiv` in Claude Code or `$daily-arxiv` in Codex means "run today's recommendation pass now"; GitHub Actions is only the unattended scheduler for the same pipeline.

Load references only when needed:

- `references/recommendation-and-ingest-policy.md` — evidence, LLM decision schema, confidence gate, and auto-ingest guardrails
- `references/automation-scaffold.md` — GitHub Actions setup/status behavior, secrets, artifacts, and failure modes

## Commands

- `/daily-arxiv` in Claude Code or `$daily-arxiv` in Codex: run a one-off recommendation pass now. If `config/daily-arxiv.yml` is missing, infer defaults from the wiki and continue.
- `/daily-arxiv setup` in Claude Code or `$daily-arxiv setup` in Codex: create or repair `config/daily-arxiv.yml` from `config/daily-arxiv.yml.example`; ensure `.github/workflows/daily-arxiv.yml` exists and that its `daily-arxiv:` job's `env:` block exposes both `SEMANTIC_SCHOLAR_API_KEY` and `DEEPXIV_TOKEN` — **add the missing lines automatically** rather than asking the user to hand-edit YAML (without these exposures the prepare step rate-limits out, identical symptom to never setting the secrets); and explain required Codex, legacy Claude Action, Review LLM, S2, DeepXiv, and SMTP secrets. See *Setup Workflow* below for the exact patch procedure.
- `/daily-arxiv status` in Claude Code or `$daily-arxiv status` in Codex: inspect config, workflow presence, schedule, mode, API/e-mail secret availability, and recent artifacts when available.
- `/daily-arxiv disable` in Claude Code or `$daily-arxiv disable` in Codex: set `schedule.enabled: false` in config or tell the user what to change; manual `/daily-arxiv` / `$daily-arxiv` must still work.

> When running `setup` or `status`, treat S2/DeepXiv repo secrets as required (not optional) for any daily-cadence pipeline, and point the user at [`docs/daily-arxiv-deployment.md`](../../../docs/daily-arxiv-deployment.md) for the full setup checklist and symptom-keyed troubleshooting.

## Inputs

- `--mode inform|auto-ingest`: default `inform`. Never infer `auto-ingest` from repo state.
- `--hours N`: pull papers from the last N hours; config/default is 24.
- `--categories <cat...>`: override configured arXiv categories.
- `--max-recommendations N`: maximum papers shown in the digest; config/default is 10.
- `--max-auto-ingest N`: cap for high-confidence auto-ingest; config/default is 1.
- `--send-email true|false`: workflow/setup preference for SMTP delivery.

## Setup Workflow

Triggered by `/daily-arxiv setup` in Claude Code or `$daily-arxiv setup` in Codex. Idempotent — re-running on a healthy repo is a no-op.

1. **Config**: if `config/daily-arxiv.yml` is missing, copy from `config/daily-arxiv.yml.example`. If present, leave it alone (the user's preferences are durable).

2. **Workflow file**: confirm `.github/workflows/daily-arxiv.yml` exists. If absent, point the user at `docs/daily-arxiv-deployment.md` and stop — re-creating the workflow from scratch is out of scope for setup.

3. **Workflow env exposures (auto-patch)**: in `.github/workflows/daily-arxiv.yml`, locate the `daily-arxiv:` job's `env:` block. Use the Edit tool to ensure both lines are present as siblings of `HAS_CODEX_AUTH`, `HAS_CLAUDE_CODE_AUTH`, and `HAS_REVIEW_LLM`:

   ```yaml
   SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
   DEEPXIV_TOKEN:            ${{ secrets.DEEPXIV_TOKEN }}
   ```

   - If both lines already exist, do nothing.
   - If only one is missing, append the missing line.
   - If the `env:` block doesn't exist at all (older workflow), insert it under the job with both lines plus the existing `HAS_CODEX_AUTH` / `HAS_CLAUDE_CODE_AUTH` / `HAS_REVIEW_LLM` flags. Do not touch any other step.
   - After any patch, tell the user what was changed and remind them to commit.

4. **Secrets check**: list which of `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN`, `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`, `SEMANTIC_SCHOLAR_API_KEY`, `DEEPXIV_TOKEN`, and the optional SMTP secrets the user has configured. Use `gh secret list` when available; otherwise instruct the user to run it. Surface any missing-but-required secrets with the exact `gh secret set` command they need.

5. **Summary**: report what was created, patched, and what the user still needs to do (install the GitHub App, set missing secrets, verify with one `gh workflow run daily-arxiv.yml`).

## Run Workflow

1. Resolve the Python interpreter and run the deterministic preparation:

   ```bash
   python3 tools/daily_arxiv.py prepare --wiki-root wiki --out .daily-arxiv/run/recommendation-context.json --out-feed .daily-arxiv/run/feed.json
   ```

2. Read `.daily-arxiv/run/recommendation-context.json`. Judge candidates with an LLM using the provided arXiv, wiki, Semantic Scholar, and DeepXiv evidence. Write `.daily-arxiv/run/llm-decisions.json` with `decision`, `confidence`, `score`, `rationale`, `wiki_connections`, and `signals_used`. In CI inform mode, the backend order is Codex CLI (`OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN`), then legacy Claude Code Action, then OpenAI-compatible Review LLM. Codex receives a compact context generated via:

   ```bash
   python3 tools/daily_arxiv.py compact-context --context .daily-arxiv/run/recommendation-context.json --out .daily-arxiv/run/codex-context.json
   ```

   The Review LLM fallback may do this via:

   ```bash
   python3 tools/daily_arxiv.py recommend-llm --context .daily-arxiv/run/recommendation-context.json --out .daily-arxiv/run/llm-decisions.json
   ```

3. If mode is `auto-ingest`, note the current runtime limit: CI auto-ingest is supported only through the legacy Claude Code Action path. Workflow dispatch must use `recommender=auto` or `recommender=claude-action`; explicit `codex`, `review-llm`, or `tool` recommenders fail closed in auto-ingest mode. Codex CI is inform-mode only until full Codex CI ingest orchestration and push are verified. Local Codex `$ingest` and force-staged writeback scope have been smoke-tested, but the unattended GitHub Actions path has not. Choose `decision: ingest` + `confidence: high`, obey `max_auto_ingest`, and invoke `/ingest <arxiv-url>` sequentially. Do not hand-write wiki or graph files. Codex inform mode and third-party LLMs are recommendation-only and must not auto-ingest.

4. Finalize the digest:

   ```bash
   python3 tools/daily_arxiv.py finalize --context .daily-arxiv/run/recommendation-context.json --decisions .daily-arxiv/run/llm-decisions.json --out-md .daily-arxiv/run/digest.md --out-json .daily-arxiv/run/digest.json
   ```

5. Report strong recommendations, maybe-interesting papers, skipped duplicates, degraded signals, auto-ingest outcomes, and setup/status hints.

## Wiki Interaction

Reads `wiki/index.md`, `wiki/papers/`, `wiki/topics/`, `wiki/concepts/`, `wiki/methods/`, `wiki/ideas/`, and `wiki/log.md` to build the interest profile and dedupe candidates.

Writes only scratch files under `.daily-arxiv/` during inform runs. In `auto-ingest`, all durable wiki/raw mutations must come from `/ingest` in Claude Code or `$ingest` in Codex.

## Relationships

- `/discover` (Claude Code) or `$discover` (Codex) answers deliberate next-read requests from anchors, topics, or wiki state; it never ingests.
- `/daily-arxiv` (Claude Code) or `$daily-arxiv` (Codex) watches the fresh arXiv stream and can notify daily or manually.
- `/ingest` (Claude Code) or `$ingest` (Codex) is the only paper incorporation path. `/daily-arxiv` / `$daily-arxiv` may call it only in explicit `auto-ingest` mode.
