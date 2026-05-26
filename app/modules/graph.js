// Graph view: interactive Cytoscape canvas of wiki/graph/edges.jsonl +
// citations.jsonl, with sidebar (filters / BFS / search).
//
// Lifted from the original tools/visualize.py:_build_html_template
// (Phase 6 retirement of generate-html). Adapted for SPA:
// - data fetched from /api/graph at viewGraph() time, not inline JSON
// - node titles taken from state.entitiesByType (already loaded at boot)
// - double-click navigates to #/reader/{type}/{slug} (was: obsidian:// URI)
// - cleanup on route change to avoid leaking Cytoscape instances

import cytoscape from "https://cdn.jsdelivr.net/npm/cytoscape@3.28.1/+esm";
import { getGraph } from "./api.js";
import { state } from "./state.js";
import {
  ENTITY_DIRS, ENTITY_LABEL,
  EDGE_WORKFLOW_COLORS, EDGE_TYPE_WORKFLOW,
  EDGE_CATEGORY_GROUPS, EDGE_PRESETS, workflowFor,
} from "./schema.js";

// Entity hex colors. MUST stay in sync with config/visualize.json's
// entity_colors block — both the SPA and tools/visualize.py read those
// colors. Future cleanup: serve config/visualize.json from a /api/visualize-
// config endpoint and drop this local copy. For now, paste-sync.
//
// Trio (papers / concepts / methods) is tuned for high mutual hue contrast:
// blue 210° + magenta 335° + lime 90° ≈ 120° apart pairwise on the wheel,
// so the 3 most-frequent entity types are immediately distinguishable.
const ENTITY_HEX = Object.freeze({
  papers: "#4A90D9",      // sky blue
  concepts: "#EC4899",    // vivid magenta (was slate-purple #7B68EE)
  topics: "#E67E22",      // warm orange
  people: "#2ECC71",      // emerald
  ideas: "#F39C12",       // amber
  experiments: "#E74C3C", // red
  methods: "#84CC16",     // lime green
  Summary: "#1ABC9C",     // teal
  foundations: "#95A5A6", // gray
});

// Module-scoped Cytoscape instance — destroyed before re-init on each
// re-entry to viewGraph() so we don't leak listeners / RAF callbacks when
// the user navigates between Graph and other views repeatedly.
let currentCy = null;
let bfsHighlighted = null;
let currentSchema = null;   // payload.schema from /api/graph (live edge metadata)
let pathState = { start: null, end: null, highlighted: false };
let hideLowConfidence = true;  // sidebar toggle, default ON
let alwaysShowLabels = false;  // sidebar toggle: bypass zoom-aware hiding

// Label visibility heuristic: don't render labels until the user zooms in
// past LABEL_ZOOM_THRESHOLD. Combined with "highlight on hover" this prevents
// 50+ overlapping labels in the default zoomed-out view. User can force
// labels via the "Always show labels" sidebar toggle.
const LABEL_ZOOM_THRESHOLD = 0.9;
const LABEL_MAX_CHARS = 30;

export async function viewGraph(mount) {
  // tear down previous instance (if any) before swapping DOM
  destroyGraph();

  mount.innerHTML = `
    <div class="graph-shell">
      <aside class="graph-sidebar">
        <h3>Graph</h3>
        <input type="search" id="graph-search" placeholder="Search nodes&hellip;" autocomplete="off">
        <div id="graph-search-results"></div>

        <h4>Preset views</h4>
        <div id="graph-presets" class="graph-presets"></div>

        <h4>Entity types</h4>
        <div id="graph-entity-filters" class="filter-group"></div>

        <h4>Edge types</h4>
        <div id="graph-edge-filters" class="filter-group"></div>

        <h4>Display options</h4>
        <label class="filter-toggle">
          <input type="checkbox" id="graph-toggle-low-conf" checked>
          Hide low-confidence edges
        </label>
        <label class="filter-toggle">
          <input type="checkbox" id="graph-toggle-labels">
          Always show labels (slow on large graphs)
        </label>

        <h4>BFS depth</h4>
        <div class="bfs-controls">
          <input type="number" id="graph-bfs-depth" value="2" min="1" max="5">
          <button type="button" id="graph-bfs-clear">Clear</button>
        </div>

        <h4>Path query</h4>
        <div id="graph-path-controls" class="bfs-controls">
          <span class="small muted" id="graph-path-status">Right-click two nodes</span>
          <button type="button" id="graph-path-clear">Reset</button>
        </div>

        <p class="muted graph-stats" id="graph-stats">loading&hellip;</p>
        <p class="muted small">Left-click: BFS highlight. Right-click: set path start/end. Dbl-click: open in Reader.</p>
      </aside>
      <div id="cy" class="cy-canvas"></div>
      <aside class="graph-info" id="graph-info" hidden>
        <h4 id="info-title"></h4>
        <p id="info-meta"></p>
      </aside>
    </div>
  `;

  let payload;
  try {
    payload = await getGraph();
  } catch (err) {
    document.getElementById("cy").innerHTML =
      `<div class="graph-empty">Failed to load /api/graph: ${escapeHtml(err.message)}</div>`;
    return;
  }
  currentSchema = payload.schema || null;
  pathState = { start: null, end: null, highlighted: false };
  hideLowConfidence = true;

  const allEdges = [...(payload.edges || []), ...(payload.citations || [])];
  if (allEdges.length === 0) {
    document.getElementById("cy").innerHTML =
      `<div class="graph-empty">No graph data yet — run <code>/ingest</code> first.</div>`;
    return;
  }

  const graph = buildGraph(allEdges);
  initCy(graph);
  buildFilters(graph);
  buildPresets(graph);
  setupSearch();

  document.getElementById("graph-bfs-clear").addEventListener("click", clearHighlight);
  document.getElementById("graph-path-clear").addEventListener("click", clearPathQuery);
  document.getElementById("graph-toggle-low-conf").addEventListener("change", (e) => {
    hideLowConfidence = e.target.checked;
    applyLowConfidenceVisibility();
  });
  document.getElementById("graph-toggle-labels").addEventListener("change", (e) => {
    alwaysShowLabels = e.target.checked;
    applyLabelVisibility();
  });
  applyLowConfidenceVisibility();
  applyLabelVisibility();

  document.getElementById("graph-stats").textContent =
    `${graph.nodes.length} nodes · ${graph.edges.length} edges`;
}

