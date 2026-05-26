// Phase 5/6: skill-intent UX.
//
// triggerIntent(skill, contextBody, schema?) — if schema is omitted, behaves
// as the original Phase-5 one-shot modal: POST /api/intent/{skill} and show
// the returned command for copy-paste. If a non-empty schema is passed, a
// form panel collects parameters first; on submit those values are merged
// into contextBody and the same modal opens with the parameters substituted
// in. The SPA still cannot run /skill — this is purely a "build me the
// right command, with my parameters" helper that the user pastes into
// Claude Code.

import { postIntent } from "./api.js";
import { showToast, escHtml } from "./ui.js";
import { state } from "./state.js";

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

// --- Form-first mode (Phase 6) ---------------------------------------------

let formPanel = null;

function ensureFormPanel() {
  if (formPanel) return formPanel;
  formPanel = document.createElement("div");
  formPanel.id = "intent-form-popover";
  formPanel.className = "edit-popover";
  formPanel.hidden = true;
  formPanel.innerHTML = `
    <div class="edit-card intent-card">
      <h4 id="intent-form-title"></h4>
      <p id="intent-form-message" class="muted small"></p>
      <form id="intent-form" class="intent-form"></form>
      <div class="edit-actions">
        <button type="button" id="intent-form-submit">Generate command</button>
        <button type="button" id="intent-form-cancel" class="ghost">Cancel</button>
      </div>
      <p id="intent-form-error" class="error-msg" hidden></p>
    </div>
  `;
  document.body.appendChild(formPanel);

  formPanel.addEventListener("click", (ev) => {
    if (ev.target === formPanel) formPanel.hidden = true;
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !formPanel.hidden) formPanel.hidden = true;
  });

  return formPanel;
}

function renderFormField(field) {
  const id = `intent-fld-${field.key}`;
  const requiredAttr = field.required ? " required" : "";
  const reqMark = field.required ? ' <span class="required-mark">*</span>' : "";
  const label = `<label for="${id}">${escHtml(field.label)}${reqMark}</label>`;

  if (field.type === "textarea") {
    return `
      <div class="intent-field">
        ${label}
        <textarea id="${id}" name="${escHtml(field.key)}" rows="3"${requiredAttr}></textarea>
      </div>
    `;
  }
  if (field.type === "select" && field.optionsFrom) {
    const entries = state.entitiesByType[field.optionsFrom] || [];
    if (entries.length === 0) {
      return `
        <div class="intent-field">
          <label>${escHtml(field.label)}${reqMark}</label>
          <p class="muted small">
            No <code>${escHtml(field.optionsFrom)}</code> in the wiki yet —
            create one first via the appropriate skill (e.g.
            <code>/ideate</code>) and try again.
          </p>
        </div>
      `;
    }
    const opts = entries
      .slice()
      .sort((a, b) => (a.title || a.slug).localeCompare(b.title || b.slug))
      .map((e) => {
        const display = e.title ? `${e.title} (${e.slug})` : e.slug;
        return `<option value="${escHtml(e.slug)}">${escHtml(display)}</option>`;
      })
      .join("");
    return `
      <div class="intent-field">
        ${label}
        <select id="${id}" name="${escHtml(field.key)}"${requiredAttr}>
          <option value="">— pick —</option>
          ${opts}
        </select>
      </div>
    `;
  }
  // Default: single-line text
  return `
    <div class="intent-field">
      ${label}
      <input id="${id}" name="${escHtml(field.key)}" type="text"${requiredAttr} />
    </div>
  `;
}

function showFormPanel(skill, schema, defaultContext, message, onSubmit) {
  const pop = ensureFormPanel();
  pop.querySelector("#intent-form-title").innerHTML =
    `Configure <code>/${escHtml(skill)}</code>`;
  pop.querySelector("#intent-form-message").textContent =
    message || "Fill the fields below — they will be substituted into the /skill command.";

  const form = pop.querySelector("#intent-form");
  form.innerHTML = schema.map(renderFormField).join("");

  // Pre-fill with any defaults the caller passed.
  for (const f of schema) {
    const el = form.querySelector(`[name="${CSS.escape(f.key)}"]`);
    if (el && defaultContext[f.key] != null) el.value = defaultContext[f.key];
  }

  const submitBtn = pop.querySelector("#intent-form-submit");
  const cancelBtn = pop.querySelector("#intent-form-cancel");
  const errorEl = pop.querySelector("#intent-form-error");
  errorEl.hidden = true;

  const submitHandler = (ev) => {
    if (ev) ev.preventDefault();
    const ctx = { ...defaultContext };
    for (const f of schema) {
      const el = form.querySelector(`[name="${CSS.escape(f.key)}"]`);
      if (!el) continue;
      const val = String(el.value || "").trim();
      if (f.required && !val) {
        errorEl.hidden = false;
        errorEl.textContent = `"${f.label}" is required.`;
        el.focus();
        return;
      }
      if (val) ctx[f.key] = val;
    }
    pop.hidden = true;
    onSubmit(ctx);
  };

  submitBtn.onclick = submitHandler;
  cancelBtn.onclick = () => { pop.hidden = true; };
  form.onsubmit = submitHandler;
  form.onkeydown = (ev) => {
    // Enter submits unless we're inside a textarea (multi-line input).
    if (ev.key === "Enter" && ev.target.tagName !== "TEXTAREA") {
      submitHandler(ev);
    }
  };

  pop.hidden = false;
  setTimeout(() => {
    const firstInput = form.querySelector("input, textarea, select");
    if (firstInput) firstInput.focus();
  }, 0);
}

export async function triggerIntent(skill, contextBody = {}, schema = null, options = {}) {
  // No schema → original one-shot behavior.
  if (!schema || !Array.isArray(schema) || schema.length === 0) {
    try {
      const payload = await postIntent(skill, contextBody);
      showIntentModal(payload);
    } catch (err) {
      showToast(`intent failed: ${escHtml(err.message)}`, 3500);
    }
    return;
  }
  // With schema → collect params via form, then open the same modal with
  // the parameters substituted into the generated command.
  showFormPanel(skill, schema, contextBody, options.message || null, async (ctx) => {
    try {
      const payload = await postIntent(skill, ctx);
      showIntentModal(payload);
    } catch (err) {
      showToast(`intent failed: ${escHtml(err.message)}`, 3500);
    }
  });
}
