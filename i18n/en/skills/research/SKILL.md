---
description: End-to-end research orchestrator — idea discovery → experiment design → execution → verdict → paper writing, with human gates and session-resumable state
argument-hint: <research-direction-or-brief> [--auto] [--start-from stage1|stage2|stage3|stage3-collect|stage3-check|stage4|stage5] [--skip-paper] [--venue ICLR|NeurIPS|ICML|ACL|CVPR]
---

# /research

> End-to-end research orchestrator that composes all skills into a complete research workflow.
> Stage 0 (Bootstrap) + 5 Stages + 2 Human Gates, covering the full pipeline from empty wiki to paper submission.
> **Zero-friction entry**: if the wiki is empty, Bootstrap is triggered automatically (search + auto-ingest 5 papers); no need to run /init manually.
> Every Gate and Stage saves progress to `wiki/outputs/pipeline-progress.md`, supporting cross-session recovery.
>
> **Stage 3 is non-blocking**: experiments are deployed and control returns immediately (`--auto` mode automatically sets up a CronCreate to monitor every 30 minutes).
> When all experiments finish, Stage 4 is triggered automatically. Use `/exp-status` at any time to check progress.
>
> `--auto` mode skips manual confirmation (automatically selects the top-1 idea). `--skip-paper` runs the research without writing a paper.

## Inputs

- `direction`: research direction description or path to a `RESEARCH_BRIEF.md` file
  - Text form: one-sentence description of the research direction (e.g. "sparse LoRA for edge devices")
  - File form: structured RESEARCH_BRIEF.md (containing domain, constraints, target venues)
- `--auto` (optional): fully automatic mode; Gate 1 auto-selects top-1 idea, Gate 2 auto-continues, Stage 3b auto-creates CronCreate
- `--start-from <stage>` (optional): resume execution from the specified stage
  - Valid values: `stage1`, `stage2`, `stage3`, `stage3-collect`, `stage3-check`, `stage4`, `stage5`
  - `stage3-collect`: skip deploy, go directly to Stage 3c (collect results from already-deployed experiments)
  - `stage3-check`: check experiment status only (equivalent to `/exp-status --pipeline {slug}`), do not continue execution
  - Requires `wiki/outputs/pipeline-progress.md` to exist
- `--skip-paper` (optional): run research only (Stages 1-4), skip paper writing (Stage 5), but still run /exp-eval (Stage 4)
- `--venue` (optional): target conference (ICLR / NeurIPS / ICML / ACL / CVPR), passed to /paper-plan

## Outputs

- **Wiki updates** (delegated to sub-skills): ideas/, experiments/, methods/, outputs/, graph/
- **wiki/outputs/pipeline-progress.md** — pipeline progress snapshot (for recovery)
- **wiki/outputs/PIPELINE_REPORT.md** — full pipeline report
- **paper/ directory** (if not --skip-paper) — submittable paper
- **wiki/log.md** — log appended after each stage

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — global context (passed to sub-skills)
- `wiki/graph/open_questions.md` — knowledge gaps (passed to /ideate)
- `wiki/ideas/*.md` — Gate 1 selection, Stage 4 verdict, Stage 5 paper planning
- `wiki/experiments/*.md` — Stage 3-4 status checks
- `wiki/methods/*.md` — Stage 5 paper writing context
- `wiki/outputs/pipeline-progress.md` — --start-from state recovery
- `wiki/papers/*.md` — Stage 5 paper writing context

### Writes
- `wiki/outputs/pipeline-progress.md` — save progress at each Gate (wiki entity writes are delegated to sub-skills)
- `wiki/outputs/PIPELINE_REPORT.md` — final report
- `wiki/log.md` — append log entries
- All other wiki entity writes are delegated to sub-skills (do not directly write to ideas/experiments/methods/)

### Graph edges created
- None directly — all graph edges are delegated to sub-skills (/ideate, /exp-design, /exp-eval each create their own edges)

