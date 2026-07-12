# Daily arXiv deployment for Codex

The Codex branch runs daily arXiv as recommendation-only automation. Configure `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN` for Codex recommendations. Optional fallback secrets are `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_FALLBACK_MODEL`. Semantic Scholar, DeepXiv, and SMTP secrets remain optional enhancements.

The workflow has read-only repository permissions. It never invokes unattended ingest, commits user wiki data, or pushes changes. Missing agent credentials fall back to the Review LLM when configured, then to deterministic tool ranking. Email is best-effort; digest finalization and artifact upload remain authoritative.

Run a manual smoke test with:

```bash
gh workflow run daily-arxiv.yml -f mode=inform -f recommender=codex -f send_email=false
gh run watch
```

Real SMTP delivery depends on the deployment environment and is not a local acceptance requirement.
