// Reader views: index (entity-type cards), list (slugs in a type),
// entity (three-pane: siblings | metadata + body | backlinks).

import { marked } from "https://cdn.jsdelivr.net/npm/marked@14.1.4/lib/marked.esm.js";
import yaml from "https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/+esm";
import markedKatex from "https://cdn.jsdelivr.net/npm/marked-katex-extension@5.1.4/+esm";
import { getEntity, patchEntity, postEdge, postCitation, getGraph } from "./api.js";
import { resolveWikilinks } from "./wikilink.js";
import { state } from "./state.js";
import { ENTITY_LABEL, EDGE_TYPE_WORKFLOW } from "./schema.js";
import { showToast } from "./ui.js";
import { triggerIntent } from "./intent.js";

marked.use({ gfm: true, breaks: false });
marked.use(markedKatex({ throwOnError: false, nonStandard: true }));

// --- viewIndex --------------------------------------------------------------

export function viewIndex(mount) {
  const cards = Object.keys(ENTITY_LABEL)
    .map((type) => {
      const entries = state.entitiesByType[type] || [];
      const sample = entries
        .slice(0, 3)
        .map((e) => esc(e.title || e.name || e.slug))
        .join(" · ");
      return `
        <a class="card" href="#/reader/${type}">
          <div class="card-head">
            <span class="card-type type-${type}">${ENTITY_LABEL[type]}</span>
            <span class="card-count">${entries.length}</span>
          </div>
          <div class="card-sample">${sample || '<em class="muted">empty</em>'}</div>
        </a>
      `;
    })
    .join("");

  // Pick three real example slugs (highest-importance paper, first concept,
  // first person) so the "examples" line shows working links, not abstract
  // {type}/{slug} placeholders.
  const examples = [];
  const firstOf = (type) => (state.entitiesByType[type] || [])[0];
  const topPaper = (state.entitiesByType.papers || [])
    .slice()
    .sort((a, b) => (b.importance || 0) - (a.importance || 0))[0];
  if (topPaper) examples.push({ type: "papers", e: topPaper });
  const c0 = firstOf("concepts");
  if (c0) examples.push({ type: "concepts", e: c0 });
  const p0 = firstOf("people");
  if (p0) examples.push({ type: "people", e: p0 });
  const exHtml = examples
    .map(({ type, e }) => {
      const href = `#/reader/${type}/${esc(e.slug)}`;
      const label = esc(e.title || e.name || e.slug);
      return `<a class="example" href="${href}"><code>${href}</code> &mdash; ${label}</a>`;
    })
    .join("");

  mount.innerHTML = `
    <div class="breadcrumb"><strong>Reader</strong></div>
    ${renderTagWordCloud()}
    <h2>Entity types</h2>
    <p class="muted">
      Click a card to browse, type a slug into the
      <strong>jump</strong> box up top, or open one of these directly:
    </p>
    <div class="examples">${exHtml}</div>
    <div class="entity-grid">${cards}</div>
  `;
}

// --- viewIndex: tag word cloud ---------------------------------------------
//
// Renders a true word-cloud of the most frequent tags across all entities.
// Font size scales with frequency (0.75–2.4rem). Color and rotation are
// derived from a stable string hash so the cloud looks lively but is the
// same every render. Hover settles each word to horizontal.

const CLOUD_PALETTE = [
  "#4A90D9", "#EC4899", "#84CC16", "#2ECC71", "#E74C3C",
  "#F39C12", "#1ABC9C", "#A855F7", "#3B82F6", "#FB923C",
];

