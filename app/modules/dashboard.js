// Dashboard view: research-lifecycle overview.
//
// Several widgets, each fed by one read endpoint or by state.entitiesByType
// (already loaded at boot). All charts are pure HTML/CSS — no chart lib.

import { marked } from "https://cdn.jsdelivr.net/npm/marked@14.1.4/lib/marked.esm.js";
import { getMaturity, getOpenQuestions, getLog, postRegenerate } from "./api.js";
import { state } from "./state.js";
import { triggerIntent } from "./intent.js";

// Reuse Reader's wikilink renderer via api ladder so unknown slugs in the
// open-questions markdown render as broken instead of erroring.
import { resolveWikilinks } from "./wikilink.js";

marked.use({ gfm: true, breaks: false });

const IDEA_STATUSES = [
  "proposed", "in_progress", "tested", "validated", "failed",
];
const IDEA_STATUS_COLORS = {
  proposed: "#94a3b8",
  in_progress: "#3b82f6",
  tested: "#fbbf24",
  validated: "#22c55e",
  failed: "#ef4444",
};

const NOVELTY_BIN_LABELS = ["1", "2", "3", "4", "5"];

export async function viewDashboard(mount) {
  mount.innerHTML = `<div class="dashboard"><p class="muted">loading dashboard&hellip;</p></div>`;

  const [maturity, openQuestionsMd, logRes] = await Promise.all([
    getMaturity().catch((err) => ({ _error: err.message })),
    getOpenQuestions().catch((err) => `_(open_questions unavailable: ${err.message})_`),
    getLog(50).catch(() => ({ entries: [] })),
  ]);

  const methods = state.entitiesByType.methods || [];
  const experiments = state.entitiesByType.experiments || [];
  const ideas = state.entitiesByType.ideas || [];

  mount.innerHTML = `
    <div class="dashboard">
      <div class="breadcrumb"><strong>Dashboard</strong></div>
      ${renderHeadline()}
      ${renderMaturity(maturity)}
      <div class="dash-row">
        ${renderMethodsByType(methods)}
        ${renderNoveltyHistogram(ideas)}
      </div>
      ${renderExperimentsTable(experiments)}
      ${renderIdeasPipeline(ideas)}
      ${renderTopTags()}
      ${renderOpenQuestions(openQuestionsMd)}
      ${renderLogTimeline(logRes.entries || [])}
      ${renderMaintenance()}
      ${renderQuickActions()}
    </div>
  `;

  wireMaintenance();
  wireQuickActions();
}

// --- Maintenance (Phase 4 regenerate buttons) -------------------------------

const REGEN_KINDS = [
  { kind: "index",          label: "Rebuild index",          help: "regen wiki/index.md from frontmatter" },
  { kind: "context-brief",  label: "Rebuild context brief",  help: "regen wiki/graph/context_brief.md" },
  { kind: "open-questions", label: "Rebuild open questions", help: "regen wiki/graph/open_questions.md" },
  { kind: "visualize",      label: "Regen visualize",        help: "regen Obsidian config + Canvas" },
];

function renderMaintenance() {
  const buttons = REGEN_KINDS.map((r) => `
    <button type="button" class="regen-btn" data-kind="${esc(r.kind)}" title="${esc(r.help)}">
      ${esc(r.label)}
    </button>
  `).join("");
  return `
    <section class="dash-card">
      <h3>Maintenance <span class="muted small">(regenerate derived state)</span></h3>
      <div class="regen-row">${buttons}</div>
      <p id="regen-status" class="muted small" hidden></p>
    </section>
  `;
}

function wireMaintenance() {
  const statusEl = document.getElementById("regen-status");
  document.querySelectorAll(".regen-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const kind = btn.dataset.kind;
      const others = document.querySelectorAll(".regen-btn");
      others.forEach((b) => { b.disabled = true; });
      btn.classList.add("running");
      statusEl.hidden = false;
      statusEl.textContent = `running ${kind}…`;
      try {
        const res = await postRegenerate(kind);
        if (res.ok) {
          const steps = (res.steps || []).map((s) => s.step).join(", ");
          statusEl.textContent = `OK — ${kind}: ${steps}`;
        } else {
          const failed = (res.steps || []).filter((s) => !s.ok).map((s) => s.step).join(", ");
          statusEl.textContent = `partial failure — ${kind}: ${failed}`;
        }
      } catch (err) {
        statusEl.textContent = `ERROR: ${err.message}`;
      } finally {
        btn.classList.remove("running");
        others.forEach((b) => { b.disabled = false; });
      }
    });
  });
}

