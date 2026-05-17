---
description: Generate an academic poster from a drafted paper — distill sections into a single-page HTML poster with figures and inter-section transitions
argument-hint: "[paper-dir] [--review] [--anonymous] [--no-figures] [--no-logos] [--no-refine]"
---

# /poster

> Generate an academic HTML poster from a drafted paper. Reads `paper/main.tex`,
> section files, and figures; builds a PaperX-compatible `dag.json` intermediate;
> distills each section into a 2–5 sentence summary; selects representative figures;
> renders into a self-contained HTML poster with a 3-column auto-fit layout.

## Inputs

### Common

- `paper_dir` (optional, default `paper/`): LaTeX project directory containing `main.tex` and `sections/`
- `--review` (optional): cross-model Review LLM critique of the generated poster content
- `--anonymous` (optional): force authors to "Anonymous" regardless of `\author{}` content, the `paper/.author_display.txt` cache, or `--authors`
- `--no-figures` (optional): render every section as text-only (useful for text-heavy posters, or when figures aren't ready)
- `--no-logos` (optional): skip the affiliation/conference-logo prompts; header shows venue text only
- `--no-refine` (optional): skip Step 5.5 critique-revise (default runs 1 iteration via Claude)

### Power-user (scripted use; rarely needed in interactive runs)

- `--authors STR`: override the authors text on the poster (e.g. `--authors "Morrow Yang, Co-Author"`). Useful for one-off override; everyday use is handled by the `paper/.author_display.txt` cache populated in Step 0 Q1. Ignored if `--anonymous` is also set.
- `--venue STR`: venue text for the header right block (e.g. `"NeurIPS 2026"`). Skips Step 0 venue prompt.
- `--affiliation-logo PATH` / `--conference-logo PATH`: logo file paths (PNG/JPG/PDF); each skips the matching Step 0 prompt.
- `--layout corners|stacked` (default `corners`): header layout. `corners` = affiliation top-left, conference top-right; `stacked` = both logos in the right `.conf` area with venue text above.
- `--auto-figures`: skip the per-section figure questions; pick the largest candidate for each section (legacy behavior). The ⚠ wide marker on aspect-extreme figures (≥ 2.0 or ≤ 0.5) is informational only — every selected figure renders inline within its section regardless of aspect.
- `--refine-iterations N` (default 1, cap 2): number of critique-revise passes in Step 5.5. `0` is equivalent to `--no-refine`. Bump to 2 if a first pass might not converge on dense content.

## Outputs

- `poster/dag.json` — PaperX-compatible intermediate (reusable by future `/slides`, `/pr`)
- `poster/outline.html` — concatenated `<section>` blocks before template injection
- `poster/poster.html` — final self-contained HTML poster (open in browser; **Cmd/Ctrl+P → Save as PDF** if you need a PDF — see Step 7 report for print settings)
- `poster/poster.png` — rendered screenshot at 2× CSS dimensions (default 2800×1800) — see Step 5b
- `poster/images/` — figures copied/converted (PDF→PNG @ 200 DPI) from `paper/figures/`
- **POSTER_REPORT** (printed to terminal)
- `wiki/log.md` — appended log entry

## Wiki Interaction

### Reads
- `paper/main.tex` + `paper/sections/*.tex` + `paper/figures/` — paper source
- `wiki/outputs/paper-plan-*.md` (optional) — narrative arc, figure plan, evidence map
- `wiki/ideas/*.md` (optional) — hypothesis, novelty argument for poster opening
- `wiki/experiments/*.md` (optional) — key results, outcome numbers for headline callouts
- `.claude/skills/shared-references/academic-writing.md` — de-AI polish rules

### Writes
- `poster/` directory (all files listed in Outputs)
- `wiki/log.md` — appended

### Graph edges created
- None (the poster is a presentation artifact, not a knowledge entity)

## Workflow

**Precondition**: confirm `paper/main.tex` exists. If not, error with "Run /paper-draft first."

### Step 0: Interactive header configuration

Goal: collect venue text and (optionally) two logos to render in the poster header. Skipped silently for any field the user already supplied as a CLI flag.

The flow uses `AskUserQuestion` for the yes/no/layout choices, then asks for paths and venue text in free-form (Claude reads the next user message as the answer).

1. **Authors** — paper-level metadata, resolved with this precedence:

   1. `--authors STR` flag → use that, do not prompt, do not persist.
   2. `--anonymous` flag → force "Anonymous", do not prompt, do not persist.
   3. `paper/.author_display.txt` exists → use its content, do not prompt. This is the "ask once, reuse" cache. Future `/paper-draft` is expected to seed this file during the writing stage; until then, `/poster` Step 0 maintains it (see below).
   4. dag.json root `content` (from `\author{...}` in `main.tex`) is non-empty AND not literally "Anonymous" → use it, do not prompt.
   5. **Otherwise (anonymized paper, no cached display name)**: ASK the user.

   Asking flow (only when reached):
   - Use `AskUserQuestion`:
     - `"Keep 'Anonymous' (double-blind submission)"` (Recommended)
     - `"Provide author names (I'll ask for the string)"`
   - If "Provide author names": ask free-text *"What author string should appear? e.g. `Morrow Yang, Co-Author Name`. Reply with the string, or `skip` to keep 'Anonymous'."* Take the next user message as the authors string.
   - **Persist the answer** to `paper/.author_display.txt` (one line, no trailing newline beyond the string). On the *next* `/poster` run, the file exists → step 0 Q1 is silent. To change later, the user edits or deletes that file.
   - Either branch ("Keep Anonymous" or a provided string) gets persisted — the goal is *no more prompts unless the user opts back in by removing the file*.

2. **Venue text** — if `--venue` was not provided:
   - Ask: *"What venue text should appear in the poster header? e.g. `NeurIPS 2026`. Reply with the text, or `skip` to leave it blank."*
   - Take the next user message verbatim. Treat the literal string `skip` (case-insensitive) as empty.

3. **Affiliation logo** — if `--affiliation-logo` was not provided AND `--no-logos` was not passed:
   - Use `AskUserQuestion` with options: `"Yes, I have a logo file"` / `"No, skip the affiliation logo"`.
   - If yes: ask *"What's the path to the affiliation logo? (PNG / JPG / PDF; relative or absolute)."* Take the next user message as the path. Verify the file exists; if not, re-ask once with the resolved-path issue surfaced, then either accept a new path or treat as skipped.

4. **Conference / journal logo** — if `--conference-logo` was not provided AND `--no-logos` was not passed:
   - Same flow as the affiliation logo (yes/no via `AskUserQuestion`, path via free text).

5. **Layout** — if at least one logo was provided AND `--layout` was not passed:
   - Use `AskUserQuestion` with options:
     - `"corners — affiliation top-left, conference top-right"` (Recommended)
     - `"stacked — both logos stacked in the right conf area, venue text on top"`
   - If only `--venue` and no logos: skip the layout question (default `corners` is fine — only the venue text slot is used).

6. **Final summary** — print one line:
   - `Header config: authors='{...}', venue='{...}', affiliation={path|none}, conference={path|none}, layout={...}`

The authors string is applied in Step 5 via `python3 tools/poster.py inject-title --authors "..."`; the venue/logos are applied via `python3 tools/poster.py inject-header`.

### Step 1: Build dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

Add `--anonymous` if the user passed it.

The bridge produces three node types:
- **Root** (`level: 0`): paper title in `name`, authors in `content`, ordered section names in `edge`
- **Section** (`level: 1`): section heading in `name`, full prose in `content`, figure refs in `visual_node`
- **Visual** (`level: 2`): markdown image ref in `name`, caption in `content`, `WxH` in `resolution`

`wiki2dag.py` preserves the paper's:
- **Math**: `$…$`, `$$…$$`, `\(…\)`, `\[…\]` pass through into section content untouched, then render via KaTeX in the poster HTML. Macros defined in `math_commands.tex` are expanded and any surviving `\ensuremath{X}` wrapper is unwrapped to `$X$` so KaTeX picks it up.
- **Citations** — *dropped by default*: `\citep{key}` / `\citet{...}` markers are stripped to empty. Real-world conference posters (per CCF-A research) typically omit inline citation markers because there's no room for a reference list. Pass `--citations` to `wiki2dag.py build` if you want them back as `[N]` / `[N, M]` (built from a first-appearance `bibkey → ordinal` map). Future poster styles that render a reference footer can opt in.
- **Tables**: `\begin{table}…\end{table}` envs (including tables inlined via `\input{tables/foo}`) are converted to live HTML `<table class="poster-table">` blocks with the booktabs caption rendered as a `<caption>` and `\multicolumn`, `\textbf`, `\emph`, `\textit`, `\texttt` handled at the cell level. The Step 3 LLM sees this HTML inside `SECTION_JSON.content` and must include it verbatim after the summary paragraph (see Step 3). The fit() algorithm sizes table fonts alongside body text; if a table still clips, Step 5.5 sees it via the DOM overflow probe and trims.
- **TikZ figures**: `\begin{figure}` envs containing `\begin{tikzpicture}` but no `\includegraphics{}` are auto-rasterized to `paper/figures/_tikz_<sec>_<label>.png` via `tools/rasterize_latex.py` (pdflatex + pdftoppm). The resulting PNG is a regular visual node from the bridge's perspective — Step 3 picks it up exactly like any other figure. If `\includegraphics{}` is also present in the same env, the existing pipeline takes precedence (TikZ extraction is skipped). Failed rasterizations are logged to stderr and the figure is dropped; the rest of the pipeline continues. Cached across runs — delete the PNG to force regeneration.

### Step 2: Compile WIKI_CONTEXT (optional)

Goal: optionally ground the Step 3 distillation prompts in the paper's own planning artifacts (hypothesis statement, novelty argument, key-result numbers from linked ideas/experiments). Always surface what's happening — do not adopt silently.

**Detection + transparency**:

- **No plan file present**: print one line — `Step 2: no paper-plan-*.md found in wiki/outputs/ — Step 3 will run without WIKI_CONTEXT.` Skip to Step 2.5.

- **Plan file present**: print one line summarizing what was found, e.g. `Step 2: found wiki/outputs/paper-plan-2026-05-17.md (3 linked ideas, 2 experiments).` Then `AskUserQuestion`:
  - `"Yes — adopt as WIKI_CONTEXT grounding"` (Recommended)
  - `"No — distill from paper source only"`

If the user picks **Yes**: read the plan for venue, narrative arc, and linked idea slugs. For each idea slug, read `wiki/ideas/<slug>.md` for the hypothesis statement and novelty argument. For each linked `wiki/experiments/*.md`, read the `outcome` and `key_result` fields. Assemble into a single `WIKI_CONTEXT` string keyed by section:

```
[INTRODUCTION]
hypothesis: <one sentence from idea>
novelty: <one sentence from idea>

[EXPERIMENTS]
key_result: <headline numbers from experiments>
outcome: <one line summary>
```

If the user picks **No**: leave `WIKI_CONTEXT` empty.

This block is passed into the Step 3 prompt under the `{WIKI_CONTEXT}` slot. The Step 3 prompt explicitly tolerates an empty slot.

### Step 2.5: Figure selection

Goal: decide which figure (if any) belongs in each selected section. Runs after `dag.json` is built and before any LLM distillation, so the figure choice becomes an *input* to Step 3 rather than something the LLM guesses. Every figure renders inline within its section; the ⚠ wide marker in the manifest is purely informational — a heads-up that an aspect-extreme figure may look cramped in a single column, so the user can pick an alternative figure or skip it.

**Section selection** (priority list, hard-capped at 6 sections to keep the poster legible at 1400×900):

1. **Introduction** (Abstract or first section)
2. **Method** (the section describing the approach)
3. **Primary results** (Experiments / Replication / main result section)
4. **Secondary results / ablation** (if space permits)
5. **Analysis / discussion** (one key insight)
6. **Conclusion** (brief takeaway)

**Mode resolution**:

- `--no-figures` passed → mode = `none`; every section renders text-only. Skip all questions.
- `--auto-figures` passed → mode = `auto`; for each section, pick the visual with the largest area (W×H from `resolution`). Skip all questions.
- Otherwise → mode = `interactive`. Run the manifest + questions below.

**Print the figure manifest** (always, regardless of mode), e.g.:

```
Figure candidates per section:
  Abstract        — text only
  Introduction    — text only
  Method          — text only
  Experiments     — 2 candidates:
                    [a] layer_curves.png   2378x618  aspect 3.85  ⚠ wide
                    [b] bootstrap.png       974x612  aspect 1.59
  Discussion      — text only
  Conclusion      — text only
```

Compute aspect from `resolution` (W×H). The ⚠ wide marker comes from the `wide` field in dag.json (true when aspect ≥ 2.0 or ≤ 0.5).

**Interactive flow** (mode = `interactive` only):

For each section, decide what to ask based on candidate count and wide-flags:

| Candidates | Wide? | Action |
|---|---|---|
| 0 | — | No figure (no question, silent) |
| 1 | any | Use it inline (no question — the manifest already showed it; if `wide`, the ⚠ marker is the heads-up). User can re-run with `--no-figures` to drop it. |
| ≥2 | any | **Ask Q-Pick** (multi-select): *"Which figure(s) for {Section}?"* — `AskUserQuestion` with `multiSelect: true`, options: each candidate (label includes ⚠ wide marker if applicable) / `Let Claude decide (pick largest one)` / `No figure`. User may pick one, several, or all. |

Use `AskUserQuestion` for each prompt; cap at 4 options total. When a section has 4+ candidates, drop the `Let Claude decide` option to stay within the limit (the user is being explicit anyway).

**Follow-up: layout when ≥2 figures were picked for the same section.** Ask via `AskUserQuestion` (single-select):

| Option | What it does | When to recommend |
|---|---|---|
| `side-by-side` | Both/all chosen figures inside ONE `<div class="img-section">`; the template's flex layout splits horizontal space evenly. | Default. Most space-efficient for a 3-col poster. Works zero-CSS-changes. |
| `vertical-stack` | One `<div class="img-section">` per figure, stacked top-to-bottom. Each figure gets full column width. | When fine detail matters per figure; risks tall section + fit() shrinking text aggressively. |
| `after-table` | Used when the section ALSO contains a `<table class="poster-table">`. Figures go side-by-side AFTER the table. | The section is content-dense; respect paper's read order. |

The HTML template already supports both `side-by-side` and `vertical-stack` natively (flex layout, plus the option of multiple `.img-section` divs). `after-table` is a placement variant, not a new CSS class.

After all decisions, print a final summary line:

```
Figures chosen:
  Experiments → fig2.png + fig3.png (side-by-side)
  Method      → tikz_chain.png (inline)
  (other sections: text only)
```

**Decision record**: persist the choices in an in-memory dict keyed by section display name:

```python
{
  "Experiments": {
    "figures": ["images/fig2.png", "images/fig3.png"],   # list, even when 1
    "alts":    ["<caption fig2>",  "<caption fig3>"],    # parallel list
    "layout":  "inline-multi-side",                       # see below
  },
  "Method": {
    "figures": ["images/tikz_chain.png"],
    "alts":    ["<caption>"],
    "layout":  "inline",                                  # single-figure case
  },
  "Conclusion": {"figures": [], "alts": [], "layout": "none"},
  ...
}
```

`layout` enum:
- `"none"` — section is text-only, no figures
- `"inline"` — exactly one figure inside one `.img-section` (back-compat with single-figure flow)
- `"inline-multi-side"` — 2+ figures inside ONE `.img-section` (flex side-by-side)
- `"inline-multi-stack"` — 2+ figures, each in its own `.img-section` (vertical stack)
- `"inline-multi-after-table"` — 2+ figures side-by-side, placed AFTER any `<table class="poster-table">` in the section content

This dict is consumed in Step 3 to fill the per-section prompt variables.

### Step 3: Distill poster sections

Load `poster/dag.json` and the figure-decision dict from Step 2.5. Iterate the selected section nodes in order.

For each selected section, prepare the variables for the prompt below. Figure variables come from the Step 2.5 decision dict — do NOT re-derive them here.

- `SECTION_JSON`: the section node from `poster/dag.json` with the `visual_node` field **removed** (the visual is conveyed separately). Keep only `name`, `content`, `level`.
- `LAYOUT`: one of `"none"` / `"inline"` / `"inline-multi-side"` / `"inline-multi-stack"` / `"inline-multi-after-table"` from `decisions[section_name]["layout"]`. Drives the HTML template branch.
- `IMAGE_SRCS`: list of image sources from `decisions[section_name]["figures"]`, e.g. `["images/fig2.png", "images/fig3.png"]`. Empty list if `LAYOUT == "none"`.
- `ALT_TEXTS`: parallel list of captions from `decisions[section_name]["alts"]`. Same length as `IMAGE_SRCS`.
- `WIKI_CONTEXT` (optional): a short block compiled from Step 2 — hypothesis statement, novelty argument, key-result numbers from linked ideas/experiments. Empty string if no wiki context was loaded.

Run the following prompt for each section (ported from PaperX `poster_outline_prompt`, extended for `LAYOUT` and `WIKI_CONTEXT`):

> You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON you see has NO `visual_node` field and must be treated as authoritative.
>
> SECTION_JSON:
> {SECTION_JSON}
>
> LAYOUT: {LAYOUT}    # one of "none" | "inline" | "inline-multi-side" | "inline-multi-stack" | "inline-multi-after-table"
>
> If LAYOUT is not "none", you are also given IMAGE_SRCS (a list of image paths) and ALT_TEXTS (parallel list of captions). The visual content MUST ONLY come from these provided sources (do not invent or substitute any other image). For single-figure layouts (`"inline"`), the lists each have length 1. For multi-figure layouts, length ≥ 2 and the order in the list is the order figures should appear in the rendered HTML (left-to-right for `*-side`, top-to-bottom for `*-stack`).
>
> IMAGE_SRCS: {IMAGE_SRCS}
> ALT_TEXTS: {ALT_TEXTS}
>
> WIKI_CONTEXT (optional, may be empty — use it ONLY to ground concrete numbers/claims, never to invent content not in the section):
> {WIKI_CONTEXT}
>
> **Task**:
> 1. Write ONE concise paragraph summarizing ONLY the section's content for a scientific poster. Constraints: 2–5 sentences, factual, non-hallucinatory, no bullet lists, avoid starting with "This section". The summary must contain no more than 40 words and be written with strong logical coherence and smooth transitions to minimize perplexity.
> 2. Output the HTML block for this section, choosing the template variant matching LAYOUT. Output ONLY the HTML and nothing else.
>
> **Strict output rules**:
> - Output only the HTML for one section (one `<section>` block).
> - Do NOT add markdown fences, explanations, or extra text.
> - The `<div class="section-bar">` must be the section title (use `SECTION_JSON.name`).
> - Replace the sample paragraph with your summary.
> - LAYOUT == `"none"`: output the section block with NO `<div class="img-section">`.
> - LAYOUT == `"inline"`: output the section block with exactly one `<div class="img-section">` containing one `<img>` whose `src` is `IMAGE_SRCS[0]` and `alt` is `ALT_TEXTS[0]`.
> - LAYOUT == `"inline-multi-side"`: output ONE `<div class="img-section">` containing all `<img>` tags in `IMAGE_SRCS` order; the template's flex layout splits them horizontally.
> - LAYOUT == `"inline-multi-stack"`: output MULTIPLE `<div class="img-section">` blocks, one per `<img>`, in `IMAGE_SRCS` order. Stacked top-to-bottom.
> - LAYOUT == `"inline-multi-after-table"`: same as `"inline-multi-side"` (one `.img-section` with all `<img>` tags) but place that `.img-section` AFTER the `<table class="poster-table">` block(s) inside `<div class="section-body">`. Useful when the section's table is the primary artifact and figures serve as visual support.
> - **TABLES**: if `SECTION_JSON.content` contains one or more `<table class="poster-table">…</table>` blocks, include EACH ONE verbatim (preserve the entire block byte-for-byte, including `<caption>`, `<thead>`, `<tbody>`, all `<tr>` / `<th>` / `<td>` tags and their attributes) inside `<div class="section-body">` AFTER your summary `<p>`. Do NOT paraphrase, restructure, or trim the table HTML. Exception — drop a table only if it is obviously too large for one column (> 5 columns AND > 6 rows) AND summarizing 2–3 key cells in prose would preserve the result; in that case, drop the table and call out the key numbers in your summary `<p>`.
>
> **Required HTML templates** (pick the one matching LAYOUT):
>
> *LAYOUT = "none"*:
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline"* (single figure):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>     </div>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline-multi-side"* (≥2 figures, horizontal):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>       <!-- repeat for IMAGE_SRCS[2], etc. -->
>     </div>
>   </div>
> </section>
> ```
>
> *LAYOUT = "inline-multi-stack"* (≥2 figures, vertical):
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>     </div>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>     </div>
>     <!-- one .img-section per figure -->
>   </div>
> </section>
> ```
>
> *With a table* — when `SECTION_JSON.content` contains
> `<table class="poster-table">`, insert the verbatim table block(s)
> after the summary `<p>`. Default placement order inside
> `<div class="section-body">`:
>   1. summary `<p>`
>   2. `<table class="poster-table">…</table>` (all tables, in source order)
>   3. `<div class="img-section">…</div>` (if LAYOUT requires figures)
>
> If LAYOUT is `"inline-multi-after-table"` the order is the same — the
> name is just a hint that the table is the primary artifact. Example:
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <table class="poster-table">…verbatim from SECTION_JSON.content…</table>
>     <div class="img-section">
>       <img src="IMAGE_SRCS[0]" alt="ALT_TEXTS[0]" class="figure" />
>       <img src="IMAGE_SRCS[1]" alt="ALT_TEXTS[1]" class="figure" />
>     </div>
>   </div>
> </section>
> ```

Apply de-AI polish per `shared-references/academic-writing.md` (vary sentence openings, drop signature words like "leverage", "comprehensive", "delve"). Pull headline numbers from `WIKI_CONTEXT` when present — these make poster results concrete.

Write all blocks (in selection order) to `poster/outline.html`.

### Step 4: Add inter-section transitions

Apply the following prompt to the assembled outline (adapted from PaperX):

> **Prompt**: You are given an HTML-like poster outline of multiple `<section class="section">` blocks. Each section has a title in `<div class="section-bar">` and main text in the first `<p>` inside `<div class="section-body">`.
>
> Generate one bridging sentence per section from the FIRST up to the SECOND-TO-LAST. Place each at the END of that section's first `<p>` to lead into the NEXT section's topic.
>
> **Output**: a JSON array of strings. Length = (number_of_sections − 1). The i-th string bridges section i to section i+1. Each is one sentence (12–25 words), fluent academic English, no newlines.
>
> **Patterns** to prefer:
> - When the next section introduces/elaborates/substantiates a method or idea: "To introduce / elaborate on / substantiate \<next topic\>, we next present \<next title\>."
> - When the next section is experimental: "Next, we evaluate \<subject\> to demonstrate ..." or "We then conduct experiments on \<task\> to empirically validate ..."
> - Always reference the next section's topic without introducing new technical claims.

Parse the JSON array. For each string, append it to the end of the corresponding section's first `<p>` in `poster/outline.html`. The last section gets no bridge.

### Step 5: Build the poster

```bash
python3 tools/poster.py build \
  --template templates/poster/poster_template.html \
  --outline poster/outline.html \
  --output poster/poster.html

python3 tools/poster.py inject-title \
  --dag poster/dag.json \
  [--authors "{authors override from Step 0 or --authors flag}"] \
  poster/poster.html
```

The `--anonymous` flag is applied at Step 1 (`wiki2dag.py`) — `dag.json` already carries the canonical title/authors, so `inject-title` reads from there by default. Pass `--authors` to override when the paper's `\author{}` was intentionally left empty (e.g. for double-blind submission) but a real author string is desired on the poster. `--anonymous` (on `inject-title`) still wins over `--authors` if both are set.

```bash
# Apply the venue text + logos from Step 0. Omit flags that the user skipped.
python3 tools/poster.py inject-header \
  --venue "{venue from Step 0}" \
  [--affiliation-logo {path}] \
  [--conference-logo {path}] \
  --layout {corners|stacked} \
  poster/poster.html

python3 tools/poster.py inject-figures \
  --dag poster/dag.json \
  --paper-dir paper/ \
  --poster-dir poster/

python3 tools/poster.py validate poster/poster.html
```

`inject-figures` copies PNG/JPG sources verbatim and converts PDF sources to PNG at 200 DPI via `pdftoppm`. `validate` checks that every `<img src=...>` resolves, the title is non-empty, at least 3 sections are present, and no `TODO`/`FIXME`/`[UNCONFIRMED]` markers remain.

### Step 5b: Render PNG

After validation passes, render the HTML poster to PNG so the user has a flat screenshot (also used as input by the future Step 5.5 critique-revise pass):

```bash
python3 tools/poster.py render poster/poster.html
```

This writes `poster/poster.png` at 2× the CSS pixel dimensions (default 2800×1800). Override with `--scale {1,2,3}` (1 = fast preview, 3 = print quality).

**Render engine**: prefers Playwright (Chromium) when available, falls back to subprocess against a system browser. Playwright is strongly preferred because it waits on **specific events** before screenshotting — `document.fonts.ready`, all `<img>` `load` events, and `flow.scrollWidth` stable for 10 consecutive animation frames (fit() converged). The subprocess fallback uses `--virtual-time-budget=5000`, a wall-clock timeout that can race with slow CDN responses for Google Fonts / KaTeX. This is the exact wait semantics PaperX uses.

**Install Playwright** (one-time, recommended): `pip install playwright && python -m playwright install chromium`. Without it, `render` still works via the subprocess path; print output shows `browser: chromium` (subprocess) vs `browser: playwright-chromium` (preferred).

**Subprocess fallback browser detection**: Chrome → Edge → Chromium → Firefox (last resort). Chrome/Edge/Chromium are equivalent (same engine, identical CLI flags). Firefox works but with two caveats — no HiDPI scaling (PNG comes out 1× regardless of `--scale`) and no `--virtual-time-budget` equivalent. `render` prints warnings to stderr when it falls back to Firefox.

**Safari is not supported** — it has no headless CLI screenshot flag; integration would require `safaridriver` + Selenium WebDriver. macOS-only users with only Safari should `brew install --cask google-chrome` (one command) to unlock the full pipeline.

If no supported browser is found, `render` exits with platform-specific install hints. The HTML poster remains usable in any browser — the user can still `open poster/poster.html` directly.

### Step 5.5: Critique-revise via Claude (screenshot + DOM overflow report)

Goal: refine the HTML using both a **programmatic overflow report** (ground truth from the rendered DOM) and the **screenshot** (visual context). The DOM report is what fit() and the LLM can both miss — it measures every leaf element's bottom/right vs the flow's edges and reports any clipping precisely. The LLM cannot declare convergence while the report shows clipping; it must trim prose until the report comes back clean.

Auto-applied; no user interaction.

**Skip conditions**:
- `--no-refine` flag passed → skip Step 5.5 entirely.
- `--refine-iterations 0` → equivalent to `--no-refine`.
- Step 5b failed to produce `poster/poster.png` (no supported browser installed) → skip with a warning.

**Iteration count**: from `--refine-iterations N` (default 1, hard cap 2). Note: convergence is gated on the overflow report, not just on prose stability — see Termination below.

**Workflow per iteration** (i = 1..N):

1. Ensure `poster/poster.png` reflects the current `poster/poster.html`. If the HTML was modified since the last render, re-run `python3 tools/poster.py render poster/poster.html`.
2. Run `python3 tools/poster.py check-overflow poster/poster.html --output raw/tmp/poster.overflow.json` (scratch path — `poster/` only ever contains final artifacts). Read the JSON.
3. **Early convergence (overflow-only path)**: if `i == 1` AND `overflow.ok == true` AND no obvious LaTeX/encoding/numbering issues are visible in the screenshot at a careful look (apply the mandatory checklist in the refinement prompt below to your own evaluation), you MAY declare convergence here: record `"converged after 0 iterations — DOM clean, no visible content issues"` and exit. Skip this shortcut if you have *any* doubt — the cost of one refinement pass is small compared to shipping a poster with subtle issues.
4. Snapshot `pre_html = <current poster.html>` in memory — needed for the prose-stability convergence check.
5. Read `poster/poster.png` (multimodal), `poster/poster.html`, and `raw/tmp/poster.overflow.json` (the ground-truth clipping report).
6. Apply the refinement prompt below. Pass the overflow JSON as part of the prompt — the LLM uses it to know *exactly* which sections need trimming, instead of guessing from the screenshot. Use Claude (in-session, multimodal). Do NOT use `mcp__llm-review__chat` — text-only per `mcp-servers/llm-review/server.py`.
7. Parse the LLM output: extract HTML from the first ```` ```html ```` fenced block.
8. Write the revised HTML back to `poster/poster.html`. Snapshot it as `post_html`.
9. Re-run `python3 tools/poster.py validate poster/poster.html`. If validation fails: stop, surface issues to the user, leave HTML as-is.
10. Re-render to `poster/poster.png`. Re-run `check-overflow --output raw/tmp/poster.overflow.json` → updated report.
11. **Convergence check (requires BOTH)**:
    - (a) New overflow report shows `ok == true`, AND
    - (b) `pre_html` and `post_html` differ by < 50 chars inside the `.flow` region.
    
    If both: declare convergence (`"converged after {i} iteration(s) — DOM clean and prose stable"`) and exit.
    
    If overflow.ok is still false: refinement is **mandatory** for the next iteration; the loop continues even if prose-stable. The LLM didn't trim enough.
    
    If iteration budget is exhausted but overflow.ok is still false: stop with a clear warning ("Step 5.5 ran N iterations but couldn't clear DOM overflow — consider re-running with `--refine-iterations 2`, or hand-trim the longest section's prose in `poster/outline.html`"). Leave HTML / PNG as-is for the user to inspect.

**Why this design**: in the previous version, the LLM declared convergence based on a casual visual scan of a downscaled PNG. Subtle clipping at column edges slipped through. The DOM overflow report removes LLM judgment from the *detection* of clipping — clipping is now a measurement, not a guess. The LLM's job becomes specifically *fixing* what the report flags, not also deciding whether there's anything to fix.

**Refinement prompt** (ported from PaperX `poster_refinement_prompt`; extended with the overflow JSON input + mandatory pre-flight checklist):

> You are an expert Academic Poster Designer and Web Developer. Your task is to refine an existing HTML poster based on its visual rendering (screenshot), the current HTML code, and a structured DOM overflow report.
>
> **INPUTS**:
> 1. **Current Poster Code (HTML)** — full poster.html
> 2. **Visual Render (PNG screenshot)** — poster.png attached via Read
> 3. **DOM Overflow Report (JSON)** — output of `tools/poster.py check-overflow`. This is **ground truth** about which elements are clipped. If `clipped` is non-empty, you MUST fix each entry.
>
> **MANDATORY PRE-FLIGHT CHECKLIST** — answer BEFORE generating any HTML. Write this as a fenced ```` ```json ```` block first; then below it, output the corrected HTML in a separate ```` ```html ```` block.
>
> ```json
> {
>   "overflow_report_ok": <true|false; copy from the report's "ok" field>,
>   "clipped_count":     <integer; the length of the report's "clipped" array>,
>   "col1_bottom_ok":    <true|false; from the screenshot, is the last text line in col 1 ≥ 10 px above the .poster bottom border AND fully readable?>,
>   "col2_bottom_ok":    <true|false; same check for col 2 — pay specific attention to any figure's x-axis label>,
>   "col3_bottom_ok":    <true|false; same check for col 3>,
>   "latex_leaks":       <list of strings; raw LaTeX patterns you found, e.g. ["\\textbf{x}", "\\citep{key}"] — empty list if none>,
>   "numbering_prefixes": <list of strings; section-bars with leading "1.", "A.", etc. — empty list if none>,
>   "will_revise":       <true|false; if ANY of the above signal a problem, this MUST be true and the HTML block below MUST contain trimming/fixes>
> }
> ```
>
> If `will_revise: false`, your HTML block may be identical to the input.
>
> If `will_revise: true`, the HTML block MUST contain real edits addressing each flagged issue. **Do not output unchanged HTML claiming you fixed it** — that's the failure mode this checklist exists to prevent.
>
> **TASKS** (apply only where flagged by the checklist):
>
> **Task 1: Fix LaTeX / encoding leaks** (when `latex_leaks` non-empty)
> - Replace raw LaTeX with HTML entities or Unicode (`\\textbf{x}` → `<strong>x</strong>`, `\\citep{key}` → `[N]`, `$d_S \\ge 10$` → `d_S ≥ 10`).
>
> **Task 2: Normalize section headers** (when `numbering_prefixes` non-empty)
> - Strip leading `1.`, `2.1`, `A.`, `E.`, `- `, etc. from `<div class="section-bar">` contents.
>
> **Task 3: Fix DOM-reported clipping** (when `overflow_report_ok: false`)
> - The JSON's `clipped` array names every offending element with its `section_title`, `tag`, `bottom_overflow_px`, and a content `preview`. For each clipped element, **trim the corresponding section's prose conservatively** (drop filler words, tighten sentences) until that element fits. Never delete claims, citations, or math expressions.
>
> **Task 4: Fix screenshot-only issues** (when any `colN_bottom_ok: false`)
> - The DOM check has tolerance; visually cramped content (line right against the border) may still pass `overflow.ok: true`. If the screenshot shows this, trim the relevant column's prose by 5–15 words.
>
> **Output requirements**:
> - First, the ```` ```json ```` checklist block (mandatory).
> - Then, the ```` ```html ```` block: complete, runnable HTML.
> - Preserve the CSS, the `<script>` fit algorithm, and font-related settings exactly. Only edit content inside `<section class="section">` and the title/authors slots.
>
> **HTML poster**:
> ```html
> {full content of poster/poster.html}
> ```
>
> **DOM Overflow Report**:
> ```json
> {full content of raw/tmp/poster.overflow.json}
> ```
>
> **Screenshot**:
> *(the contents of poster/poster.png attached via the Read tool — Claude reads it as an image)*

**Termination conditions**:
- **Convergence (preferred)**: overflow.ok=true AND prose diff < 50 chars. Exit normally.
- **Iteration cap reached with overflow.ok=true**: also exit normally.
- **Iteration cap reached with overflow.ok=false**: stop and warn the user — the budget wasn't enough to clear all clipping. Suggest `--refine-iterations 2` or hand-trimming the longest section's prose in `poster/outline.html`.
- **LLM output missing the JSON checklist block** → stop, log warning ("refinement LLM did not produce the mandatory pre-flight checklist"), leave HTML as-is.
- **LLM output missing the HTML fenced block** → stop, log warning, leave HTML as-is.
- **Validation fails after revision** → stop, surface validation issues, leave HTML as-is.
- **LLM declares `will_revise: false` but overflow.ok is false** → log warning ("refinement LLM ignored DOM clipping report"), continue to next iteration if budget remains; otherwise warn user.

### Step 6: Optional Review LLM critique (`--review`)

If `--review` is passed, send the poster HTML to the Review LLM:

```
mcp__llm-review__chat
  system: "You are a senior researcher reviewing an academic poster.
           Evaluate: (1) Is the content hierarchy clear? (2) Are key results prominently placed?
           (3) Is each section self-contained and readable? (4) Is the visual balance good (text vs figures)?
           (5) Are transitions between sections logical? (6) Would a passerby understand the contribution in 30 seconds?"
  message: |
    ## Poster HTML
    {full content of poster/poster.html}

    ## DAG
    {full content of poster/dag.json}

    Review for: content completeness, text density, figure selection, narrative flow.
    Flag any section that is unclear, off-topic, or missing key context.
```

Apply revisions by editing `poster/outline.html` and re-running Step 5. Do not loop more than 2 review-revision rounds.

### Step 7: Log and report

```bash
python3 tools/research_wiki.py log wiki/ \
  "poster | generated poster for '{title}' | {N} sections, {M} figures | reviewed: {yes/no}"
```

Print POSTER_REPORT:

```markdown
# Poster Report

## Source
- Paper: {title}
- Authors: {authors}
- Paper directory: {paper_dir}

## Generation
- Sections included: {N}/{total available}
- Figure selection mode: {interactive | auto | none}
- Figures embedded: {M}
- PDF→PNG conversions: {K}
- Header: venue='{venue}', affiliation={path|none}, conference={path|none}, layout={corners|stacked}
- Critique-revise (Step 5.5): {k/N iterations applied | converged after k/N (no material changes) | skipped (--no-refine) | skipped (no headless browser)}
- Review LLM (Step 6): {invoked / skipped}

## Output
- poster/poster.html ← open in a browser
- poster/poster.png ← flat screenshot, 2× CSS (default 2800×1800)
- poster/dag.json (intermediate, reusable by /slides /pr)

## Export to PDF
Open `poster/poster.html` in Chrome / Edge / Firefox, then **Cmd+P** (macOS)
or **Ctrl+P** (Win/Linux) → **Save as PDF**. Recommended print settings:
- Layout: **Landscape**
- Paper size: **Custom 1400×900 px** (fall back to Letter / A3 Landscape if Custom is unavailable)
- Margins: **None**
- Scale: **100%** (or "Fit to page" if 100% overflows)
- Background graphics: **On** (so the blue header + section bars render)

## Notes
- {any warnings, e.g. missing figures, sections selected, etc.}
```

## Constraints

- **Do not modify `paper/` source files**: this skill is read-only over LaTeX source (`main.tex`, `sections/*.tex`, `figures/`, `references.bib`, `math_commands.tex`). The only allowed writes to `paper/` are: (a) `paper/.author_display.txt` — Step 0 author cache; (b) `paper/figures/_tikz_<sec>_<label>.png` — rasterized TikZ figure cache (Step 1, see "TikZ figures" in Step 1's preservation list). The `_tikz_` prefix marks these as derived from `paper/sections/*.tex`; they're safe to delete (next run rebuilds). All other output goes to `poster/`.
- **Do not create wiki entities or graph edges**: the poster is a presentation artifact.
- **Reuse compiled figures**: do not regenerate figures from `paper/figures/plot_*.py`. The user already ran `/paper-compile`.
- **Respect `--anonymous`**: when set, authors become "Anonymous" in both `dag.json` and the poster header.
- **Max section limit**: hard-coded at 6 sections to keep the poster legible at 1400×900. Sections are selected from the priority list in Step 2.5; Related Work / Background / Appendix get dropped first when papers have more sections than the cap.
- **40-word summary**: per the poster_outline_prompt, each section paragraph stays ≤ 40 words before transitions are added.
- **De-AI polish is mandatory**: per `shared-references/academic-writing.md`. Avoid signature openings ("In this work", "We propose", "Our approach"), replace inflated verbs ("leverage" → "use", "delve" → "examine").
- **Strict template injection**: `tools/poster.py build` only injects between `<div class="flow" id="flow">...</div>`; do not edit the template's CSS or JavaScript fit algorithm.
- **Figure selection is interactive by default**: omitting both `--auto-figures` and `--no-figures` runs the Step 2.5 manifest + question flow. The flags are user-owned per CLAUDE.md rule 5 — do not infer them; ask if unsure which mode to use.
- **No special layout for wide figures**: every figure renders inline within its `<section>`. The `wide` flag on visual nodes is informational only — used to surface the ⚠ marker in the manifest so the user can pick an alternative or skip a cramped figure. A future figure-generation skill is expected to solve the aspect-ratio problem upstream by producing poster-fit figures.

## Error Handling

- **`paper/main.tex` not found**: error with "Run /paper-draft first to generate the paper."
- **No sections found in `\input{sections/...}`**: error with the list of files searched; suggest checking `main.tex` for non-standard section includes.
- **No figures referenced**: continue with text-only sections; warn in POSTER_REPORT.
- **`pdftoppm` not installed**: PDF figures fail to convert; warn and suggest `brew install poppler` (macOS) or `apt install poppler-utils` (Linux). The poster will still render but with broken image refs for those figures.
- **Nested figure paths** (`paper/figures/exp1/foo.pdf`): the bridge currently flattens to `images/foo.png` and the figure resolver looks only in `paper/figures/`. If two figures across nested dirs share the same basename, the second one wins. Flat `paper/figures/` is the supported layout for now.
- **`PIL`/Pillow not installed**: image resolutions cannot be computed; `dag.json` visuals have empty `resolution`. The poster_outline_prompt loses its "highest-resolution wins" tiebreaker — Claude picks by section order instead. Suggest `pip install Pillow`.
- **Validation fails**: print all issues to stderr; do not delete the partial output. User can fix the outline and re-run from Step 5.
- **No supported browser found for `render`**: print install instructions per platform (Chrome / Edge / Chromium recommended; Firefox accepted as fallback) and continue. The HTML poster is still usable; only the PNG is missing. Step 5.5 critique-revise also skips (no screenshot → nothing to critique). Safari is not supported (no headless CLI).
- **Firefox fallback in use**: `render` prints warnings to stderr (no HiDPI scale, layout may not be fully converged). Output is functional but lower quality than Chrome/Edge. Suggest the user install a Chromium-based browser for best results.
- **Refinement output malformed (Step 5.5)**: if the LLM does not return a fenced ```` ```html ```` block containing a valid `<section>` + `<h1 class="title">`, stop the iteration loop, leave the HTML unchanged, and surface a warning. Do NOT overwrite the HTML with broken output.
- **Review LLM unreachable**: skip Step 6, note in report, continue.

## Dependencies

### Tools (via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous] [--citations]` — build dag.json; `--citations` opts back in to inline `[N]` markers (default: dropped, no reference list on the poster)
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` — inject outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous] [--authors STR]` — set title/authors; `--authors` overrides dag.json's author field when the paper was anonymized at the source
- `python3 tools/poster.py inject-header <poster.html> [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked]` — venue text + optional logos
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` — figure copy/convert
- `python3 tools/poster.py validate <poster.html>` — sanity checks
- `python3 tools/poster.py render <poster.html> [--scale 1|2|3] [--output PATH]` — HTML → PNG via headless browser (Chrome / Edge / Chromium preferred, Firefox fallback)
- `python3 tools/poster.py check-overflow <poster.html> [--output PATH]` — Playwright DOM query for clipped content; emits poster.overflow.json. Used as ground truth by Step 5.5.
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `pdflatex` (TeX Live) — required for TikZ figure rasterization (Step 1); install via `brew install --cask mactex` / `apt install texlive-full`. With `tikz`, `pgfplots`, `standalone`, `booktabs`, `multirow`, `array`, `xcolor`, `amsmath`, `amssymb` packages. If absent, TikZ figures inside `\begin{figure}` envs without `\includegraphics{}` are dropped with a stderr warning; the rest of the build continues.
- `pdftoppm` (poppler) — PDF → PNG conversion at 200 DPI (used both for paper figures and for rasterized TikZ)
- `pdfinfo` (poppler) — PDF page-size for resolution
- Playwright + Chromium (preferred, optional) — `pip install playwright && python -m playwright install chromium`. Enables event-driven waits (fonts/images/fit-stable). Falls back gracefully if missing.
- Headless system browser (fallback) — auto-detected in this order: Google Chrome → Microsoft Edge → Chromium → Firefox. Chrome/Edge/Chromium are equivalent; Firefox renders at 1× scale only and without sync-wait. Safari is not supported (no headless CLI).

### MCP Servers
- `mcp__llm-review__chat` — optional cross-model review (`--review`)

### Claude Code Native
- `Read` — read .tex, dag.json, outline.html
- `Write` — write outline.html
- `Edit` — apply transition sentences to outline.html
- `Bash` — invoke wiki2dag, poster, research_wiki tools

### Shared References
- `.claude/skills/shared-references/academic-writing.md` — de-AI polish standards
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM protocol (when `--review`)

### Called by
- Manual user invocation
- Future: `/research` Stage 5b (post paper-compile)
