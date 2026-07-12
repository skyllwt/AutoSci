---
name: daily-arxiv
description: 在 Codex 中运行或配置 daily arXiv 推荐
argument-hint: "[setup|status|disable] [--mode inform] [--hours 24] [--categories <cat...>] [--max-recommendations 10] [--send-email true|false]"
---

# $daily-arxiv

直接运行 `$daily-arxiv` 会执行一次本地推荐。`setup`、`status`、`disable` 用于管理 `config/daily-arxiv.yml` 与 `.github/workflows/daily-arxiv.yml`。

本地流水线为 `prepare` → Codex 推荐判断 → `finalize`。只读 wiki 兴趣画像，不修改 wiki。Decision 仅为 `strong_recommend`、`maybe`、`skip`；边界论文保持 `maybe`。Codex 判断不可用时，生成确定性工具排序降级摘要并明确标记。

GitHub Actions 可通过 `OPENAI_API_KEY` 或 `CODEX_ACCESS_TOKEN` 使用 Codex 推荐，并可降级到 OpenAI-compatible Review LLM。CI 只负责推荐：不得入库论文、提交 wiki 数据或推送仓库。SMTP 可选，发送失败不得导致摘要 artifact 丢失。

`disable` 修改 schedule 前必须明确确认。不得打印或写出认证 secrets。详见 `references/automation-scaffold.md` 与 `docs/daily-arxiv-deployment.md`。