// --- 1. Headline ------------------------------------------------------------

function renderHeadline() {
  const counts = Object.fromEntries(
    Object.entries(state.entitiesByType).map(([k, v]) => [k, v.length])
  );
  // edges count from backlinkIndex sum
  let edgeCount = 0;
  for (const arr of state.backlinkIndex.values()) edgeCount += arr.length;

  const cells = [
    { label: "Papers", value: counts.papers || 0, color: "#4A90D9" },
    { label: "Concepts", value: counts.concepts || 0, color: "#EC4899" },
    { label: "Methods", value: counts.methods || 0, color: "#84CC16" },
    { label: "People", value: counts.people || 0, color: "#2ECC71" },
    { label: "Experiments", value: counts.experiments || 0, color: "#E74C3C" },
    { label: "Ideas", value: counts.ideas || 0, color: "#F39C12" },
    { label: "Edges", value: edgeCount, color: "#1ABC9C" },
  ];
  return `
    <section class="dash-card headline">
      <div class="headline-row">
        ${cells.map((c) => `
          <div class="headline-cell">
            <div class="hl-label" style="color:${c.color}">${esc(c.label)}</div>
            <div class="hl-num">${c.value}</div>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

// --- 2. Maturity gauge ------------------------------------------------------

function renderMaturity(m) {
  if (m._error) {
    return `<section class="dash-card"><h3>Maturity</h3><p class="muted">unavailable: ${esc(m._error)}</p></section>`;
  }
  const score = (m.coverage_score || 0);
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const level = m.level || "—";
  const levelColor = {
    cold: "#94a3b8",
    warm: "#fbbf24",
    hot: "#ef4444",
  }[level] || "#94a3b8";
  return `
    <section class="dash-card">
      <h3>Maturity <span class="badge maturity-${esc(level)}" style="background:${levelColor}">${esc(level)}</span></h3>
      <div class="gauge">
        <div class="gauge-fill" style="width:${pct.toFixed(1)}%; background:${levelColor}"></div>
      </div>
      <p class="muted small gauge-detail">
        coverage ${score.toFixed(3)} ·
        density ${(m.graph_density || 0).toFixed(4)} ·
        ${m.papers || 0} papers ·
        ${m.ideas || 0} ideas ·
        ${m.experiments_completed || 0} completed experiments
      </p>
    </section>
  `;
}

// --- 3. Methods by type -----------------------------------------------------

const METHOD_TYPE_COLORS = {
  architecture: "#4A90D9",
  training:     "#22c55e",
  inference:    "#3b82f6",
  evaluation:   "#fbbf24",
  data:         "#a855f7",
  benchmark:    "#ec4899",
  system:       "#f97316",
  optimization: "#10b981",
  prompting:    "#14b8a6",
  protocol:     "#6366f1",
  other:        "#94a3b8",
};

function renderMethodsByType(methods) {
  const buckets = new Map();
  for (const m of methods) {
    const t = (m.type || "other");
    buckets.set(t, (buckets.get(t) || 0) + 1);
  }
  if (methods.length === 0) {
    return `
      <section class="dash-card half">
        <h3>Methods by type <span class="muted small">(0)</span></h3>
        <p class="muted">No method pages yet. <code>/ingest</code> creates them when a paper introduces a reusable, namable method.</p>
      </section>
    `;
  }
  const total = methods.length || 1;
  const rows = [...buckets.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([t, n]) => {
      const pct = (n / total) * 100;
      return `
        <div class="bar-row">
          <span class="bar-label">${esc(t)}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:${pct.toFixed(1)}%; background:${METHOD_TYPE_COLORS[t] || "#94a3b8"}"></div>
          </div>
          <span class="bar-num">${n}</span>
        </div>
      `;
    }).join("");
  return `
    <section class="dash-card half">
      <h3>Methods by type <span class="muted small">(${methods.length})</span></h3>
      <div class="bars">${rows}</div>
    </section>
  `;
}

// --- 4. Idea novelty histogram ---------------------------------------------

function renderNoveltyHistogram(ideas) {
  const bins = new Array(5).fill(0); // novelty_score 1..5
  for (const i of ideas) {
    if (typeof i.novelty_score !== "number") continue;
    const idx = Math.min(4, Math.max(0, Math.floor(i.novelty_score - 1)));
    bins[idx]++;
  }
  const max = Math.max(1, ...bins);
  const cols = bins.map((n, i) => {
    const h = (n / max) * 100;
    return `
      <div class="hist-col" title="${NOVELTY_BIN_LABELS[i]}/5: ${n} idea(s)">
        <div class="hist-bar" style="height:${h.toFixed(1)}%"></div>
        <div class="hist-tick">${NOVELTY_BIN_LABELS[i]}</div>
      </div>
    `;
  }).join("");
  const scored = ideas.filter((i) => typeof i.novelty_score === "number").length;
  return `
    <section class="dash-card half">
      <h3>Idea novelty <span class="muted small">(${scored} of ${ideas.length} scored)</span></h3>
      <div class="histogram">${cols}</div>
    </section>
  `;
}

// --- 5. Experiments table ---------------------------------------------------

function renderExperimentsTable(exps) {
  if (exps.length === 0) {
    return `
      <section class="dash-card">
        <h3>Experiments <span class="muted small">(0)</span></h3>
        <p class="muted">No experiments yet. Use <code>/exp-design</code> in Claude Code to plan one.</p>
      </section>
    `;
  }
  const rows = exps.map((e) => `
    <tr>
      <td><a href="#/reader/experiments/${esc(e.slug)}">${esc(e.title || e.slug)}</a></td>
      <td><span class="chip status">${esc(e.status || "—")}</span></td>
      <td>${e.linked_idea ? `<a href="#/reader/ideas/${esc(e.linked_idea)}">${esc(e.linked_idea)}</a>` : '<span class="muted">—</span>'}</td>
      <td class="muted small">${esc(e.started || e.date_planned || "—")}</td>
      <td class="muted small">${e.estimated_hours ? esc(String(e.estimated_hours)) + "h" : "—"}</td>
    </tr>
  `).join("");
  return `
    <section class="dash-card">
      <h3>Experiments <span class="muted small">(${exps.length})</span></h3>
      <table class="dash-table">
        <thead><tr><th>Slug</th><th>Status</th><th>Linked idea</th><th>Started</th><th>Est.</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </section>
  `;
}

// --- 6. Ideas pipeline ------------------------------------------------------

function renderIdeasPipeline(ideas) {
  if (ideas.length === 0) {
    return `
      <section class="dash-card">
        <h3>Ideas pipeline <span class="muted small">(0)</span></h3>
        <p class="muted">No ideas captured yet. Use <code>/ideate</code> in Claude Code to generate from gaps.</p>
      </section>
    `;
  }
  const cols = IDEA_STATUSES.map((s) => {
    const items = ideas.filter((i) => (i.status || "proposed") === s);
    const cards = items.map((i) => `
      <a class="kanban-card" href="#/reader/ideas/${esc(i.slug)}">
        ${esc(i.title || i.slug)}
        ${i.priority ? `<span class="chip">P${esc(i.priority)}</span>` : ""}
      </a>
    `).join("");
    return `
      <div class="kanban-col">
        <div class="kanban-head" style="border-color:${IDEA_STATUS_COLORS[s]}">
          ${esc(s)} <span class="muted">${items.length}</span>
        </div>
        <div class="kanban-body">${cards || '<div class="muted small">—</div>'}</div>
      </div>
    `;
  }).join("");
  return `
    <section class="dash-card">
      <h3>Ideas pipeline <span class="muted small">(${ideas.length})</span></h3>
      <div class="kanban">${cols}</div>
    </section>
  `;
}

// --- 6.5 Top tags -----------------------------------------------------------

function renderTopTags() {
  const counter = new Map();
  for (const arr of Object.values(state.entitiesByType)) {
    for (const e of arr) {
      for (const t of (e.tags || [])) {
        counter.set(t, (counter.get(t) || 0) + 1);
      }
    }
  }
  const top = [...counter.entries()].sort((a, b) => b[1] - a[1]).slice(0, 30);
  if (top.length === 0) {
    return `
      <section class="dash-card">
        <h3>Top tags <span class="muted small">(0)</span></h3>
        <p class="muted">No tags yet. Add one via "edit field…" on any entity page.</p>
      </section>
    `;
  }
  // Cloud sizes scale by frequency
  const max = top[0][1];
  const cloud = top.map(([t, n]) => {
    const scale = 0.78 + (n / max) * 0.6;  // 0.78–1.38 rem
    return `
      <a class="chip tag tag-cloud-item" href="#/tag/${encodeURIComponent(t)}"
         style="font-size:${scale.toFixed(2)}rem">
        ${esc(t)}
        <span class="muted small">${n}</span>
      </a>
    `;
  }).join("");
  return `
    <section class="dash-card">
      <h3>Top tags <span class="muted small">(${counter.size} distinct)</span></h3>
      <div class="tag-cloud">${cloud}</div>
    </section>
  `;
}

// --- 7. Open questions ------------------------------------------------------

function renderOpenQuestions(md) {
  const html = resolveWikilinks(marked.parse(md || ""));
  return `
    <section class="dash-card">
      <h3>Open questions</h3>
      <div class="open-questions markdown">${html}</div>
    </section>
  `;
}

// --- 8. Log timeline --------------------------------------------------------

function renderLogTimeline(entries) {
  if (entries.length === 0) {
    return `<section class="dash-card"><h3>Log</h3><p class="muted">no log entries</p></section>`;
  }
  const rows = entries.slice().reverse().map((e) => `
    <li class="log-row">
      <span class="log-date">${esc(e.date)}</span>
      <span class="log-skill chip skill-${esc(skillSlug(e.skill))}">${esc(e.skill)}</span>
      <span class="log-detail">${esc(truncate(e.details, 200))}</span>
    </li>
  `).join("");
  return `
    <section class="dash-card">
      <h3>Recent activity <span class="muted small">(last ${entries.length})</span></h3>
      <ul class="log-list">${rows}</ul>
    </section>
  `;
}

function skillSlug(s) {
  return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

// --- 9. Quick actions strip (Phase 5: open intent modal) -------------------

const QUICK_ACTIONS = [
  { skill: "ingest",     desc: "Add a paper to the wiki" },
  { skill: "ask",        desc: "Query the knowledge graph in natural language" },
  { skill: "edit",       desc: "Edit wiki content with intent parsing" },
  { skill: "check",      desc: "Lint + audit the whole wiki" },
  { skill: "ideate",     desc: "Generate research ideas from open questions" },
  { skill: "discover",   desc: "Find related papers via citation graph" },
  { skill: "exp-design", desc: "Plan an experiment for a linked idea" },
];

function renderQuickActions() {
  const cards = QUICK_ACTIONS.map((a) => `
    <button type="button" class="action-card" data-skill="${esc(a.skill)}">
      <code>/${esc(a.skill)}</code>
      <span class="muted small">${esc(a.desc)}</span>
    </button>
  `).join("");
  return `
    <section class="dash-card">
      <h3>Quick actions <span class="muted small">(intent helper — does not execute)</span></h3>
      <p class="muted small">
        Skills run inside Claude Code, not from this UI. Click a tile to get a
        ready-to-paste <code>/skill ...</code> command with the right slug or arxiv-id
        already filled in (when applicable).
      </p>
      <div class="action-grid">${cards}</div>
    </section>
  `;
}

function wireQuickActions() {
  document.querySelectorAll(".action-card[data-skill]").forEach((btn) => {
    btn.addEventListener("click", () => {
      triggerIntent(btn.dataset.skill, {});
    });
  });
}

// --- helpers ---------------------------------------------------------------

function truncate(s, n) {
  s = String(s ?? "");
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
