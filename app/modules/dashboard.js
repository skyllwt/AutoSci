// Dashboard view: research-lifecycle overview.
//
// Several widgets, each fed by one read endpoint or by state.entitiesByType
// (already loaded at boot). All charts are pure HTML/CSS — no chart lib.

import { marked } from "https://cdn.jsdelivr.net/npm/marked@14.1.4/lib/marked.esm.js";
import {
  getMaturity, getOpenQuestions, getLog, postRegenerate,
  getLint, postLintFix, listDiscoverCheckpoints, getDiscoverCheckpoint,
} from "./api.js";
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
      ${renderMethodsByType(methods)}
      ${renderExperimentsTable(experiments)}
      ${renderIdeasPipeline(ideas)}
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
//
// Thresholds mirror tools/research_wiki.py (MATURITY_WARM / MATURITY_HOT).
// Keep in sync when those constants change.
const MATURITY_WARM = { papers: 5, ideas: 5 };
const MATURITY_HOT  = { papers: 20, ideas: 15 };

function renderMaturity(m) {
  if (m._error) {
    return `<section class="dash-card"><h3>Maturity</h3><p class="muted">unavailable: ${esc(m._error)}</p></section>`;
  }
  const score = m.coverage_score || 0;
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const level = m.level || "—";
  const levelColor = {
    cold: "#94a3b8",
    warm: "#fbbf24",
    hot: "#ef4444",
  }[level] || "#94a3b8";

  const papers = m.papers || 0;
  const ideas = m.ideas || 0;
  const exps = m.experiments_completed || 0;
  const edges = m.edges || 0;
  const hasEvidence = !!m.has_experiment_evidence;

  // Next-step hint — the one piece of actionable info; always visible.
  const need = [];
  let nextHint;
  if (level === "cold") {
    if (papers < MATURITY_WARM.papers) need.push(`<strong>${MATURITY_WARM.papers - papers}</strong> more paper(s)`);
    if (ideas < MATURITY_WARM.ideas)   need.push(`<strong>${MATURITY_WARM.ideas - ideas}</strong> more idea(s)`);
    const ideateHint = (papers >= MATURITY_WARM.papers && ideas < MATURITY_WARM.ideas)
      ? ` — try <code>/ideate</code>` : "";
    nextHint = `To reach <strong>warm</strong>: ${need.join(" and ")}${ideateHint}.`;
  } else if (level === "warm") {
    if (papers < MATURITY_HOT.papers) need.push(`<strong>${MATURITY_HOT.papers - papers}</strong> more paper(s)`);
    if (ideas < MATURITY_HOT.ideas)   need.push(`<strong>${MATURITY_HOT.ideas - ideas}</strong> more idea(s)`);
    if (!hasEvidence) need.push(`at least <strong>1</strong> experiment evidence edge (<code>supports</code> / <code>invalidates</code> from an <code>experiments/</code> node)`);
    nextHint = `To reach <strong>hot</strong>: ${need.join(", ")}.`;
  } else {
    nextHint = `<strong>Hot</strong> — full lifecycle covered.`;
  }

  // Coverage breakdown: same formula as tools/research_wiki.py:get_maturity.
  const cov = {
    papers: Math.min(1, papers / 20) * 0.30,
    ideas:  Math.min(1, ideas / 15)  * 0.30,
    exps:   Math.min(1, exps / 5)    * 0.20,
    edges:  Math.min(1, edges / 50)  * 0.20,
  };

  return `
    <section class="dash-card maturity-card">
      <h3>
        Maturity <span class="badge maturity-${esc(level)}" style="background:${levelColor}">${esc(level)}</span>
      </h3>

      <div class="gauge" title="Coverage score (0 → 1). Reaching 1.0 means a balanced full-lifecycle wiki.">
        <div class="gauge-fill" style="width:${pct.toFixed(1)}%; background:${levelColor}"></div>
      </div>
      <p class="muted small gauge-detail">
        Coverage <strong>${(score * 100).toFixed(1)}%</strong> — weighted lifecycle progress toward "hot" (target 100%).
      </p>

      <p class="maturity-hint">${nextHint}</p>

      <details class="maturity-explain">
        <summary>What do these numbers actually mean?</summary>
        <div class="explain-body">
          <p><strong>Level</strong> is a discrete lifecycle stage:</p>
          <ul>
            <li><code>cold</code> — default; not enough papers or ideas yet.</li>
            <li><code>warm</code> — at least <strong>${MATURITY_WARM.papers}</strong> papers <em>and</em> <strong>${MATURITY_WARM.ideas}</strong> ideas.</li>
            <li><code>hot</code> — at least <strong>${MATURITY_HOT.papers}</strong> papers <em>and</em> <strong>${MATURITY_HOT.ideas}</strong> ideas <em>and</em> at least one experiment-evidence edge (a <code>supports</code> or <code>invalidates</code> edge from an <code>experiments/</code> node).</li>
          </ul>

          <p><strong>Coverage</strong> is a weighted sum capped at 1.0. Weights make all four lifecycle axes count — you can't reach 1.0 by collecting papers alone:</p>
          <table class="coverage-table">
            <thead>
              <tr><th>component</th><th>current / target</th><th>contribution</th></tr>
            </thead>
            <tbody>
              <tr><td>papers / 20 × 0.30</td><td>${papers} / 20</td><td>${cov.papers.toFixed(3)}</td></tr>
              <tr><td>ideas / 15 × 0.30</td><td>${ideas} / 15</td><td>${cov.ideas.toFixed(3)}</td></tr>
              <tr><td>completed experiments / 5 × 0.20</td><td>${exps} / 5</td><td>${cov.exps.toFixed(3)}</td></tr>
              <tr><td>edges / 50 × 0.20</td><td>${edges} / 50</td><td>${cov.edges.toFixed(3)}</td></tr>
              <tr class="total"><td colspan="2">total (capped at 1.0)</td><td>${score.toFixed(3)}</td></tr>
            </tbody>
          </table>

          <p><strong>Density</strong> <code>${(m.graph_density || 0).toFixed(4)}</code> = edges ÷ N×(N−1), where N is the count of non-terminal entities. It measures how interconnected the graph is relative to a hypothetical complete directed graph. Knowledge graphs are intrinsically sparse, so this number is normally small — interpret it as "is the density growing as I add edges?" rather than as an absolute target.</p>

          <p class="muted small">Thresholds and weights live in <code>tools/research_wiki.py</code> (<code>MATURITY_WARM</code>, <code>MATURITY_HOT</code>, <code>get_maturity</code>).</p>
        </div>
      </details>
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

// --- 9. Quick actions strip (Phase 5/6: interactive helpers) ---------------
//
// Click flow per skill:
//   /check     -> fetch /api/lint, render inline lint card (mechanical, no LLM)
//   /discover  -> render checkpoint browser inline (peek at past ranked runs)
//   others     -> open the intent form with a per-skill schema, then show the
//                 generated /skill command in the existing copy-to-clipboard
//                 modal. The schemas mirror the keys each intent builder in
//                 tools/serve.py:_handle_intent actually consumes — drift
//                 there is harmless (unknown keys ignored) but pointless.

const QUICK_ACTIONS = [
  { skill: "ingest",     desc: "Add a paper to the wiki" },
  { skill: "ask",        desc: "Query the knowledge graph in natural language" },
  { skill: "edit",       desc: "Edit wiki content with intent parsing" },
  { skill: "check",      desc: "Run wiki lint inline (no LLM needed)" },
  { skill: "ideate",     desc: "Generate research ideas from open questions" },
  { skill: "discover",   desc: "Browse ranked candidate papers from past /discover" },
  { skill: "exp-design", desc: "Plan an experiment for a linked idea" },
];

const QUICK_ACTION_SCHEMAS = {
  ingest: [
    { key: "path", label: "arXiv URL / id / local .pdf or .tex path",
      required: true, type: "text" },
  ],
  ask: [
    { key: "question", label: "Question to ask the wiki",
      required: true, type: "textarea" },
  ],
  edit: [
    { key: "intent", label: "Natural-language edit instruction",
      required: true, type: "textarea" },
  ],
  check: null,        // handled inline by openLintCard
  ideate: [
    { key: "from_concept", label: "Seed from a concept slug (optional)" },
    { key: "from_topic",   label: "Or seed from a topic slug (optional)" },
  ],
  discover: null,     // handled inline by openCheckpointBrowser
  "exp-design": [
    { key: "linked_idea", label: "Linked idea slug",
      required: true, type: "select", optionsFrom: "ideas" },
  ],
};

function renderQuickActions() {
  const cards = QUICK_ACTIONS.map((a) => `
    <button type="button" class="action-card" data-skill="${esc(a.skill)}">
      <code>/${esc(a.skill)}</code>
      <span class="muted small">${esc(a.desc)}</span>
    </button>
  `).join("");
  return `
    <section class="dash-card">
      <h3>Quick actions <span class="muted small">(interactive helpers)</span></h3>
      <p class="muted small">
        <code>/check</code> and <code>/discover</code> run inline below
        (mechanical, no LLM). The other five open a parameter form, then
        produce a ready-to-paste <code>/skill ...</code> command for Claude Code.
      </p>
      <div class="action-grid">${cards}</div>
      <div id="quick-action-result" class="quick-action-result" aria-live="polite"></div>
    </section>
  `;
}

function wireQuickActions() {
  const mount = document.getElementById("quick-action-result");
  document.querySelectorAll(".action-card[data-skill]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const skill = btn.dataset.skill;
      if (skill === "check") {
        openLintCard(mount);
        return;
      }
      if (skill === "discover") {
        openCheckpointBrowser(mount);
        return;
      }
      const schema = QUICK_ACTION_SCHEMAS[skill] || null;
      triggerIntent(skill, {}, schema);
    });
  });
}

// --- /check inline lint card ------------------------------------------------

async function openLintCard(mount) {
  mount.innerHTML = `<div class="lint-card loading"><p class="muted small">Running <code>tools/lint.py --json</code>…</p></div>`;
  try {
    const issues = await getLint();
    mount.innerHTML = renderLintCard(issues, { fixesApplied: null });
    wireLintCard(mount);
  } catch (err) {
    mount.innerHTML = `<div class="lint-card error">lint failed: ${esc(err.message)}</div>`;
  }
}

function renderLintCard(issues, { fixesApplied }) {
  // issues is an array. Defensive: if backend returned an object (shouldn't),
  // extract .issues.
  const list = Array.isArray(issues) ? issues : (issues.issues || []);
  const counts = { "🔴": 0, "🟡": 0, "🔵": 0 };
  for (const i of list) {
    if (counts[i.level] != null) counts[i.level]++;
  }
  const fixable = list.filter((i) => i.fixable).length;
  const fixesNote = fixesApplied
    ? `<p class="lint-fixes-note">✓ Auto-fix applied: <strong>${fixesApplied.length}</strong> fix(es). Click "Re-lint" to confirm.</p>`
    : "";
  const rows = list.length === 0
    ? `<p class="muted small">No lint issues — the wiki is clean.</p>`
    : `<table class="lint-table">
         <thead><tr><th>Level</th><th>Category</th><th>File</th><th>Message</th></tr></thead>
         <tbody>${list.map(renderLintRow).join("")}</tbody>
       </table>`;
  return `
    <div class="lint-card">
      <div class="lint-header">
        <h4>Wiki lint <span class="muted small">(${list.length} issue${list.length === 1 ? "" : "s"})</span></h4>
        <div class="lint-summary">
          <span class="lint-pill lint-pill-red"   title="errors">🔴 ${counts["🔴"]}</span>
          <span class="lint-pill lint-pill-amber" title="warnings">🟡 ${counts["🟡"]}</span>
          <span class="lint-pill lint-pill-blue"  title="info">🔵 ${counts["🔵"]}</span>
        </div>
        <div class="lint-actions">
          <button type="button" class="lint-relint">Re-lint</button>
          <button type="button" class="lint-fix" ${fixable === 0 ? "disabled" : ""}
                  title="${fixable} auto-fixable issue${fixable === 1 ? "" : "s"}">
            Auto-fix reversible (${fixable})
          </button>
          <button type="button" class="lint-fix-dry ghost" ${fixable === 0 ? "disabled" : ""}>
            Preview fixes (dry-run)
          </button>
          <button type="button" class="lint-close ghost">Close</button>
        </div>
      </div>
      ${fixesNote}
      ${rows}
    </div>
  `;
}

function renderLintRow(i) {
  const sev = i.level === "🔴" ? "red" : i.level === "🟡" ? "amber" : "blue";
  const fixMark = i.fixable ? ' <span class="chip fixable" title="auto-fixable">fixable</span>' : "";
  const suggest = i.suggestion
    ? `<div class="lint-suggestion muted small">💡 ${esc(i.suggestion)}</div>`
    : "";
  return `
    <tr class="lint-row lint-severity-${sev}">
      <td>${esc(i.level)}</td>
      <td><code>${esc(i.category)}</code>${fixMark}</td>
      <td><code class="lint-file">${esc(i.file)}</code></td>
      <td>${esc(i.message)}${suggest}</td>
    </tr>
  `;
}

function wireLintCard(mount) {
  const reLint = mount.querySelector(".lint-relint");
  const fixBtn = mount.querySelector(".lint-fix");
  const dryBtn = mount.querySelector(".lint-fix-dry");
  const close = mount.querySelector(".lint-close");
  if (close) close.onclick = () => { mount.innerHTML = ""; };
  if (reLint) reLint.onclick = () => openLintCard(mount);
  if (fixBtn) fixBtn.onclick = async () => {
    fixBtn.disabled = true;
    fixBtn.textContent = "Fixing…";
    try {
      const res = await postLintFix({ dryRun: false });
      mount.innerHTML = renderLintCard(res.issues || [], { fixesApplied: res.fixes || [] });
      wireLintCard(mount);
    } catch (err) {
      mount.innerHTML = `<div class="lint-card error">fix failed: ${esc(err.message)}</div>`;
    }
  };
  if (dryBtn) dryBtn.onclick = async () => {
    dryBtn.disabled = true;
    dryBtn.textContent = "Previewing…";
    try {
      const res = await postLintFix({ dryRun: true });
      const fixes = res.fixes || [];
      const list = fixes.length === 0
        ? `<p class="muted">No fixes to preview.</p>`
        : `<ul class="lint-fix-preview">${fixes.map((f) => `
            <li><code>${esc(f.file)}</code> — ${esc(f.action)}</li>
          `).join("")}</ul>`;
      mount.querySelector(".lint-card").insertAdjacentHTML("afterbegin", `
        <div class="lint-fix-preview-box">
          <strong>Dry-run preview:</strong> ${fixes.length} fix(es) would be applied.
          ${list}
        </div>
      `);
      dryBtn.disabled = false;
      dryBtn.textContent = "Preview fixes (dry-run)";
    } catch (err) {
      mount.innerHTML = `<div class="lint-card error">dry-run failed: ${esc(err.message)}</div>`;
    }
  };
}

// --- /discover checkpoint browser ------------------------------------------

async function openCheckpointBrowser(mount) {
  mount.innerHTML = `<div class="checkpoint-browser loading"><p class="muted small">Loading <code>.checkpoints/discover-*.json</code>…</p></div>`;
  try {
    const res = await listDiscoverCheckpoints();
    mount.innerHTML = renderCheckpointBrowser(res.checkpoints || []);
    wireCheckpointBrowser(mount);
  } catch (err) {
    mount.innerHTML = `<div class="checkpoint-browser error">listing failed: ${esc(err.message)}</div>`;
  }
}

function renderCheckpointBrowser(items) {
  // Header: title + always-visible primary "New /discover" action + close.
  // Same header for empty and non-empty states — only the body differs.
  const header = `
    <div class="checkpoint-header">
      <h4>Past <code>/discover</code> runs <span class="muted small">(${items.length})</span></h4>
      <div class="checkpoint-actions">
        <button type="button" class="checkpoint-fresh-btn">+ New <code>/discover</code></button>
        <button type="button" class="checkpoint-close ghost">Close</button>
      </div>
    </div>
  `;

  if (items.length === 0) {
    return `
      <div class="checkpoint-browser">
        ${header}
        <p class="checkpoint-empty muted">
          No runs yet. After <code>/discover</code> finishes in Claude Code its
          ranked candidate list will appear here for one-click <code>/ingest</code>.
        </p>
      </div>
    `;
  }

  const rows = items.map((c) => `
    <li class="checkpoint-row" data-name="${esc(c.name)}">
      <button type="button" class="checkpoint-toggle">
        <code class="checkpoint-name">${esc(c.name)}</code>
        <span class="muted small">
          ${(c.size / 1024).toFixed(1)} KB · ${new Date(c.mtime * 1000).toLocaleString()}
        </span>
      </button>
      <div class="checkpoint-detail" hidden></div>
    </li>
  `).join("");
  return `
    <div class="checkpoint-browser">
      ${header}
      <ul class="checkpoint-list">${rows}</ul>
    </div>
  `;
}

function wireCheckpointBrowser(mount) {
  const close = mount.querySelector(".checkpoint-close");
  if (close) close.onclick = () => { mount.innerHTML = ""; };
  const fresh = mount.querySelector(".checkpoint-fresh-btn");
  if (fresh) fresh.onclick = () => {
    // /discover supports four seed modes (see .claude/skills/discover/SKILL.md).
    // All form fields are optional — leave everything blank and the backend
    // returns `/discover --from-wiki`, which mines the existing wiki.
    triggerIntent(
      "discover",
      {},
      [
        { key: "anchor", label: "Anchor: arXiv ID or paper slug — find similar to this paper" },
        { key: "topic",  label: "OR Topic: a query phrase like \"diffusion HDR fusion\"" },
        { key: "venue",  label: "OR Venue slug (e.g. cvpr) — paired with year" },
        { key: "year",   label: "    Year (paired with venue)" },
        { key: "limit",  label: "Max results (optional; default 10)" },
      ],
      {
        message: (
          "Leave everything blank and you'll get /discover --from-wiki, which " +
          "mines your current wiki state for next-read suggestions. Otherwise " +
          "fill exactly one mode (anchor / topic / venue+year)."
        ),
      },
    );
  };
  mount.querySelectorAll(".checkpoint-row").forEach((row) => {
    const toggle = row.querySelector(".checkpoint-toggle");
    const detail = row.querySelector(".checkpoint-detail");
    toggle.addEventListener("click", async () => {
      if (!detail.hidden) {
        detail.hidden = true;
        return;
      }
      if (!detail.dataset.loaded) {
        detail.innerHTML = `<p class="muted small">Loading…</p>`;
        try {
          const data = await getDiscoverCheckpoint(row.dataset.name);
          detail.innerHTML = renderCheckpointDetail(data);
          wireCheckpointDetail(detail);
        } catch (err) {
          detail.innerHTML = `<p class="error-msg">load failed: ${esc(err.message)}</p>`;
        }
        detail.dataset.loaded = "1";
      }
      detail.hidden = false;
    });
  });
}

function renderCheckpointDetail(data) {
  // Defensive: discover writes various candidate lists at top level. Try
  // common keys; fall back to dumping a summary.
  const candidates = data.shortlist || data.candidates || data.local_papers
                     || data.ranked || [];
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return `
      <p class="muted small">
        No candidate array found in this checkpoint. Keys present:
        <code>${esc(Object.keys(data).join(", "))}</code>
      </p>
    `;
  }
  const topic = data.topic ? `<p class="muted small">Topic: <code>${esc(data.topic)}</code></p>` : "";
  const mode = data.mode ? `<p class="muted small">Mode: <code>${esc(data.mode)}</code></p>` : "";
  const rows = candidates.slice(0, 50).map((c, idx) => {
    const rank = c.shortlist_rank ?? c.rank ?? (idx + 1);
    const title = c.title || c.candidate_id || "(no title)";
    const arxiv = c.arxiv_id || c.arxiv || "";
    const score = c.total_score != null ? c.total_score.toFixed(2) : "";
    const year = c.year || "";
    const ingestBtn = arxiv
      ? `<button type="button" class="ingest-from-candidate" data-arxiv="${esc(arxiv)}">→ /ingest</button>`
      : "";
    return `
      <tr>
        <td>${rank}</td>
        <td>${esc(title)}</td>
        <td>${arxiv ? `<code>${esc(arxiv)}</code>` : "—"}</td>
        <td>${esc(String(year))}</td>
        <td class="num">${esc(String(score))}</td>
        <td>${ingestBtn}</td>
      </tr>
    `;
  }).join("");
  return `
    ${topic}${mode}
    <table class="candidate-table">
      <thead>
        <tr><th>#</th><th>Title</th><th>arXiv</th><th>Year</th><th>Score</th><th></th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    ${candidates.length > 50 ? `<p class="muted small">Showing first 50 of ${candidates.length}.</p>` : ""}
  `;
}

function wireCheckpointDetail(scope) {
  scope.querySelectorAll(".ingest-from-candidate[data-arxiv]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const arxiv = btn.dataset.arxiv;
      // Open the existing intent modal pre-filled with this arXiv id. The
      // user pastes the result into Claude Code as usual.
      triggerIntent("ingest", { path: arxiv }, null);
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
