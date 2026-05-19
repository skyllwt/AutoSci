---
description: Experiment verdict gate — Review LLM independently judges results → 4 verdict paths → auto-update the linked idea's status / failure_reason and graph edges
argument-hint: <experiment-slug> [--auto]
---

# /exp-eval

> Convert completed experiment results into wiki knowledge updates.
> Review LLM acts as an impartial judge (following cross-model-review), independently evaluating how experimental results affect the linked idea's hypothesis.
> Four verdict paths: supported → idea validated / partially_supported → supplementary experiments /
> not_supported → idea failed / inconclusive → debug.
> Auto-updates the linked idea's `status`, `failure_reason`, and graph edges.

## Inputs

- `experiment`: slug from `wiki/experiments/` (status must be `completed`)
- `--auto` (optional): automatic mode — do not pause for user confirmation before wiki updates (used when called by /research)

## Outputs

- `wiki/ideas/{linked-idea}.md` — updated `status`, `failure_reason`, `date_resolved`
- `wiki/experiments/{slug}.md` — `## Idea updates` section filled in (records the linked idea's status transition; replaces the legacy `## Claim updates` heading)
- `wiki/graph/edges.jsonl` — new `supports` / `invalidates` edges added (experiment → idea)
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/graph/open_questions.md` — rebuilt
- `wiki/log.md` — appended log entry
- **VERDICT_REPORT** (printed to terminal) — verdict result, wiki change summary, next step suggestions

## Wiki Interaction

### Reads
- `wiki/experiments/{slug}.md` — experiment results: `outcome`, `key_result`, `metrics`, full Results section, `linked_idea`
- `wiki/ideas/{linked-idea}.md` — linked idea current state: `status`, `## Hypothesis`, `## Risks`
- `wiki/experiments/*.md` — sibling experiments with the same `linked_idea` (aggregate assessment)
- `wiki/graph/context_brief.md` — global context
- `.claude/skills/shared-references/cross-model-review.md` — reviewer independence principle

### Writes
- `wiki/ideas/{linked-idea}.md` — update `status`, `failure_reason`, `date_resolved`
- `wiki/experiments/{slug}.md` — fill in `## Idea updates` section
- `wiki/graph/edges.jsonl` — add `supports` / `invalidates` edges (experiment → idea)
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log.md` — append operation log

### Graph edges created
- `supports`: experiment → idea (experiment supports the idea's hypothesis) — verdict = supported or partially_supported
- `invalidates`: experiment → idea (experiment refutes the idea's hypothesis) — verdict = not_supported

## Workflow

**Precondition**:
1. Confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`)
2. Confirm experiment status == `completed` (incomplete experiments cannot be evaluated)

### Step 1: Load Context

1. **Read experiment page** `wiki/experiments/{slug}.md`:
   - `outcome` (succeeded/failed/inconclusive)
   - `key_result`
   - `linked_idea` slug (mandatory; refuse to proceed if missing)
   - `metrics` and full `## Results` section
   - `hypothesis`

2. **Read linked idea** `wiki/ideas/{linked-idea}.md`:
   - Current `status`
   - `## Hypothesis`, `## Approach sketch`, `## Risks`, `## Novelty argument`

3. **Load sibling experiments** (same `linked_idea`):
   - Glob `wiki/experiments/*.md`, filter `linked_idea == this idea`
   - Summarize their outcomes (the verdict considers the whole evidence portfolio, not just this one experiment)

4. **Read global context**: `wiki/graph/context_brief.md`

5. **Read cross-model-review.md**: confirm Review LLM independence principle

### Step 2: Review LLM Verdict (Cross-Model Verdict)

**Follow cross-model-review.md**: do not send Claude's pre-judgment to Review LLM.