export function destroyGraph() {
  if (currentCy) {
    try { currentCy.destroy(); } catch { /* ignore */ }
    currentCy = null;
  }
  bfsHighlighted = null;
}

// --- Build Cytoscape data --------------------------------------------------

function buildGraph(allEdges) {
  // Title lookup from boot-time state (no per-render API roundtrip).
  const titles = new Map();
  for (const t of ENTITY_DIRS) {
    for (const e of state.entitiesByType[t] || []) {
      titles.set(`${t}/${e.slug}`, e.title || e.name || e.slug);
    }
  }

  const nodeSet = new Set();
  for (const e of allEdges) {
    if (e.from) nodeSet.add(e.from);
    if (e.to) nodeSet.add(e.to);
  }

  const nodes = Array.from(nodeSet).map((id) => {
    const [type, ...rest] = id.split("/");
    const slug = rest.join("/");
    const fullLabel = titles.get(id) || slug || id;
    return {
      data: {
        id,
        label: truncateLabel(fullLabel),
        labelFull: fullLabel,
        entity: type,
        slug,
        fullId: id,
      },
      classes: type,
    };
  });

  const edgeTypes = new Set();
  const edges = allEdges.map((e, i) => {
    const t = e.type || "ref";
    edgeTypes.add(t);
    const wf = workflowFor(t);
    const isFm = e.source === "frontmatter" || t.startsWith("fm_");
    const direction = directionFor(t);
    const conf = (e.confidence || "").toLowerCase();
    const classList = [
      cssSafe(t),
      `wf-${cssSafe(wf)}`,
      `dir-${direction}`,
      isFm ? "fm" : "",
      conf ? `conf-${conf}` : "",
    ].filter(Boolean);
    return {
      data: {
        id: `e${i}`,
        source: e.from,
        target: e.to,
        label: t,
        workflow: wf,
        sourceKind: e.source || (isFm ? "frontmatter" : "edges.jsonl"),
        field: e.field || "",
        evidence: e.evidence || "",
        confidence: conf,
        direction,
        symmetric: direction === "symmetric" || !!e.symmetric,
      },
      classes: classList.join(" "),
    };
  });

  return { nodes, edges, edgeTypes: Array.from(edgeTypes) };
}

function directionFor(edgeType) {
  if (currentSchema?.edge_types?.[edgeType]?.direction) {
    return currentSchema.edge_types[edgeType].direction;
  }
  // Frontmatter projections are intrinsically directional from the frontmatter
  // field owner to its target.
  if (typeof edgeType === "string" && edgeType.startsWith("fm_")) return "directed";
  return "directed";
}

// --- Force layout (ported from visualize.py:obsidianForceLayout) -----------

