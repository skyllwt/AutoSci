// Wikilink resolver for [[slug]] body references.
//
// On boot, callers populate state.slugMap from the 9 entity-type listings.
// resolveWikilinks() takes rendered HTML (output of marked.parse) and
// rewrites every [[slug]] to a hash-routed anchor. Unknown slugs render as
// red dashed broken-link spans.

import { state } from "./state.js";
import { TYPE_PRECEDENCE } from "./schema.js";

// Regex matches [[slug]] outside of <code> / <pre> blocks. We do a simple
// whole-document regex; marked.js already escapes content inside code blocks
// to entities (e.g. &lt;), so [[ in code stays as [[ but is wrapped in
// <code>; we explicitly skip replacements inside <code>...</code> spans.
const WIKILINK_RE = /\[\[([a-z0-9][a-z0-9-]*)\]\]/g;
const CODE_BLOCK_RE = /<(code|pre)\b[^>]*>[\s\S]*?<\/\1>/g;

export function resolveWikilinks(html) {
  // Replace [[slug]] outside code blocks. Strategy: split by code-block
  // boundaries, transform non-code segments, rejoin.
  const segments = [];
  let lastIndex = 0;
  let m;
  CODE_BLOCK_RE.lastIndex = 0;
  while ((m = CODE_BLOCK_RE.exec(html)) !== null) {
    segments.push({ kind: "text", value: html.slice(lastIndex, m.index) });
    segments.push({ kind: "code", value: m[0] });
    lastIndex = m.index + m[0].length;
  }
  segments.push({ kind: "text", value: html.slice(lastIndex) });

  return segments
    .map((s) => (s.kind === "code" ? s.value : transformSegment(s.value)))
    .join("");
}

function transformSegment(text) {
  return text.replace(WIKILINK_RE, (_full, slug) => renderLink(slug));
}

function renderLink(slug) {
  const matches = state.slugMap.get(slug) || [];
  if (matches.length === 0) {
    return `<span class="broken-wikilink" title="not found">[[${escapeHtml(
      slug
    )}]]</span>`;
  }
  let chosen = matches[0];
  if (matches.length > 1) {
    for (const t of TYPE_PRECEDENCE) {
      const hit = matches.find((x) => x.type === t);
      if (hit) {
        chosen = hit;
        break;
      }
    }
    console.warn(
      `wikilink ambiguous: [[${slug}]] matches`,
      matches.map((x) => x.type),
      "-> chose",
      chosen.type
    );
  }
  const href = `#/reader/${chosen.type}/${slug}`;
  const title = chosen.title || slug;
  return `<a class="wikilink" href="${href}" title="${escapeHtml(
    title
  )}">${escapeHtml(slug)}</a>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}