function tagHash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function renderTagWordCloud() {
  const counter = new Map();
  for (const arr of Object.values(state.entitiesByType)) {
    for (const e of arr) {
      for (const t of (e.tags || [])) {
        counter.set(t, (counter.get(t) || 0) + 1);
      }
    }
  }
  if (counter.size === 0) return "";

  const top = [...counter.entries()].sort((a, b) => b[1] - a[1]).slice(0, 40);
  const max = top[0][1];
  const min = top[top.length - 1][1];
  const range = Math.max(1, max - min);

  // Shuffle deterministically by hash so high-frequency words aren't clumped
  // at the start of the flex row.
  const shuffled = top.slice().sort((a, b) => tagHash(a[0]) - tagHash(b[0]));

  const items = shuffled.map(([t, n]) => {
    const ratio = (n - min) / range;       // 0..1
    const sizeRem = (0.75 + ratio * 1.65).toFixed(2); // 0.75–2.40 rem
    const h = tagHash(t);
    const color = CLOUD_PALETTE[h % CLOUD_PALETTE.length];
    const rotation = ((h % 31) - 15);      // -15..+15 deg
    const title = `${t} — ${n} mention${n === 1 ? "" : "s"}`;
    return `
      <a class="cloud-word" href="#/tag/${encodeURIComponent(t)}"
         style="font-size:${sizeRem}rem; color:${color}; --rot:${rotation}deg;"
         title="${esc(title)}">${esc(t)}</a>
    `;
  }).join("");

  return `
    <section class="word-cloud-section">
      <h2 class="cloud-heading">Top tags
        <span class="muted small">(${counter.size} distinct · showing top ${top.length})</span>
      </h2>
      <div class="word-cloud">${items}</div>
    </section>
  `;
}

// --- viewList ---------------------------------------------------------------

export function viewList(mount, type) {
  const entries = (state.entitiesByType[type] || []).slice();
  // Sort: importance desc (default 3), then title asc
  entries.sort((a, b) => {
    const ia = (typeof a.importance === "number" ? a.importance : 3);
    const ib = (typeof b.importance === "number" ? b.importance : 3);
    if (ib !== ia) return ib - ia;
    const ta = (a.title || a.name || a.slug || "").toLowerCase();
    const tb = (b.title || b.name || b.slug || "").toLowerCase();
    return ta.localeCompare(tb);
  });

  const rows = entries
    .map((e) => {
      const title = e.title || e.name || e.slug;
      const imp = typeof e.importance === "number" ? e.importance : null;
      const status = e.status || e.maturity || null;
      const tagsHtml = (e.tags || [])
        .slice(0, 4)
        .map((t) => `<span class="chip tag">${esc(t)}</span>`)
        .join("");
      const impHtml = imp
        ? `<span class="chip importance imp-${imp}">★${imp}</span>`
        : "";
      const statusHtml = status
        ? `<span class="chip status">${esc(status)}</span>`
        : "";
      return `
        <a class="row" href="#/reader/${type}/${esc(e.slug)}">
          <div class="row-title">${esc(title)}</div>
          <div class="row-meta">${impHtml}${statusHtml}${tagsHtml}</div>
        </a>
      `;
    })
    .join("");

  mount.innerHTML = `
    <div class="breadcrumb">
      <a href="#/">Reader</a> &rsaquo; <strong>${ENTITY_LABEL[type] || type}</strong>
      <span class="muted">(${entries.length})</span>
    </div>
    <div class="list">${rows || '<p class="muted">No entries.</p>'}</div>
  `;
}

// --- viewEntity (three-pane) ------------------------------------------------