function obsidianForceLayout(graph, container) {
  const W = container.clientWidth || 1000;
  const H = container.clientHeight || 600;
  const nodes = graph.nodes.map((n, i) => {
    const angle = (i / graph.nodes.length) * Math.PI * 2;
    const r = 200 + Math.random() * 100;
    return {
      id: n.data.id,
      x: W / 2 + Math.cos(angle) * r + (Math.random() - 0.5) * 80,
      y: H / 2 + Math.sin(angle) * r + (Math.random() - 0.5) * 80,
      vx: 0, vy: 0, degree: 0, entity: n.data.entity,
    };
  });
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const edgeList = graph.edges
    .map((e) => ({ source: nodeMap.get(e.data.source), target: nodeMap.get(e.data.target) }))
    .filter((e) => e.source && e.target);
  edgeList.forEach((e) => { e.source.degree++; e.target.degree++; });

  // Tuned for label legibility: many node titles run 30-60 chars (e.g.
  // "training-language-models-follow-instructions-human"). Stronger
  // repulsion + longer rest length + larger collision pad keep adjacent
  // labels from overlapping. Center gravity is dialed down so spread
  // dominates over centering.
  //
  // Density-aware: scale repulsion + link distance up when there are more
  // nodes so the graph naturally spreads to fill the canvas. Keeps small
  // graphs compact while preventing 50+ node crowding.
  const N = nodes.length;
  const densityScale = Math.min(2.2, 1 + Math.sqrt(Math.max(0, N - 20)) * 0.12);
  const REPULSION = 16000 * densityScale;
  const LINK_STRENGTH = 0.003;
  const LINK_DISTANCE = 320 * densityScale;
  const GRAVITY = 0.010;
  const DAMPING = 0.85;
  const COLLISION_PAD = 28;
  const CENTER_X = W / 2, CENTER_Y = H / 2;
  const MAX_SPEED = 40;
  const ITERS = 1200;

  const baseRadius = (n) => Math.min(4 + Math.sqrt(n.degree) * 4, 20);

  function tick() {
    const n = nodes.length;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
        const d = Math.sqrt(d2);
        const f = REPULSION / d2;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
      }
    }
    for (const e of edgeList) {
      let dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (d - LINK_DISTANCE) * LINK_STRENGTH;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      e.source.vx += fx; e.source.vy += fy;
      e.target.vx -= fx; e.target.vy -= fy;
    }
    for (const nd of nodes) {
      nd.vx += (CENTER_X - nd.x) * GRAVITY;
      nd.vy += (CENTER_Y - nd.y) * GRAVITY;
    }
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = nodes[i], b = nodes[j];
        const minDist = baseRadius(a) + baseRadius(b) + COLLISION_PAD;
        let dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        if (d < minDist) {
          const overlap = (minDist - d) / 2;
          const nx = dx / d, ny = dy / d;
          a.x -= nx * overlap; a.y -= ny * overlap;
          b.x += nx * overlap; b.y += ny * overlap;
        }
      }
    }
    for (const nd of nodes) {
      nd.vx *= DAMPING; nd.vy *= DAMPING;
      const sp = Math.sqrt(nd.vx * nd.vx + nd.vy * nd.vy);
      if (sp > MAX_SPEED) { nd.vx = (nd.vx / sp) * MAX_SPEED; nd.vy = (nd.vy / sp) * MAX_SPEED; }
      nd.x += nd.vx; nd.y += nd.vy;
    }
  }

  for (let i = 0; i < ITERS; i++) tick();

  const positions = {}, sizeMap = {};
  for (const nd of nodes) {
    positions[nd.id] = { x: nd.x, y: nd.y };
    const r = baseRadius(nd);
    sizeMap[nd.id] = { w: r * 2, h: r * 2, radius: r };
  }
  return { positions, sizeMap };
}

// --- Cytoscape init --------------------------------------------------------