## Workflow

**Precondition**:
1. Confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`)
2. If `--start-from` is specified, read `wiki/outputs/pipeline-progress.md` to restore state

### Step 0: Initialize

1. **Parse input**:
   - If file path: read RESEARCH_BRIEF.md, extract direction, domain, constraints, target_venue
   - If text: use as direction; leave domain/constraints blank
   - Generate slug: `python3 tools/research_wiki.py slug "{direction}"`

2. **Auto-recovery detection** (when `--start-from` is not specified):
   - If `wiki/outputs/pipeline-progress.md` exists and `status == running`:
     - Read direction, current_stage, started, slug
     - Use AskUserQuestion to prompt the user:
       ```
       Unfinished pipeline detected:
       Direction: {direction}
       Current stage: {current_stage}
       Started: {started}

       [1] Resume from {current_stage} (recommended)
       [2] Start a new pipeline (will overwrite old progress)
       [3] View experiment status first (/exp-status --pipeline {slug})
       ```
     - If --auto or user selects [1]: auto-set `--start-from {current_stage}`, continue execution
     - If user selects [2]: continue creating new pipeline (overwrite old progress file)
     - If user selects [3]: call `/exp-status --pipeline {slug}` then exit without continuing

3. **Check recovery** (when `--start-from` is specified):
   - If `wiki/outputs/pipeline-progress.md` exists:
     - Read progress file, restore idea_slug, experiment_slugs, stage3a_deployed, linked_idea_slugs, monitoring_cron_id
     - Jump to specified stage
   - If progress file does not exist: report error and exit; prompt user to run the full pipeline first
   - **`--start-from stage3-check`**: equivalent to calling `/exp-status --pipeline {slug}`; display status then exit
   - **`--start-from stage3-collect`**: skip Stage 3a+3b; go directly to Stage 3c (collect already-deployed experiments)

3. **Create progress file** `wiki/outputs/pipeline-progress.md`:
   ```yaml
   ---
   slug: "{pipeline-slug}"
   direction: "{research direction}"
   status: running
   current_stage: stage1
   started: YYYY-MM-DD
   mode: auto|interactive
   skip_paper: true|false
   venue: "{venue}"
   idea_slug: ""
   experiment_slugs: []
   stage3a_deployed: []
   linked_idea_slugs: []
   iteration_count: 0
   ---
   ## Stage Log
   - Stage 0 (Bootstrap): skipped
   - Stage 1: pending
   - Gate 1: pending
   - Stage 2: pending
   - Stage 3a (Deploy): pending
   - Stage 3b (Await): pending
   - Stage 3c (Collect): pending
   - Stage 4: pending
   - Gate 2: pending
   - Stage 5: pending
   ```

4. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | started | direction: {direction} | mode: {auto|interactive}"
   ```

5. **Snapshot wiki state** (for Growth Report in Step Final):
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   Save returned JSON to memory variable `maturity_before`.

### Stage 0: Bootstrap (triggered automatically when wiki is empty)

**Trigger condition**: run `python3 tools/research_wiki.py maturity wiki/ --json`. If `level == "cold"` and `papers < 3`: enter Bootstrap automatically. Otherwise skip and proceed to Stage 1.

1. **Initialize wiki structure** (if not yet initialized):
   ```bash
   python3 tools/research_wiki.py init wiki/
   ```

2. **Search for relevant papers** (use Agent tool with 3 parallel searches):
   - DeepXiv: `python3 tools/fetch_deepxiv.py search "{direction}" --mode hybrid --limit 20`
   - Semantic Scholar: `python3 tools/fetch_s2.py search "{direction}" --limit 20`
   - arXiv: `python3 tools/fetch_arxiv.py` (using direction keywords)
   - If DeepXiv is unavailable: skip; use only S2 + arXiv

3. **Merge, rank, and select top 5**:
   - Deduplicate by arxiv_id
   - Ranking priority: DeepXiv relevance score > S2 citation count > recency
   - Select top 5 (5 = minimum threshold for cold→warm)

