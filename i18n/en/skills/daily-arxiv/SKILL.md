---
name: daily-arxiv
description: Prepare and judge fresh arXiv recommendations locally, or configure the recommendation-only GitHub Actions digest
---

# Daily arXiv

Inputs are an optional operation (`setup`, `status`, or `disable`) plus optional `--hours`, `--categories`, `--max-recommendations`, and `--send-email`. With no operation, run one local recommendation pass.

The pipeline is fixed: `prepare` → recommendation judgment → `finalize`. It never ingests papers or mutates the wiki. Read wiki profile data only. Write only `.daily-arxiv/`, the example/config file when explicitly requested, and the workflow when setting up automation.

For a local run, execute `tools/daily_arxiv.py prepare`, judge candidates using the supplied evidence, write decisions containing only `strong_recommend`, `maybe`, or `skip`, then execute `finalize`. Borderline items stay `maybe`. If no LLM is available, omit decisions and explicitly report the deterministic tool-ranked fallback.

For automation, use `.github/workflowsdaily-arxiv.yml`. CI calls only an independent OpenAI-compatible API; it does not run OpenCode. Digest finalization and artifact upload must use `always()` semantics. SMTP is optional and best-effort. `disable` requires confirmation before changing the schedule. See `references/automation-scaffold.md`.