export async function viewEntity(mount, type, slug) {
  const entry = (state.entitiesByType[type] || []).find((e) => e.slug === slug);
  let payload;
  try {
    payload = await getEntity(type, slug);
  } catch (err) {
    if (String(err.message).startsWith("404")) {
      view404(mount, `entity not found: ${type}/${slug}`);
      return;
    }
    throw err;
  }

  const { frontmatter_yaml, body } = payload;
  let fm = {};
  if (frontmatter_yaml) {
    try {
      fm = yaml.load(frontmatter_yaml) || {};
    } catch (err) {
      console.warn("frontmatter parse error", err);
    }
  }

  const title = fm.title || fm.name || entry?.title || entry?.name || slug;
  const html = resolveWikilinks(marked.parse(body || ""));

  // --- Left pane: siblings list -------------------------------------------
  const siblings = (state.entitiesByType[type] || []).slice().sort((a, b) => {
    const ia = (typeof a.importance === "number" ? a.importance : 3);
    const ib = (typeof b.importance === "number" ? b.importance : 3);
    if (ib !== ia) return ib - ia;
    return (a.title || a.slug).localeCompare(b.title || b.slug);
  });
  const sibHtml = siblings
    .map((e) => {
      const cls = e.slug === slug ? "sib current" : "sib";
      return `<a class="${cls}" href="#/reader/${type}/${esc(
        e.slug
      )}">${esc(e.title || e.name || e.slug)}</a>`;
    })
    .join("");

  // --- Right pane: outgoing + backlinks -----------------------------------
  const id = `${type}/${slug}`;
  const outgoing = state.forwardIndex.get(id) || [];
  const backlinks = state.backlinkIndex.get(id) || [];
  const renderEdgeRow = (other, etype, evidence, dir) => {
    const [bt, bs] = other.split("/", 2);
    const ev = evidence ? ` <span class="muted">— ${esc(String(evidence).slice(0, 80))}${String(evidence).length > 80 ? "…" : ""}</span>` : "";
    return `<li><a href="#/reader/${bt}/${esc(bs)}">${esc(bs)}</a> <span class="chip edge">${esc(etype || "ref")}</span>${ev}</li>`;
  };
  const outHtml = outgoing.length
    ? outgoing.map((o) => renderEdgeRow(o.target, o.type, o.evidence, "out")).join("")
    : '<li class="muted">(no outgoing edges)</li>';
  const blHtml = backlinks.length
    ? backlinks.map((b) => renderEdgeRow(b.source, b.type, b.evidence, "in")).join("")
    : '<li class="muted">(no backlinks)</li>';

  // --- Center pane: metadata card + body ----------------------------------
  const meta = renderMetadata(type, fm);

  mount.innerHTML = `
    <div class="breadcrumb">
      <a href="#/">Reader</a> &rsaquo;
      <a href="#/reader/${type}">${ENTITY_LABEL[type] || type}</a> &rsaquo;
      <strong>${esc(slug)}</strong>
      <span class="bc-actions">
        <button type="button" class="ghost-mini" id="edit-field-btn" title="Edit a frontmatter field">edit field…</button>
        <button type="button" class="ghost-mini" id="add-edge-btn" title="Add a graph edge from this entity">+ edge</button>
        ${type === "papers" ? `<button type="button" class="ghost-mini" id="add-cite-btn" title="Add a bibliographic citation from this paper">+ cites</button>` : ""}
        ${renderIntentButtons(type, slug, fm)}
      </span>
    </div>
    <div class="reader-grid">
      <aside class="pane left">
        <h3>${ENTITY_LABEL[type] || type}</h3>
        <div class="sib-list">${sibHtml}</div>
      </aside>
      <article class="pane center">
        <h1>${esc(title)}</h1>
        ${meta}
        <div class="body markdown">${html}</div>
      </article>
      <aside class="pane right">
        <h3>Outgoing <span class="muted">(${outgoing.length})</span></h3>
        <ul class="backlinks">${outHtml}</ul>
        <h3 class="rp-divider">Backlinks <span class="muted">(${backlinks.length})</span></h3>
        <ul class="backlinks">${blHtml}</ul>
        <a class="ghost-link" href="#/graph">Open in graph &rarr;</a>
      </aside>
    </div>
    <div id="edit-popover" class="edit-popover" hidden>
      <div class="edit-card">
        <h4>Edit field on <code>${esc(type)}/${esc(slug)}</code></h4>
        <label>Field
          <select id="edit-field"></select>
        </label>
        <label>Value
          <input id="edit-value" type="text" autocomplete="off">
        </label>
        <label class="checkbox-row">
          <input id="edit-append" type="checkbox">
          <span>Append to list (use this for adding a single item to <code>tags</code>, <code>aliases</code>, etc.)</span>
        </label>
        <div class="edit-actions">
          <button type="button" id="edit-save">Save (PATCH)</button>
          <button type="button" id="edit-cancel" class="ghost">Cancel</button>
        </div>
        <p id="edit-status" class="muted small" hidden></p>
      </div>
    </div>
    <div id="edge-popover" class="edit-popover" hidden>
      <div class="edit-card">
        <h4>Add graph edge from <code>${esc(type)}/${esc(slug)}</code></h4>
        <label>To (target)
          <input id="edge-to" list="entity-slug-list" autocomplete="off"
                 placeholder="papers/foo, concepts/bar &hellip;">
        </label>
        <label>Edge type
          <select id="edge-type"></select>
        </label>
        <label>Evidence (optional)
          <textarea id="edge-evidence" rows="2"
                    placeholder="brief justification or quote"></textarea>
        </label>
        <label>Confidence
          <select id="edge-confidence">
            <option value="">— (let CLI decide)</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label class="checkbox-row">
          <input id="edge-symmetric" type="checkbox">
          <span>Symmetric (only meaningful for paper-paper similar/complementary edges; stored once with sorted endpoints)</span>
        </label>
        <div class="edit-actions">
          <button type="button" id="edge-save">Save (POST)</button>
          <button type="button" id="edge-cancel" class="ghost">Cancel</button>
        </div>
        <p id="edge-status" class="muted small" hidden></p>
      </div>
    </div>
    ${type === "papers" ? `
    <div id="cite-popover" class="edit-popover" hidden>
      <div class="edit-card">
        <h4>Add citation from <code>${esc(type)}/${esc(slug)}</code></h4>
        <label>Cited paper (target)
          <input id="cite-to" list="paper-slug-list" autocomplete="off"
                 placeholder="papers/cited-paper-slug">
        </label>
        <label>Source
          <select id="cite-source">
            <option value="manual">manual</option>
            <option value="parsed_bib">parsed_bib</option>
            <option value="semantic_scholar">semantic_scholar</option>
          </select>
        </label>
        <div class="edit-actions">
          <button type="button" id="cite-save">Save (POST)</button>
          <button type="button" id="cite-cancel" class="ghost">Cancel</button>
        </div>
        <p id="cite-status" class="muted small" hidden></p>
      </div>
    </div>
    ` : ""}
  `;

  ensureEntityDatalist();
  if (type === "papers") ensurePaperDatalist();
  wireEditPopover(type, slug, fm);
  wireEdgeAddPopover(type, slug);
  if (type === "papers") wireCiteAddPopover(type, slug);
  wireIntentButtons(type, slug, fm);
  applyJustAddedHighlight(type, slug);
}

