# AutoSci - Codex 项目说明

编辑 `i18n/zh/AGENTS.md`, 不要改根目录下的副本。运行 `./setup.sh --lang zh` 同步。

`CLAUDE.md` 是 Claude Code 的配套说明文件。除非规则只针对某一个 agent runtime, 否则要让 `AGENTS.md` 与 `CLAUDE.md` 中的共享仓库规则保持一致。

## Agent 入口

- Claude Code skills 位于 `.claude/skills`, 以 `/init`、`/ingest` 等 slash command 调用。
- Codex skills 位于 `.agents/skills`, 以 `$init`、`$ingest` 或 Codex `/skills` 调用。
- 两个 active skill tree 的源文件都在 `i18n/<lang>/skills`。修改 workflow 时, 先改本地化源文件, 保持中英文一致, 再运行 setup 重新生成 active files。
- Codex 要求每个 `SKILL.md` frontmatter 同时包含 `name` 和 `description`; 新增或编辑 skill 时必须保留这些 metadata。

## 仓库布局

- `wiki/` - 产物面。`index.md` 是目录; `log.md` 是 append-only; 每类实体一个子目录; `wiki/graph/` 自动生成。
- `runtime/` - 契约源(schema + policy + templates)。修改任何规则前先读 `runtime/CLAUDE.md`; 虽然文件名含 Claude, 它是共享 runtime contract。
- `raw/` - 用户自有 `{papers,notes,web}/`(只读) + skill 可写的 `discovered/`、`tmp/`。
- `tools/` - Python 助手(`research_wiki.py` 是 wiki 引擎, `lint.py` 是校验器)。

完整目录树: `docs/runtime-directory-structure.zh.md`。

## 链接语法

Wikilink: `[[slug]]`。slug 全小写、连字符分隔、无空格。

## 硬规则

1. `raw/{papers,notes,web}` 归用户所有, 只读。skill 只能向 `raw/discovered/` 或 `raw/tmp/` 追加。
2. `wiki/graph/` 是派生态。仅通过 `tools/research_wiki.py`(`add-edge`、`add-citation`、`rebuild-*`)修改。
3. `wiki/log.md` 是 append-only。绝不就地重写。
4. 写正向链接 -> 同步写反向链接。完整规则在 `runtime/schema/xref.yaml`。
5. 用户面 skill 参数(skill `argument-hint` 里列出的 flag)归用户所有。不得仅根据仓库状态擅自补出、翻转或删除它们。用户未提供时, 只有 skill 文档化了省略行为才用默认值; 否则询问用户。

## 查阅索引

| 需要 | 去哪 |
|---|---|
| 页面 frontmatter 字段、enum、默认值、生命周期 | `runtime/schema/entities.yaml` |
| 页面正文章节结构 | `runtime/templates/{kind}.md.tmpl` |
| 边类型、属性、方向、confidence | `runtime/schema/edges.yaml` |
| 正向 -> 反向链接规则 | `runtime/schema/xref.yaml` |
| slug 规则、ownership、edge 存储位置 | `runtime/schema/conventions.yaml` |
| 各 skill 对字段/边的写权限 | `runtime/policy/writers.yaml` |
| 改契约本身 / 重新 regen | `runtime/CLAUDE.md` |

## Python 环境

按优先级: `.venv/bin/python`(Windows 上 `.venv/Scripts/python.exe`) -> 当前激活的 conda 环境 -> `python3`(Windows 上 `python`)。tools/ 通过 `tools/_env.py` 自动从 `~/.env` 和项目根 `.env` 加载 API key。

## Review 指南

- 把用户自有的 `raw/`、`wiki/`、`.env` 和生成的实验输出丢失或被误改视为高严重度问题。
- workflow instruction 改动时, 检查 `.claude/skills`、`.agents/skills` 与 `i18n/<lang>/skills` 是否同步。
- 优先把确定性逻辑放在 `tools/`, 不要在 skill prompt 中复制实现逻辑。

## OpenCode 快速入门

1. 运行 `./setup.sh --lang zh` 从 `i18n/zh/` 生成 `.opencode/skills/` 和本 `AGENTS.md`。
2. 如需 MCP server 权限, 复制 `config/opencode.json.example` 到项目根目录并重命名为 `opencode.json`。
3. Skills 按名称调用(如 "run the autosci-init skill")或通过 OpenCode skill loader 调用。注意: 为避免与 OpenCode 内建的 `init` 命令冲突, 仓库中的 `init` skill 在 OpenCode 中重命名为 `autosci-init`。
4. `wiki/log.md`、`wiki/graph/edges.jsonl`、`wiki/graph/citations.jsonl` 和 `wiki/index.md` 使用 `merge=union`(见 `.gitattributes`) — 可安全支持多个代理并发追加。

## 跨代理说明 (OpenCode & Codex)

`.opencode/skills/`、`.claude/skills/` 和 `.agents/skills/` 下的 skill 文件均由共同的 `i18n/<lang>/skills` 源生成，而该源最初是为 Claude Code 编写的。因此 skill 文件中包含 Claude Code 专属构件, 非 Claude 代理需自行转换:

- **硬编码路径**: 形如 `.claude/skills/shared-references/...` 的引用 — 在其他代理中使用时, 分别解析为 `.opencode/skills/shared-references/...`(OpenCode) 或 `.agents/skills/...`(Codex)。
- **调用语法**: skill 内部以 `/skill-name`(Claude 风格) 和 `Skill: name`(Claude 工具) 引用其他 skill。OpenCode 代理应将其视为要直接调用的 skill 名称; Codex 代理应转换为 `$skill-name`。
- **命名冲突**: `init` skill 在 OpenCode 中注册为 `autosci-init`, 以避免与 OpenCode 内建的 `init` 命令冲突。当 skill 文本中出现 `/init` 时, 应调用 `autosci-init` skill。
- **Claude Code Native 工具**: 标记为 `### Claude Code Native` 的小节列出了 Claude 专属工具(`WebSearch`、`Agent`、`AskUserQuestion`)。非 Claude 代理必须映射到自身的等效工具(网页搜索、子代理调用、用户提示)。
- **MCP 命名**: `mcp__llm-review__chat` 是 Claude Code 的 MCP 前缀约定。其他代理使用不同的 MCP 调用模式 — 请参考你的代理的 MCP 文档。

编写或修改 skill 时, 请优先使用代理中立语言(使用相对路径, 描述意图而非工具名称), 并保持 `i18n/en/` 和 `i18n/zh/` 中对应的代理小节同步。
