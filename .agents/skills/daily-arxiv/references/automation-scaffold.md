# Codex recommendation automation

The workflow prepares evidence, runs Codex when `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN` is available, falls back to the configured Review LLM or deterministic ranking, finalizes the digest, uploads artifacts, and optionally sends email. It has read-only repository permissions and never performs unattended ingest or writeback.
