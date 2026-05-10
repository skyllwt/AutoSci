---
description: Idea-driven experiment design — scope an idea's hypothesis → design experiment blocks (baseline / validation / ablation / robustness) → build run order → optional Review LLM review → write to wiki
argument-hint: <idea-slug-or-hypothesis> [--linked-idea <idea-slug>] [--review] [--budget <gpu-hours>]
---

# /exp-design

> Given an idea (or a free-text hypothesis), design a complete experiment plan.
> Ideas are the core: scope the idea's hypothesis across three dimensions — Target, Decomposition, and Threats.
> Design four types of experiment blocks: baseline (reproduce baseline), validation (core verification), ablation (factor isolation), and robustness (stress testing).
> Experiments are ordered by dependency with decision gates between stages (sanity fail → early stop).
> Optional Review LLM review checks experiment plan completeness. All experiments are written to `wiki/experiments/` and reverse-link back to the idea via the `linked_idea` frontmatter field.

## Inputs

- `idea`: one of:
  - A slug from `wiki/ideas/` (e.g. `sparse-lora-for-edge-devices`) — the recommended path
  - A free-text hypothesis description (acceptable; an idea page will be created or referenced)
- `--linked-idea <idea-slug>` (optional): explicit binding when the positional arg is free text but the user already has an idea page they want every new experiment to reference. Equivalent to passing the slug positionally; provided so the SPA can call `/exp-design --linked-idea <slug>` from the idea reader page.
- `--review` (optional): enable Review LLM review to check experiment plan completeness
- `--budget <gpu-hours>` (optional): total compute budget cap (GPU hours), affects robustness experiment scope

## Outputs

