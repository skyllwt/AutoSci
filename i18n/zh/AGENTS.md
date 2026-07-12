# 在 OpenCode 中使用 AutoSci

OpenCode 是唯一支持的终端代理。`setup.sh` 或 `setup.ps1` 会把技能生成到 `.opencode/skills`；`i18n/<lang>` 下的双语源是事实来源。通过 `skill` 工具加载技能，初始化 wiki 时使用 `init`。

`raw/`、`wiki/`、`.checkpoints/`、实验输出和本地配置均属于用户数据。只按任务需要读取；未经人类明确确认，不得发布、删除、重置或覆盖。技能只能写入其 Wiki Interaction 中声明的路径。依据 `runtime/schema/xref.yaml` 同步正向与反向图链接。

使用 OpenCode 原生工具：`websearch`、`webfetch`、`task`、`question`、`skill`。`websearch` 不可用时优先使用项目 Python 检索工具，并明确标记为降级结果。并行任务不得写同一文件；共享索引和图更新必须串行。保留所有人类确认门，特别是实验运行、部署、破坏性重置和外部通信。

仓库契约位于 `runtime/schema`、`runtime/policy` 与 `runtime/templates`。修改契约前先读 `runtime/AGENTS.md`。wiki 变更后运行 `python tools/lint.py --wiki-dir wiki`。不得提交密钥、生成的 `.opencode`、`opencode.json`、用户 wiki 内容、原始资料或实验产物。
