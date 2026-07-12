# Configuration

Setup creates `.env` from `.env.example` without overwriting an existing file. Optional values include retrieval credentials, OpenAI-compatible review/recommendation settings, and SMTP settings.

Setup also generates gitignored `opencode.json` with the official schema, project permissions, and the `llm-review` local MCP command. The command uses the absolute Python executable inside this project's `.venv`; never commit this machine-specific file.

The active language is cleanly generated from `i18n/<lang>` into `.opencode/skills`. Re-running setup removes stale generated skills first.

Copy `daily-arxiv.yml.example` to `daily-arxiv.yml` to customize recommendation categories, lookback, schedule, enrichment, and email. Daily arXiv has no runtime, mode, or automatic-ingest settings.
