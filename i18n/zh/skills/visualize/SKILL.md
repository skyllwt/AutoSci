---
description: 生成并更新可视化产物 —— Obsidian 图谱配置与 Canvas 知识地图。交互式网页图谱视图位于 SPA 的 app/modules/graph.js（由 tools/serve.py 提供服务）。
argument-hint: [--obsidian] [--canvas] [--focus <node_id>] [--depth N] [--types <page-type,...>] [--edge-types <edge-type,...>] [--all]
---

# /visualize

> 为 OmegaWiki 知识图谱生成可视化产物。
> 产出 Obsidian 图谱配置（按实体类型分色组）以及带类型标签边的精选 Canvas 视图。
> 交互式网页探索请使用 SPA 的 Graph 视图（先跑 `tools/serve.py`，然后访问 `#/graph`）。

## Inputs

- `--obsidian`（可选）：生成或更新 `.obsidian/graph.json`，按实体类型分色组
- `--canvas`（可选）：基于图谱数据生成 Obsidian Canvas（`.canvas`），边带类型标签
- `--focus <node_id>`（可选）：把 Canvas 聚焦到某个具体节点（例如 `methods/my-method`）
- `--depth N`（可选）：聚焦 Canvas 的 BFS 深度（默认：2）
- `--types <list>`（可选）：把节点过滤到这些 page type，逗号分隔（例如 `papers,concepts`）
- `--edge-types <list>`（可选）：把边过滤到这些语义类型，逗号分隔（例如 `builds_on,challenges`）
- `--all`（可选，没传任何 flag 时即默认）：生成全部可视化产物

## Outputs

- `wiki/.obsidian/graph.json` —— Obsidian 图谱颜色配置（按实体类型分色组）
- `wiki/.obsidian/app.json` —— Obsidian 应用设置（仅当不存在时才创建）
- `wiki/canvases/knowledge-map.canvas` —— 完整知识地图 Canvas，边带标签
- `wiki/canvases/idea-evidence.canvas` —— 以 idea 为中心的子图 Canvas
- `wiki/canvases/focus-{node-id}.canvas` —— 聚焦 Canvas（使用 `--focus` 时）
- 终端输出：Obsidian 插件推荐与设置说明

独立 HTML 探索器（`wiki/graph-view.html`）已停产；同样的用法由 SPA Graph 视图（`app/modules/graph.js`，由 `tools/serve.py` 提供服务）覆盖，且与前端其余部分共用同一份代码库。

## Wiki Interaction

### Reads

- `wiki/graph/edges.jsonl` —— 带类型的语义边
- `wiki/graph/citations.jsonl` —— 论文引用
- `wiki/*/` —— 全部 entity 目录的 frontmatter
- `config/visualize.json` —— 颜色调色板与可视化偏好

### Writes

- `wiki/.obsidian/graph.json` —— CREATE/OVERWRITE（本地产物，已 gitignore；每次都从 `config/visualize.json` 重生成）
- `wiki/.obsidian/app.json` —— 仅在不存在时 CREATE（不覆盖用户自定义；已 gitignore）
- `wiki/canvases/*.canvas` —— CREATE/OVERWRITE（本地产物，已 gitignore）

## Workflow

**前置条件**：确认当前工作目录是 wiki 项目根（包含 `wiki/`、`raw/`、`tools/`）。
设 `WIKI_ROOT=wiki/`。

### Step 0: 确认图谱数据存在

检查 `wiki/graph/edges.jsonl` 存在且非空。若为空，提示尚无图谱数据，建议先运行 `/ingest`。

### Step 1: 生成 Obsidian 配置（`--obsidian` 或 `--all`）

```bash
python3 tools/visualize.py generate-obsidian-config wiki/
```

创建 `.obsidian/graph.json`，包含 9 类实体的色组，使用 `path:{entity_type}` 形式的查询。
`.obsidian/app.json` 仅在不存在时才创建。

### Step 2: 生成 Canvas 视图（`--canvas` 或 `--all`）

#### Step 2a —— 完整知识地图

```bash
python3 tools/visualize.py generate-canvas wiki/
```

