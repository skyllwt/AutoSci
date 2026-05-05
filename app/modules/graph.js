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

export async function viewGraph(mount) {
  // tear down previous instance (if any) before swapping DOM
  destroyGraph();

  mount.innerHTML = `
    <div class="graph-shell">
      <aside class="graph-sidebar">
        <h3>Graph</h3>
        <input type="search" id="graph-search" placeholder="Search nodes&hellip;" autocomplete="off">
        <div id="graph-search-results"></div>

        <h4>Entity types</h4>
        <div id="graph-entity-filters" class="filter-group"></div>

        <h4>Edge types</h4>
        <div id="graph-edge-filters" class="filter-group"></div>

        <h4>BFS depth</h4>
        <div class="bfs-controls">
          <input type="number" id="graph-bfs-depth" value="2" min="1" max="5">
          <button type="button" id="graph-bfs-clear">Clear</button>
        </div>

        <p class="muted graph-stats" id="graph-stats">loading&hellip;</p>
        <p class="muted small">Click: focus + BFS highlight. Dbl-click: open in Reader.</p>
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
  const allEdges = [...(payload.edges || []), ...(payload.citations || [])];
  if (allEdges.length === 0) {
    document.getElementById("cy").innerHTML =
      `<div class="graph-empty">No graph data yet — run <code>/ingest</code> first.</div>`;
    return;
  }

  const graph = buildGraph(allEdges);
  initCy(graph);
  buildFilters(graph);
  setupSearch();

  document.getElementById("graph-bfs-clear").addEventListener("click", clearHighlight);

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
    return {
      data: {
        id,
        label: titles.get(id) || slug || id,
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
    return {
      data: {
        id: `e${i}`,
        source: e.from,
        target: e.to,
        label: t,
        workflow: EDGE_TYPE_WORKFLOW[t] || "provenance",
        symmetric: !!e.symmetric,
      },
      classes: cssSafe(t),
    };
  });

  return { nodes, edges, edgeTypes: Array.from(edgeTypes) };
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
  const REPULSION = 12000;
  const LINK_STRENGTH = 0.003;
  const LINK_DISTANCE = 280;
  const GRAVITY = 0.012;
  const DAMPING = 0.85;
  const COLLISION_PAD = 18;
  const CENTER_X = W / 2, CENTER_Y = H / 2;
  const MAX_SPEED = 40;
  const ITERS = 800;

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
        "line-color": EDGE_WORKFLOW_COLORS[EDGE_TYPE_WORKFLOW[et]] || "#999",
        "target-arrow-color": EDGE_WORKFLOW_COLORS[EDGE_TYPE_WORKFLOW[et]] || "#999",
        "target-arrow-shape": "triangle",
        "curve-style": "haystack",
        width: 0.8,
        opacity: 0.35,
      },
    })),
    { selector: "node:hover", style: { ...labelBaseStyle } },
    {
      selector: "node.highlighted",
      style: {
        ...labelBaseStyle,
        "border-width": 2,
        "border-color": "#e94560",
        opacity: 1,
      },
    },
    { selector: ".faded", style: { opacity: 0.08 } },
    { selector: "edge.highlighted", style: { opacity: 0.9, width: 2 } },
    { selector: "edge.faded", style: { opacity: 0.04 } },
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
  document.getElementById("info-title").textContent = node.data("label");
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

  const xDiv = document.getElementById("graph-edge-filters");
  for (const et of graph.edgeTypes.slice().sort()) {
    const wf = EDGE_TYPE_WORKFLOW[et] || "provenance";
    const label = document.createElement("label");
    label.innerHTML =
      `<input type="checkbox" checked data-edge="${escapeAttr(et)}">` +
      `<span class="dot" style="background:${EDGE_WORKFLOW_COLORS[wf] || "#999"}"></span>` +
      `${escapeHtml(et)}`;
    xDiv.appendChild(label);
  }
  xDiv.querySelectorAll("input").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (!currentCy) return;
      const t = cb.dataset.edge;
      currentCy.edges("." + cssSafe(t)).style("display", cb.checked ? "element" : "none");
    });
  });
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

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function escapeAttr(s) {
  return escapeHtml(s);
}