// --- Phase 5: context-aware /skill intent buttons --------------------------

function renderIntentButtons(type, slug, fm) {
  const buttons = [];
  if (type === "ideas") {
    buttons.push(`<button type="button" class="ghost-mini intent-btn"
                          data-skill="exp-design"
                          data-context='{"linked_idea":"${esc(slug)}"}'
                          title="Design experiments for this idea">/exp-design</button>`);
  }
  if (type === "concepts") {
    buttons.push(`<button type="button" class="ghost-mini intent-btn"
                          data-skill="ideate"
                          data-context='{"from_concept":"${esc(slug)}"}'
                          title="Generate research ideas around this concept">/ideate</button>`);
  }
  if (type === "topics") {
    buttons.push(`<button type="button" class="ghost-mini intent-btn"
                          data-skill="ideate"
                          data-context='{"from_topic":"${esc(slug)}"}'
                          title="Generate research ideas under this topic">/ideate</button>`);
  }
  if (type === "papers") {
    const anchor = (fm && fm.arxiv) ? fm.arxiv : slug;
    buttons.push(`<button type="button" class="ghost-mini intent-btn"
                          data-skill="discover"
                          data-context='{"anchor":"${esc(anchor)}"}'
                          title="Find papers related to this one">/discover</button>`);
  }
  // /edit is universal — it edits the current entity
  buttons.push(`<button type="button" class="ghost-mini intent-btn"
                        data-skill="edit"
                        data-context='{"type":"${esc(type)}","slug":"${esc(slug)}"}'
                        title="Edit this entity in natural language via /edit">/edit</button>`);
  return buttons.join("");
}

function wireIntentButtons(type, slug, fm) {
  document.querySelectorAll(".intent-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      let ctx = {};
      try { ctx = JSON.parse(btn.dataset.context || "{}"); } catch { /* ignore */ }
      triggerIntent(btn.dataset.skill, ctx);
    });
  });
}

// --- shared <datalist> populated once per session --------------------------