function initCy(graph) {
  const container = document.getElementById("cy");
  const { positions, sizeMap } = obsidianForceLayout(graph, container);
  for (const n of graph.nodes) {
    const p = positions[n.data.id], s = sizeMap[n.data.id];
    if (p) n.position = { x: p.x, y: p.y };
    if (s) { n.data.nodeW = s.w; n.data.nodeH = s.h; n.data.baseRadius = s.radius; }
  }

  // Cytoscape parses style values as concrete colors, not as CSS variables,
  // so resolve light/dark scheme up front and feed it concrete colors.
  // This both fixes "labels are illegibly thick black blobs on light theme"
  // (was: 11px font + 2.5px outline = 5px total stroke per glyph) and the
  // contrast-inversion problem in dark theme.
  const isDark = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const labelColor = isDark ? "#e6e6f0" : "#1a1a2e";
  const labelOutline = isDark ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.85)";

  const labelBaseStyle = {
    label: "data(label)",
    "font-size": "10px",
    "font-weight": "normal",
    color: labelColor,
    "text-outline-color": labelOutline,
    "text-outline-width": 1,
    "text-valign": "bottom",
    "text-margin-y": 4,
  };

  // Resolve color tables: server-side schema in /api/graph wins; fallback to
  // local schema.js constants if absent.
  const wfColors = {
    ...EDGE_WORKFLOW_COLORS,
    ...(currentSchema?.edge_workflow_colors || {}),
  };
  const edgeColorFor = (et) => wfColors[edgeWorkflowFor(et)] || "#999";

  const style = [
    ...ENTITY_DIRS.map((et) => ({
      selector: "." + et,
      style: {
        "background-color": ENTITY_HEX[et] || "#999",
        label: "",
        width: "data(nodeW)",
        height: "data(nodeH)",
        "border-width": 1,
        "border-color": "rgba(127,127,127,0.18)",
        "overlay-opacity": 0,
      },
    })),
    { selector: "node:active", style: { "overlay-opacity": 0 } },
    ...graph.edgeTypes.map((et) => ({
      selector: "." + cssSafe(et),
      style: {
        "line-color": edgeColorFor(et),
        "target-arrow-color": edgeColorFor(et),
        // P2.6: arrows ONLY on directed edges. dir-directed selector below
        // turns them on; dir-symmetric leaves them off.
        "target-arrow-shape": "none",
        "curve-style": "bezier",
        width: 1.0,
        opacity: 0.55,
      },
    })),
    // P2.6: directed edges get a triangle arrowhead
    { selector: "edge.dir-directed", style: { "target-arrow-shape": "triangle" } },
    { selector: "edge.dir-symmetric", style: { "target-arrow-shape": "none" } },
    // P2.2: frontmatter projections render dashed + lighter
    {
      selector: "edge.fm",
      style: {
        "line-style": "dashed",
        opacity: 0.45,
        width: 0.9,
      },
    },
    // P2.5: confidence-based weighting (explicit edges only; fm has no confidence)
    { selector: "edge.conf-high",   style: { opacity: 0.95, width: 2.2 } },
    { selector: "edge.conf-medium", style: { opacity: 0.70, width: 1.5 } },
    { selector: "edge.conf-low",    style: { opacity: 0.40, width: 1.0 } },
    // Hover shows the FULL (untruncated) label — useful when the visible
    // node label is the 30-char ellipsized form.
    {
      selector: "node:hover",
      style: { ...labelBaseStyle, label: "data(labelFull)" },
    },
    // Zoom-aware label visibility: by default labels are hidden (entity
    // selectors set `label: ""`); when zoomed in past threshold, every node
    // gains class .show-label.
    { selector: "node.show-label", style: { ...labelBaseStyle } },
    {
      selector: "node.highlighted",
      style: {
        ...labelBaseStyle,
        "border-width": 2,
        "border-color": "#e94560",
        opacity: 1,
      },
    },
    // Path query endpoints
    {
      selector: "node.path-start",
      style: { ...labelBaseStyle, "border-width": 3, "border-color": "#22c55e" },
    },
    {
      selector: "node.path-end",
      style: { ...labelBaseStyle, "border-width": 3, "border-color": "#3b82f6" },
    },
    { selector: ".faded", style: { opacity: 0.08 } },
    { selector: "edge.highlighted", style: { opacity: 0.95, width: 2.5 } },
    { selector: "edge.faded", style: { opacity: 0.04 } },
    { selector: "edge.filtered-out", style: { display: "none" } },
    // P2.5: hide-low-confidence toggle
    { selector: "edge.hide-low", style: { display: "none" } },
  ];

  currentCy = cytoscape({
    container,
    elements: [...graph.nodes, ...graph.edges],
    style,
    layout: { name: "preset", positions: (n) => positions[n.id()] || { x: 0, y: 0 } },
    minZoom: 0.05,
    maxZoom: 8,
    wheelSensitivity: 0.3,
  });

  setTimeout(() => { try { currentCy.fit(currentCy.elements(), 60); } catch {} }, 50);

  currentCy.on("tap", "node", (evt) => {
    const node = evt.target;
    showNodeInfo(node);
    const depth = parseInt(document.getElementById("graph-bfs-depth").value, 10) || 2;
    highlightBFS(node.id(), depth);
  });
  currentCy.on("tap", (evt) => {
    if (evt.target === currentCy) {
      clearHighlight();
      const panel = document.getElementById("graph-info");
      if (panel) panel.hidden = true;
    }
  });
  // P2.4: right-click to set path-query start/end nodes
  currentCy.on("cxttap", "node", (evt) => {
    handlePathClick(evt.target.id());
  });
  // Hovering an edge shows source/field/confidence/evidence tooltip
  currentCy.on("mouseover", "edge", (evt) => showEdgeTooltip(evt.target, evt.renderedPosition));
  currentCy.on("mouseout", "edge", hideEdgeTooltip);
  // Re-evaluate label visibility on zoom so labels appear only when the user
  // has zoomed in enough to read them.
  currentCy.on("zoom", applyLabelVisibility);
  currentCy.on("dbltap", "node", (evt) => {
    // Phase-2 replacement for the original obsidian:// open: navigate
    // to the SPA Reader view for the same node.
    const id = evt.target.id();
    const [type, ...rest] = id.split("/");
    const slug = rest.join("/");
    if (type && slug) {
      location.hash = `#/reader/${type}/${encodeURIComponent(slug)}`;
    }
  });
}

// --- Sidebar widgets -------------------------------------------------------

