# Daily arXiv deployment

Daily arXiv is recommendation-only. It reads the local wiki profile, prepares fresh-paper evidence, asks an independent OpenAI-compatible LLM for recommendations, and writes Markdown/JSON artifacts. It never invokes OpenCode in CI, commits repository data, or ingests papers.

Copy `config/daily-arxiv.yml.example` to `config/daily-arxiv.yml`, adjust the categories, and configure these GitHub repository secrets:

- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`; optional `LLM_FALLBACK_MODEL`
- optional enrichment: `SEMANTIC_SCHOLAR_API_KEY`, `DEEPXIV_TOKEN`
- optional email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO`

Both scheduled and manual runs use `.github/workflows/daily-arxiv.yml`. If the LLM is absent or fails, finalization still emits a deterministic tool-ranked digest. SMTP is also best-effort: missing configuration, authentication failures, timeouts, and TLS failures cannot prevent digest finalization or artifact upload.

Trigger a smoke run with:

```bash
gh workflow run daily-arxiv.yml -f send_email=false
gh run watch
```

Automated tests mock SMTP. Real delivery depends on the deployed provider, firewall, credentials, and TLS policy, so it is not part of local acceptance. After deployment, an optional manual smoke test is:

```bash
python tools/send_email.py --subject "AutoSci SMTP smoke test" --body-file .daily-arxiv/run/digest.md
```
