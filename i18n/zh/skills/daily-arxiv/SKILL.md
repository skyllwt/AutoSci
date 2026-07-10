---
name: daily-arxiv
description: 运行或管理每日 arXiv 推荐 feed。用于手动获取新论文推荐、配置/检查/停用 GitHub Actions 定时任务、邮件 digest、选择 runtime，以及显式高置信 auto-ingest。
argument-hint: "[setup|status|disable] [--runtime auto|claude|codex|codex-account|codex-api|llm] [--mode inform|auto-ingest] [--hours 24] [--categories <cat...>] [--max-recommendations 10] [--max-auto-ingest 1] [--send-email true|false]"
---

# /daily-arxiv

> 运行或管理每日论文推荐 feed。裸 `/daily-arxiv` 表示“现在跑一次今天的推荐”；GitHub Actions 只是同一条 pipeline 的无人值守调度器。

按需读取 reference：

- `references/recommendation-and-ingest-policy.md` — evidence、LLM 决策 schema、置信度门控和 auto-ingest 约束
- `references/automation-scaffold.md` — GitHub Actions setup/status、secrets、artifacts 与失败行为

## Commands

- `/daily-arxiv`：现在跑一次推荐。如果缺少 `config/daily-arxiv.yml`，从 wiki 推断默认值后继续。
- `/daily-arxiv setup`：从 `config/daily-arxiv.yml.example` 创建或修复配置，检查 `.github/workflows/daily-arxiv.yml` 是否支持 `runtime`，并说明需要的 secrets。
- `/daily-arxiv status`：检查 config、workflow、schedule、mode、API/e-mail secrets 可用性，以及最近 artifacts。
- `/daily-arxiv disable`：把 config 中的 `schedule.enabled` 设为 `false`，或告诉用户需要怎样修改；手动 `/daily-arxiv` 仍可使用。

## Inputs

- `--mode inform|auto-ingest`：默认 `inform`。不要从 repo 状态推断 `auto-ingest`。
- `--runtime auto|claude|codex|codex-account|codex-api|llm`：GitHub Actions
  的 decision runtime。在 private repo 中，`auto` 与 `codex` 优先使用
  `CODEX_AUTH_JSON` 的 coding-plan account auth，再使用 `OPENAI_API_KEY`。
  GitHub-hosted runner 的定时 account auth 还需要
  `CODEX_AUTH_SECRET_SYNC_TOKEN` 来保存刷新后的登录状态。
- `--hours N`：拉取最近 N 小时论文；config/default 为 24。
- `--categories <cat...>`：覆盖配置中的 arXiv 分类。
- `--max-recommendations N`：digest 中最多展示的论文数；config/default 为 10。
- `--max-auto-ingest N`：高置信 auto-ingest 上限；config/default 为 1。
- `--send-email true|false`：workflow/setup 用的 SMTP 发送偏好。

## Setup Workflow

由 `/daily-arxiv setup` 触发。幂等 —— 在健康的 repo 上重跑是 no-op。

1. **Config**：如果缺少 `config/daily-arxiv.yml`，从 `config/daily-arxiv.yml.example` 拷贝。如果已存在，则保持不动（用户的偏好是持久的）。

2. **Workflow 文件**：确认 `.github/workflows/daily-arxiv.yml` 存在。如果缺失，引导用户查阅 `docs/daily-arxiv-deployment.md` 并停止 —— 从零重建该 workflow 超出 setup 的范围。

3. **Workflow env 暴露（自动补丁）**：在 `.github/workflows/daily-arxiv.yml` 中，定位 `daily-arxiv:` job 的 `env:` 块。用 Edit 工具确保下面两行作为 `HAS_CLAUDE_CODE_AUTH` 的同级存在：

   ```yaml
   SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
   DEEPXIV_TOKEN:            ${{ secrets.DEEPXIV_TOKEN }}
   ```

   - 如果两行都已存在，什么都不做。
   - 如果只缺一行，追加缺失的那一行。
   - 如果 `env:` 块根本不存在（较旧的 workflow），在该 job 下插入它，包含这两行以及已有的 auth 标志。不要改动任何其他 step。
   - 任何补丁之后，告诉用户改了什么，并提醒他们 commit。