function showNodeInfo(node) {
  const panel = document.getElementById("graph-info");
  document.getElementById("info-title").textContent =
    node.data("labelFull") || node.data("label");
  const entity = node.data("entity");
  const slug = node.data("slug");
  const dot = `<span class="dot" style="background:${ENTITY_HEX[entity] || "#999"}"></span>`;
  const link = `<a href="#/reader/${entity}/${escapeAttr(slug)}">open in reader →</a>`;
  document.getElementById("info-meta").innerHTML =
    `${dot} ${escapeHtml(entity)} / ${escapeHtml(slug)}<br>${link}`;
  panel.hidden = false;
}

function highlightBFS(nodeId, depth) {
  if (!currentCy) return;
  clearHighlight();
  const visited = new Set([nodeId]);
  let frontier = new Set([nodeId]);
  for (let d = 0; d < depth; d++) {
    const next = new Set();
    for (const nid of frontier) {
      currentCy.getElementById(nid).neighborhood("node").forEach((n) => {
        if (!visited.has(n.id())) { visited.add(n.id()); next.add(n.id()); }
      });
    }
    frontier = next;
  }
  const visitedEdges = new Set();
  currentCy.edges().forEach((e) => {
    if (visited.has(e.data("source")) && visited.has(e.data("target"))) {
      visitedEdges.add(e.id());
    }
  });
  bfsHighlighted = { nodes: visited, edges: visitedEdges };
  currentCy.elements().addClass("faded");
  for (const id of visited) currentCy.getElementById(id).removeClass("faded").addClass("highlighted");
  for (const id of visitedEdges) currentCy.getElementById(id).removeClass("faded").addClass("highlighted");
}

function clearHighlight() {
  if (!currentCy || !bfsHighlighted) return;
  currentCy.elements().removeClass("faded highlighted");
  bfsHighlighted = null;
}

function buildFilters(graph) {
  // Entity filters (unchanged — flat list with counts)
  const eDiv = document.getElementById("graph-entity-filters");
  for (const et of ENTITY_DIRS) {
    const count = graph.nodes.filter((n) => n.data.entity === et).length;
    if (count === 0) continue;
    const label = document.createElement("label");
    label.innerHTML =
      `<input type="checkbox" checked data-entity="${et}">` +
      `<span class="dot" style="background:${ENTITY_HEX[et] || "#999"}"></span>` +
      `${escapeHtml(ENTITY_LABEL[et] || et)} (${count})`;
    eDiv.appendChild(label);
  }
  eDiv.querySelectorAll("input").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (!currentCy) return;
      const e = cb.dataset.entity;
      currentCy.nodes("." + e).style("display", cb.checked ? "element" : "none");
    });
  });

  // Edge filters — grouped + collapsible (P2.1)
  const xDiv = document.getElementById("graph-edge-filters");
  const groups = currentSchema?.edge_category_groups || EDGE_CATEGORY_GROUPS;
  const wfColors = {
    ...EDGE_WORKFLOW_COLORS,
    ...(currentSchema?.edge_workflow_colors || {}),
  };

  // Count edges per type once
  const counts = new Map();
  for (const e of graph.edges) {
    const t = e.data.label;
    counts.set(t, (counts.get(t) || 0) + 1);
  }

  // Track which types are listed in any group, so we can collect leftovers
  // under "Other" without dropping them silently.
  const listedTypes = new Set();
  for (const types of Object.values(groups)) {
    for (const t of types) listedTypes.add(t);
  }
  const leftovers = graph.edgeTypes.filter((t) => !listedTypes.has(t));

  const renderGroup = (groupName, edgeTypes, openByDefault) => {
    // Only render groups that have at least one edge type present in current data
    const presentTypes = edgeTypes.filter((t) => counts.has(t));
    if (presentTypes.length === 0) return;

    const total = presentTypes.reduce((s, t) => s + counts.get(t), 0);
    const details = document.createElement("details");
    if (openByDefault) details.open = true;
    details.className = "edge-group";

    const summary = document.createElement("summary");
    summary.innerHTML =
      `<label class="group-summary" onclick="event.stopPropagation()">` +
      `<input type="checkbox" checked data-group="${escapeAttr(groupName)}">` +
      `<strong>${escapeHtml(groupName)}</strong> ` +
      `<span class="muted small">(${total})</span>` +
      `</label>`;
    details.appendChild(summary);

    for (const et of presentTypes.slice().sort()) {
      const wf = edgeWorkflowFor(et);
      const c = counts.get(et) || 0;
      const isFm = et.startsWith("fm_");
      const label = document.createElement("label");
      label.className = "edge-type-row";
      label.innerHTML =
        `<input type="checkbox" checked data-edge="${escapeAttr(et)}" ` +
                                       `data-group="${escapeAttr(groupName)}">` +
        `<span class="dot ${isFm ? "dot-dashed" : ""}" style="background:${wfColors[wf] || "#999"}"></span>` +
        `<span class="${isFm ? "small muted" : ""}">${escapeHtml(et)}</span>` +
        `<span class="muted small"> · ${c}</span>`;
      details.appendChild(label);
    }
    xDiv.appendChild(details);
  };

  // Render canonical groups first, then leftovers (e.g. an edge type added
  // by /ingest that isn't yet listed in config/visualize.json).
  const openByDefault = new Set([
    "Citations", "Paper relations", "Paper → Concept", "Method genealogy",
  ]);
  for (const [name, types] of Object.entries(groups)) {
    renderGroup(name, types, openByDefault.has(name));
  }
  if (leftovers.length > 0) {
    renderGroup("Other", leftovers, false);
  }

  // Per-type checkbox: show/hide that edge class
  xDiv.querySelectorAll("input[data-edge]").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (!currentCy) return;
      const t = cb.dataset.edge;
      setEdgeTypeVisible(t, cb.checked);
      // Reflect group state if all children agree
      syncGroupCheckbox(cb.dataset.group);
    });
  });

  // Group-level checkbox: toggle every child
  xDiv.querySelectorAll("input[data-group]:not([data-edge])").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (!currentCy) return;
      const group = cb.dataset.group;
      xDiv.querySelectorAll(`input[data-edge][data-group="${cssEscape(group)}"]`)
        .forEach((child) => {
          child.checked = cb.checked;
          const t = child.dataset.edge;
          setEdgeTypeVisible(t, cb.checked);
        });
    });
  });
}

