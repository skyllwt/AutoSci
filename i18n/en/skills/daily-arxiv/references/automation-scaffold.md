# Recommendation automation

The workflow has read-only repository permissions and runs `prepare`, an optional OpenAI-compatible LLM decision step, `finalize`, optional SMTP, and artifact upload. Required LLM secrets are `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. If they are absent or the request fails, deterministic finalization still succeeds. SMTP failures must never suppress the digest or artifact. See `docsdaily-arxiv-deployment.md` for deployment and the optional manual mail smoke test.
