---
description: Generate and update visualization artifacts — Obsidian graph config and Canvas knowledge maps. The interactive web graph view lives in the SPA at app/modules/graph.js (served by tools/serve.py).
argument-hint: [--obsidian] [--canvas] [--focus <node_id>] [--depth N] [--types <page-type,...>] [--edge-types <edge-type,...>] [--all]
---

# /visualize

> Generate visualization artifacts for the OmegaWiki knowledge graph.
> Produces Obsidian graph config (color groups by entity type) and curated
> Canvas views with labeled typed edges. For interactive web exploration
> use the SPA Graph view (`tools/serve.py`, then `#/graph`).

## Inputs

- `--obsidian` (optional): Generate/update `.obsidian/graph.json` with entity-type color groups
- `--canvas` (optional): Generate Obsidian Canvas (`.canvas`) from graph data with labeled edges
- `--focus <node_id>` (optional): Center canvas on a specific node (e.g., `methods/my-method`)
- `--depth N` (optional): BFS depth for focused canvas (default: 2)
- `--types <list>` (optional): Filter nodes to these page types, comma-separated (e.g., `papers,concepts`)
- `--edge-types <list>` (optional): Filter edges to these semantic types, comma-separated (e.g., `builds_on,challenges`)
- `--all` (optional, default if no flags): Generate all visualization artifacts

## Outputs

- `wiki/.obsidian/graph.json` — Obsidian graph color configuration (per-entity-type color groups)
- `wiki/.obsidian/app.json` — Obsidian app settings (only if not exists)
- `wiki/canvases/knowledge-map.canvas` — Full knowledge map Canvas with labeled edges
- `wiki/canvases/idea-evidence.canvas` — Idea-centric subgraph Canvas
- `wiki/canvases/focus-{node-id}.canvas` — Focused Canvas (when --focus is used)
- Console output: Obsidian plugin recommendations and setup instructions

The standalone-HTML explorer (`wiki/graph-view.html`) was retired; the
SPA Graph view at `app/modules/graph.js` (served by `tools/serve.py`)
covers the same use case and lives in the same codebase as the rest of
the frontend.

## Wiki Interaction

### Reads

- `wiki/graph/edges.jsonl` — typed semantic edges
- `wiki/graph/citations.jsonl` — bibliographic paper citations
- `wiki/*/` — all entity directories for page metadata (frontmatter)
- `config/visualize.json` — color palette and visualization preferences

### Writes

- `wiki/.obsidian/graph.json` — CREATE/OVERWRITE (local-only artifact, gitignored; regenerated each run from `config/visualize.json`)
- `wiki/.obsidian/app.json` — CREATE only (never overwrite user customizations; gitignored)
- `wiki/canvases/*.canvas` — CREATE/OVERWRITE (local-only artifact, gitignored)

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).
Set `WIKI_ROOT=wiki/`.

### Step 0: Verify graph data exists

Check that `wiki/graph/edges.jsonl` exists and is non-empty. If empty, report that no graph data
exists yet and suggest running `/ingest` first.

### Step 1: Generate Obsidian config (--obsidian or --all)

```bash
python3 tools/visualize.py generate-obsidian-config wiki/
```

Creates `.obsidian/graph.json` with 9 per-entity-type color groups using `path:{entity_type}` queries.
Creates `.obsidian/app.json` only if it does not already exist.

### Step 2: Generate Canvas views (--canvas or --all)

#### Step 2a — Full knowledge map

```bash
python3 tools/visualize.py generate-canvas wiki/
```

Layout: force-directed (no fixed center). Nodes are initially clustered by
entity type, then settled via a spring–electron simulation.

#### Step 2b — Focused canvas

**Resolve the focus node before generating:**

1. If the user passed `--focus <node_id>` explicitly, use it as-is. Skip the
   rest of this resolution.