```
mcp__llm-review__chat:
  system: "You are an impartial scientific judge evaluating whether experimental
           results support or refute a research hypothesis. Be rigorous and objective.
           Consider: statistical significance, effect size, experimental validity,
           potential confounds, and whether the results generalize beyond the
           specific setup tested."
  message: |
    ## Idea Hypothesis Under Test
    Title: {idea title}
    Hypothesis: {idea ## Hypothesis section}
    Novelty argument: {idea ## Novelty argument section}
    Current status: {idea status}

    ## Experiment
    Title: {experiment title}
    Hypothesis: {experiment hypothesis}
    Setup: {model, dataset, hardware, framework}
    Metrics: {metrics list}

    ## Results
    {full Results section from experiment page}

    ## Key Finding
    {key_result}

    ## Sibling Experiments on This Idea
    {summary of other experiments' outcomes that share the same linked_idea, if any}

    ## Your Task
    Provide your verdict:
    1. **Verdict**: One of: supported / partially_supported / not_supported / inconclusive
    2. **Evidence strength**: weak / moderate / strong
    3. **Idea status recommendation**: keep current / advance to validated / mark failed
    4. **Key reasoning**: 2-3 sentences explaining your verdict
    5. **Concerns**: Any methodological concerns or limitations
    6. **Suggested next steps**: What would strengthen or clarify this result?
```

Record Review LLM's verdict.

### Step 3: Claude Synthesis

1. **Form Claude's independent verdict** (after reading Review LLM's verdict, Claude also analyzes independently):
   - Based on experimental results, the idea's hypothesis, and aggregate evidence from sibling experiments
   - Form Claude's own verdict and idea-status recommendation

2. **Synthesize both verdicts** (follow cross-model-review.md composing rules):
   - **Both agree** (same verdict): use that verdict, high certainty
   - **Both disagree**:
     - Explicitly flag the disagreement
     - Take the more conservative verdict (supported > partially_supported > not_supported)
     - Detail the disagreement reason in the report
   - **Fatal findings take priority**: if either party finds a methodological issue (data leakage, unfair comparison), that finding takes precedence

3. **Determine final verdict**: verdict + evidence_strength + idea_status_change

### Step 4: Update Wiki Based on Verdict

**If `--auto` is not set**: display verdict and planned changes first, wait for user confirmation.

#### Path A: SUPPORTED (experiment supports the idea's hypothesis)

1. **Update idea**:
   - If the idea covers a single hypothesis and this experiment is the main experiment block, transition the idea to `validated`:
     ```bash
     python3 tools/research_wiki.py transition wiki/ideas/{linked-idea}.md --to validated
     ```
   - Otherwise leave the idea in its current lifecycle state (`tested` if it had previously been; `in_progress` if not).

2. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type supports --evidence "{key_result}"
   ```

3. **Suggest next steps**: `/paper-plan {linked-idea}` or continue ablation/robustness experiments

#### Path B: PARTIALLY_SUPPORTED (partial support)

1. **Update idea**:
   - Lifecycle stays at the current state (`in_progress` or `tested`)

2. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type supports --evidence "Partially supported: {limitation}"
   ```

3. **Suggest supplementary experiments**:
   - Specify what evidence is missing
   - Suggest using `/exp-design --linked-idea {linked-idea}` to design supplementary experiments
   - If Review LLM-flagged concerns are addressable by experiment, suggest concrete experiment direction

#### Path C: NOT_SUPPORTED (experiment refutes the idea's hypothesis)

1. **Update idea**:
   - Transition to `failed`:
     ```bash
     python3 tools/research_wiki.py transition wiki/ideas/{linked-idea}.md --to failed --reason "<concrete reason>"
     ```
     `transition` requires a non-empty `--reason`; supply the synthesized failure reason here. The `transition` command writes `failure_reason` and `date_resolved` automatically.
   - Note: `failure_reason` is anti-repetition memory — it must state the concrete reason, not vague "did not work".

2. **Add graph edge**:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "experiments/{slug}" --to "ideas/{linked-idea}" \
     --type invalidates --evidence "{failure_reason}"
   ```

3. **Suggest next steps**:
   - Analyze the failure reason
   - Consider pivoting (new idea addressing the same gap while avoiding the known failure)
   - Suggest `/ideate` to generate alternatives

#### Path D: INCONCLUSIVE (results are uncertain)

1. **Do not modify idea status**: insufficient evidence to make a judgment

2. **Update experiment page**: outcome is already inconclusive (set by /exp-run)

3. **Suggest debugging**:
   - Data issue? Implementation bug? Wrong metric?
   - Too much variance? More seeds needed?
   - Experiment setup not aligned with the idea's hypothesis?

4. **Idea status unchanged**: keep current status

#### All Paths (common steps)

1. **Fill in the `## Idea updates` section of the experiment page** (records changes to the linked idea, not a separate claim entity):
   ```markdown
   ## Idea updates
   - **Verdict**: {supported/partially_supported/not_supported/inconclusive}
   - **Linked idea**: [[{linked-idea}]] status {old} → {new}
   - **Judge agreement**: {Claude and Review LLM agreed / disagreed on ...}
   - **Date**: YYYY-MM-DD
   ```