function ensureEntityDatalist() {
  if (document.getElementById("entity-slug-list")) return;
  const list = document.createElement("datalist");
  list.id = "entity-slug-list";
  for (const [t, items] of Object.entries(state.entitiesByType)) {
    for (const e of items) {
      if (!e.slug) continue;
      const opt = document.createElement("option");
      opt.value = `${t}/${e.slug}`;
      opt.label = `${e.title || e.name || e.slug} (${t})`;
      list.appendChild(opt);
    }
  }
  document.body.appendChild(list);
}

function ensurePaperDatalist() {
  if (document.getElementById("paper-slug-list")) return;
  const list = document.createElement("datalist");
  list.id = "paper-slug-list";
  for (const e of state.entitiesByType.papers || []) {
    const opt = document.createElement("option");
    opt.value = `papers/${e.slug}`;
    opt.label = e.title || e.slug;
    list.appendChild(opt);
  }
  document.body.appendChild(list);
}

// --- edge-add popover -------------------------------------------------------

function wireEdgeAddPopover(type, slug) {
  const btn = document.getElementById("add-edge-btn");
  const pop = document.getElementById("edge-popover");
  const toInput = document.getElementById("edge-to");
  const typeSel = document.getElementById("edge-type");
  const evidenceTa = document.getElementById("edge-evidence");
  const confSel = document.getElementById("edge-confidence");
  const symCb = document.getElementById("edge-symmetric");
  const saveBtn = document.getElementById("edge-save");
  const cancelBtn = document.getElementById("edge-cancel");
  const statusEl = document.getElementById("edge-status");
  if (!btn || !pop) return;

  // Populate edge-type dropdown grouped by workflow
  const groups = new Map();
  for (const [et, wf] of Object.entries(EDGE_TYPE_WORKFLOW)) {
    if (et === "cites") continue;  // cites lives in citations.jsonl, not edges.jsonl
    if (!groups.has(wf)) groups.set(wf, []);
    groups.get(wf).push(et);
  }
  typeSel.innerHTML = [...groups.entries()].map(([wf, types]) => `
    <optgroup label="${wf}">
      ${types.map((et) => `<option value="${et}">${et}</option>`).join("")}
    </optgroup>
  `).join("");

  btn.addEventListener("click", () => {
    pop.hidden = false;
    statusEl.hidden = true;
    saveBtn.disabled = false;
    toInput.value = "";
    evidenceTa.value = "";
    symCb.checked = false;
    confSel.value = "";
    toInput.focus();
  });
  cancelBtn.addEventListener("click", () => { pop.hidden = true; });
  pop.addEventListener("click", (ev) => { if (ev.target === pop) pop.hidden = true; });

  saveBtn.addEventListener("click", async () => {
    const to = toInput.value.trim();
    const etype = typeSel.value;
    const evidence = evidenceTa.value.trim();
    const confidence = confSel.value;
    const symmetric = symCb.checked;
    if (!to) {
      statusEl.hidden = false;
      statusEl.textContent = "target is required";
      return;
    }
    if (!to.includes("/")) {
      statusEl.hidden = false;
      statusEl.textContent = `target must be type/slug (e.g. papers/${to})`;
      return;
    }
    saveBtn.disabled = true;
    statusEl.hidden = false;
    statusEl.textContent = "saving…";
    try {
      await postEdge({
        from: `${type}/${slug}`,
        to,
        type: etype,
        evidence: evidence || undefined,
        confidence: confidence || undefined,
        symmetric: symmetric || undefined,
      });
      // Refresh the in-memory graph indexes so the right-pane reflects it
      await refreshGraphIndex();
      showToast(
        `Added edge <code>${esc(etype)}</code>: ` +
        `${esc(type)}/${esc(slug)} &rarr; ${esc(to)}`,
        4000,
      );
      pop.hidden = true;
      const mount = document.getElementById("view");
      if (mount) await viewEntity(mount, type, slug);
    } catch (err) {
      statusEl.textContent = `ERROR: ${err.message}`;
      saveBtn.disabled = false;
    }
  });
}

// --- citation-add popover (papers only) ------------------------------------