布局：力导（无固定中心）。节点先按 entity type 聚类初始化位置，然后用 spring–electron 模拟稳定下来。

#### Step 2b —— 聚焦 Canvas

**生成前先决定 focus 节点：**

1. 若用户显式传了 `--focus <node_id>`，直接使用，跳过下面步骤。
2. 否则枚举 foundation 页：`ls wiki/foundations/*.md`（排除 `.gitkeep`）。
   - **0 个**：跳过 Step 2b，不生成聚焦 Canvas，只输出 Step 2a 的完整知识地图。
   - **1 个**：自动用该 foundation 作为 `--focus`（即 `foundations/<slug>`），打印选择，**不弹问**。
   - **2 个及以上**：用 `AskUserQuestion` 让用户挑一个。每个 foundation 列为一个选项（label = `foundations/<slug>`，description = 该页 frontmatter 的 `title`）。把用户选的 slug 作为 `--focus`。

然后生成：

```bash
python3 tools/visualize.py generate-canvas wiki/ --focus <node_id> --depth <N>
```

布局：径向同心圆。focus 节点位于画布中心；距离 focus BFS 距离 `d` 的节点落在第 `d` 环。每环内按 entity type 排序，同类节点在圆上聚团。

**`--focus` BFS 逻辑**：从目标节点开始，在 `edges.jsonl` + `citations.jsonl` 上做广度优先搜索，收集 `--depth` 跳之内的全部节点和边。只渲染该邻域子图。若 `node_id` 找不到，中止并列出 5 个最相近的 slug 候选。

Canvas 节点 schema：

```json
{
  "id": "<slug>",
  "type": "file",
  "file": "<relative-path-to-md>",
  "label": "<frontmatter title>",
  "x": <int>,
  "y": <int>,
  "width": <int，papers 按 importance 缩放>,
  "height": <int，papers 按 importance 缩放>,
  "color": "<obsidian-color-id>"
}
```

`label` 字段覆盖显示名；旧版 Obsidian 不支持时会 fallback 到文件名（slug）。width/height 基础尺寸按 entity type 决定；papers 按 importance 缩放（1→0.7×、2→0.85×、3→1.0×、4→1.2×、5→1.5×，缺失时默认 3）。

Canvas 边 schema：

```json
{
  "id": "<source>-<target>-<edge-type>",
  "fromNode": "<slug>",
  "toNode": "<slug>",
  "label": "<edge-type>"
}
```

若设置了 `--types`，丢弃不在列表里的节点，并丢弃 source 或 target 已被丢弃的边。
若设置了 `--edge-types`，丢弃不在列表里的边。

### Step 3: SPA Graph 视图（后台自动启动）

之前的独立 HTML 探索器已停产。如需交互式网页探索，本 skill **自动**在后台启动 SPA 后端（`tools/serve.py`）—— 用户**不需要**手动跑 `python tools/serve.py`。

**自动启动逻辑：**

1. 探测 8765 端口，看服务是否已经在跑：

   ```bash
   python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.3); sys.exit(0 if s.connect_ex(('127.0.0.1',8765))==0 else 1)"
   ```

   退出码 `0` = 端口被占（服务已起 —— 跳过启动）。退出码 `1` = 端口空闲（需要启动）。

2. 若端口空闲，用 **`Bash` tool 的 `run_in_background: true`** 后台启动（不要前台，前台会无限阻塞 skill）：

   ```bash
   python3 tools/serve.py
   ```

   不要用 `Agent` subagent 包裹 —— agent 不适合长跑服务，且 agent 返回时服务可能跟着挂掉。后台 `Bash` 进程归 Claude Code 会话所有，活到会话结束。

3. 把 URL 打印给用户：

   ```
   SPA Graph view: http://127.0.0.1:8765/#/graph
   ```

SPA Graph 视图（`app/modules/graph.js`）是真正的 ES module，包含与原单文件生成器一样的 Cytoscape + 力导向布局 + 过滤器 + BFS 搜索，并集成了双击跳转到 SPA Reader 视图的能力。`/visualize` 不再重新生成 `wiki/graph-view.html`。