4. **Auto-ingest each paper**:
   ```
   Skill: ingest
   Args: "{arxiv_url_or_path}"
   ```
   Output progress after each ingest: `[{i}/5] Ingested: {paper_title}`

5. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

6. **Bootstrap report**:
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   Output to terminal:
   ```
   Bootstrap complete:
   Papers: {N} | Concepts: {K} | Methods: {Mt} | Edges: {E}
   Maturity: cold → {new_level}
   Proceeding to Stage 1: Idea Discovery...
   ```

7. **Log + update progress**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | stage0-bootstrap | auto-ingested {N} papers | maturity: {level}"
   python3 tools/research_wiki.py set-meta \
     wiki/outputs/pipeline-progress.md current_stage stage1
   ```

### Stage 1: Idea Discovery

Call `/ideate`:

```
Skill: ideate
Args: "{direction}" --auto
```

**After completion**:
1. Read the generated ideas and sort them according to the pilot experiment results and priority.
2. Update pipeline-progress: Stage 1 → completed, record generated idea slugs
3. Append log

### Gate 1: Select Idea

**If `--auto` mode**:
- Automatically select the highest-priority (top-1) idea
- Output selection result to terminal without waiting for confirmation

**If interactive mode**:
- List all generated ideas (slug, title, priority, novelty score，pilot result)
- Use AskUserQuestion to prompt user to select one idea (or enter "stop" to halt)
- If user selects stop: save progress, terminate pipeline

**Save progress**:
- Update pipeline-progress: Gate 1 → passed, record idea_slug
- Update selected idea status: proposed → in_progress

### Stage 2: Experiment Design

Call `/exp-design`:

```
Skill: exp-design
Args: "{idea_slug}"
```

**After completion**:
1. Read generated experiment slugs (pages in wiki/experiments/ where linked_idea == idea_slug，and retrieve the detailed specs of the experiment block from experiments/designs/{slug}-master.md based on the exp-slug)
2. Update pipeline-progress: Stage 2 → completed, record experiment_slugs

### Stage 3: Experiment Execution (non-blocking)

Stage 3 is divided into three sub-stages, allowing experiments to run asynchronously in the background without blocking the session.

#### Stage 3a: Deploy All

Deploy each experiment in run order (baseline → validation → ablation → robustness) by calling `/exp-run {experiment_slug}` (default deploy mode, Phase 1+2):

```
Skill: exp-run
Args: "{experiment_slug}"
```

(Default deploy mode, Phase 1+2: returns immediately after deployment, does not wait for experiment to finish)

**After each deployment**:
- Record deployment result (success/failure) in memory
- If deploy fails: record to pipeline-progress with a warning (baseline deploy failure gets a stronger warning), but **continue deploying remaining experiments** (do not abort)

**After all deployments complete**, update pipeline-progress.md:
```bash
python3 tools/research_wiki.py set-meta \
  wiki/outputs/pipeline-progress.md current_stage stage3-await
python3 tools/research_wiki.py set-meta \
  wiki/outputs/pipeline-progress.md stage3a_deployed \
  "[{experiment_slug_1}, {experiment_slug_2}, ...]"
```
Append log:
```bash
python3 tools/research_wiki.py log wiki/ \
  "research | stage3a | deployed {N} experiments | pipeline: {slug}"
```

#### Stage 3b: Await (non-blocking)

After all experiments are deployed, compute ETA, save progress, and end the current session.

1. Update pipeline-progress:
   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/outputs/pipeline-progress.md current_stage stage3-await
   ```
2. **Compute estimated completion time for each experiment**:
   For each deployed experiment, read `started` and `estimated_hours` from frontmatter:
   - `eta = started + estimated_hours`
   - `recommended_return = max(all etas) + 30-minute buffer, rounded up to nearest hour or half-hour`