function wireCiteAddPopover(type, slug) {
  const btn = document.getElementById("add-cite-btn");
  const pop = document.getElementById("cite-popover");
  const toInput = document.getElementById("cite-to");
  const sourceSel = document.getElementById("cite-source");
  const saveBtn = document.getElementById("cite-save");
  const cancelBtn = document.getElementById("cite-cancel");
  const statusEl = document.getElementById("cite-status");
  if (!btn || !pop) return;

  btn.addEventListener("click", () => {
    pop.hidden = false;
    statusEl.hidden = true;
    saveBtn.disabled = false;
    toInput.value = "";
    sourceSel.value = "manual";
    toInput.focus();
  });
  cancelBtn.addEventListener("click", () => { pop.hidden = true; });
  pop.addEventListener("click", (ev) => { if (ev.target === pop) pop.hidden = true; });

  saveBtn.addEventListener("click", async () => {
    const to = toInput.value.trim();
    const source = sourceSel.value;
    if (!to) {
      statusEl.hidden = false;
      statusEl.textContent = "target paper is required";
      return;
    }
    saveBtn.disabled = true;
    statusEl.hidden = false;
    statusEl.textContent = "saving…";
    try {
      await postCitation({ from: `${type}/${slug}`, to, source });
      await refreshGraphIndex();
      showToast(
        `Added citation: ${esc(type)}/${esc(slug)} &rarr; ${esc(to)} ` +
        `<span class="muted small">(source: ${esc(source)})</span>`,
        4000,
      );
      pop.hidden = true;
      const mount = document.getElementById("view");
      if (mount) await viewEntity(mount, type, slug);
    } catch (err) {
      statusEl.textContent = `ERROR: ${err.message}`;
      saveBtn.disabled = false;
    }
  });
}

// Re-fetch /api/graph and rebuild forward+backlink indexes after a write so
// the next viewEntity() render sees the new edge in the right pane.
async function refreshGraphIndex() {
  try {
    const g = await getGraph();
    state.backlinkIndex.clear();
    state.forwardIndex.clear();
    function pushIndex(idx, key, entry) {
      const arr = idx.get(key) || [];
      arr.push(entry);
      idx.set(key, arr);
    }
    for (const e of g.edges || []) {
      const meta = { type: e.type, evidence: e.evidence || "", confidence: e.confidence || "" };
      pushIndex(state.backlinkIndex, e.to,   { source: e.from, ...meta });
      pushIndex(state.forwardIndex,  e.from, { target: e.to,   ...meta });
    }
    for (const c of g.citations || []) {
      const meta = { type: "cites", evidence: "", confidence: "" };
      pushIndex(state.backlinkIndex, c.to,   { source: c.from, ...meta });
      pushIndex(state.forwardIndex,  c.from, { target: c.to,   ...meta });
    }
  } catch (err) {
    console.warn("graph refresh failed:", err);
  }
}

// --- Phase 4 edit popover --------------------------------------------------

const EDITABLE_FIELDS = {
  papers: ["tags", "importance", "tldr", "contribution_type", "datasets", "code_url", "venue", "year"],
  concepts: ["tags", "aliases", "maturity", "definition", "related_concepts"],
  topics: ["tags", "key_venues"],
  people: ["research_areas", "affiliation", "homepage", "scholar"],
  ideas: ["tags", "status", "priority", "target_venue", "novelty_score", "failure_reason"],
  experiments: ["tags", "status", "outcome", "key_result"],
  methods: ["tags", "type", "code_repo", "source_papers"],
  Summary: ["tags", "scope", "key_topics"],
  foundations: ["tags", "aliases", "status"],
};
const LIST_FIELDS = new Set([
  "tags", "aliases", "related_concepts", "research_areas",
  "key_venues", "key_topics", "contribution_type", "datasets",
  "source_papers",
]);