function syncGroupCheckbox(groupName) {
  if (!groupName) return;
  const xDiv = document.getElementById("graph-edge-filters");
  const children = xDiv.querySelectorAll(
    `input[data-edge][data-group="${cssEscape(groupName)}"]`
  );
  const groupCb = xDiv.querySelector(
    `input[data-group="${cssEscape(groupName)}"]:not([data-edge])`
  );
  if (!groupCb || children.length === 0) return;
  const allOn = Array.from(children).every((c) => c.checked);
  const allOff = Array.from(children).every((c) => !c.checked);
  groupCb.checked = allOn;
  groupCb.indeterminate = !allOn && !allOff;
}

// P2.3: Preset views — clicking a button TOGGLES the categories it maps to.
// Multiple presets can be active at once; the resulting visible set is the
// union of their category lists.
function buildPresets(graph) {
  const div = document.getElementById("graph-presets");
  const labels = {
    "Citations": "📚 Citations", "Methods": "🔬 Methods",
    "Ideas": "💡 Ideas",         "People": "👥 People",
    "Concepts": "🎯 Concepts",   "All": "🌐 All",
  };
  const order = ["Citations", "Methods", "Ideas", "People", "Concepts", "All"];
  for (const key of order) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preset-btn";
    btn.dataset.preset = key;
    btn.textContent = labels[key];
    btn.addEventListener("click", () => applyPreset(key, btn));
    div.appendChild(btn);
  }
  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "preset-btn preset-reset";
  reset.textContent = "↺ All on";
  reset.addEventListener("click", () => resetAllEdges());
  div.appendChild(reset);
}

function applyPreset(presetKey, btn) {
  if (!currentCy) return;
  const categories = EDGE_PRESETS[presetKey];
  if (!categories) return;

  if (presetKey === "All") {
    resetAllEdges();
    document.querySelectorAll(".preset-btn").forEach(
      (b) => b.classList.remove("active")
    );
    return;
  }

  // Toggle on/off
  const active = btn.classList.toggle("active");
  const xDiv = document.getElementById("graph-edge-filters");

  // Build the union of all CURRENTLY-ACTIVE preset categories
  const activeBtns = document.querySelectorAll(".preset-btn.active");
  const wantCategories = new Set();
  for (const b of activeBtns) {
    for (const cat of EDGE_PRESETS[b.dataset.preset] || []) wantCategories.add(cat);
  }
  // If no preset is active after this click, reset to all-on
  if (wantCategories.size === 0) {
    resetAllEdges();
    return;
  }

  const groups = currentSchema?.edge_category_groups || EDGE_CATEGORY_GROUPS;
  const visibleTypes = new Set();
  for (const cat of wantCategories) {
    for (const t of groups[cat] || []) visibleTypes.add(t);
  }

  xDiv.querySelectorAll("input[data-edge]").forEach((cb) => {
    const t = cb.dataset.edge;
    const show = visibleTypes.has(t);
    cb.checked = show;
    setEdgeTypeVisible(t, show);
  });
  // Refresh group checkboxes
  xDiv.querySelectorAll("input[data-group]:not([data-edge])").forEach((cb) => {
    syncGroupCheckbox(cb.dataset.group);
  });
}