3. Append log:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "research | stage3b | awaiting {N} experiments | latest eta: {YYYY-MM-DD HH:MM} | pipeline: {slug}"
   ```
4. Output instructions then **end current session**:
   ```
   Stage 3a complete: {N} experiments all deployed:

   Experiment                      Environment     Est. Duration   Est. Completion
   ──────────────────────────────  ──────────────  ─────────────   ───────────────
   exp-foo-baseline                local           ~8h             Tomorrow 09:30
   exp-foo-validation              remote (gpu1)   ~6h             Today 23:00
   exp-foo-ablation                local           ~4h             Today 21:00

   Latest completion: Tomorrow 09:30 (exp-foo-baseline)
   Recommended time to return: Tomorrow 10:00+

     /exp-status                              ← confirm all experiments complete
     /research --start-from stage3-collect    ← collect results and continue

   Progress saved to wiki/outputs/pipeline-progress.md; current session can be closed.
   ```

#### Stage 3c: Collect (triggered after experiments complete)

**Trigger**: user manually runs `/research --start-from stage3-collect`

For each deployed experiment (read from `stage3a_deployed` list):
```
Skill: exp-run
Args: "{experiment_slug} --collect"
```

(Collect mode, Phase 3+4: check completion status and collect results)

**Decision after each collect**:
- If outcome == failed and this is the baseline experiment → **terminate pipeline**, report baseline cannot be reproduced
- If outcome == failed and this is a validation experiment → record failure, continue collecting remaining experiments, proceed to Stage 4 evaluation
- If outcome == inconclusive → record and continue

**After all collects complete**:
- Update pipeline-progress: Stage 3 → completed
  ```bash
  python3 tools/research_wiki.py set-meta \
    wiki/outputs/pipeline-progress.md current_stage stage4
  ```
- Append log:
  ```bash
  python3 tools/research_wiki.py log wiki/ \
    "research | stage3c | collected {N} experiments | pipeline: {slug}"
  ```

- Update the status of linked idea: in_progress -> tested

- Proceed to Stage 4

### Stage 4: Verdict & Iteration

Call `/exp-eval` for each completed experiment:

```
Skill: exp-eval
Args: "{experiment_slug}" --auto
```

**Evaluate whether the linked idea is sufficient**:
1. Read the latest status of the primary linked idea (and any supporting ideas)
2. Determine whether iteration is needed:
   - **Sufficient** (primary linked idea has been transitioned to `validated`, OR ≥1 supporting experiment has `outcome=succeeded`) → proceed to Gate 2
   - **Insufficient** (idea remains `proposed`or`in_progress`or`tested` and all linked experiments are `failed`/`inconclusive`, or idea is `failed`) → enter iteration

**Iteration path** (when insufficient, up to 1 retry):
1. Analyze the cause of failure
2. Call `/refine` for the corresponding experimental blocks that need improvement to optimize the experiment plan:
   ```
   Skill: refine
   Args: "{experiment_plan_slug}" --max-rounds 2 --focus evidence
   ```
3. Re-run Stage 3 → Stage 4 for new/modified experiments
4. Maximum 2 iterations (prevents infinite loops); each stage has at most 1 auto-retry

**After completion**:
- Update pipeline-progress: Stage 4 → completed, record linked_idea_slugs

### Gate 2: Confirm Paper Ready

**If `--skip-paper`**: skip Gate 2 and Stage 5, generate final report directly

**If `--auto` mode**: automatically continue, enter Stage 5

**If interactive mode**:
- Display idea status summary:
  ```
  Idea: {slug} | Status: {status} | Novelty: {novelty_score}
  Linked experiments: {count} ({succeeded}/{inconclusive}/{failed})
  ```
- Use AskUserQuestion to prompt user: ready for paper / need more experiments / stop here
- If "need more experiments": return to Stage 2 for replanning
- If "stop here": save progress, generate final report (without paper)

**Save progress**:
- Update pipeline-progress: Gate 2 → passed

### Stage 5: Paper Writing

Call sub-skills in sequence: /paper-plan → /paper-draft → /refine → /paper-compile

**5a. Call /paper-plan**:
```
Skill: paper-plan
Args: "{linked_idea_slugs}" --venue {venue}
```
(passes the validated idea slug(s) collected in Stage 4 to /paper-plan)

**5b. Call /paper-draft**:
```
Skill: paper-draft
Args: "wiki/outputs/PAPER_PLAN.md" --review
```

**5c. Call /refine on paper**:
```
Skill: refine
Args: "paper/main.tex" --max-rounds 3 --target-score 8 --focus writing
```

**5d. Call /paper-compile**:
```
Skill: paper-compile
Args: "paper/"
```

**After completion**:
- Update pipeline-progress: Stage 5 → completed, status: completed

### Step Final: Pipeline Report

Generate `wiki/outputs/PIPELINE_REPORT.md`:

```markdown
# Research Pipeline Report

