---
description: Pilot result evaluation — read pilot results, apply success criteria, update idea page (pilot_result, failure_reason if failed), generate PILOT_VERDICT_REPORT. Called by /ideate Phase 5 after /exp-pilot-run.
argument-hint: <idea-slug> [--auto]
---

# /exp-pilot-eval

> Evaluate pilot experiment results and update the linked idea page.
> Reads pilot results from `experiments/pilot/code/{slug}/results/`, applies verdict logic (pass/fail/inconclusive), and updates the idea's `pilot_result`, `failure_reason`, and `status` fields.
> Called by `/ideate` Phase 5 after `/exp-pilot-run` completes.

## Inputs

- `idea-slug`: slug of the idea whose pilot was just run
- `--auto` (optional): automatic mode, no pause for user confirmation (used when called by `/research`)

## Outputs

- `wiki/ideas/{slug}.md` — updated `pilot_result` (always), `failure_reason` (if failed), `status` (if failed → `failed`)
- `wiki/log.md` — appended log entry
- **PILOT_VERDICT_REPORT** (printed to terminal) — verdict, wiki change summary, next step suggestions
- `experiments/pilot/{slug}/report.md` — PILOT_VERDICT_REPORT file copy (persistent record)

## Wiki Interaction

### Reads
- `wiki/ideas/{slug}.md` — linked idea current state: `status`, `pilot_result`, `failure_reason`
- `experiments/pilot/code/{slug}/results/seed_*.json` — pilot experiment results
- `experiments/pilot/code/{slug}/pilot.log` — pilot run log (for failure diagnosis: errors, warnings, runtime behavior)
- `experiments/pilot/{slug}.yaml` — Pilot Spec (for success_criterion and baseline reference)

### Writes
- `wiki/ideas/{slug}.md` — update `pilot_result`, `failure_reason` (if failed), `status` (if failed)
- `wiki/log.md` — append operation log
- `experiments/pilot/{slug}/report.md` — PILOT_VERDICT_REPORT file copy

### Graph edges created
- None. Pilot evaluations do not create graph edges (those are for formal experiments via `/exp-eval`).

## Workflow

**Step 1: Load Context**

1. Read idea page `wiki/ideas/{slug}.md`:
   - Current `status` and `pilot_result`
   - Current `failure_reason` (should be empty for proposed ideas)

2. Read pilot results from `experiments/pilot/code/{slug}/results/seed_*.json`:
   - Parse result files (JSON)
   - Compute mean ± std per metric (across seeds)

3. Read pilot log from `experiments/pilot/code/{slug}/pilot.log`:
   - Scan for errors, warnings, OOM, divergence signals
   - Extract runtime behavior context for failure diagnosis and verdict report

4. Read Pilot Spec from `experiments/pilot/{slug}.yaml`:
   - Extract `success_criterion` (pass, fail, inconclusive conditions)
   - Extract `baseline.expected_value` for comparison

**Step 2: Apply Verdict Logic**

Evaluate the pilot results against the success_criterion from the Pilot Spec. The verdict thresholds are intentionally lenient — the purpose of a pilot is to detect obvious failures, not to measure final performance.

