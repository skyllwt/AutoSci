// Module-scoped caches for slug map + backlink reverse index.
// Populated once at app boot, then read-only for views.

export const state = {
  // Map<slug, [{ type, title }]> — one slug may be in multiple types
  slugMap: new Map(),
  // Map<"type/slug", [{ source, type, evidence, confidence }]>
  // ↑ "what edges point AT this node" (incoming)
  backlinkIndex: new Map(),
  // Map<"type/slug", [{ target, type, evidence, confidence }]>
  // ↑ "what edges this node points OUT to" (outgoing)
  forwardIndex: new Map(),
  // { papers: [...], concepts: [...], ... } — full frontmatter, by type
  entitiesByType: {},
  // Whether boot has finished (graph + slugMap populated)
  ready: false,
  // Last error during boot, if any (string)
  bootError: null,
  // Timestamp of most recent SPA-initiated write (ms since epoch). Used by
  // the SSE live-reload listener to suppress redundant reboots when our
  // own PATCH/POST is the cause of the file-change event.
  lastWriteAt: 0,
};

const listeners = new Set();

export function onReady(fn) {
  if (state.ready) {
    queueMicrotask(fn);
  } else {
    listeners.add(fn);
  }
}

export function markReady() {
  state.ready = true;
  for (const fn of listeners) fn();
  listeners.clear();
}
