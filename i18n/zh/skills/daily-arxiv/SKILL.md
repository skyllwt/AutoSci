---
name: daily-arxiv
description: 在本地准备并判断最新 arXiv 推荐，或配置仅推荐的 GitHub Actions 摘要
---

# Daily arXiv

输入可包含操作 `setup`、`status`、`disable`，以及 `--hours`、`--categories`、`--max-recommendations`、`--send-email`。省略操作时执行一次本地推荐。

流水线固定为 `prepare` → 推荐判断 → `finalize`。它绝不入库论文或修改 wiki；wiki 兴趣画像只读。只允许写 `.daily-arxiv/`，以及用户明确要求时的配置文件和 workflow。

本地运行时先执行 `tools/daily_arxiv.py prepare`，依据给出的证据判断候选，只写 `strong_recommend`、`maybe`、`skip` 三种 decision，最后执行 `finalize`。边界论文保持 `maybe`。LLM 不可用时不提供 decisions，并明确说明使用确定性工具排序降级。

自动化使用 `.github/workflowsdaily-arxiv.yml`。CI 只调用独立 OpenAI-compatible API，不运行 OpenCode。摘要 finalize 和 artifact 上传必须采用 `always()` 语义。SMTP 可选且失败不阻塞。`disable` 修改定时任务前必须确认。详见 `references/automation-scaffold.md`。
