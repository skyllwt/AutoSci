# Codex 推荐自动化

Workflow 先准备证据；有 `OPENAI_API_KEY` 或 `CODEX_ACCESS_TOKEN` 时运行 Codex，否则降级到 Review LLM 或确定性排序；随后 finalize 摘要、上传 artifact，并可选发送邮件。仓库权限只读，绝不执行无人值守 ingest 或写回。
