---
description: Generate an academic poster from a drafted paper — distill sections into a single-page HTML poster with figures and inter-section transitions
argument-hint: "[paper-dir] [--review] [--anonymous] [--max-sections N] [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked] [--no-logos] [--auto-figures] [--no-figures]"
---

# /poster

> Generate an academic HTML poster from a drafted paper. Reads `paper/main.tex`,
> section files, and figures; builds a PaperX-compatible `dag.json` intermediate;
> distills each section into a 2–5 sentence summary; selects representative figures;
> renders into a self-contained HTML poster with a 3-column auto-fit layout.

## Inputs

- `paper_dir` (optional, default `paper/`): LaTeX project directory containing `main.tex` and `sections/`
- `--review` (optional): cross-model Review LLM critique of the generated poster content
- `--anonymous` (optional): force authors to "Anonymous" regardless of `\author{}` content
- `--max-sections N` (optional, default 6): maximum poster sections to include
- `--venue STR` (optional): venue text shown in the header right block (e.g. `"NeurIPS 2026"`); if omitted, asked interactively
- `--affiliation-logo PATH` (optional): path to affiliation/lab logo (PNG/JPG/PDF); copied into `poster/images/`
- `--conference-logo PATH` (optional): path to conference/journal logo (PNG/JPG/PDF); copied into `poster/images/`
- `--layout corners|stacked` (optional, default `corners`): header layout. `corners` puts affiliation top-left and conference top-right; `stacked` puts both logos in the right `.conf` area with venue text above
- `--no-logos` (optional): skip all logo prompts and ship a header with venue text only
- `--auto-figures` (optional): skip the per-section figure questions; pick the largest candidate for each section (legacy behavior). Wide figures auto-render full-width.
- `--no-figures` (optional): skip all figures; render every section as text-only. Useful for text-heavy posters or when figures are not yet ready.

## Outputs

- `poster/dag.json` — PaperX-compatible intermediate (reusable by future `/slides`, `/pr`)
- `poster/outline.html` — concatenated `<section>` blocks before template injection
- `poster/poster.html` — final self-contained HTML poster (open in browser)
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

1. **Venue text** — if `--venue` was not provided:
   - Ask: *"What venue text should appear in the poster header? e.g. `NeurIPS 2026`. Reply with the text, or `skip` to leave it blank."*
   - Take the next user message verbatim. Treat the literal string `skip` (case-insensitive) as empty.

2. **Affiliation logo** — if `--affiliation-logo` was not provided AND `--no-logos` was not passed:
   - Use `AskUserQuestion` with options: `"Yes, I have a logo file"` / `"No, skip the affiliation logo"`.
   - If yes: ask *"What's the path to the affiliation logo? (PNG / JPG / PDF; relative or absolute)."* Take the next user message as the path. Verify the file exists; if not, re-ask once with the resolved-path issue surfaced, then either accept a new path or treat as skipped.

3. **Conference / journal logo** — if `--conference-logo` was not provided AND `--no-logos` was not passed:
   - Same flow as the affiliation logo (yes/no via `AskUserQuestion`, path via free text).

4. **Layout** — if at least one logo was provided AND `--layout` was not passed:
   - Use `AskUserQuestion` with options:
     - `"corners — affiliation top-left, conference top-right"` (Recommended)
     - `"stacked — both logos stacked in the right conf area, venue text on top"`
   - If only `--venue` and no logos: skip the layout question (default `corners` is fine — only the venue text slot is used).

5. **Final summary** — print one line:
   - `Header config: venue='{...}', affiliation={path|none}, conference={path|none}, layout={...}`

These values are applied in Step 5 via `python3 tools/poster.py inject-header`.

### Step 1: Build dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

Add `--anonymous` if the user passed it.

The bridge produces three node types:
- **Root** (`level: 0`): paper title in `name`, authors in `content`, ordered section names in `edge`
- **Section** (`level: 1`): section heading in `name`, full prose in `content`, figure refs in `visual_node`
- **Visual** (`level: 2`): markdown image ref in `name`, caption in `content`, `WxH` in `resolution`

### Step 2: Compile WIKI_CONTEXT (optional)

If `wiki/outputs/paper-plan-*.md` exists, read it for:
- Venue name (passed to `inject-header` in Step 5 if the user did not supply one)
- Narrative arc and evidence map
- Linked idea slugs

For each linked idea slug, read `wiki/ideas/<slug>.md` for the hypothesis statement and novelty argument. For linked `wiki/experiments/*.md`, read the `outcome` and `key_result` fields. Assemble these into a single `WIKI_CONTEXT` string keyed by section:

```
[INTRODUCTION]
hypothesis: <one sentence from idea>
novelty: <one sentence from idea>

[EXPERIMENTS]
key_result: <headline numbers from experiments>
outcome: <one line summary>
```

This block is passed into the Step 3 prompt under the `{WIKI_CONTEXT}` slot. If no wiki context is available, the slot is left empty — the prompt explicitly tolerates that.

### Step 2.5: Figure selection

Goal: decide which figure (if any) belongs in each selected section. Runs after `dag.json` is built and before any LLM distillation, so the figure choice becomes an *input* to Step 3 rather than something the LLM guesses. Every figure renders inline within its section; the ⚠ wide marker in the manifest is purely informational — a heads-up that an aspect-extreme figure may look cramped in a single column, so the user can pick an alternative figure or skip it.

**Section selection** (same priority list as before, capped at `--max-sections`, default 6):

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
| ≥2 | any | **Ask Q-Pick**: *"Which figure for {Section}?"* — options: each candidate (label includes ⚠ wide marker if applicable) / `Let Claude decide (pick largest)` / `No figure`. |

