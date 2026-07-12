---
name: edit
description: 根据用户要求更新 wiki 内容，或在不修改用户 raw sources 的前提下准备生成型 raw 输入
argument-hint: "[request]"
---

# $edit

> 根据用户要求更新 wiki 内容，或准备生成型 raw 输入。用户拥有的 raw sources 保持只读。

## 触发

用户手动：Codex 中 `$edit <用户要求>`，或 Codex 中 `$edit <用户要求>`。

## 输入

用户请求，例如：
- "把这篇论文下载为后续 ingest 可用的输入"
- "把这个 arXiv source 准备到 raw/discovered/"
- "为 raw/papers/xxx.pdf 制定删除计划"
- "更新 topics/efficient-llm-adaptation 的 SOTA tracker"
- "给 concepts/lora 加一个新变体"

## 输出

更新后的 wiki 文件、`index.md`、`log.md`，以及可选的 `raw/discovered/` 或 `raw/tmp/` 下生成型辅助文件。

## 步骤

### STEP 1: 解析用户意图

1. **准备生成型 raw 输入**：
   - 若用户提供的是 `raw/papers/`、`raw/notes/` 或 `raw/web/` 下的本地路径：把它当作只读输入，不复制、不重写、不删除。
   - 若用户提供 arXiv URL 且要求 agent 抓取：生成的 source artifact 只写入 `raw/discovered/`。
   - 若用户提供临时中间内容：只写入 `raw/tmp/`。
   - 不要把抓取的网页内容写入 `raw/web/`；该目录归用户所有。除非已有文档明确指定其他可写路径，否则临时网页摘录放 `raw/tmp/`。
2. **删除 raw sources**：
   - 不删除 `raw/papers/`、`raw/notes/` 或 `raw/web/` 下文件。只给出删除计划，并说明这些用户拥有文件必须由用户自行删除，或通过另行授权的破坏性操作处理。
   - `raw/discovered/` 或 `raw/tmp/` 下的生成文件只有在用户明确确认后才可删除。
3. **更新 wiki**：
   - 读取相关页面，按用户要求修改内容

### STEP 2: 执行更新

1. 生成型 raw 输入后续可通过 Codex 的 `$ingest` 或 Codex 的 `$ingest` 纳入 wiki
2. 直接 wiki 修改：按用户指令更新特定页面的特定字段/内容
3. 写正向链接时同步写反向链接

### STEP 3: 更新导航

1. `EDIT wiki/index.md`：更新相关条目
2. `APPEND wiki/log.md`：`## [{date}] update | {description}`

### STEP 4: 报告

- 列出变更内容
- 提示后续操作（如需要 ingest 新增的 raw sources）

## 约束

- `raw/papers/`、`raw/notes/`、`raw/web/` 归用户所有且只读。本 skill 不得在其中创建、覆盖、移动或删除文件。
- skill 生成的 raw artifact 只能写入 `raw/discovered/` 或 `raw/tmp/`。
- wiki 修改遵循模板结构
- 双向链接同步维护
