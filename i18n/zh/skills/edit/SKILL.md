---
name: edit
description: 根据用户要求增删 raw sources 或更新 wiki 内容
---

# edit

> 根据用户要求增删 raw sources 或更新 wiki 内容。

## 触发

用户手动：`edit <用户要求>`

## 输入

用户请求，例如：
- "把这篇论文下载到 raw/papers/"
- "删除 raw/papers/xxx.pdf"
- "更新 topics/efficient-llm-adaptation 的 SOTA tracker"
- "给 concepts/lora 加一个新变体"

## 输出

更新后的 wiki 文件、`index.md`、`log.md`

## 步骤

### STEP 1: 解析用户意图

1. **增加 raw sources**：
   - 若用户提供了本地路径：复制到 `raw/` 对应目录
   - 若用户提供了 arXiv URL：下载到 `raw/papers/`
   - 若用户提供了网页 URL：用 markdownify 抓取内容存到 `raw/web/`
2. **删除 raw sources**：
   - 确认后执行删除
3. **更新 wiki**：
   - 读取相关页面，按用户要求修改内容

### STEP 2: 执行更新

1. 增加的 raw sources 后续可通过 `ingest` 纳入 wiki
2. 直接 wiki 修改：按用户指令更新特定页面的特定字段/内容
3. 写正向链接时同步写反向链接

### STEP 3: 更新导航

1. `EDIT wiki/index.md`：更新相关条目
2. `APPEND wiki/log.md`：`## [{date}] update | {description}`

### STEP 4: 报告

- 列出变更内容
- 提示后续操作（如需要 ingest 新增的 raw sources）

## 约束

- `raw/` 只读（本 skill 可以往 `raw/` 添加文件，但不修改已有文件）
- wiki 修改遵循模板结构
- 双向链接同步维护
