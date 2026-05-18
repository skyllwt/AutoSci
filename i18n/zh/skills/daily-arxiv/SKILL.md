---
description: 运行或管理每日 arXiv 推荐 feed。用于手动获取新论文推荐、配置/检查/停用 GitHub Actions 定时任务、邮件 digest，以及显式高置信 auto-ingest。
argument-hint: "[setup|status|disable] [--mode inform|auto-ingest] [--hours 24] [--categories <cat...>] [--max-recommendations 10] [--max-auto-ingest 1] [--send-email true|false]"
---

# /daily-arxiv

> 运行或管理每日论文推荐 feed。裸 `/daily-arxiv` 表示“现在跑一次今天的推荐”；GitHub Actions 只是同一条 pipeline 的无人值守调度器。

按需读取 reference：

- `references/recommendation-and-ingest-policy.md` — evidence、LLM 决策 schema、置信度门控和 auto-ingest 约束
- `references/automation-scaffold.md` — GitHub Actions setup/status、secrets、artifacts 与失败行为

## Commands

- `/daily-arxiv`：现在跑一次推荐。如果缺少 `config/daily-arxiv.yml`，从 wiki 推断默认值后继续。
- `/daily-arxiv setup`：从 `config/daily-arxiv.yml.example` 创建或修复配置，检查 `.github/workflows/daily-arxiv.yml`，并说明需要的 secrets。
- `/daily-arxiv status`：检查 config、workflow、schedule、mode、API/e-mail secrets 可用性，以及最近 artifacts。
- `/daily-arxiv disable`：把 config 中的 `schedule.enabled` 设为 `false`，或告诉用户需要怎样修改；手动 `/daily-arxiv` 仍可使用。

## Inputs

- `--mode inform|auto-ingest`：默认 `inform`。不要从 repo 状态推断 `auto-ingest`。
- `--hours N`：拉取最近 N 小时论文；config/default 为 24。
- `--categories <cat...>`：覆盖配置中的 arXiv 分类。
- `--max-recommendations N`：digest 中最多展示的论文数；config/default 为 10。
- `--max-auto-ingest N`：高置信 auto-ingest 上限；config/default 为 1。
- `--send-email true|false`：workflow/setup 用的 SMTP 发送偏好。

## Run Workflow

1. 解析 Python 解释器并准备 deterministic context：

   ```bash
   python3 tools/daily_arxiv.py prepare --wiki-root wiki --out .daily-arxiv/run/recommendation-context.json --out-feed .daily-arxiv/run/feed.json
   ```

2. 读取 `.daily-arxiv/run/recommendation-context.json`。基于 arXiv、wiki、Semantic Scholar、DeepXiv evidence，用 LLM 判断推荐质量。写出 `.daily-arxiv/run/llm-decisions.json`，字段包括 `decision`、`confidence`、`score`、`rationale`、`wiki_connections`、`signals_used`。在 CI 的 inform mode 中，可用 OpenAI-compatible review LLM 执行：

   ```bash
   python3 tools/daily_arxiv.py recommend-llm --context .daily-arxiv/run/recommendation-context.json --out .daily-arxiv/run/llm-decisions.json
   ```

3. 如果 mode 是 `auto-ingest`，只能使用 Claude Code runtime：选择 `decision: ingest` 且 `confidence: high` 的论文，遵守 `max_auto_ingest`，并按顺序调用 `/ingest <arxiv-url>`。不要手写 wiki 或 graph 文件。第三方 LLM 只用于推荐，不能 auto-ingest。

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
