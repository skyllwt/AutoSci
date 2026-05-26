// Fetch wrappers used by all views. Phase 1: GET-only. Phase 4+ adds writes.

import { state } from "./state.js";

const BASE = "";  // same-origin

// `cache: "no-store"` because the SPA writes (PATCH/POST) routinely change
// the same resources we GET. Without this, the browser may serve a stale
// copy of /api/entities/{type}/{slug} after a PATCH and the user sees
// "no change" on the page even though the file was updated correctly.
const NO_STORE = { cache: "no-store" };

export async function fetchJSON(path) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    ...NO_STORE,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} from ${url}`);
  }
  return res.json();
}

export async function fetchText(path) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    ...NO_STORE,
    headers: { Accept: "text/plain, text/markdown, text/*" },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} from ${url}`);
  }
  return res.text();
}

// --- Phase 1 endpoints ------------------------------------------------------

// Re-exported from schema.js so existing `import { ENTITY_DIRS } from "./api.js"`
// callers keep working. Single source of truth lives in modules/schema.js.
export { ENTITY_DIRS } from "./schema.js";

export function getStats() {
  return fetchJSON("/api/stats");
}

export function getEntities(type) {
  return fetchJSON(`/api/entities/${encodeURIComponent(type)}`);
}

export function getEntity(type, slug) {
  return fetchJSON(
    `/api/entities/${encodeURIComponent(type)}/${encodeURIComponent(slug)}`
  );
}

export function getEntityRaw(type, slug) {
  return fetchText(
    `/api/entities/${encodeURIComponent(type)}/${encodeURIComponent(slug)}/raw`
  );
}

export function getGraph() {
  return fetchJSON("/api/graph");
}

// --- Phase 3 endpoints ------------------------------------------------------

export function getMaturity() {
  return fetchJSON("/api/maturity");
}

export function getOpenQuestions() {
  return fetchText("/api/open-questions");
}

export function getLog(tail = 200) {
  return fetchJSON(`/api/log?tail=${tail}`);
}

// --- Phase 4 write endpoints ------------------------------------------------

async function sendJSON(path, method, body) {
  const res = await fetch(`${BASE}${path}`, {
    ...NO_STORE,
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  let payload = null;
  try { payload = await res.json(); } catch { /* may be empty */ }
  if (!res.ok) {
    const msg = payload && payload.error
      ? payload.error
      : `${res.status} ${res.statusText}`;
    const err = new Error(msg);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }
  // Mark our own write so the SSE listener knows to suppress the
  // redundant reboot caused by *this* request's file changes.
  state.lastWriteAt = Date.now();
  return payload;
}

export function patchEntity(type, slug, { field, value, append = false }) {
  return sendJSON(
    `/api/entities/${encodeURIComponent(type)}/${encodeURIComponent(slug)}`,
    "PATCH",
    { field, value, append },
  );
}

export function postEdge({ from, to, type, evidence, confidence, symmetric }) {
  return sendJSON("/api/edges", "POST",
    { from, to, type, evidence, confidence, symmetric });
}

export function postCitation({ from, to, source }) {
  return sendJSON("/api/citations", "POST", { from, to, source });
}

export function postLog(message) {
  return sendJSON("/api/log", "POST", { message });
}

export function postRegenerate(kind) {
  return sendJSON(`/api/regenerate/${encodeURIComponent(kind)}`, "POST", {});
}

// --- Phase 5: skill-intent endpoints ----------------------------------------
// Returns command guidance (no execution). See app/modules/intent.js.

export function postIntent(skill, body = {}) {
  return sendJSON(`/api/intent/${encodeURIComponent(skill)}`, "POST", body);
}

// --- Phase 6: deterministic skill operations exposed in-browser -------------
//
// /check has a fully deterministic core (tools/lint.py) — no LLM needed.
// /discover writes ranked candidate JSONs to .checkpoints/, which we can
// browse without re-running anything. Both bypass the intent-modal flow.

export function getLint() {
  return fetchJSON("/api/lint");
}

export function postLintFix({ dryRun = false } = {}) {
  return sendJSON("/api/lint/fix", "POST", { dry_run: dryRun });
}

export function listDiscoverCheckpoints() {
  return fetchJSON("/api/checkpoints/discover");
}

export function getDiscoverCheckpoint(name) {
  return fetchJSON(`/api/checkpoints/discover/${encodeURIComponent(name)}`);
}