### Step 4: 打印推荐

```bash
python3 tools/visualize.py list-recommendations
```

打印推荐的 Obsidian 插件（Graph Analysis、Dataview、Excalidraw）以及配置说明。

### Step 5: 日志

```bash
python3 tools/research_wiki.py log wiki/ "visualize | generated: [产物列表]"
```

标准日志格式：

```markdown
## [YYYY-MM-DD] /visualize | <format> — <n> nodes, <m> edges<focus-note>
```

`<focus-note>` 在使用 `--focus` 时为 ` (focus: <node_id>, depth <N>)`，否则为空。

## Color Palette

### 节点颜色（按 page_type）

| page_type     | HTML hex  | Obsidian color ID |
| ------------- | --------- | ----------------- |
| `papers`      | `#4C9BE8` | `"1"`             |
| `concepts`    | `#F4A261` | `"2"`             |
| `topics`      | `#2A9D8F` | `"3"`             |
| `people`      | `#E76F51` | `"4"`             |
| `ideas`       | `#A8DADC` | `"5"`             |
| `experiments` | `#9B5DE5` | `"6"`             |
| `methods`     | `#84CC16` | `"3"`             |
| `Summary`     | `#90BE6D` | `"4"`             |
| `foundations` | `#B5B5B5` | `"6"`             |

### 边颜色（HTML 模式，按语义类别）

| 类别        | 类型                                                                  | Hex       |
| ----------- | --------------------------------------------------------------------- | --------- |
| 相似        | `same_problem_as`、`similar_method_to`                                | `#ADB5BD` |
| 谱系        | `builds_on`、`extends_concept`、`derived_from`、`inspired_by`         | `#4C9BE8` |
| 比较        | `challenges`、`critiques_concept`                                     | `#E76F51` |
| 概念使用    | `introduces_concept`、`uses_concept`                                  | `#F4A261` |
| 证据        | `supports`、`contradicts`、`tested_by`、`invalidates`                 | `#9B5DE5` |
| Gap         | `addresses_gap`                                                       | `#F9C74F` |
| Citation    | `cites`                                                               | `#B5B5B5` |

## Constraints

- 不要手动改 `wiki/graph/` —— 只读
- `config/visualize.json` 是用户拥有的 —— 不要覆盖
- `.obsidian/app.json` 仅在缺失时创建（尊重用户自定义）
- Canvas 文件每次运行重生成（幂等覆盖）
- 不依赖外部 Python 包（仅用 stdlib）
- `wiki/.obsidian/` 与 `wiki/canvases/` 都是已 gitignore 的本地产物；source of truth 是 `config/visualize.json` + `wiki/graph/`。`/init` Step 6 与直接调用 `/visualize` 都会幂等地重生成它们 —— 永远不要 commit 它们。

## Error Handling

- **没有图谱数据**：提醒用户先跑 `/ingest` 建立知识库
- **`config/visualize.json` 缺失**：报错，文件应当存在于 `config/visualize.json`
- **`--focus` 节点找不到**：中止并打印 `Error: node "<node_id>" not found`；列出 5 个最相近的 slug 候选
- **过滤后没有节点**：中止并汇总当前过滤器与可用类型
- **Canvas 节点超过 500 个**：警告大型 Canvas 可能很慢；建议用 `--focus` 或 `--types` 缩小范围
- **entity 目录缺失**：静默跳过，只处理存在的目录
- **JSONL 行格式不正确**：静默跳过，继续处理后续行
- **`wiki/canvases/` 不存在**：写入前先创建目录

## Dependencies

### Tools（via Bash）

- `python3 tools/visualize.py generate-obsidian-config wiki/` —— Obsidian 配置
- `python3 tools/visualize.py generate-canvas wiki/ [--focus <node_id>] [--depth N]` —— Canvas 生成
- `python3 tools/visualize.py list-recommendations` —— 插件推荐
- `python3 tools/research_wiki.py log wiki/ "<message>"` —— 追加日志
- `python3 tools/serve.py` —— 本地 SPA 服务器（Graph 视图位于 `#/graph`）
