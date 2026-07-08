---
name: reset
description: 按 scope 重置 wiki 到干净 scaffold（wiki / raw / log / checkpoints / all）。适用于开发迭代或 setup 失败后的无痛重启。
argument-hint: "--scope wiki|raw|log|checkpoints|all"
---

# /reset

> 按 scope 重置 AutoSci 生成状态。设计目的是开发迭代和 setup 失败恢复 — 不是日常操作。

## Trigger

手动：Claude Code 中 `/reset --scope wiki`，或 Codex 中 `$reset --scope wiki`。支持 scope：`wiki`、`raw`、`log`、`checkpoints`、`all`。可用逗号组合多个 scope：`--scope wiki,log`。

## Inputs

- `--scope`（必填）：取值
  - `wiki` — 删除 `wiki/<entity>/` 与 `wiki/outputs/` 下所有 `*.md`，同时删除 `wiki/index.md`、`wiki/log.md` 和 `wiki/graph/` 下的文件。保留 `.gitkeep` 和 `wiki/CLAUDE.md`。
  - `raw` — 删除 `raw/discovered/` 与 `raw/tmp/` 下的生成型条目（保留 `.gitkeep`）。保留用户拥有的 `raw/papers/`、`raw/notes/` 与 `raw/web/`。
  - `log` — 重置 `wiki/log.md` 为空模板。
  - `checkpoints` — 通过 `research_wiki.py checkpoint-clear` 清除批处理状态。
  - `all` — 以上全部。

## Outputs

- 磁盘上清空 / 重置后的文件。
- 控制台摘要：已删除文件数、已重置文件数。

## Wiki Interaction

### 读取
- 所有 `wiki/<entity>/*.md`（用于枚举删除清单）。
- `raw/discovered/*` 与 `raw/tmp/*`（用于枚举生成型 raw 删除清单）。

### 写入
- 删除 `wiki/<entity>/*.md`（保留 `.gitkeep`）。
- 重写 `wiki/index.md`、`wiki/graph/*`，可选地重写 `wiki/log.md`。
- 删除生成型 `raw/discovered/*` 与 `raw/tmp/*`（保留 `.gitkeep`）。永不删除用户拥有的 `raw/papers/`、`raw/notes/` 或 `raw/web/`。

## Workflow

**前置条件**：当前目录包含 `wiki/`、`tools/`。`WIKI_ROOT=wiki/`。

### Step 1: 构造删除计划（dry-run）

```bash
python3 tools/reset_wiki.py --scope <scope>
```

该命令打印 JSON 计划，列出将要删除或重置的全部文件，**不修改任何东西**。按 scope 分组展示给用户（wiki entity 目录、raw 子目录、log、checkpoints）。

### Step 2: 与用户确认

打印计划摘要并请求显式确认：

```
About to delete N files and reset M files. Continue? [y/N]
```

用户拒绝则退出。**未经明确许可不得执行** — `/reset` 是破坏性操作，`raw/` 的删除不可恢复。

### Step 3: 执行

```bash
python3 tools/reset_wiki.py --scope <scope> --yes
```

工具打印 JSON 状态报告（`{deleted_files, reset_files}`）。

### Step 4: 记录日志（除非已重置 log）

若执行的 scope 不包含 `log`，追加一条日志：

```bash
python3 tools/research_wiki.py log wiki/ "reset | scope: <scope>"
```

### Step 5: 报告

打印结果并建议下一步：

```
## Reset complete — scope: <scope>

Deleted: N files
Reset:   M files

Next steps:
- Claude Code 的 /init 或 Codex 的 $init       — 从 raw/ 引导 wiki
- Claude Code 的 /prefill 或 Codex 的 $prefill — 沉淀基础背景知识
- Claude Code 的 /ingest 或 Codex 的 $ingest   — 手动添加单个来源
```

## Constraints

- **破坏性操作前必须确认**：禁止在未展示计划并征得用户同意前调用 `--yes`。
- **保留**：`.gitkeep` 占位、`wiki/CLAUDE.md`、`.claude/` 与 `.agents/`（skill 永不被触碰）。
- **用户 raw 永不删除**：`raw/papers/`、`raw/notes/` 与 `raw/web/` 对本 skill 只读，即使在 `raw` 或 `all` scope 下也是如此。helper 只清理生成型 `raw/discovered/` 与 `raw/tmp/`。
- **`/reset` 不触碰** `tools/`、`mcp-servers/`、`i18n/`、`.env` 或 git 状态。
- **scope 必填**：无默认行为（`/reset` 不带参数时提示用户选择 scope，而非猜测）。

## Error Handling

- **未知 scope**：列出有效 scope 并以非零退出码退出。
- **wiki 目录缺失**：报错并建议运行 `/init`。
- **`checkpoint-clear` 失败**：记录警告但不影响其他 scope。

## Dependencies

### 工具（通过 Bash）
- `python3 tools/reset_wiki.py --scope <scope> [--yes] [--project-root .]` — 确定性破坏性辅助工具；`raw` scope 仅限生成型 `raw/discovered/` 与 `raw/tmp/`
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `reset_wiki.py` 在 `checkpoints` scope 下直接删除 `wiki/.checkpoints/*.json`(不走 CLI — `checkpoint-clear` 子命令需指定具体的 `task_id`,而 `/reset --scope checkpoints` 的语义是"全部清除")