function resetAllEdges() {
  if (!currentCy) return;
  const xDiv = document.getElementById("graph-edge-filters");
  xDiv.querySelectorAll("input[data-edge]").forEach((cb) => {
    cb.checked = true;
    setEdgeTypeVisible(cb.dataset.edge, true);
  });
  xDiv.querySelectorAll("input[data-group]:not([data-edge])").forEach((cb) => {
    cb.checked = true; cb.indeterminate = false;
  });
  document.querySelectorAll(".preset-btn").forEach((b) => b.classList.remove("active"));
}

function edgeWorkflowFor(edgeType) {
  return currentSchema?.edge_types?.[edgeType]?.workflow || workflowFor(edgeType);
}

function setEdgeTypeVisible(edgeType, visible) {
  if (!currentCy || !edgeType) return;
  const edges = currentCy.edges("." + cssSafe(edgeType));
  // Remove old inline display bypasses from earlier filter operations so
  // stylesheet classes such as .hide-low can still take effect.
  edges.removeStyle("display");
  edges.toggleClass("filtered-out", !visible);
}

// P2.5: hide-low-confidence toggle handler
function applyLowConfidenceVisibility() {
  if (!currentCy) return;
  if (hideLowConfidence) {
    currentCy.edges(".conf-low").addClass("hide-low");
  } else {
    currentCy.edges(".conf-low").removeClass("hide-low");
  }
}

// Zoom-aware label visibility: hide labels at low zoom to declutter the
// default view; show all when zoomed in. "Always show labels" toggle
// bypasses the zoom rule.
function applyLabelVisibility() {
  if (!currentCy) return;
  const showAll = alwaysShowLabels || currentCy.zoom() >= LABEL_ZOOM_THRESHOLD;
  if (showAll) {
    currentCy.nodes().addClass("show-label");
  } else {
    currentCy.nodes().removeClass("show-label");
  }
}

function truncateLabel(s) {
  const str = String(s || "");
  if (str.length <= LABEL_MAX_CHARS) return str;
  return str.slice(0, LABEL_MAX_CHARS - 1) + "…";
}

// ---------------------------------------------------------------------------
// P2.4: Two-node path query (right-click → set start/end → highlight paths)
// ---------------------------------------------------------------------------

function handlePathClick(nodeId) {
  if (!pathState.start) {
    pathState.start = nodeId;
    updatePathStatus(`Start: ${shortId(nodeId)}. Right-click another node for end.`);
    refreshPathHighlight();
    return;
  }
  if (!pathState.end && nodeId !== pathState.start) {
    pathState.end = nodeId;
    updatePathStatus(`Computing paths between ${shortId(pathState.start)} and ${shortId(nodeId)}…`);
    refreshPathHighlight();
    computeAndHighlightPaths(pathState.start, pathState.end);
    return;
  }
  // Both set already — clicking again replaces start with the new node
  pathState.start = nodeId;
  pathState.end = null;
  updatePathStatus(`Start: ${shortId(nodeId)}. Right-click another node for end.`);
  clearPathHighlight();
  refreshPathHighlight();
}

function clearPathQuery() {
  pathState = { start: null, end: null, highlighted: false };
  clearPathHighlight();
  refreshPathHighlight();
  updatePathStatus("Right-click two nodes");
}

function refreshPathHighlight() {
  if (!currentCy) return;
  currentCy.nodes().removeClass("path-start path-end");
  if (pathState.start) {
    const n = currentCy.getElementById(pathState.start);
    if (n.length) n.addClass("path-start");
  }
  if (pathState.end) {
    const n = currentCy.getElementById(pathState.end);
    if (n.length) n.addClass("path-end");
  }
}

function clearPathHighlight() {
  if (!currentCy || !pathState.highlighted) return;
  currentCy.elements().removeClass("faded highlighted");
  pathState.highlighted = false;
}