## Stage Summary
| Stage | Status | Duration |
|-------|--------|----------|
| Stage 0: Bootstrap | completed/skipped | ... |
| Stage 1: Idea Discovery | completed | ... |
| Gate 1: Idea Selection | passed | ... |
| Stage 2: Experiment Design | completed | ... |
| Stage 3a: Deploy Experiments | completed | ... |
| Stage 3b: Await (async) | completed | ... |
| Stage 3c: Collect Results | completed | ... |
| Stage 4: Verdict | completed | ... |
| Gate 2: Paper Ready | passed | ... |
| Stage 5: Paper Writing | completed | ... |

## Selected Idea
- **Idea**: [[{idea_slug}]] — {idea title}
- **Priority**: {N}
- **Novelty score**: {score}

## Idea Trail
| Idea | Initial Status | Final Status | Novelty (start → end) |
|------|----------------|--------------|------------------------|
| [[{slug}]] | proposed | validated | 3 → 4 |

## Experiment Results
| Experiment | Outcome | Key Result |
|-----------|---------|------------|
| [[{slug}]] | succeeded | {result} |

## Iteration History
- Total iterations: {N}
- Reason for iteration: {idea evidence insufficient / ...}

## Deliverables
- Ideas: +{N} created, {N} validated
- Experiments: +{N} created, {N} completed
- Methods: +{N} created/updated
- Graph edges: +{N}
- Paper: paper/main.pdf (if applicable)

## Wiki Growth (pipeline total)
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Papers | {N} | {N} | +{N} |
| Methods | {N} | {N} | +{N} |
| Ideas | {N} | {N} | +{N} |
| Experiments | {N} | {N} | +{N} |
| Edges | {N} | {N} | +{N} |
| Maturity | {level} | {level} | {status} |
| Coverage | {%} | {%} | +{%} |
(Data from comparing `maturity_before` from Step 0 against a fresh call to `maturity --json` here. Only rows with delta != 0 are shown.)

## Next Steps
- {recommendations based on remaining gaps or unresolved issues}
```

Append log:
```bash
python3 tools/research_wiki.py log wiki/ \
  "research | completed | idea: {slug} | linked ideas: {N} updated | paper: {yes/no}"
