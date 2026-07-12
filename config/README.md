# Codex configuration

`setup.sh` and `setup.ps1` create `.env` without overwriting an existing file and cleanly rebuild `.agents/skills` from the selected bilingual source under `i18n/<lang>`.

Codex reads project instructions from `AGENTS.md` and skills from `.agents/skills`. Optional `llm-review` MCP configuration is provided in `codex.config.toml.example`; add it to the Codex user configuration using an absolute path to this project's `.venv` Python executable and MCP server script.

Optional API values include Semantic Scholar and DeepXiv retrieval credentials, OpenAI-compatible Review LLM settings, and SMTP settings. Never commit `.env`, credentials, user wiki content, raw papers, checkpoints, or experiment artifacts.
