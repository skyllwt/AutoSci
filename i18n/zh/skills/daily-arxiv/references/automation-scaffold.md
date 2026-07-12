# 推荐自动化

Workflow 仅有仓库只读权限，依次运行 `prepare`、可选 OpenAI-compatible LLM 判断、`finalize`、可选 SMTP 和 artifact 上传。LLM 密钥为 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。缺少配置或请求失败时，确定性 finalize 仍须成功。SMTP 失败不得导致摘要或 artifact 丢失。部署步骤与可选人工邮件冒烟测试见 `docsdaily-arxiv-deployment.md`。