2. Otherwise, enumerate foundation pages: `ls wiki/foundations/*.md` (excluding
   `.gitkeep`).
   - **0 files**: skip Step 2b entirely. No focused canvas is generated; only
     the full knowledge map from Step 2a is produced.
   - **1 file**: auto-select that foundation as `--focus` (e.g.
     `foundations/<slug>`). Print the choice to the console; do **not** prompt.
   - **2+ files**: ask the user via `AskUserQuestion` to pick one. List each
     foundation slug as an option (label = `foundations/<slug>`, description =
     the page's frontmatter `title`). Use the picked slug as `--focus`.

Then generate:

```bash
python3 tools/visualize.py generate-canvas wiki/ --focus <node_id> --depth <N>
```

Layout: radial concentric rings. The focus node sits at the canvas center;
nodes at BFS distance `d` from the focus occupy ring `d`. Within each ring,
nodes are sorted by entity type so same-type nodes cluster on the circle.

**`--focus` BFS logic**: starting from the target node, run breadth-first search over
`edges.jsonl` + `citations.jsonl`, collecting all nodes and edges within `--depth` hops.
Render only that neighbourhood subgraph. If `node_id` is not found, abort and list the
5 closest slug matches.

Canvas node schema:

```json
{
  "id": "<slug>",
  "type": "file",
  "file": "<relative-path-to-md>",
  "label": "<frontmatter title>",
  "x": <int>,
  "y": <int>,
  "width": <int, base size × importance scale for papers>,
  "height": <int, base size × importance scale for papers>,
  "color": "<obsidian-color-id>"
}
```

The `label` field overrides the displayed name; older Obsidian versions that
do not honour it fall back to the filename (slug). The width/height base is
per entity type; for papers the size is multiplied by an importance scale
(1→0.7×, 2→0.85×, 3→1.0×, 4→1.2×, 5→1.5×, default 3 when missing).

Canvas edge schema:

```json
{
  "id": "<source>-<target>-<edge-type>",
  "fromNode": "<slug>",
  "toNode": "<slug>",
  "label": "<edge-type>"
}
```

If `--types` is set, drop nodes not in the list and drop edges whose source or target was dropped.
If `--edge-types` is set, drop edges not in the list.

### Step 3: SPA Graph view (auto-started in background)

The previous standalone-HTML explorer was retired. For interactive web
exploration, the SPA backend (`tools/serve.py`) is started automatically
by this skill — the user does **not** need to run `python tools/serve.py`
manually.

**Auto-start logic:**

1. Probe port 8765 to check whether the server is already running:

   ```bash
   python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.3); sys.exit(0 if s.connect_ex(('127.0.0.1',8765))==0 else 1)"
   ```

   Exit code `0` = port in use (server already up — skip start). Exit code
   `1` = port free (need to start).

2. If the port is free, start the server in the background via the **`Bash`
   tool with `run_in_background: true`** (not foreground — foreground would
   block the skill indefinitely):

   ```bash
   python3 tools/serve.py
   ```

   Do not spawn an `Agent` subagent for this — agents are not designed for
   long-running services, and the server may die when the agent returns. The
   background `Bash` process is owned by the Claude Code session and lives
   for the session's lifetime.

3. Print the SPA URL to the user:

   ```
   SPA Graph view: http://127.0.0.1:8765/#/graph
   ```

The SPA Graph view (`app/modules/graph.js`) is a real ES module with
the same Cytoscape + force layout + filters + BFS search as the old
single-page generator, plus integrated double-click navigation to the
SPA Reader view. `/visualize` no longer regenerates `wiki/graph-view.html`.

### Step 4: Print recommendations

```bash
python3 tools/visualize.py list-recommendations
```

Prints recommended Obsidian plugins (Graph Analysis, Dataview, Excalidraw) and setup instructions.

### Step 5: Log

```bash
python3 tools/research_wiki.py log wiki/ "visualize | generated: [list of artifacts]"
```

Standard log format:

```markdown
## [YYYY-MM-DD] /visualize | <format> — <n> nodes, <m> edges<focus-note>
```

Where `<focus-note>` is ` (focus: <node_id>, depth <N>)` when `--focus` was used, or empty otherwise.

## Color Palette

### Node colors (by page_type)

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

### Edge colors (HTML mode, by semantic category)

| Category    | Types                                                                | Hex       |
| ----------- | -------------------------------------------------------------------- | --------- |
| Similarity  | `same_problem_as`, `similar_method_to`                               | `#ADB5BD` |
| Lineage     | `builds_on`, `extends_concept`, `derived_from`, `inspired_by`        | `#4C9BE8` |
| Comparison  | `challenges`, `critiques_concept`                                    | `#E76F51` |
| Concept use | `introduces_concept`, `uses_concept`                                 | `#F4A261` |
| Evidence    | `supports`, `contradicts`, `tested_by`, `invalidates`                | `#9B5DE5` |
| Gap         | `addresses_gap`                                                      | `#F9C74F` |
| Citation    | `cites`                                                              | `#B5B5B5` |

## Constraints

- Never edit `wiki/graph/` manually — only read from it
- `config/visualize.json` is user-owned — never overwrite it
- `.obsidian/app.json` is created only if missing (respect user customizations)
- Canvas files are regenerated on each run (idempotent overwrite)
- No external Python dependencies required (stdlib only)
- `wiki/.obsidian/` and `wiki/canvases/` are gitignored as local-only artifacts; the source of truth is `config/visualize.json` + `wiki/graph/`. `/init` Step 6 and direct `/visualize` invocations regenerate them deterministically — never commit them.

## Error Handling

- **No graph data**: inform user to run `/ingest` first to build the knowledge base
- **config/visualize.json missing**: report error, file should exist at `config/visualize.json`
- **--focus node not found**: abort with `Error: node "<node_id>" not found`; list 5 closest slug matches
- **No nodes after filtering**: abort with summary of filters applied and types available
- **Canvas > 500 nodes**: warn that large canvases may be slow; suggest `--focus` or `--types` to narrow scope
- **Entity directory missing**: skip silently, only process directories that exist
- **Malformed JSONL lines**: skip silently, continue processing remaining lines
- **wiki/canvases/ missing**: create directory before writing

## Dependencies

### Tools (via Bash)

- `python3 tools/visualize.py generate-obsidian-config wiki/` — Obsidian config
- `python3 tools/visualize.py generate-canvas wiki/ [--focus <node_id>] [--depth N]` — Canvas generation
- `python3 tools/visualize.py list-recommendations` — Plugin recommendations
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log entry
- `python3 tools/serve.py` — local SPA server (Graph view at `#/graph`)
