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
- 手动 dispatch 可覆盖 runtime、mode、hours、categories、caps 和 e-mail。
- `runtime: auto` 保持 Claude 优先；在 private repository 配置
  `CODEX_AUTH_JSON` 时先选择 Codex account auth；再在配置
  `OPENAI_API_KEY` 时选择 Codex API-key auth；之后使用 inform-only 的
  OpenAI-compatible LLM，最后输出 tool-ranked fallback digest。
- 将 `runtime: codex` 设为让 workflow 在 API key 前优先选择 account auth；用
  `runtime: codex-account` 或 `runtime: codex-api` 可强制指定路径。API-key auth
  调用 `openai/codex-action@v1`；account auth 恢复 `auth.json` 后直接运行
  `codex exec`，并使用仓库中的 schema 写出结构化 decision 文件。
- Auto-ingest mode 只有在选中的 runtime 是 Claude 或 Codex 时才允许；LLM
  和 fallback runtime 只能推荐，不能 ingest。
- Auto-ingest 只提交 `/ingest` 产生并 staged 的 `wiki/` 和
  `raw/discovered/` 变更。

## Secrets

推荐/ingest：

- `ANTHROPIC_API_KEY` — Claude Code Action 的直接 Anthropic API auth。
- `CLAUDE_CODE_OAUTH_TOKEN` — Pro/Max 用户的 Claude Code OAuth auth；在本地
  通过 `claude setup-token` 生成。它是 `ANTHROPIC_API_KEY` 的替代方案。
- `OPENAI_API_KEY` — 通过 `openai-api-key` input 传给
  `openai/codex-action@v1` 的 OpenAI API key。不要把它暴露为 job-level
  environment variable。
- `CODEX_AUTH_JSON` — 可选的 coding-plan account credential，内容来自本地
  `~/.codex/auth.json`。只允许在 private repository 中使用；workflow 会把它
  恢复到 runner 临时目录，绝不 commit。
- `CODEX_AUTH_SECRET_SYNC_TOKEN` — GitHub-hosted runner 上的定时 account-auth
  运行需要。它是仅限这个 private repository、仅有 `Secrets: Read and write`
  权限的 fine-grained GitHub PAT；Codex 退出后 workflow 用它保存刷新后的
  `CODEX_AUTH_JSON`，供下次运行使用。不要在 public repository 使用此路径。
- `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` — 可选的 OpenAI-compatible
  LLM，用于没有 Claude Code 时的 `inform` 推荐。
- `LLM_FALLBACK_MODEL` — 可选的 OpenAI-compatible LLM fallback。
- `SEMANTIC_SCHOLAR_API_KEY` — daily-cadence pipeline 需要；否则 S2 匿名
  rate limit 可能让 prepare 超时。
- `DEEPXIV_TOKEN` — daily-cadence pipeline 需要；否则 DeepXiv enrichment
  会退化到匿名请求并可能触发限流。

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
- 任一 agent runtime 运行时的 `llm-decisions.json`
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
- Agent 越过 write boundary 时，在 commit/push 之前直接失败。
- Codex inform 使用 `workspace-write`；Codex auto-ingest 使用隔离的 GitHub
  runner 上更宽的 sandbox，因为 `/ingest` 需要网络访问。prompt 与确定性
  boundary 检查仍会把持久写回限制在 `/ingest` 所有的路径内。
- Account-auth Codex 运行在 repository visibility 不是 `private` 时会
  fail closed。
- 定时 account-auth 运行缺少 `CODEX_AUTH_SECRET_SYNC_TOKEN` 时会 fail closed；
  手动 smoke run 不需要它，但无法保存刷新的登录状态。
