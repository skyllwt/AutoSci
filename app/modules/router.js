// Hash router. Phase 1 routes:
//
//   #/                         -> viewIndex()
//   #/reader                   -> viewIndex()
//   #/reader/{type}            -> viewList(type)
//   #/reader/{type}/{slug}     -> viewEntity(type, slug)
//   anything else              -> view404()

import {
  viewIndex, viewList, viewEntity, viewTag, view404, viewError,
} from "./reader.js";
import { viewGraph, destroyGraph } from "./graph.js";
import { viewDashboard } from "./dashboard.js";
import { state } from "./state.js";
import { VALID_TYPES } from "./schema.js";

export function startRouter(mountId = "view") {
  const mount = document.getElementById(mountId);
  if (!mount) {
    throw new Error(`router: no #${mountId} mount point`);
  }

  async function route() {
    const hash = location.hash || "#/";
    const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);

    // Always tear down Graph view's Cytoscape instance when leaving #/graph,
    // even if the next route fails. Avoids leaking listeners and RAF.
    if (parts[0] !== "graph") destroyGraph();

    try {
      if (parts.length === 0 || parts[0] === "reader" && parts.length === 1) {
        await viewIndex(mount);
        return;
      }
      if (parts[0] === "graph") {
        await viewGraph(mount);
        return;
      }
      if (parts[0] === "dashboard") {
        await viewDashboard(mount);
        return;
      }
      if (parts[0] === "tag") {
        const tagname = parts[1];
        if (!tagname) {
          view404(mount, "missing tag name in URL");
          return;
        }
        await viewTag(mount, decodeURIComponent(tagname));
        return;
      }
      if (parts[0] !== "reader") {
        view404(mount, `route not found: ${hash}`);
        return;
      }
      const type = parts[1];
      const slug = parts[2];
      if (!VALID_TYPES.has(type)) {
        view404(mount, `unknown entity type: ${type}`);
        return;
      }
      if (!slug) {
        await viewList(mount, type);
        return;
      }
      await viewEntity(mount, type, slug);
    } catch (err) {
      console.error(err);
      viewError(mount, err);
    }
  }

  window.addEventListener("hashchange", route);
  if (state.ready) {
    route();
  } else {
    // wait for boot
    document.addEventListener("wiki:ready", route, { once: true });
  }
}

// Programmatic navigation helper (used by views to update breadcrumb links).
export function navigate(hash) {
  if (location.hash !== hash) location.hash = hash;
}