```

Update pipeline-progress: status: completed

## Constraints

- **Orchestrator does not directly modify wiki entities or embed sub-skill logic**: all wiki modifications are delegated to sub-skills; the pipeline only coordinates by calling them via the Skill tool
- **Gates and Stages must save progress**: every Gate and Stage must save pipeline-progress.md when completed or entering await
- **Stage 3a deploy failures do not abort**: record a warning and continue deploying; do not terminate early (baseline collect failure is what triggers termination)
- **Baseline collect failure terminates**: in Stage 3c, if baseline outcome == failed, terminate the pipeline
- **Stage 3b ends the session**: after Stage 3b completes, the current session ends; do not continue waiting for experiments
- **Maximum 2 iterations**: Stage 4 iterates at most 2 times to prevent infinite loops
- **--auto does not skip computation**: auto mode skips human confirmation but skips no computation steps
- **--skip-paper still runs Stage 4 /exp-eval**: idea/experiment updates must be completed even when not writing a paper
- **Pass sub-skill parameters through**: correctly pass domain, --venue, and other parameters to sub-skills
- **Log every Stage**: append a log.md audit entry after each Stage completes
- **Do not re-run completed stages**: --start-from skips already-completed stages
- **Progress file at wiki/outputs/pipeline-progress.md**: consistent location for easy discovery and recovery
- **Auto-recovery first**: if no --start-from is given and an unfinished pipeline exists, default to prompting the user to resume rather than starting fresh

## Error Handling

- **pipeline-progress missing but --start-from specified**: report error; prompt user to run the full pipeline first
- **pipeline-progress corrupted or malformed**: attempt to infer progress from current wiki state (read ideas/experiments statuses), recover to the nearest Gate
- **Sub-skill call fails**: record error to pipeline-progress, report the failed stage, suggest --start-from to resume
- **All ideas generation fails**: terminate pipeline; suggest the user adjust the research direction
- **All experiment deploys fail**: terminate pipeline (Stage 3a); generate failure report; suggest checking GPU/SSH configuration
- **Stage 3c baseline collect fails**: terminate pipeline; report baseline cannot be reproduced; suggest re-running /exp-design
- **All experiment collects fail (non-baseline)**: proceed to Stage 4 evaluation (treat failures as evidence)
- **Gate user selects stop**: save progress to pipeline-progress; generate partial report
- **RESEARCH_BRIEF.md malformed**: fall back to plain-text direction; ignore structured fields
- **Wiki empty (no papers/concepts)**: auto-trigger Stage 0 Bootstrap (search + auto-ingest 5 papers)
- **Idea evidence still insufficient after iteration**: annotate report with "idea evidence insufficient after max iterations"; let user decide whether to continue
- **User selects view status (auto-recovery detection [3])**: call `/exp-status --pipeline {slug}` then exit without starting a new pipeline

## Dependencies

### Skills（via Skill tool）
- `/ingest` — Stage 0 Bootstrap auto-ingest
- `/ideate` — Stage 1 idea discovery
- `/exp-design` — Stage 2 experiment design
- `/exp-run` — Stage 3a (deploy mode) and Stage 3c (--collect mode)
- `/exp-status` — user manually checks experiment progress; `--auto-advance` can automatically trigger Stage 4 when all complete
- `/exp-eval` — Stage 4 verdict
- `/refine` — Stage 4 iteration + Stage 5 paper improvement
- `/paper-plan` — Stage 5 paper planning
- `/paper-draft` — Stage 5 paper writing
- `/paper-compile` — Stage 5 paper compilation

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "{title}"` — generate pipeline slug
- `python3 tools/research_wiki.py set-meta <path> <field> <value>` — update pipeline-progress fields
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log entry
- `python3 tools/research_wiki.py maturity wiki/ --json` — check wiki maturity (Stage 0 trigger + Growth Report)
- `python3 tools/research_wiki.py init wiki/` — initialize wiki structure (Stage 0)
- `python3 tools/fetch_deepxiv.py search "{query}" --mode hybrid --limit 20` — DeepXiv semantic search (Stage 0)
- `python3 tools/fetch_s2.py search "{query}" --limit 20` — Semantic Scholar search (Stage 0)
- `python3 tools/fetch_arxiv.py` — arXiv RSS search (Stage 0)

### MCP Servers
- None directly — all Review LLM interactions are used indirectly via sub-skills

### Claude Code Native
- `Read` — read pipeline-progress, wiki pages, RESEARCH_BRIEF
- `Write` — write pipeline-progress, PIPELINE_REPORT
- `Glob` — find experiments, ideas, methods
- `Skill` — call sub-skills (core capability)
- `AskUserQuestion` — user interaction at Gates and auto-recovery detection