- `wiki/experiments/{slug}.md` — one page per experiment block (status: planned, `linked_idea` set)
- `wiki/graph/edges.jsonl` — new `tested_by` edges: idea → experiment
- `wiki/ideas/{slug}.md` — updated `linked_experiments` field
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/graph/open_questions.md` — rebuilt
- `wiki/log.md` — appended log entry
- **EXPERIMENT_PLAN_REPORT** (printed to terminal) — experiment block summary, run order, compute budget

## Wiki Interaction

### Reads
- `wiki/ideas/{slug}.md` — idea's hypothesis, approach, risks, novelty argument, `origin_gaps`
- `wiki/concepts/*.md` and `wiki/topics/*.md` — referenced via the idea's `origin_gaps` (concepts/topics this idea closes)
- `wiki/methods/*.md` — relevant reusable methods that the idea builds on (sourced from the idea's `## Approach sketch` references)
- `wiki/papers/*.md` — for baseline setups and prior experiment protocols, traversed via `concepts.key_papers` / `methods.source_papers`
- `wiki/experiments/*.md` — existing experiments (avoid duplicate designs, reference setup configs)
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps (guide experiment priority)

### Writes
- `wiki/experiments/{slug}.md` — create experiment pages (one per experiment block); each includes a non-empty `linked_idea` frontmatter field
- `wiki/ideas/{slug}.md` — append new experiment slugs to `linked_experiments`; transition status from `proposed` to `in_progress` if applicable
- `wiki/graph/edges.jsonl` — add `tested_by` edges (idea → experiment)
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log.md` — append operation log

### Graph edges created
- `tested_by`: idea → experiment (the idea is being validated by this experiment). The reverse direction is captured by the experiment's `linked_idea` frontmatter field, which `xref.yaml` reverses into the idea's `linked_experiments` list.

## Workflow

**Precondition**: confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

### Step 1: Load Context

1. **Parse idea input**:
   - If a slug (or `--linked-idea` was passed): read `wiki/ideas/{slug}.md`, extract `## Motivation`, `## Hypothesis`, `## Approach sketch`, `## Novelty argument`, `## Risks` plus the frontmatter fields `origin_gaps`, `tags`, `target_venue`, `priority`, `novelty_score`.
   - If free text: use directly as the hypothesis description and warn that no idea page is bound; the user should pass `--linked-idea` so each experiment can carry a `linked_idea` slug. Without an idea slug, exit with an error — `linked_idea` is required on every experiment in the new schema.
2. **Load relevant wiki context**:
   - Read `wiki/graph/context_brief.md` (global context)
   - Read `wiki/graph/open_questions.md` (knowledge gaps)
   - From the idea's `origin_gaps`, read each `wiki/concepts/{slug}.md` or `wiki/topics/{slug}.md`. From their `key_papers` (concepts) / `## Seminal works` + `## SOTA tracker` (topics), recover the relevant `wiki/papers/*.md` for baseline setups.
   - From `## Approach sketch` wikilinks, read the referenced `wiki/methods/{slug}.md` pages — these tell you which reusable techniques the idea inherits and shape the ablation factors.
   - Read existing `wiki/experiments/*.md` whose `linked_idea` matches this idea (avoid duplicating prior designs).

### Step 2: Scope the Hypothesis

Decompose the idea's `## Hypothesis` along three dimensions. The output of this step is a tabular scope sheet, not new wiki pages — `/exp-design` does not create concepts or methods. (If the scoping reveals a missing concept, the right move is `/edit` or `/ingest`, not silent creation here.)

1. **Target dimension** — the idea's central proposition restated as one testable statement. Typically 1, at most 2.
2. **Decomposition dimension** — list each independent factor in the proposed approach. One row per factor; this is the ablation backbone.
3. **Threats dimension** — known risks, alternative explanations, boundary conditions. Sources: the idea's `## Risks`, the source papers' `## Limitations`, and any related concept/topic `## Open problems` entries. This is the robustness backbone.

Output: a markdown table with columns `dimension | proposition | source (idea section / concept / method / paper)`.

### Step 3: Design Experiment Blocks

Design experiment blocks for each scope row. Four types:

**A. Baseline experiments (reproduce baseline)**:
- Purpose: confirm the problem exists and the baseline is reproducible
- Reproduce the core experiment from the most relevant paper (resolved via `origin_gaps → concept.key_papers` or `## Approach sketch → method.source_papers`)
- Success criterion: baseline results deviate < 5% from reported paper values (this threshold is the same one used by the Stage 1 decision gate below — do not introduce a different number elsewhere)
- Compute: typically minimal

**B. Validation experiments (validate Target)**:
- Purpose: validate the idea's central proposition on top of the baseline
- Metrics: statistically significant improvement over baseline
- Requires sufficient seed/run count for reliability (recommend >= 3 seeds)
- Compute: moderate

**C. Ablation experiments (validate Decomposition factors)**:
- Purpose: isolate the contribution of each independent factor
- Each ablation removes one factor and validates the resulting performance drop
- N factors → N ablation experiments
- Compute: similar to validation × N

**D. Robustness experiments (rule out Threats)**:
- Purpose: rule out known risks and alternative explanations; verify the method holds under varied conditions
- Variation dimensions: model size, dataset, hyperparameters, domain
- Test at least 2 variation dimensions
- Compute: depends on `--budget`

Each experiment block carries:
- `title`: descriptive title
- `linked_idea`: the source idea slug (mandatory; required by the schema and validated at write time)
- `hypothesis`: specific hypothesis the experiment tests
- `type`: baseline / validation / ablation / robustness — captured as a tag rather than a frontmatter enum (the schema has no `type` field on experiments)
- `setup`: model, dataset, hardware, framework
- `metrics`: list of evaluation metrics
- `baseline`: comparison baseline
- `success_criterion`: explicit pass/fail criterion (will live in `## Procedure` of the experiment page)
- `estimated_gpu_hours`: estimated compute time
- `seeds`: number of random seeds (recommend >= 3)

### Step 4: Build Run Order

Sort experiments by dependency and set decision gates:

```
Stage 0: Sanity check
  └── Small-scale run (1 epoch / 100 steps) to verify no code bugs, data loads, GPU available, loss decreasing
  └── Gate: sanity fails → stop, fix code

Stage 1: Baseline (reproduce baseline)
  └── Reproduce baseline results
  └── Gate: baseline deviation > 5% → stop, check implementation (same threshold as Step 3 success criterion)

Stage 2: Validation (core verification)
  └── Validate the idea's central proposition on top of the baseline
  └── Gate: no improvement → stop, analyze reason (idea may not hold)

Stage 3: Ablation (factor isolation)
  └── Multiple ablations can run in parallel
  └── Gate: if a factor ablation shows no effect → record it, but continue other ablations

Stage 4: Robustness (robustness verification)
  └── Only execute after Stage 2 succeeds
  └── Scope determined by remaining --budget
```

Output:
- Ordered experiment list (with dependencies)
- Decision gate conditions for each stage
- Total compute budget estimate (if exceeding `--budget`, adjust Stage 4 scope)

### Step 5: Optional Review LLM Review (`--review`)

If `--review` is specified:

```
mcp__llm-review__chat:
  system: "You are a senior ML researcher reviewing an experiment plan.
           Focus on: missing baselines, missing ablations, unfair comparisons,
           statistical rigor (enough seeds?), and dataset selection.
           For every issue found, suggest a concrete fix."
  message: |
    ## Idea
    {idea title, hypothesis, novelty argument}

    ## Experiment Plan
    {complete experiment plan: scope sheet, blocks, run order, budgets}

    ## Context
    {related papers' experiment setups, concepts/methods the idea inherits}

    ## Review Questions
    1. Are any critical experiments missing?
    2. Are the baselines fair and comprehensive?
    3. Is the ablation design sufficient to isolate each contribution?
    4. Are the success criteria well-defined and reasonable?
    5. Any statistical concerns (sample size, variance, seeds)?
```

Revise the experiment plan based on Review LLM feedback (add missing experiments, correct unreasonable criteria).

### Step 6: Write to Wiki

1. **Create experiment pages**:
   For each experiment block:
   ```bash
   python3 tools/research_wiki.py slug "<experiment-title>"
   ```
   Create `wiki/experiments/{slug}.md` following `runtime/schema/entities.yaml::experiments` and `runtime/templates/experiments.md.tmpl` exactly — every frontmatter field below must be present even if empty, because `/exp-run` later uses `tools/research_wiki.py set-meta` to update them, and `set-meta` refuses to create fields that don't already exist:
   ```yaml
   ---
   title: ""
   slug: ""
   status: planned
   linked_idea: "{idea-slug}"   # MANDATORY (required by schema). Reverse link to wiki/ideas/{idea-slug}.md::linked_experiments via xref.yaml.
   hypothesis: ""
   tags: []                     # include the type tag here: ["baseline"], ["validation"], ["ablation"], or ["robustness"]
   setup:
     model: ""
     dataset: ""
     hardware: ""
     framework: ""
   metrics: []
   baseline: ""
   outcome: ""                  # empty until /exp-run Phase 4 — succeeded | failed | inconclusive
   key_result: ""               # empty until /exp-run Phase 4
   date_planned: YYYY-MM-DD
   date_completed: ""           # empty until /exp-run Phase 4
   run_log: ""                  # empty until /exp-run Phase 2
   started: ""                  # empty until /exp-run Phase 2 (ISO timestamp, set via set-meta)
   estimated_hours: 0           # 0 until /exp-run Phase 2 (set via set-meta)
   remote:                      # full block must exist so /exp-run --env remote can populate sub-fields via Edit
     server: ""
     gpu: ""
     session: ""
     started: ""
     completed: ""
   ---

   ## Objective
   {what this experiment proves about the linked idea}

   ## Setup
   {detailed setup: model, dataset, hardware, hyperparameters}

   ## Procedure
   {step-by-step execution plan, including the explicit success criterion}

   ## Results
   (to be filled after /exp-run)

   ## Analysis
   (to be filled after /exp-run)

   ## Idea updates
   (to be filled after /exp-eval — records the linked idea's status / pilot_result transition)

   ## Follow-up
   {contingency plans: what to do if success / failure}
   ```

2. **Add graph edges**:
   ```bash
   # For each experiment, idea → experiment
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{idea-slug}" --to "experiments/{slug}" \
     --type tested_by --evidence "Designed by /exp-design"
   ```

3. **Update idea page**:
   - Append all new experiment slugs to `linked_experiments` in `wiki/ideas/{idea-slug}.md`
   - If idea status is `proposed`, transition to `in_progress` via `tools/research_wiki.py transition`

4. **Update index.md**: append entries under the experiments category.

5. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

6. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-design | {N} experiments designed for idea {slug} | linked_idea: {slug}"
   ```

7. **Print EXPERIMENT_PLAN_REPORT to terminal**:
   ```markdown
   # Experiment Plan Report

   ## Target Idea
   - Idea: [[idea-slug]]
   - Hypothesis: {hypothesis}
   - Novelty score: N/5 (or "—" if not yet scored)

   ## Scoped Hypothesis
   | Dimension | Proposition | Source |
   |-----------|-------------|--------|
   | target | {target proposition} | idea ## Hypothesis |
   | decomposition | {factor 1} | method [[method-slug]] |
   | decomposition | {factor 2} | method [[method-slug]] |
   | threat | {known risk} | idea ## Risks / concept ## Open problems |

   ## Experiment Blocks
   | # | Experiment | Type | Linked idea | GPU-hrs | Stage |
   |---|-----------|------|-------------|---------|-------|
   | 1 | [[baseline-slug]] | baseline | idea-slug | 2 | 1 |
   | 2 | [[validation-slug]] | validation | idea-slug | 8 | 2 |
   | 3 | [[ablation-1-slug]] | ablation | idea-slug | 8 | 3 |
   | 4 | [[robustness-slug]] | robustness | idea-slug | 16 | 4 |

   ## Run Order
   Stage 0: Sanity → Stage 1: Baseline → Stage 2: Validation → Stage 3: Ablation → Stage 4: Robustness
   Decision gates at each stage boundary.

   ## Budget
   - Total estimated: {N} GPU-hours
   - Budget limit: {--budget or "unlimited"}

   ## Next Steps
   - Run `/exp-run [[baseline-slug]]` to start Stage 1
   - After each stage, run `/exp-eval` to update the linked idea's status / pilot_result
   ```

## Constraints

- **Every experiment must reference an idea**: `linked_idea` is required by the schema and by this skill's contract. If no idea page exists, refuse to design experiments — instruct the user to run `/ideate` or write an idea page first.
- **No duplicate experiments**: before creating, scan `wiki/experiments/*.md` for existing experiments with the same `linked_idea` + `hypothesis`.
- **Scoped propositions are not persisted**: the dimension table from Step 2 is a planning artifact, not a wiki write. Do not create new concept/method/topic pages from `/exp-design`.
- **Success criteria must be quantified**: each experiment block's success criterion must include a specific number (e.g. "> 2% accuracy improvement"). Place it in the `## Procedure` body section.
- **At least 3 seeds**: experiments requiring statistical reliability (validation, ablation) must specify >= 3 random seeds.
- **Graph edges via tools/research_wiki.py**: do not manually edit `edges.jsonl`.
- **Idea status advances only forward**: `proposed → in_progress`, irreversible (governed by `entities.yaml::ideas.lifecycle`).
- **Slug uniqueness**: check for existing slug before creating.

## Error Handling

- **Idea not found**: prompt user to check slug, list candidates in `wiki/ideas/`.
- **Free-text input without `--linked-idea`**: refuse to proceed — direct the user to `/ideate` first or to pass `--linked-idea`.
- **Similar experiment already exists**: list existing experiments, ask user whether to add or skip.
- **Review LLM unavailable** (`--review` mode): skip Step 5, note "unreviewed — Review LLM unavailable" in report.
- **Budget insufficient**: reduce Stage 4 robustness experiment scope, note actual budget allocation in report.
- **Slug conflict**: append numeric suffix (e.g. `sparse-lora-ablation-v2`).
- **Wiki is empty**: proceed normally but baseline experiments have no prior results to reference; recommend running `/ingest` for relevant papers first.

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — generate slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to in_progress` — advance idea lifecycle
- `python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md linked_experiments [<slug>] --append` — update idea linked_experiments
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### MCP Servers
- `mcp__llm-review__chat` — Step 5 experiment plan review (optional)

### Claude Code Native
- `Read` — read wiki pages
- `Glob` — find existing experiments

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Step 5 Review LLM review independence (if enabled)

### Called by
- `/research` Stage 2 (experiment design stage)
- User directly
- The SPA's idea-page action button (`/exp-design --linked-idea <idea-slug>` via `tools/serve.py`)
