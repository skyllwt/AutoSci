// Bootstrap: load entity listings (for slug map) + graph (for backlinks)
// in parallel, populate state, then start the router.
//
// SSE live-reload: subscribes to /api/events; when wiki/ files change
// outside the SPA's own writes, re-fetch state and trigger a re-render.

import { getEntities, getGraph } from "./api.js";
import { ENTITY_DIRS, TYPE_PRECEDENCE } from "./schema.js";
import { state, markReady } from "./state.js";
import { startRouter } from "./router.js";

// First-time bootstrap: load + wire jump-input + start router. Called once
// on page load. Subsequent SSE-triggered refreshes call reloadData() only.
async function boot() {
  try {
    await reloadData();
    setupJumpInput();
    markReady();
    document.dispatchEvent(new Event("wiki:ready"));
    startRouter("view");
    setupLiveReload();
  } catch (err) {
    state.bootError = String(err);
    console.error("boot failed:", err);
    const mount = document.getElementById("view");
    if (mount) {
      mount.innerHTML = `
        <h2>Failed to load wiki data</h2>
        <pre class="error">${err.message || err}</pre>
        <p>Is the API server running on the same origin? Check <code>tools/serve.py</code>.</p>
      `;
    }
  }
}

// Re-fetch all wiki data and rebuild state caches. Safe to call repeatedly.
async function reloadData() {
  const banner = document.getElementById("boot-status");
  const [graph, ...listings] = await Promise.all([
    getGraph().catch((err) => {
      console.warn("graph fetch failed:", err);
      return { edges: [], citations: [] };
    }),
    ...ENTITY_DIRS.map((t) =>
      getEntities(t).catch((err) => {
        console.warn(`entities ${t} fetch failed:`, err);
        return [];
      })
    ),
  ]);

  // Wipe and rebuild — state is reused so existing references stay valid
  state.slugMap.clear();
  state.backlinkIndex.clear();
  state.forwardIndex.clear();
  for (const k of Object.keys(state.entitiesByType)) delete state.entitiesByType[k];

  let totalSlugs = 0;
  ENTITY_DIRS.forEach((type, i) => {
    const arr = listings[i] || [];
    state.entitiesByType[type] = arr;
    for (const e of arr) {
      if (!e.slug) continue;
      const existing = state.slugMap.get(e.slug) || [];
      existing.push({ type, title: e.title || e.name || e.slug });
      state.slugMap.set(e.slug, existing);
      totalSlugs++;
    }
  });

  function pushIndex(idx, key, entry) {
    const arr = idx.get(key) || [];
    arr.push(entry);
    idx.set(key, arr);
  }
  for (const e of graph.edges || []) {
    const meta = { type: e.type, evidence: e.evidence || "", confidence: e.confidence || "" };
    pushIndex(state.backlinkIndex, e.to,   { source: e.from, ...meta });
    pushIndex(state.forwardIndex,  e.from, { target: e.to,   ...meta });
  }
  for (const c of graph.citations || []) {
    const meta = { type: "cites", evidence: "", confidence: "" };
    pushIndex(state.backlinkIndex, c.to,   { source: c.from, ...meta });
    pushIndex(state.forwardIndex,  c.from, { target: c.to,   ...meta });
  }

  if (banner) {
    banner.textContent = `${totalSlugs} pages · ${(graph.edges || []).length} edges`;
  }
}

// --- SSE live-reload --------------------------------------------------------

let eventSource = null;
const SELF_WRITE_GRACE_MS = 2500;  // suppress reload triggered by our own write

function setupLiveReload() {
  if (!window.EventSource) {
    console.info("EventSource unavailable — live-reload disabled");
    return;
  }
  try {
    eventSource = new EventSource("/api/events");
  } catch (err) {
    console.warn("failed to open /api/events:", err);
    return;
  }

  eventSource.addEventListener("change", async (ev) => {
    // Suppress redundant reload caused by our own PATCH/POST a moment ago
    if (Date.now() - state.lastWriteAt < SELF_WRITE_GRACE_MS) return;

    let info = {};
    try { info = JSON.parse(ev.data || "{}"); } catch { /* ignore */ }
    const indicator = document.getElementById("live-indicator");
    if (indicator) indicator.classList.add("active");

    try {
      await reloadData();
      // Re-render current view by dispatching hashchange (the router already
      // listens for it). This keeps the user on whatever page they were on.
      window.dispatchEvent(new HashChangeEvent("hashchange"));
      console.info(`live-reload: ${info.count || "?"} files changed externally`);
    } catch (err) {
      console.warn("live-reload reloadData failed:", err);
    } finally {
      if (indicator) {
        setTimeout(() => indicator.classList.remove("active"), 600);
      }
    }
  });

  eventSource.onerror = (err) => {
    // EventSource auto-reconnects with backoff; just log.
    console.debug("EventSource error (will auto-reconnect):", err);
  };
}

// --- jump-to-slug input (topnav) -------------------------------------------
//
// Populates the <datalist> with all known slugs after boot, and on Enter
// navigates to #/reader/{type}/{slug}. Uses TYPE_PRECEDENCE from schema.js
// for ambiguous slugs (same precedence the wikilink resolver uses).

function setupJumpInput() {
  const input = document.getElementById("jump-input");
  const list = document.getElementById("slug-list");
  if (!input || !list) return;

  // Populate datalist (browser-native autocomplete; one option per slug).
  const opts = [];
  for (const [slug, matches] of state.slugMap) {
    const m0 = matches[0];
    const label = matches.length > 1
      ? `${m0.title} · (${matches.map(x => x.type).join("/")})`
      : `${m0.title} · ${m0.type}`;
    opts.push(
      `<option value="${slug}">${escapeAttr(label)}</option>`
    );
  }
  list.innerHTML = opts.join("");
  input.disabled = false;

  function go(value) {
    const slug = value.trim();
    if (!slug) return;
    const matches = state.slugMap.get(slug);
    if (!matches || matches.length === 0) {
      input.classList.add("jump-error");
      setTimeout(() => input.classList.remove("jump-error"), 700);
      return;
    }
    let chosen = matches[0];
    for (const t of TYPE_PRECEDENCE) {
      const hit = matches.find((x) => x.type === t);
      if (hit) { chosen = hit; break; }
    }
    location.hash = `#/reader/${chosen.type}/${slug}`;
    input.value = "";
    input.blur();
  }

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      go(input.value);
    } else if (ev.key === "Escape") {
      input.value = "";
      input.blur();
    }
  });
  input.addEventListener("change", () => go(input.value));
}

function escapeAttr(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

boot();