function wireEditPopover(type, slug, fm) {
  const btn = document.getElementById("edit-field-btn");
  const pop = document.getElementById("edit-popover");
  const fieldSel = document.getElementById("edit-field");
  const valInput = document.getElementById("edit-value");
  const appendCb = document.getElementById("edit-append");
  const saveBtn = document.getElementById("edit-save");
  const cancelBtn = document.getElementById("edit-cancel");
  const statusEl = document.getElementById("edit-status");
  if (!btn || !pop) return;

  const fields = EDITABLE_FIELDS[type] || ["tags"];
  fieldSel.innerHTML = fields.map(
    (f) => `<option value="${f}">${f}</option>`,
  ).join("");

  function refreshDefaults() {
    const f = fieldSel.value;
    const isList = LIST_FIELDS.has(f);
    appendCb.checked = isList;
    appendCb.parentElement.style.display = isList ? "" : "none";
    const cur = fm[f];
    if (isList) {
      valInput.placeholder = `single value to append (e.g. "phase4-test")`;
      valInput.value = "";
    } else {
      valInput.placeholder = "new value";
      valInput.value = (cur === undefined || cur === null) ? "" : String(cur);
    }
  }
  fieldSel.addEventListener("change", refreshDefaults);
  refreshDefaults();

  btn.addEventListener("click", () => {
    pop.hidden = false;
    statusEl.hidden = true;
    valInput.focus();
  });
  cancelBtn.addEventListener("click", () => { pop.hidden = true; });
  pop.addEventListener("click", (ev) => { if (ev.target === pop) pop.hidden = true; });

  saveBtn.addEventListener("click", async () => {
    const field = fieldSel.value;
    let valueRaw = valInput.value;
    let value = valueRaw;
    const append = appendCb.checked;
    if (value === "" && !append) {
      statusEl.hidden = false;
      statusEl.textContent = "value is empty";
      return;
    }
    // Coerce numeric-looking input for known scalar number fields
    if (field === "importance" || field === "priority" || field === "year") {
      const n = Number(value);
      if (!Number.isNaN(n)) value = n;
    }
    if (field === "confidence") {
      const n = Number(value);
      if (!Number.isNaN(n)) value = n;
    }
    saveBtn.disabled = true;
    statusEl.hidden = false;
    statusEl.textContent = "saving…";
    try {
      await patchEntity(type, slug, { field, value, append });
      // Stash the change so the next render can highlight the new chip
      pendingHighlight = {
        type, slug, field,
        value: append ? valueRaw : String(value),
        append,
        at: Date.now(),
      };
      // Persistent toast — survives the re-render below
      showToast(
        `${append ? "Added" : "Set"} ${esc(field)}` +
        (append ? `: <code>${esc(valueRaw)}</code>` : ` to <code>${esc(String(value))}</code>`) +
        ` &middot; <span class="muted">wiki/${esc(type)}/${esc(slug)}.md</span>`,
        4000,
      );
      // Close popover, re-render to fetch the fresh frontmatter
      pop.hidden = true;
      const mount = document.getElementById("view");
      if (mount) await viewEntity(mount, type, slug);
    } catch (err) {
      statusEl.textContent = `ERROR: ${err.message}`;
      saveBtn.disabled = false;
    }
  });
}

// --- just-added highlight (Phase 4 visible feedback) -----------------------

let pendingHighlight = null;  // { type, slug, field, value, append, at }

function applyJustAddedHighlight(type, slug) {
  if (!pendingHighlight) return;
  if (pendingHighlight.type !== type || pendingHighlight.slug !== slug) return;
  if (Date.now() - pendingHighlight.at > 5000) {
    pendingHighlight = null;
    return;
  }
  const { value } = pendingHighlight;
  // Find a chip whose visible text matches the just-added value
  const chips = document.querySelectorAll(".metadata .chip, .metadata .chip.tag");
  for (const chip of chips) {
    if (chip.textContent.trim() === String(value).trim()) {
      chip.classList.add("just-added");
      setTimeout(() => chip.classList.remove("just-added"), 2200);
      break;
    }
  }
  pendingHighlight = null;
}

