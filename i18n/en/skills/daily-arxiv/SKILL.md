---
name: daily-arxiv
description: Run or configure the daily arXiv recommendation feed in Codex
argument-hint: "[setup|status|disable] [--mode inform] [--hours 24] [--categories <cat...>] [--max-recommendations 10] [--send-email true|false]"
---

# $daily-arxiv

Bare `$daily-arxiv` runs one local recommendation pass. `setup`, `status`, and `disable` manage `config/daily-arxiv.yml` and `.github/workflows/daily-arxiv.yml`.

The local pipeline is `prepare` → Codex recommendation judgment → `finalize`. Read wiki profile data without mutating it. Decisions are `strong_recommend`, `maybe`, or `skip`; borderline papers remain `maybe`. If Codex judgment is unavailable, finalize the deterministic tool-ranked fallback and label it clearly.

GitHub Actions supports Codex recommendation through `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN`, with an optional OpenAI-compatible Review LLM fallback. CI is recommendation-only: it does not ingest papers, commit wiki data, or push repository changes. SMTP is optional and must not suppress digest artifacts when it fails.

`disable` requires explicit confirmation before changing the schedule. Never print or write authentication secrets. See `references/automation-scaffold.md` and `docs/daily-arxiv-deployment.md`.
