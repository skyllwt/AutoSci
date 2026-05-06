// Phase 5: skill-intent UX.
//
// triggerIntent(skill, contextBody) calls POST /api/intent/{skill} and shows
// the returned command in a copy-to-clipboard modal. The SPA cannot run
// /skill (no LLM session) — this is purely a "build me the right command"
// helper that the user pastes into Claude Code.

import { postIntent } from "./api.js";
import { showToast, escHtml } from "./ui.js";

let popover = null;

function ensurePopover() {
  if (popover) return popover;
  popover = document.createElement("div");
  popover.id = "intent-popover";
  popover.className = "edit-popover";
  popover.hidden = true;
  popover.innerHTML = `
    <div class="edit-card intent-card">
      <h4 id="intent-title"></h4>
      <p id="intent-message" class="muted small"></p>
      <pre id="intent-cmd"></pre>
      <p id="intent-doc" class="muted small"></p>
      <div class="edit-actions">
        <button type="button" id="intent-copy">Copy command</button>
        <button type="button" id="intent-close" class="ghost">Close</button>
      </div>
      <p id="intent-status" class="muted small" hidden></p>
    </div>
  `;
  document.body.appendChild(popover);

  const closeBtn = popover.querySelector("#intent-close");
  const copyBtn = popover.querySelector("#intent-copy");
  const statusEl = popover.querySelector("#intent-status");
  const cmdEl = popover.querySelector("#intent-cmd");

  closeBtn.addEventListener("click", () => { popover.hidden = true; });
  popover.addEventListener("click", (ev) => {
    if (ev.target === popover) popover.hidden = true;
  });

  copyBtn.addEventListener("click", async () => {
    const text = cmdEl.textContent;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        statusEl.hidden = false;
        statusEl.textContent = "✓ Copied — paste into Claude Code.";
      } else {
        // Fallback: select the <pre> content so user can Ctrl+C
        const range = document.createRange();
        range.selectNodeContents(cmdEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        statusEl.hidden = false;
        statusEl.textContent = "Selected — press Ctrl+C / ⌘C to copy.";
      }
      setTimeout(() => { statusEl.hidden = true; }, 2800);
    } catch (err) {
      statusEl.hidden = false;
      statusEl.textContent = `clipboard error: ${err.message}`;
    }
  });

  // ESC key dismisses
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !popover.hidden) popover.hidden = true;
  });

  return popover;
}

function showIntentModal(payload) {
  const pop = ensurePopover();
  pop.querySelector("#intent-title").innerHTML =
    `Run <code>/${escHtml(payload.skill)}</code> in Claude Code`;
  pop.querySelector("#intent-message").textContent = payload.message || "";
  pop.querySelector("#intent-cmd").textContent = payload.command || "";
  const docEl = pop.querySelector("#intent-doc");
  if (payload.doc_url) {
    docEl.innerHTML = `Skill spec: <code>${escHtml(payload.doc_url)}</code>`;
    docEl.style.display = "";
  } else {
    docEl.style.display = "none";
  }
  pop.querySelector("#intent-status").hidden = true;
  pop.hidden = false;
  // Focus the copy button so Enter works as the primary action
  setTimeout(() => pop.querySelector("#intent-copy").focus(), 0);
}

export async function triggerIntent(skill, contextBody = {}) {
  try {
    const payload = await postIntent(skill, contextBody);
    showIntentModal(payload);
  } catch (err) {
    showToast(`intent failed: ${escHtml(err.message)}`, 3500);
  }
}