Use `AskUserQuestion` for each prompt; cap at 4 options total. When a section has 4+ candidates, drop the `Let Claude decide` option to stay within the limit (the user is being explicit anyway).

After all decisions, print a final summary line:

```
Figures chosen:
  Experiments → bootstrap.png (inline)
  (other sections: text only)
```

**Decision record**: persist the choices in an in-memory dict keyed by section display name:

```python
{
  "Experiments": {"figure": "images/bootstrap.png", "layout": "inline", "alt": "<caption>"},
  "Conclusion": {"figure": None, "layout": None, "alt": None},
  ...
}
```

This dict is consumed in Step 3 to fill the per-section prompt variables.

### Step 3: Distill poster sections

Load `poster/dag.json` and the figure-decision dict from Step 2.5. Iterate the selected section nodes in order.

For each selected section, prepare the variables for the prompt below. Figure variables come from the Step 2.5 decision dict — do NOT re-derive them here.

- `SECTION_JSON`: the section node from `poster/dag.json` with the `visual_node` field **removed** (the visual is conveyed separately). Keep only `name`, `content`, `level`.
- `LAYOUT`: one of `"none"` or `"inline"` from `decisions[section_name]["layout"]`. Drives the HTML template branch.
- `IMAGE_SRC`: e.g. `images/layer_curves.png` from `decisions[section_name]["figure"]`. Empty string if `LAYOUT == "none"`.
- `ALT_TEXT`: the chosen visual's caption from `decisions[section_name]["alt"]`. Empty if `LAYOUT == "none"`.
- `WIKI_CONTEXT` (optional): a short block compiled from Step 2 — hypothesis statement, novelty argument, key-result numbers from linked ideas/experiments. Empty string if no wiki context was loaded.

Run the following prompt for each section (ported from PaperX `poster_outline_prompt`, extended for `LAYOUT` and `WIKI_CONTEXT`):

> You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON you see has NO `visual_node` field and must be treated as authoritative.
>
> SECTION_JSON:
> {SECTION_JSON}
>
> LAYOUT: {LAYOUT}    # one of "none" | "inline"
>
> If LAYOUT is "inline", you are also given IMAGE_SRC and ALT_TEXT. The visual content MUST ONLY come from this provided IMAGE_SRC (do not invent or substitute any other image).
>
> IMAGE_SRC: {IMAGE_SRC}
> ALT_TEXT: {ALT_TEXT}
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
> - LAYOUT == `"inline"`: output the section block with exactly one `<div class="img-section">` containing one `<img>` whose `src` is exactly `IMAGE_SRC` and `alt` is `ALT_TEXT`.
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
> *LAYOUT = "inline"*:
> ```html
> <section class="section">
>   <div class="section-bar" contenteditable="true">SECTION_TITLE</div>
>   <div class="section-body" contenteditable="true">
>     <p>SUMMARY_TEXT</p>
>     <div class="img-section">
>       <img src="IMAGE_SRC" alt="ALT_TEXT" class="figure" />
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
  poster/poster.html
```

The `--anonymous` flag is applied at Step 1 (`wiki2dag.py`) — `dag.json` already carries the canonical title/authors, so `inject-title` just reads.

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

This writes `poster/poster.png` at 2× the CSS pixel dimensions (default 2800×1800) using headless Chrome via the system binary — no Python dependency added. Override with `--scale {1,2,3}` (1 = fast preview, 3 = print quality).

If Chrome is not installed, `render` fails with an actionable message (`brew install --cask google-chrome` on macOS, `apt install chromium-browser` on Linux, or download from google.com/chrome on Windows). The HTML poster remains usable — the user can still `open poster/poster.html` directly.

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
- Review LLM: {invoked / skipped}

## Output
- poster/poster.html ← open in a browser
- poster/dag.json (intermediate, reusable by /slides /pr)

## Notes
- {any warnings, e.g. missing figures, sections selected, etc.}
```

## Constraints

- **Do not modify `paper/`**: this skill is read-only over the source paper. All output goes to `poster/`.
- **Do not create wiki entities or graph edges**: the poster is a presentation artifact.
- **Reuse compiled figures**: do not regenerate figures from `paper/figures/plot_*.py`. The user already ran `/paper-compile`.
- **Respect `--anonymous`**: when set, authors become "Anonymous" in both `dag.json` and the poster header.
- **Max section limit**: hard cap at `--max-sections` (default 6) to keep the poster legible at 1400×900.
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
- **Chrome not found for `render`**: print install instructions per platform and continue. The HTML poster is still usable; only the PNG is missing.
- **Review LLM unreachable**: skip Step 6, note in report, continue.

## Dependencies

### Tools (via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous]` — build dag.json
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` — inject outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous]` — set title/authors
- `python3 tools/poster.py inject-header <poster.html> [--venue STR] [--affiliation-logo PATH] [--conference-logo PATH] [--layout corners|stacked]` — venue text + optional logos
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` — figure copy/convert
- `python3 tools/poster.py validate <poster.html>` — sanity checks
- `python3 tools/poster.py render <poster.html> [--scale 1|2|3] [--output PATH]` — HTML → PNG via headless Chrome
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `pdftoppm` (poppler) — PDF → PNG conversion at 200 DPI
- `pdfinfo` (poppler) — PDF page-size for resolution
- Chrome / Chromium (system binary) — used by `render` for headless screenshot; auto-detected at common paths

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
