# AutoSci — 运行时契约（Qoder 版）

编辑 `i18n/zh/AGENTS.md`,不要改根目录下的副本。运行 `setup-qoder.sh --lang zh`(或 `setup-qoder.ps1`)同步。

## 仓库布局

- `wiki/` — 产物面。`index.md` 是目录;`log.md` 是 append-only;每类实体一个子目录;`wiki/graph/` 自动生成。
- `runtime/` — 契约源(schema + policy + templates)。修改任何规则前先读 `runtime/CLAUDE.md`。
- `raw/` — 用户自有 `{papers,notes,web}/`(只读)+ skill 可写的 `discovered/`、`tmp/`。
- `tools/` — Python 助手(`research_wiki.py` 是 wiki 引擎,`lint.py` 是校验器)。
- `.qoder/skills/` — 由 `tools/convert_to_qoder.py` 从 `i18n/zh/skills` 生成的 Qoder 原生 skills。不要手改;改 i18n 源后重跑 setup。

完整目录树:`docs/runtime-directory-structure.zh.md`。

## 链接语法

Wikilink:`[[slug]]`。slug 全小写、连字符分隔、无空格。

## Skill 调用约定（Qoder）

- Skill 位于 `.qoder/skills/<name>/SKILL.md`。文档中的 `/init`、`/ingest` 等写法表示"调用 skill `init`"、"调用 skill `ingest`" —— 按该 skill 的 `SKILL.md` 工作流逐步执行。
- 当一个 skill 把任务委托给另一个 skill(如 `/init` Step 5 扇出到 `/ingest`)时,为每个工作单元启动一个 Qoder 子代理(Agent 工具),把被委托 skill 的指令和输入交给它。
- 并行扇出使用 Qoder 子代理;`.qoder/skills/init/references/parallel-ingest.md` 中的 git worktree 隔离契约保持不变。子代理 prompt 必须用相对路径,且子代理的工作目录必须是 worktree 路径。
- `llm-review` MCP server 的工具写作 `llm-review.chat`、`llm-review.chat-reply`、`llm-review.web_search`。使用 `/review`、`/rebuttal` 等之前,先从 `.qoder/mcp.json`(或 Qoder 的 MCP 设置)注册该 server。
- 长跑服务(如 `tools/serve.py`)以后台 Bash 进程运行,归 Qoder 会话所有;不要用子代理包裹。

## 硬规则

1. `raw/{papers,notes,web}` 归用户所有,只读。skill 只能向 `raw/discovered/` 或 `raw/tmp/` 追加。
2. `wiki/graph/` 是派生态。仅通过 `tools/research_wiki.py`(`add-edge`、`add-citation`、`rebuild-*`)修改。
3. `wiki/log.md` 是 append-only。绝不就地重写。
4. 写正向链接 → 同步写反向链接。完整规则在 `runtime/schema/xref.yaml`。
5. 用户面 skill 参数(记录在 skill 的 **Usage** 行中的 flag)归用户所有。不得仅根据仓库状态擅自补出、翻转或删除它们。用户未提供时,只有 skill 文档化了省略行为才用默认值;否则询问用户。

## 查阅索引

| 需要 | 去哪 |
|---|---|
| 页面 frontmatter 字段、enum、默认值、生命周期 | `runtime/schema/entities.yaml` |
| 页面正文章节结构                                | `runtime/templates/{kind}.md.tmpl` |
| 边类型、属性、方向、confidence                | `runtime/schema/edges.yaml` |
| 正向 → 反向链接规则                            | `runtime/schema/xref.yaml` |
| slug 规则、ownership、edge 存储位置            | `runtime/schema/conventions.yaml` |
| 各 skill 对字段/边的写权限                     | `runtime/policy/writers.yaml` |
| 改契约本身 / 重新 regen                        | `runtime/CLAUDE.md` |

## Python 环境

按优先级:`.venv/bin/python`(Windows 上 `.venv/Scripts/python.exe`)→ 当前激活的 conda 环境 → `python3`(Windows 上 `python`)。tools/ 通过 `tools/_env.py` 自动从 `~/.env` 和项目根 `.env` 加载 API key。
