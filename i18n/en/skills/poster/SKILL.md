---
description: Generate an academic poster from a drafted paper — distill sections into a single-page HTML poster with figures and inter-section transitions
argument-hint: "[paper-dir] [--review] [--anonymous] [--max-sections N]"
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

## Outputs

- `poster/dag.json` — PaperX-compatible intermediate (reusable by future `/slides`, `/pr`)
- `poster/outline.html` — concatenated `<section>` blocks before template injection
- `poster/poster.html` — final self-contained HTML poster (open in browser)
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

### Step 1: Build dag.json

```bash
python3 tools/wiki2dag.py build --paper-dir paper/ --output poster/dag.json
```

Add `--anonymous` if the user passed it.

The bridge produces three node types:
- **Root** (`level: 0`): paper title in `name`, authors in `content`, ordered section names in `edge`
- **Section** (`level: 1`): section heading in `name`, full prose in `content`, figure refs in `visual_node`
- **Visual** (`level: 2`): markdown image ref in `name`, caption in `content`, `WxH` in `resolution`

### Step 2: Read optional wiki context

If `wiki/outputs/paper-plan-*.md` exists, read it for:
- Venue name (used for poster header badge)
- Narrative arc and evidence map
- Linked idea slugs

For each linked idea slug, read `wiki/ideas/<slug>.md` for the hypothesis statement and novelty argument. Read linked `wiki/experiments/*.md` for outcome numbers and key results. These enrich the distillation prompts in Step 3 but are not required.

### Step 3: Select and distill poster sections

Load `poster/dag.json`. Skip the root and any visual nodes; iterate section nodes only.

Select up to `--max-sections` sections (default 6) following this priority:
1. **Introduction** (Abstract or first section)
2. **Method** (the section describing the approach)
3. **Primary results** (Experiments / Replication / main result section)
4. **Secondary results / ablation** (if space permits)
5. **Analysis / discussion** (one key insight)
6. **Conclusion** (brief takeaway)

For each selected section, locate the best visual: from the section's `visual_node` list, pick the visual node with the largest `resolution` (W×H area). If no visuals are referenced, the section has no figure.

For each section, generate **one** `<section class="section">` HTML block using the following prompt (adapted from PaperX, content-only — Claude executes this directly):

> **Prompt**: You are given a section node JSON (SECTION_JSON) from a paper DAG. The section JSON has NO `visual_node` field and must be treated as authoritative.
>
> If a visual is available, you are also given IMAGE_SRC (e.g. `images/foo.png`) and ALT_TEXT (the caption).
>
> **Task**:
> 1. Write ONE concise paragraph summarizing ONLY the section's content for a scientific poster. Constraints: 2–5 sentences, factual, non-hallucinatory, no bullet lists, avoid starting with "This section". The summary must contain no more than 40 words and be written with strong logical coherence to minimize perplexity.
> 2. Output EXACTLY ONE HTML section block in the required template below. Output ONLY the HTML and nothing else.
>
> **Strict output rules**:
> - Output only ONE `<section class="section">...</section>` block.
> - Do NOT add markdown fences, explanations, or extra text.
> - The `<div class="section-bar">` must be the section title.
> - Replace the sample paragraph with your summary.
> - If a visual is provided AND IMAGE_SRC is non-empty, include exactly one `<div class="img-section">` with one `<img>` whose `src` is exactly IMAGE_SRC and `alt` is ALT_TEXT.
> - If no visual, do NOT output any img-section or img tag.
>
> **Required HTML template**:
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

Apply de-AI polish per `shared-references/academic-writing.md` (vary sentence openings, drop signature words like "leverage", "comprehensive", "delve"). Pull headline numbers from `wiki/experiments/<slug>.md` when relevant — these make poster results concrete.

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

Add `--anonymous` to inject-title if the user passed it.

```bash
python3 tools/poster.py inject-figures \
  --dag poster/dag.json \
  --paper-dir paper/ \
  --poster-dir poster/

python3 tools/poster.py validate poster/poster.html
```

`inject-figures` copies PNG/JPG sources verbatim and converts PDF sources to PNG at 200 DPI via `pdftoppm`. `validate` checks that every `<img src=...>` resolves, the title is non-empty, at least 3 sections are present, and no `TODO`/`FIXME`/`[UNCONFIRMED]` markers remain.

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
- Figures embedded: {M}
- PDF→PNG conversions: {K}
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

## Error Handling

- **`paper/main.tex` not found**: error with "Run /paper-draft first to generate the paper."
- **No sections found in `\input{sections/...}`**: error with the list of files searched; suggest checking `main.tex` for non-standard section includes.
- **No figures referenced**: continue with text-only sections; warn in POSTER_REPORT.
- **`pdftoppm` not installed**: PDF figures fail to convert; warn and suggest `brew install poppler` (macOS) or `apt install poppler-utils` (Linux). The poster will still render but with broken image refs for those figures.
- **`PIL`/Pillow not installed**: image resolutions cannot be computed; `dag.json` visuals have empty `resolution`. The poster_outline_prompt loses its "highest-resolution wins" tiebreaker — Claude picks by section order instead. Suggest `pip install Pillow`.
- **Validation fails**: print all issues to stderr; do not delete the partial output. User can fix the outline and re-run from Step 5.
- **Review LLM unreachable**: skip Step 6, note in report, continue.

## Dependencies

### Tools (via Bash)
- `python3 tools/wiki2dag.py build --paper-dir <dir> --output <path> [--anonymous]` — build dag.json
- `python3 tools/poster.py build --template <path> --outline <path> --output <path>` — inject outline
- `python3 tools/poster.py inject-title --dag <path> <poster.html> [--anonymous]` — set title/authors
- `python3 tools/poster.py inject-figures --dag <path> --paper-dir <path> --poster-dir <path>` — figure copy/convert
- `python3 tools/poster.py validate <poster.html>` — sanity checks
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `pdftoppm` (poppler) — PDF → PNG conversion at 200 DPI
- `pdfinfo` (poppler) — PDF page-size for resolution

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