2. **Update index.md** (if idea status changed)

3. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

4. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-eval | {slug} → ideas/{linked-idea} | verdict: {verdict} | idea status: {old}→{new}"
   ```

5. **Print VERDICT_REPORT to terminal**:
   ```markdown
   # Verdict Report: {experiment title}

   ## Verdict: {SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE}

   ## Judge Assessment
   | | Claude | Review LLM | Final |
   |---|-------|------|-------|
   | Verdict | {verdict} | {verdict} | {verdict} |
   | Idea status rec | {rec} | {rec} | {rec} |
   | Evidence strength | {strength} | {strength} | {strength} |

   ## Key Reasoning
   {2-3 sentences from Review LLM + Claude synthesis}

   ## Wiki Changes
   | Entity | Field | Before | After |
   |--------|-------|--------|-------|
   | ideas/{slug} | status | {old} | {new} |

   ## Graph Edges Added
   - experiments/{slug} → ideas/{linked-idea} (supports/invalidates)

   ## Concerns
   {methodological concerns from Review LLM}

   ## Next Steps
   - {path-specific suggestions}

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Ideas validated | {before} | {after} | +{delta} |
   | Ideas failed | {before} | {after} | +{delta} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {level} | {level} | {unchanged/upgraded} |
   (Data from comparing `python3 tools/research_wiki.py maturity wiki/ --json` calls at the start of Step 1 and end of Step 4.)
   ```

## Constraints

- **Only process completed experiments**: experiments with status != completed are refused; prompt user to use /exp-run first.
- **`linked_idea` is mandatory**: refuse to evaluate any experiment whose `linked_idea` is empty (the new schema enforces this; if you encounter such a page it is a pre-refactor artifact and must be fixed manually).
- **Reviewer independence**: strictly follow cross-model-review.md — do not send Claude's pre-judgment to Review LLM.
- **`failure_reason` must be specific**: the not_supported path's `failure_reason` cannot be vague (e.g. "experiment failed") — must state the concrete reason. `transition --reason` rejects an empty string.
- **Idea lifecycle is forward-only**: `proposed → in_progress → tested → validated/failed`. Use `tools/research_wiki.py transition` (not direct frontmatter writes) so the lifecycle validator runs.
- **Graph edges via tools/research_wiki.py**: do not manually edit `edges.jsonl`.
- **Conservative principle**: when Claude and Review LLM verdicts disagree, use the more conservative verdict.
- **Assess using all sibling experiments**: consider not just the current experiment but also other experiments sharing the same `linked_idea`.

## Error Handling

- **Experiment not found**: prompt user to check slug, list candidates in `wiki/experiments/` with status=completed.
- **Experiment not completed**: report status, suggest running `/exp-run {slug}` or `/exp-run {slug} --check`.
- **`linked_idea` missing**: refuse to proceed; instruct the user to run `/edit` to set the experiment's `linked_idea`.
- **Linked idea page does not exist**: report a dangling reference; refuse to update — recommend `/edit` or `/ideate` to create the idea page first.
- **Review LLM unavailable**: fall back to Claude single-model verdict, note "single-model verdict, cross-model verification unavailable" in report, suggest user confirm later.
- **Idea was modified by another experiment**: re-read the latest state before applying transitions; do not overwrite a more advanced lifecycle state with a lower one.
- **Results data missing**: if the experiment page's Results section is empty, prompt user to run `/exp-run {slug} --check` first.

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to validated|failed [--reason "..."]` — advance idea lifecycle
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### MCP Servers
- `mcp__llm-review__chat` — Step 2 Review LLM independent verdict

### Claude Code Native
- `Read` — read wiki pages
- `Glob` — find sibling experiments sharing the same `linked_idea`
- `Edit` — update wiki pages

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Review LLM independence principle (required reading)

### Called by
- `/research` Stage 4 (verdict and iteration stage)
- User directly