- **Pass**: pilot does NOT show clear failure. Since pilots use reduced batch size (1/4–1/8 of paper's) and shortened training (10–30% of full steps), results are inherently noisy and biased downward. Therefore: improvement over baseline, roughly on par with baseline, or even slightly worse than baseline all count as pass. Also passes if the gap is confirmed (path C: existing methods indeed fail under new setting).
- **Fail**: pilot shows clear, unambiguous failure (divergence, severe degradation vs baseline, fundamental incompatibility). The threshold is high — only ideas that are clearly broken should fail at this stage.
- **Inconclusive**: pilot is noisy or ambiguous — results don't clearly pass or fail.

**Step 3: Update Idea Page**

If verdict == `pass`:
- Set `pilot_result`: `"pass — <one-sentence summary of key metric vs baseline>"`
- Status unchanged (stays `proposed` or current)
- Example: `"pass — accuracy 0.82 vs baseline 0.80, loss converges"`

If verdict == `fail`:
- Set `pilot_result`: `"fail — <specific failure>"`
- Set `failure_reason`: `"[pilot] <specific failure description>"`
  - The `[pilot]` prefix distinguishes pilot failures from `[filter]` eliminations (Phase 3) and post-experiment failures from `/exp-eval`
- Transition status to `failed`:
  ```bash
  python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md pilot_result "fail — <specific failure>"
  python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to failed --reason "[pilot] <specific failure description>"
  ```
  - `transition` validates lifecycle rules (e.g. refuses to downgrade `validated` → `failed`) and auto-sets `failure_reason` and `date_resolved`.
- Example failure_reason: `"[pilot] loss diverged after 50 steps (reached 1e5 vs baseline 0.3)"`

If verdict == `inconclusive`:
- Set `pilot_result`: `"inconclusive — needs full experiment"`
- Status unchanged

**Step 4: Report**

1. If `--auto` is not set: display verdict and wiki changes in terminal, wait for user confirmation on borderline cases

2. Append log:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-pilot-eval | {slug} | verdict: {verdict} | pilot_result: {result}"
   ```

3. Print **PILOT_VERDICT_REPORT** to terminal and write to `experiments/pilot/{slug}/report.md`:
   ```markdown
   # Pilot Verdict Report: {slug}

   ## Verdict: {pass / fail / inconclusive}

   ## Results Summary
   | Metric | Baseline | Pilot (mean±std) | Δ |
   |--------|----------|------------------|---|
   | {metric} | {baseline-value} | {mean}±{std} | {delta} |

   ## Pilot Log
   - Log: experiments/pilot/code/{slug}/pilot.log
   - Key signals: {errors / warnings / OOM / divergence observed in log, or "clean run"}

   ## Wiki Changes
   | Page | Field | Old | New |
   |------|-------|-----|-----|
   | ideas/{slug} | pilot_result | {old} | {new} |
   | ideas/{slug} | status | {old} | {new} | (only if changed) |
   | ideas/{slug} | failure_reason | — | {new} | (only if failed) |

   ## Next Steps
   - {if pass: proceed to /exp-design for full experiments}
   - {if fail: idea eliminated; review pilot log for details}
   - {if inconclusive: proceed to full experiment with caution}
   ```

## Constraints

- **Only processes pilot-tested ideas**: results must exist in `experiments/pilot/code/{slug}/results/`
- **failure_reason must be specific**: not vague "pilot failed" — include what failed and why
- **Idea lifecycle is forward-only**: `proposed → failed` (cannot regress validated → failed)
- **Does NOT create graph edges**: those are for formal experiments via `/exp-eval`
- **Pilot pass threshold is intentionally low**: detect obvious failures, not measure final performance
- **The `[pilot]` prefix is mandatory on failure_reason**: distinguishes from `[filter]` and post-experiment failures

## Error Handling

- **Idea page not found**: report error, suggest running `/ideate` first
- **Pilot results not found**: report error, suggest running `/exp-pilot-run` first
- **Idea already failed**: report current state, do not overwrite
- **Idea already validated**: refuse to downgrade status, report warning
- **Pilot Spec not found**: report error, suggest running `/ideate` first to generate the spec

## Dependencies

### Skills (via Skill tool)
- None

### Tools (via Bash)
- `python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md <field> "<value>"` — update idea fields (e.g. pilot_result)
- `python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to <status> [--reason "..."]` — transition idea lifecycle status
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log

### Claude Code Native
- `Read` — read idea page, pilot results, pilot log, Pilot Spec
- `Edit` — update idea page fields
- `Bash` — execute research_wiki.py commands

### Called by
- `/ideate` Phase 5
- User directly