function renderMetadata(type, fm) {
  const chips = [];
  if (typeof fm.importance === "number") {
    chips.push(`<span class="chip importance imp-${fm.importance}">★${fm.importance}</span>`);
  }
  if (fm.status) {
    chips.push(`<span class="chip status">${esc(fm.status)}</span>`);
  }
  if (fm.maturity) {
    chips.push(`<span class="chip status">${esc(fm.maturity)}</span>`);
  }
  if (typeof fm.confidence === "number") {
    chips.push(`<span class="chip">conf ${fm.confidence.toFixed(2)}</span>`);
  }
  if (fm.domain) {
    chips.push(`<span class="chip">${esc(fm.domain)}</span>`);
  }
  if (fm.year) {
    chips.push(`<span class="chip">${esc(String(fm.year))}</span>`);
  }
  if (fm.venue) {
    chips.push(`<span class="chip">${esc(fm.venue)}</span>`);
  }
  if (fm.affiliation) {
    chips.push(`<span class="chip">${esc(fm.affiliation)}</span>`);
  }
  if (fm.arxiv) {
    chips.push(`<a class="chip ext" target="_blank" rel="noopener" href="https://arxiv.org/abs/${esc(fm.arxiv)}">arXiv:${esc(fm.arxiv)}</a>`);
  }
  if (fm.code_url) {
    chips.push(`<a class="chip ext" target="_blank" rel="noopener" href="${esc(fm.code_url)}">code</a>`);
  }
  if (fm.homepage) {
    chips.push(`<a class="chip ext" target="_blank" rel="noopener" href="${esc(fm.homepage)}">homepage</a>`);
  }
  for (const t of (fm.tags || []).slice(0, 8)) {
    chips.push(
      `<a class="chip tag" href="#/tag/${encodeURIComponent(t)}" title="all entities tagged ${esc(t)}">${esc(t)}</a>`
    );
  }
  if (chips.length === 0) return "";
  return `<div class="metadata">${chips.join("")}</div>`;
}

// --- viewTag: cross-type list of all entities sharing a tag ----------------

export function viewTag(mount, tagname) {
  const groups = {};
  let total = 0;
  for (const t of Object.keys(ENTITY_LABEL)) {
    const matches = (state.entitiesByType[t] || []).filter(
      (e) => Array.isArray(e.tags) && e.tags.includes(tagname),
    );
    if (matches.length) {
      // Sort by importance desc, then title asc — same as viewList
      matches.sort((a, b) => {
        const ia = typeof a.importance === "number" ? a.importance : 3;
        const ib = typeof b.importance === "number" ? b.importance : 3;
        if (ib !== ia) return ib - ia;
        return (a.title || a.slug || "").localeCompare(b.title || b.slug || "");
      });
      groups[t] = matches;
      total += matches.length;
    }
  }

  const sections = Object.entries(groups).map(([t, items]) => {
    const rows = items.map((e) => {
      const title = e.title || e.name || e.slug;
      const imp = typeof e.importance === "number" ? e.importance : null;
      const impHtml = imp ? `<span class="chip importance imp-${imp}">★${imp}</span>` : "";
      return `
        <a class="row" href="#/reader/${t}/${esc(e.slug)}">
          <div class="row-title">${esc(title)}</div>
          <div class="row-meta">${impHtml}</div>
        </a>
      `;
    }).join("");
    return `
      <section class="dash-card">
        <h3>${esc(ENTITY_LABEL[t] || t)} <span class="muted small">(${items.length})</span></h3>
        <div class="list">${rows}</div>
      </section>
    `;
  }).join("");

  mount.innerHTML = `
    <div class="breadcrumb">
      <a href="#/">Reader</a> &rsaquo;
      <strong>tag: <code>${esc(tagname)}</code></strong>
      <span class="muted">${total} ${total === 1 ? "entity" : "entities"}</span>
    </div>
    ${total === 0
      ? `<p class="muted">No entities tagged <code>${esc(tagname)}</code>. Add one via "edit field…" on any page.</p>`
      : `<div class="dashboard">${sections}</div>`}
  `;
}

// --- 404 / error views ------------------------------------------------------

export function view404(mount, message) {
  mount.innerHTML = `
    <div class="breadcrumb"><a href="#/">Reader</a></div>
    <h2>Not found</h2>
    <p class="muted">${esc(message)}</p>
    <p><a href="#/">&larr; back to entity types</a></p>
  `;
}

export function viewError(mount, err) {
  mount.innerHTML = `
    <div class="breadcrumb"><a href="#/">Reader</a></div>
    <h2>Error</h2>
    <pre class="error">${esc(err.message || String(err))}</pre>
    <p><a href="#/">&larr; back</a></p>
  `;
}

// --- escape helper ----------------------------------------------------------

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}