function computeAndHighlightPaths(startId, endId) {
  if (!currentCy) return;
  // Treat graph as undirected for path finding. Cap depth and result count.
  const MAX_DEPTH = 4;
  const MAX_PATHS = 20;
  const adjacency = new Map();
  currentCy.edges().forEach((e) => {
    if (e.style("display") === "none") return; // respect current filters
    const s = e.data("source"), t = e.data("target");
    if (!adjacency.has(s)) adjacency.set(s, new Set());
    if (!adjacency.has(t)) adjacency.set(t, new Set());
    adjacency.get(s).add(t);
    adjacency.get(t).add(s);
  });

  const paths = [];
  const stack = [{ node: startId, path: [startId], visited: new Set([startId]) }];
  while (stack.length && paths.length < MAX_PATHS) {
    const cur = stack.pop();
    if (cur.path.length > MAX_DEPTH + 1) continue;
    const nexts = adjacency.get(cur.node) || new Set();
    for (const n of nexts) {
      if (n === endId) {
        paths.push([...cur.path, n]);
        if (paths.length >= MAX_PATHS) break;
        continue;
      }
      if (cur.visited.has(n)) continue;
      const newVisited = new Set(cur.visited);
      newVisited.add(n);
      stack.push({ node: n, path: [...cur.path, n], visited: newVisited });
    }
  }

  if (paths.length === 0) {
    updatePathStatus(`No path within depth ${MAX_DEPTH} between selected nodes.`);
    return;
  }

  const nodesOnPath = new Set();
  for (const p of paths) for (const n of p) nodesOnPath.add(n);

  const edgesOnPath = new Set();
  currentCy.edges().forEach((e) => {
    const s = e.data("source"), t = e.data("target");
    for (const p of paths) {
      for (let i = 0; i < p.length - 1; i++) {
        if ((p[i] === s && p[i+1] === t) || (p[i] === t && p[i+1] === s)) {
          edgesOnPath.add(e.id());
        }
      }
    }
  });

  currentCy.elements().addClass("faded");
  for (const nid of nodesOnPath) currentCy.getElementById(nid).removeClass("faded").addClass("highlighted");
  for (const eid of edgesOnPath) currentCy.getElementById(eid).removeClass("faded").addClass("highlighted");
  pathState.highlighted = true;
  refreshPathHighlight();
  updatePathStatus(`${paths.length} path${paths.length === 1 ? "" : "s"} between selected (≤${MAX_DEPTH} hops).`);
}

function updatePathStatus(msg) {
  const el = document.getElementById("graph-path-status");
  if (el) el.textContent = msg;
}

function shortId(id) {
  const [_kind, ...rest] = id.split("/");
  const slug = rest.join("/");
  return slug.length > 24 ? slug.slice(0, 22) + "…" : slug;
}

// ---------------------------------------------------------------------------
// Edge tooltip on hover (shows source / field / evidence / confidence)
// ---------------------------------------------------------------------------

let edgeTooltip = null;
function showEdgeTooltip(edge, _pos) {
  hideEdgeTooltip();
  const d = edge.data();
  const parts = [
    `<strong>${escapeHtml(d.label)}</strong>`,
    `<span class="small">source: ${escapeHtml(d.sourceKind || "")}</span>`,
  ];
  if (d.field) parts.push(`<span class="small">field: ${escapeHtml(d.field)}</span>`);
  if (d.confidence) parts.push(`<span class="small">confidence: ${escapeHtml(d.confidence)}</span>`);
  if (d.evidence) {
    const short = d.evidence.length > 200 ? d.evidence.slice(0, 198) + "…" : d.evidence;
    parts.push(`<span class="small">${escapeHtml(short)}</span>`);
  }
  edgeTooltip = document.createElement("div");
  edgeTooltip.className = "edge-tooltip";
  edgeTooltip.innerHTML = parts.join("<br>");
  document.body.appendChild(edgeTooltip);
  const move = (e) => {
    if (!edgeTooltip) return;
    edgeTooltip.style.left = (e.clientX + 12) + "px";
    edgeTooltip.style.top = (e.clientY + 12) + "px";
  };
  edgeTooltip._move = move;
  document.addEventListener("mousemove", move);
}
function hideEdgeTooltip() {
  if (!edgeTooltip) return;
  if (edgeTooltip._move) document.removeEventListener("mousemove", edgeTooltip._move);
  edgeTooltip.remove();
  edgeTooltip = null;
}

function setupSearch() {
  const input = document.getElementById("graph-search");
  const results = document.getElementById("graph-search-results");
  input.addEventListener("input", () => {
    const q = input.value.toLowerCase().trim();
    results.innerHTML = "";
    if (!q || !currentCy) return;
    const matches = currentCy.nodes().filter((n) => {
      const label = String(n.data("label") || "").toLowerCase();
      const id = String(n.data("fullId") || "").toLowerCase();
      return label.includes(q) || id.includes(q);
    }).slice(0, 20);
    matches.forEach((node) => {
      const div = document.createElement("div");
      div.className = "search-item";
      div.innerHTML =
        `<span class="dot" style="background:${ENTITY_HEX[node.data("entity")] || "#999"}"></span>` +
        `${escapeHtml(node.data("label"))}`;
      div.addEventListener("click", () => {
        currentCy.animate({ center: { eles: node }, zoom: 2 });
        const depth = parseInt(document.getElementById("graph-bfs-depth").value, 10) || 2;
        highlightBFS(node.id(), depth);
        showNodeInfo(node);
      });
      results.appendChild(div);
    });
  });
}

// --- helpers ----------------------------------------------------------------

function cssSafe(s) {
  return String(s).replace(/[^a-zA-Z0-9_-]/g, "_");
}

// CSS.escape polyfill — needed for category names with spaces/arrows in
// querySelector selectors. Old browsers may lack it.
function cssEscape(s) {
  if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(String(s));
  return String(s).replace(/[^a-zA-Z0-9_-]/g, (c) =>
    "\\" + c.codePointAt(0).toString(16) + " "
  );
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function escapeAttr(s) {
  return escapeHtml(s);
}
