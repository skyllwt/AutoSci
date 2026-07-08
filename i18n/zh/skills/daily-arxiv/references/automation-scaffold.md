# Daily arXiv Automation

GitHub Actions 是 `/daily-arxiv` 的无人值守调度器。它应运行与手动 slash
skill 相同的 pipeline；它不定义这个功能的用户入口。

## Source of Truth

- `config/daily-arxiv.yml`：持久、非 secret 的用户偏好。
- `tools/daily_arxiv.py`：确定性的 config、feed、evidence、digest helper。
- `/daily-arxiv`：LLM 判断、setup/status UX，以及可选 `/ingest` 编排。
- `.github/workflows/daily-arxiv.yml`：定时执行器。

如果缺少 `config/daily-arxiv.yml`，手动运行继续使用推断默认值。
`/daily-arxiv setup` 可复制 `config/daily-arxiv.yml.example`。

## Workflow Behavior

- 默认定时：`17 0 * * *` UTC。
- 手动 dispatch 可覆盖 mode、hours、categories、caps 和 e-mail。
- Inform mode 准备 context，然后使用第一个可用 recommender：
  带 `OPENAI_API_KEY` 或 `CODEX_ACCESS_TOKEN` 的 Codex CLI；否则使用带
  `ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_OAUTH_TOKEN` 的 legacy Claude Code
  Action；否则使用 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 对应的
  OpenAI-compatible LLM；否则输出 tool-ranked fallback digest。
- Auto-ingest mode 缺少 legacy Claude Code Action auth 时 fail closed。Codex
  CI 在写回路径单独验证前仅用于 inform mode。
- Auto-ingest 只提交 `/ingest` 产生并 staged 的 `wiki/` 和
  `raw/discovered/` 变更。

## Secrets

推荐/ingest：

- `OPENAI_API_KEY` — Codex CLI 的 CI inform-mode API-key auth。
- `CODEX_ACCESS_TOKEN` — Codex CLI 的 CI inform-mode access-token auth；它是
  `OPENAI_API_KEY` 的替代方案。
- `CODEX_MODEL` — 可选，覆盖 CI 推荐步骤使用的 Codex 模型。
- `ANTHROPIC_API_KEY` — Claude Code Action 的直接 Anthropic API auth。
- `CLAUDE_CODE_OAUTH_TOKEN` — Pro/Max 用户的 Claude Code OAuth auth；在本地
  通过 `claude setup-token` 生成。它是 legacy Claude Code Action 的
  `ANTHROPIC_API_KEY` 替代方案。
- `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` — 可选的 OpenAI-compatible
  LLM，用于没有 Claude Code 时的 `inform` 推荐。
- `LLM_FALLBACK_MODEL` — 可选的 OpenAI-compatible LLM fallback。
- `SEMANTIC_SCHOLAR_API_KEY` — daily-cadence 运行需要；匿名 S2 rate limit
  会让 prepare 步骤在大量候选上超时。
- `DEEPXIV_TOKEN` — daily-cadence 运行需要；避免 DeepXiv enrichment 的匿名限流。

SMTP 发送：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `DAILY_ARXIV_EMAIL_TO`

不要把 secrets 写进 `config/daily-arxiv.yml`。

## Artifacts

每次 workflow run 上传：

- `resolved-config.json`
- `feed.json`
- `recommendation-context.json`
- Codex recommender 运行时的 `codex-context.json`
- 任一 LLM 或 agent recommender 运行时的 `llm-decisions.json`
- `digest.md`
- `digest.json`

Markdown digest 也会写入 GitHub Actions job summary。

## Status Checks

`/daily-arxiv status` 应检查：

- config 是否存在，以及解析后的 mode/caps/categories
- workflow 文件是否存在和 schedule
- `schedule.enabled` 是否为 false
- 本地 env vars 或可见 CI secrets 是否可用
- 本地 `.daily-arxiv/` 中最近 digest（若存在）

## Failure Behavior

- arXiv fetch 失败：在 recommendation/finalization 前失败。
- SMTP secrets 缺失：仅在 e-mail 启用时失败。
- 空 feed 或全部重复：生成合法空 artifacts。
- 外部 API 失败：继续运行，并保留 degraded notes。
- Auto-ingest 失败：保留逐论文 error，并继续生成最终 digest。
