# ΩmegaWiki — Runtime Contract

编辑 `i18n/zh/CLAUDE.md`,不要改根目录下的副本。运行 `./setup.sh --lang zh` 同步。

## 仓库布局

- `wiki/` — 产物面。`index.md` 是目录;`log.md` 是 append-only;每类实体一个子目录;`wiki/graph/` 自动生成。
- `runtime/` — 契约源(schema + policy + templates)。修改任何规则前先读 `runtime/CLAUDE.md`。
- `raw/` — 用户自有 `{papers,notes,web}/`(只读)+ skill 可写的 `discovered/`、`tmp/`。
- `tools/` — Python 助手(`research_wiki.py` 是 wiki 引擎,`lint.py` 是校验器)。

完整目录树:`docs/runtime-directory-structure.zh.md`。

## 链接语法

Wikilink:`[[slug]]`。slug 全小写、连字符分隔、无空格。

## 硬规则

1. `raw/{papers,notes,web}` 归用户所有,只读。skill 只能向 `raw/discovered/` 或 `raw/tmp/` 追加。
2. `wiki/graph/` 是派生态。仅通过 `tools/research_wiki.py`(`add-edge`、`add-citation`、`rebuild-*`)修改。
3. `wiki/log.md` 是 append-only。绝不就地重写。
4. 写正向链接 → 同步写反向链接。完整规则在 `runtime/schema/xref.yaml`。
5. 用户面 skill 参数(skill `argument-hint` 里列出的 flag)归用户所有。不得仅根据仓库状态擅自补出、翻转或删除它们。用户未提供时,只有 skill 文档化了省略行为才用默认值;否则询问用户。

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