4. **Secrets 检查**：列出用户已配置了哪些 —— `CODEX_AUTH_JSON`、
   `CODEX_AUTH_SECRET_SYNC_TOKEN`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_OAUTH_TOKEN`、
   `SEMANTIC_SCHOLAR_API_KEY`、`DEEPXIV_TOKEN`，以及可选的 SMTP secrets。
   `CODEX_AUTH_JSON` 是 coding-plan account credential，只允许用于 private
   repo；把本地 `~/.codex/auth.json` 的内容存为 repository secret，绝不打印
   或 commit。GitHub-hosted 定时运行还需要 `CODEX_AUTH_SECRET_SYNC_TOKEN`：
   它是只限此 repo、仅有 `Secrets: Read and write` 权限的 fine-grained PAT，
   仅用于在运行后保存 Codex 刷新的 auth 文件。`OPENAI_API_KEY` 仍是 API-key 替代路径，必须通过 Codex Action
   input 传递，不能设成 job-level environment variable。对任何缺失但必需的
   secret，给出他们需要的确切 `gh secret set` 命令。

5. **Summary**：汇报创建了什么、打了什么补丁，以及用户还需要做什么（按选中的 runtime 设置 secrets；account-auth 测试必须在 private repo 中；只有 Claude runtime 需要安装 Claude GitHub App；用一次 `gh workflow run daily-arxiv.yml` 验证）。

## Run Workflow

1. 解析 Python 解释器并准备 deterministic context：

   ```bash
   python3 tools/daily_arxiv.py prepare --wiki-root wiki --out .daily-arxiv/run/recommendation-context.json --out-feed .daily-arxiv/run/feed.json
   ```

2. 读取 `.daily-arxiv/run/recommendation-context.json`。基于 arXiv、wiki、Semantic Scholar、DeepXiv evidence，用 LLM 判断推荐质量。写出 `.daily-arxiv/run/llm-decisions.json`，字段包括 `decision`、`confidence`、`score`、`rationale`、`wiki_connections`、`signals_used`。在 CI 的 inform mode 中，可用 OpenAI-compatible review LLM 执行：

   ```bash
   python3 tools/daily_arxiv.py recommend-llm --context .daily-arxiv/run/recommendation-context.json --out .daily-arxiv/run/llm-decisions.json
   ```

3. 如果 mode 是 `auto-ingest`，只有 Claude、Codex account 或 Codex API
   runtime 可以选择 `decision: ingest` 且 `confidence: high`。遵守
   `max_auto_ingest`，使用选中 runtime 的 skill 语法按顺序调用
   `/ingest <arxiv-url>`，不要手写 wiki 或 graph 文件。第三方 LLM 与
   tool-ranked fallback 只用于推荐，不能 auto-ingest。

4. 生成 digest：

   ```bash
   python3 tools/daily_arxiv.py finalize --context .daily-arxiv/run/recommendation-context.json --decisions .daily-arxiv/run/llm-decisions.json --out-md .daily-arxiv/run/digest.md --out-json .daily-arxiv/run/digest.json
   ```

5. 汇报 strong recommendations、maybe interesting、重复跳过项、degraded signals、auto-ingest 结果，以及 setup/status 提示。

## Wiki Interaction

读取 `wiki/index.md`、`wiki/papers/`、`wiki/topics/`、`wiki/concepts/`、`wiki/methods/`、`wiki/ideas/`、`wiki/log.md` 来构建兴趣 profile 和去重。

inform 运行只写 `.daily-arxiv/` 下的 scratch 文件。`auto-ingest` 中所有持久 wiki/raw 变更都必须来自 `/ingest`。

## Relationships

- `/discover` 回答用户主动提出的 next-read 请求，可来自 anchors、topic 或 wiki 状态；它永不 ingest。
- `/daily-arxiv` 监听 fresh arXiv stream，可手动或每日通知。
- `/ingest` 是唯一论文纳入路径。`/daily-arxiv` 只能在显式 `auto-ingest` mode 下调用它。
