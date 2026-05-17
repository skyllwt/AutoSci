---
description: Idea-driven experiment design with iterative ablation — method candidate generation (direct / hybrid / cross-idea combination) → benchmark selection → iterative ablation (non-linear: ablation can trigger method simplification and re-planning) → sensitivity analysis → main experiment → optional generalization → deep analysis of intermediate quantities. Use when designing a full experiment suite for an idea after pilot evaluation.
argument-hint: <idea-slug>
---

# /exp-design

> Design a complete, non-linear experiment suite for an idea.
> This skill supports method candidate generation, iterative ablation with method simplification, sensitivity analysis, and deep analysis of intermediate quantities.
> The ablation loop is the core non-linear feature: ablation results classify factors as essential/contributing/marginal/harmful, and marginal/harmful factors trigger method simplification and re-planning (capped at 2 iterations).

## Inputs

- `idea-slug`: the idea to design experiments for (reads from `wiki/ideas/{slug}.md`)

## Outputs

- Experiment wiki pages: `wiki/experiments/{exp-slug}.md` — one per experiment block (ablation, sensitivity, main, generalization, analysis), each with `status: planned` and `linked_idea` set
- Master design document: `experiments/designs/{slug}-master.md` — detailed specs for all experiment blocks
- `wiki/graph/edges.jsonl` — new `tested_by` edges: idea → each experiment
- `wiki/ideas/{slug}.md` — updated `linked_experiments` field
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/graph/open_questions.md` — rebuilt
- `wiki/log.md` — appended log entry
- **DESIGN_REPORT** (printed to terminal) — experiment suite summary, run order, compute budget

## Wiki Interaction

### Reads
- `wiki/ideas/{slug}.md` — idea's hypothesis, approach, risks, novelty argument
- `wiki/ideas/*.md` — other ideas (for Candidate C cross-idea combination, filtering for validated/pilot-passed ideas)
- `experiments/pilot/{slug}/report.md` — pilot evaluation results (if exists)
- `wiki/papers/*.md` — related papers for baseline setups and method details
- `wiki/concepts/*.md` and `wiki/topics/*.md` — referenced via idea's `origin_gaps`
- `wiki/methods/*.md` — reusable methods the idea builds on
- `wiki/experiments/*.md` — existing experiments (avoid duplicate designs)
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps

### Writes
- `wiki/experiments/{exp-slug}.md` — experiment wiki pages (one per block, following entity schema)
- `experiments/designs/{slug}-master.md` — master design document with detailed block specs
- `wiki/ideas/{slug}.md` — append experiment slugs to `linked_experiments`
- `wiki/graph/edges.jsonl` — add `tested_by` edges (idea → each experiment)
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log.md` — append operation log

### Graph edges created
- `tested_by`: idea → experiment (the idea is being validated by this experiment). The reverse direction is captured by the experiment's `linked_idea` frontmatter field, which `xref.yaml` reverses into the idea's `linked_experiments` list.

## Workflow

**Precondition**: confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

---

### Phase 1: Load Context & Validate Prerequisites

1. **Read idea page**: load `wiki/ideas/{slug}.md`, extract `## Motivation`, `## Hypothesis`, `## Approach sketch`, `## Novelty argument`, `## Risks` plus frontmatter fields `origin_gaps`, `tags`, `target_venue`, `priority`, `novelty_score`.

2. **Read pilot results** (if exists): load `experiments/pilot/{slug}/report.md` to understand pilot outcome. If pilot passed, proceed with confidence. If no pilot exists, proceed with caution and note reduced confidence in design document.

3. **Load relevant wiki context**:
   - Read `wiki/graph/context_brief.md` and `wiki/graph/open_questions.md`
   - From idea's `origin_gaps`, read referenced `wiki/concepts/*.md` and `wiki/topics/*.md`
   - From `## Approach sketch` wikilinks, read referenced `wiki/methods/*.md`
   - Read existing `wiki/experiments/*.md` whose `linked_idea` matches this idea

4. **Read related papers**: from `wiki/papers/*.md`, extract baseline setups and method details relevant to the idea.

---

### Phase 2: Method Candidate Generation

Generate 2–3 method candidates from the idea. Each candidate represents a different implementation strategy:

- **Candidate A — Direct**: straight implementation of the idea's proposed method from `## Approach sketch`
- **Candidate B — Hybrid/Fusion**: combine the idea's method with an existing method (from `wiki/methods/`) to balance performance and cost
- **Candidate C — Cross-idea Combination**: combine this idea with another existing idea that has been validated or passed pilot experiments (check `wiki/ideas/` for ideas with `pilot_result: passed` or `status: validated`). This tests whether two complementary ideas can compound gains.

For each candidate, document:
- Core mechanism / algorithm sketch (2–4 sentences)
- Expected advantages and risks
- Implementation complexity: low / medium / high
- Computational cost estimate (relative to baseline)

**Present candidates to user for review and selection.** User selects 1–2 candidates to proceed with. If user doesn't select, re-present with clearer trade-off comparison.

---

### Phase 3: Benchmark & Metric Selection

> Select the benchmark, including datasets, evaluation metrics and baseline methods. Among them, the datasets and evaluation metrics shall adopt the universally recognized standard benchmarks in the corresponding research field.

1. **Identify benchmark(s)** based on:
   - The idea's domain (NLP, CV, RL, etc.)
   - Standard benchmarks used in related papers (from `wiki/papers/`)
   - Dataset availability and compute constraints

2. **Select Dataset**:
   - Clarify the dataset to be used (taking into account task adaptability, scale and standardization level)
   - Specify the composition structure, usage methods and specifications of the dataset

3. **Select metrics**:
   - Primary metric: the single most important measure of success (e.g., accuracy, F1, reward)
   - Secondary metrics: supplementary measures (e.g., latency, memory, throughput)

4. **Define baselines**: list all methods the selected candidate(s) will be compared against. Include:
   - The reproduced baseline from the most relevant paper
   - Any SOTA methods from related work

5. **Document rationale**: why these benchmarks and metrics are appropriate for the idea's hypothesis.

---

### Phase 4: Experiment Suite Design (non-linear, with iteration)

This phase designs all experiment blocks. The ablation loop (Step 4.6) is the core non-linear feature.

#### Step 4.1 — Design Ablation Experiment

- Identify **ablation factors**: each independent component or hypothesis of the method that can be toggled on/off
- Design the **ablation matrix**: which combinations to test (typically: full method minus one factor per run)
- Define **metrics to collect**: not just final performance — also intermediate quantities (loss components, gradient norms, etc.) that help diagnose why each factor matters
- Each factor will later be classified as: ESSENTIAL / CONTRIBUTING / MARGINAL / HARMFUL

#### Step 4.2 — Design Sensitivity Analysis

- Identify **hyperparameters to sweep**: learning rate, method-specific parameters (e.g., sparsity ratio, fusion weight), model-specific params
- Define **sweep ranges and resolution**: start broad, refine later
- Plan **incremental execution**: run on a subset first (fewer steps, smaller dataset), then run full sweep with narrowed ranges

#### Step 4.3 — Design Main Experiment

- Selected method candidate(s) vs all baselines on full benchmark
- Multi-seed (>= 3 seeds for variance estimation)
- Full training budget
- Collect both final metrics and intermediate quantities (for deep analysis in Step 4.5)

#### Step 4.4 — Design Generalization Experiment (optional)

- Test on a different benchmark, dataset, or setting
- Verify the method's assumptions hold beyond the primary setup
- Only include if the idea's hypothesis makes generalization claims
- If included, document: what changes from main experiment, what new insight it provides

#### Step 4.5 — Design Deep Analysis

- Identify **intermediate quantities to log** during main experiment:
  - Gradient norms (per-layer, per-component)
  - Attention patterns or feature distributions
  - Loss decomposition (individual loss terms)
  - Anything that validates or invalidates the method's core hypothesis
- Define **analysis scripts/visualizations** to produce after experiments complete
- This is NOT about final metrics — it's about understanding *why* the method works (or doesn't)
- Specify which quantities must be collected *before* experiments run (instrumentation requirements)

Each experiment block carries:
- `title`: descriptive title
- `linked_idea`: the source idea slug (mandatory; required by the schema)
- `hypothesis`: specific hypothesis the experiment tests
- `type`: ablation / sensitivity / main / generalization / analysis — captured as a tag
- `setup`: model, dataset, hardware, framework
- `metrics`: list of evaluation metrics
- `baseline`: comparison baseline
- `success_criterion`: explicit pass/fail criterion (will live in `## Procedure` of the experiment page)
- `estimated_gpu_hours`: estimated compute time
- `seeds`: number of random seeds (recommend >= 3)

Block-specific requirements:

**Ablation**:
- Purpose: isolate the contribution of each independent factor of the method
- Each ablation removes one factor and validates the resulting performance drop
- N factors → N ablation runs (plus full method as control)
- Collect intermediate quantities for each run (not just final metrics)
- Success criterion: factor classification table (ESSENTIAL / CONTRIBUTING / MARGINAL / HARMFUL)
- Compute: similar to main experiment × N factors

**Sensitivity**:
- Purpose: find optimal hyperparameter values for the method
- Identify all method-specific hyperparameters (learning rate, sparsity ratio, fusion weight, etc.)
- Define sweep ranges (start broad) and resolution (grid or random search)
- Incremental: run on subset first, narrow ranges, then full sweep
- Success criterion: identified optimal hparams with clear sensitivity patterns
- Compute: moderate (subset sweep is cheap, full sweep depends on param count)

**Main**:
- Purpose: validate the idea's central proposition vs all baselines on full benchmark
- Selected method with best hparams from sensitivity analysis
- Multi-seed (>= 3 seeds) for statistical reliability
- Collect both final metrics and intermediate quantities for deep analysis
- Success criterion: statistically significant improvement over baselines
- Compute: highest (full training budget, multiple seeds, multiple baselines)

**Generalization** (optional):
- Purpose: verify the method holds under different conditions
- Test on at least 2 variation dimensions (different dataset, model size, domain, etc.)
- Uses finalized method and best hparams from main experiment
- Success criterion: performance holds (no catastrophic degradation) on new settings
- Compute: depends on number of variation dimensions

**Analysis**:
- Purpose: understand *why* the method works (or doesn't) by examining intermediate quantities
- Input: logs and intermediate data collected during main experiment
- Produce visualizations: gradient norms, attention patterns, loss decomposition, etc.
- Success criterion: intermediate quantities confirm (or contradict) the method's core hypothesis
- Compute: minimal (post-hoc analysis, no new training runs)

#### Step 4.6 — Iterative Ablation Loop (non-linear core)

This is the key difference from linear experiment design. After initial ablation results:

```
iteration = 0
while iteration < 2:
    run ablation experiment (via /exp-run)
    classify each ablation factor based on results:
      - ESSENTIAL:   removing it causes major performance degradation (>10%)  → keep
      - CONTRIBUTING: removing it causes moderate degradation (3-10%)        → keep
      - MARGINAL:    removing it has negligible effect (<3%)                 → candidate for removal
      - HARMFUL:     removing it improves performance                        → remove
    if any MARGINAL or HARMFUL factors found:
      simplify method:
        - Remove all HARMFUL factors
        - Discuss with user whether to remove MARGINAL factors
      re-plan ablation with reduced factor set
      iteration += 1
    else:
      break  # method is clean, proceed to main experiment
```

- After loop exits (max 2 iterations): finalize method design
- Record full iteration history in design document (what was removed, why, results at each iteration)
- The finalized method from this loop becomes the method used in main experiment (Step 4.3)

---

### Phase 5: Build Run Order

Order experiments by dependency and set decision gates:

```
Stage 0: Ablation (iteration 1)
  └── Run ablation matrix
  └── Classify factors → simplify if needed → re-run (iteration 2, up to max 2)
  
Stage 1: Sensitivity analysis (subset)
  └── Run on small subset to narrow hyperparameter ranges
  └── Gate: if no reasonable hparams found → stop, reconsider method

Stage 2: Main experiment
  └── Finalized method vs baselines, full benchmark, multi-seed
  └── Gate: no improvement over baseline → stop, analyze via deep analysis

Stage 3: Generalization (optional)
  └── Only if generalization experiment was designed in Step 4.4
  └── Uses finalized method and best hparams

Stage 4: Deep analysis
  └── Analyze intermediate quantities collected during Stage 2
  └── Produce visualizations and diagnostic report
```

Estimate total compute budget. Generate execution checklist with dependencies.

---

### Gate: User reviews designed experimental modules and execution sequence

**Before finalizing experimental modules and preparing design documents and wiki pages, confirmation must be obtained from users. Users are required to manually inspect the designed experimental modules. Proceed to Phase6 once confirmed; otherwise, make revisions repeatedly until users give approval.**

### Phase 6: Write Design Document

1. **Create master design document** at `experiments/designs/{slug}-master.md`:
   ```markdown
   ---
   title: "Experiment Design: {idea-title}"
   slug: "{idea-slug}-design"
   status: planned
   linked_idea: "{idea-slug}"
   tags: ["exp-design"]
   date_planned: YYYY-MM-DD
   ---

   ## Idea Summary
   {idea hypothesis and approach sketch}

   ## Method Candidates
   {table of candidates with selection rationale}

   ## Benchmark & Metrics
   {dataset, metrics, baselines}

   ## Experiment Blocks

   ### Ablation
   {ablation factors, matrix, metrics}

   ### Sensitivity Analysis
   {hyperparameters, sweep ranges}

   ### Main Experiment
   {method vs baselines, full config}

   ### Generalization (optional)
   {different setting/benchmark}

   ### Deep Analysis
   {intermediate quantities, analysis plan}

   ## Ablation Iteration History
   {record of each iteration: factors classified, simplifications made}

   ## Run Order & Budget
   {stage dependencies, estimated GPU-hours}

   ## Results
   (to be filled after /exp-run)
   ```

2. **Create experiment wiki pages** — one page per experiment block (following `runtime/schema/entities.yaml` and `runtime/templates/experiments.md.tmpl`):
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
   tags: []                     # include the type tag here: ["ablation"], ["sensitivity"], ["main"], ["generalization"], or ["analysis"]
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
   ```

   Body sections per block type:

   **Ablation** (`tags: ["ablation"]`):
   - `## Objective` — which factors are being tested, what the ablation reveals about the method
   - `## Setup` — ablation matrix (factor combinations), model, dataset, hardware, hyperparameters
   - `## Procedure` — step-by-step: run each factor combination, collect metrics and intermediate quantities
   - `## Results` (to be filled after /exp-run) — factor classification table: ESSENTIAL / CONTRIBUTING / MARGINAL / HARMFUL
   - `## Analysis` (to be filled after /exp-run) — which factors to remove, iteration history
   - `## Follow-up` — if MARGINAL/HARMFUL found: simplify method and re-run ablation (iteration 2); if all ESSENTIAL/CONTRIBUTING: proceed to main experiment

   **Sensitivity** (`tags: ["sensitivity"]`):
   - `## Objective` — which hyperparameters are being swept, what range is optimal
   - `## Setup` — sweep ranges and resolution, model, dataset, hardware
   - `## Procedure` — step-by-step: run subset first, narrow ranges, then full sweep
   - `## Results` (to be filled after /exp-run) — best hyperparameter values, performance curves
   - `## Analysis` (to be filled after /exp-run) — sensitivity patterns, recommended values for main experiment
   - `## Follow-up` — pass best hparams to main experiment

   **Main** (`tags: ["main"]`):
   - `## Objective` — what this experiment proves about the linked idea vs baselines
   - `## Setup` — method vs all baselines, full benchmark, multi-seed (>=3), best hparams from sensitivity
   - `## Procedure` — step-by-step execution plan with explicit success criterion; collect intermediate quantities for deep analysis
   - `## Results` (to be filled after /exp-run) — metric comparison table (method vs baselines), statistical significance
   - `## Analysis` (to be filled after /exp-run) — why method works/fails, intermediate quantity analysis
   - `## Follow-up` — contingency plans: what to do if success / failure

   **Generalization** (`tags: ["generalization"]`, optional):
   - `## Objective` — what generalization claim is being tested
   - `## Setup` — different benchmark/dataset/setting from main experiment
   - `## Procedure` — run finalized method with best hparams on new setting
   - `## Results` (to be filled after /exp-run) — performance on new setting vs main setting
   - `## Analysis` (to be filled after /exp-run) — does the method generalize?
   - `## Follow-up` — if fails: identify which assumption breaks

   **Analysis** (`tags: ["analysis"]`):
   - `## Objective` — which intermediate quantities to analyze, what hypothesis they validate
   - `## Setup` — data sources (logs from main experiment), visualization specs
   - `## Procedure` — run analysis scripts, produce plots and diagnostic tables
   - `## Results` (to be filled after /exp-run) — plots, tables, key observations
   - `## Analysis` (to be filled after /exp-run) — do intermediate quantities confirm the method's hypothesis?
   - `## Follow-up` — if hypothesis not confirmed: identify what went wrong

3. **Add graph edges**:
   ```bash
   # For each experiment page, idea → experiment
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{idea-slug}" --to "experiments/{exp-slug}" \
     --type tested_by --evidence "Designed by /exp-design"
   ```

4. **Update idea page**: append all experiment slugs to `linked_experiments` in `wiki/ideas/{slug}.md`.

6. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

7. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-design | {N} experiments designed for idea {slug} | linked_idea: {slug}"
   ```

8. **Print DESIGN_REPORT to terminal**:
   ```markdown
   # Design Report: {idea-slug}

   ## Target Idea
   - Idea: [[idea-slug]]
   - Hypothesis: {hypothesis}

   ## Method Candidates
   | # | Candidate | Type | Complexity | Selected |
   |---|-----------|------|------------|----------|
   | A | {name} | Direct | {low/med/high} | {yes/no} |
   | B | {name} | Hybrid/Fusion | {low/med/high} | {yes/no} |
   | C | {name} | Cross-idea Combination | {low/med/high} | {yes/no} |

   ## Benchmark
   - Primary: {benchmark} | Metric: {metric}
   - Baselines: {list}

   ## Experiment Blocks
   | # | Experiment | Type | GPU-hrs | Stage |
   |---|-----------|------|---------|-------|
   | 1 | [[slug]] | sensitivity | {N} | 0 |
   | 2 | [[slug]] | ablation | {N} | 1 |
   | 3 | [[slug]] | main | {N} | 2 |
   | 4 | [[slug]] | generalization | {N} | 3 |

   ## Ablation Iterations
   - Iterations planned: {N} (max 2)
   - Factors: {list with classifications}

   ## Run Order
   Stage 0: Sensitivity → Stage 1: Ablation → Stage 2: Main → Stage 3: Generalization → Stage 4: Deep Analysis

   ## Budget
   - Total estimated: {N} GPU-hours

   ## Next Steps
   - Run `/exp-run [[sensitivity-slug]]` to start Stage 0
   ```

## Constraints

- **Every experiment must reference an idea**: `linked_idea` is required by the schema. If no idea page exists, refuse to design — instruct user to run `/ideate` first.
- **No duplicate experiments**: before creating, scan `wiki/experiments/*.md` for existing experiments with same `linked_idea` + `hypothesis`.
- **Do NOT overwrite existing design files**: if `experiments/designs/{slug}-master.md` already exists, ask user before overwriting.
- **Method candidates must be grounded**: no hallucinated methods — all candidates must derive from the idea page's content.
- **Ablation loop capped at 2 iterations**: prevents infinite loops. After 2 iterations, finalize with current design.
- **Sensitivity sweep must be incremental**: subset first, full sweep second.
- **Deep analysis must be pre-planned**: specify which intermediate quantities to collect *before* experiments run — this is instrumentation, not post-hoc analysis.
- **Graph edges via tools/research_wiki.py**: do not manually edit `edges.jsonl`.
- **At least 3 seeds**: experiments requiring statistical reliability (main experiment) must specify >= 3 random seeds.
- **Success criteria must be quantified**: each experiment block needs a specific pass/fail number.

## Error Handling

- **Idea page not found**: report error, suggest running `/ideate` first.
- **No pilot results**: warn user, proceed but note reduced confidence in design document.
- **User doesn't select any method candidate**: re-present candidates with clearer trade-off comparison, ask for explicit choice.
- **Benchmark unavailable**: suggest alternatives, let user decide.
- **Ablation loop hits 2 iterations**: finalize with current design, note remaining marginal factors in report.
- **Similar experiment already exists**: list existing experiments, ask user whether to add or skip.
- **Insufficient compute budget**: reduce generalization experiment scope, note actual allocation in report.

## Dependencies

### Skills (via Skill tool)
- `/exp-run` — execute designed experiments
- `/exp-pilot-eval` — prerequisite: pilot evaluation should complete before formal design

### Tools (via Bash)
- `python3 tools/research_wiki.py slug "<title>"` — generate slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py set-meta ...` — update frontmatter fields
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild context
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gaps
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### Claude Code Native
- `Read` — read wiki pages
- `Write` — create design documents and experiment pages
- `Glob` — find existing experiments
- `AskUserQuestion` — method candidate selection

### Called by
- `/ideate` (after pilot evaluation)
- User directly
