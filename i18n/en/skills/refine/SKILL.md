---
description: General-purpose multi-round iterative improvement — repeatedly calls /review on any research artifact, parses feedback, applies fixes, updates wiki, until the target score is reached
argument-hint: <artifact-slug-or-path> [--max-rounds N] [--target-score N] [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /refine

> General-purpose multi-round iterative improvement loop for any research artifact
> (idea, proposal, experiment plan, paper draft).
> Each round calls /review for structured feedback → parses actionable items → Claude fixes the artifact →
> updates wiki entities → re-reviews, until the score reaches the target or the maximum rounds are exhausted.
> Outputs an improvement history and the final review score.

## Inputs

- `artifact`: the artifact to improve, one of:
  - slug of a wiki page (searched in ideas/experiments/methods/outputs/)
  - file path (e.g. `wiki/outputs/paper-draft-v1.md`)
- `--max-rounds N` (optional, default 4): maximum iteration rounds
- `--target-score N` (optional, default 8): target review score (1-10); stop when reached
- `--difficulty` (optional, default `hard`): difficulty level passed to /review
- `--focus` (optional): review focus passed to /review

## Outputs

- **Improved artifact** (wiki page or file, updated in place)
- **Wiki entity updates** (if review finds ideas/methods needing strengthening or identifies gaps)
- **REFINE_REPORT** (output to terminal):
  - Score trajectory across all rounds
  - Cumulative list of fixed issues
  - Final review score and verdict
  - Unresolved issues (if any)

## Wiki Interaction

### Reads
- `wiki/ideas/*.md` — if artifact is an idea
- `wiki/experiments/*.md` — if artifact is an experiment plan
- `wiki/methods/*.md` — methods referenced by the review
- `wiki/papers/*.md` — papers referenced by the review
- `wiki/outputs/*.md` — if artifact is a paper draft or output
- `wiki/graph/context_brief.md` — global context passed to /review
- `wiki/graph/open_questions.md` — check whether new gaps need recording

### Writes
- `wiki/ideas/{slug}.md` — if artifact is an idea, fix issues found by review
- `wiki/experiments/{slug}.md` — if artifact is an experiment plan
- `wiki/methods/{slug}.md` — if review flags a method gap (e.g. missing source_papers, weak Procedure)
- `wiki/outputs/*.md` — if artifact is a paper draft or output
- `wiki/graph/edges.jsonl` — if new relationships are discovered during fixes
- `wiki/graph/context_brief.md` — rebuild after each round if wiki changes were made
- `wiki/graph/open_questions.md` — rebuild after each round if wiki changes were made
- `wiki/log.md` — append operation log

### Graph edges created
- Depends on fix content; may add: `supports`, `addresses_gap`, `inspired_by`, etc.

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).

### Step 1: Initialize

1. **Locate artifact**:
   - If slug: search sequentially in `wiki/ideas/`, `wiki/experiments/`, `wiki/methods/`, `wiki/outputs/`, `wiki/papers/` for `{slug}.md`
   - If file path: read directly
   - Record artifact type and path
2. **Read current content**: load full artifact text
3. **Initialize tracking variables**:
   - `round = 0`
   - `score_history = []`
   - `fixed_issues = []`
   - `unresolved_issues = []`
   - `wiki_changes = []`

### Step 2: Iteration Loop

Repeat the following steps until the termination condition is met:

**Round N (N = 1, 2, ..., max-rounds):**

#### 2a. Call /review

```
Skill: review
Args: "<artifact-path-or-content>" --difficulty {difficulty} --focus {focus}
```

Parse the review output and extract:
- `score` (1-10)
- `verdict` (ready / needs-work / major-revision / rethink)
- `weaknesses` (by severity: critical / major / minor)
- `actionable_items` (ranked list)
- `wiki_entity_mapping` (ideas/methods needing strengthening, gaps identified)

#### 2b. Check Termination Conditions

- **Target score reached**: `score >= target-score` → terminate, output final report
- **No score improvement for two consecutive rounds**: `score_history[-1] == score_history[-2]` → terminate (converged)
- **Maximum rounds reached**: `round >= max-rounds` → terminate
- **verdict == ready**: → terminate
- **verdict == rethink and round == 1**: → terminate and suggest redesign (do not iterate on a rethink-level artifact)

#### 2c. Classify Actionable Items and Apply Fixes

Classify and handle each actionable item:

**Category A — Method/content issues (Claude fixes directly):**
- Method description too vague → add details
- Missing comparative analysis → add comparison against baseline
- Incomplete argumentative logic → add reasoning steps
- Unclear expression → rewrite relevant paragraphs
- → Edit the artifact file directly

**Category B — Wiki knowledge gaps (suggest external operations):**
- Idea novelty argument too thin → suggest running `/novelty` rerun
- Method has no source_papers → flag for `/ingest` review
- Missing related work citations → suggest running `/ingest` to add papers
- Requires experimental validation → suggest running `/exp-run`
- → Record in `unresolved_issues`, list suggested operations in the report

**Category C — Idea / method updates (Claude fixes wiki):**
- Review identifies a missing concept link in an idea's `origin_gaps` → add the link and write the reverse `linked_ideas`
- Review finds a method missing parent/child relations → patch the method page
- Review discovers a new gap → record to gap_map (via rebuild)
- Review discovers a new relationship → add graph edge
- → Update relevant wiki pages, record in `wiki_changes`

**Category D — Out of scope (skip):**
- Requires new experimental data → cannot resolve in refine loop
- Requires domain expert judgment → mark as unresolved
- → Record in `unresolved_issues`

#### 2d. Update Tracking

- `score_history.append(score)`
- `fixed_issues.extend(category_A_items + category_C_items)`
- `unresolved_issues.extend(category_B_items + category_D_items)`
- `wiki_changes.extend(category_C_changes)`
- `round += 1`

#### 2e. Rebuild Derived Data (if wiki was changed)

If this round had wiki changes (Category C):
```bash
python3 tools/research_wiki.py rebuild-context-brief wiki/
python3 tools/research_wiki.py rebuild-open-questions wiki/
```

### Step 3: Final Report

After iteration ends, generate the REFINE_REPORT:

```markdown
# Refine Loop Report: {artifact title}

## Summary
- **Artifact**: {slug or path}
- **Rounds**: {N} / {max-rounds}
- **Score trajectory**: {score_history, e.g., 5 → 6 → 7 → 8}
- **Final score**: {final_score}/10
- **Final verdict**: {verdict}
- **Termination reason**: {target reached / converged / max rounds / rethink}

## Issues Fixed ({count})

| Round | Issue | Severity | Fix applied |
|-------|-------|----------|-------------|
| 1 | Method description too vague | major | Added specific algorithm steps |
| 1 | Idea novelty argument too thin | major | Flagged [[idea-slug]] for `/novelty` rerun |
| 2 | Missing ablation design | minor | Added ablation plan |

## Wiki Changes Made

| Page | Change | Round |
|------|--------|-------|
| `wiki/methods/{slug}.md` | added missing source_papers link | 1 |
| `wiki/graph/edges.jsonl` | +1 edge (addresses_gap) | 2 |

## Unresolved Issues ({count})

| Issue | Severity | Suggested action |
|-------|----------|------------------|
| Missing experimental validation | critical | Run `/exp-design {slug}` |
| Missing comparison paper | major | Run `/ingest` for {paper-title} |

## Next Steps
- {based on verdict and unresolved issues}
```

Append log:
```bash
python3 tools/research_wiki.py log wiki/ \
  "refine | {artifact-slug} | {N} rounds | score {initial}→{final} | verdict: {verdict}"
```

## Constraints

- **Each round must show substantive progress**: if score does not change for two consecutive rounds, terminate (prevents infinite loops)
- **Do not iterate on rethink**: if the first round verdict == rethink, terminate immediately and suggest redesign
- **Wiki modifications limited to review suggestions**: refine only modifies wiki entities explicitly recommended by the review; do not expand scope proactively
- **Unresolved issues must be listed**: do not silently skip issues that cannot be resolved in the loop
- **Preserve improvement history**: score_history and fixed_issues are recorded in full; do not discard intermediate state
- **Pass review parameters through**: --difficulty and --focus are passed through to /review; maintain consistent review standards
- **Artifact updated in place**: fixes modify the original file directly; do not create copies

## Error Handling

- **Artifact not found**: prompt user to check slug or path, list likely candidate pages
- **/review call fails**: retry once; if still failing, terminate the loop and output the improvement history completed so far
- **Wiki write fails**: log the error, continue to the next round (wiki changes downgraded to unresolved)
- **First round score already >= target-score**: terminate immediately, output report (no improvement needed)
- **All issues are Category B/D**: cannot fix within the loop; terminate and output the unresolved issues list

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gap_map
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge (if needed)
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log entry

### Skills（via Skill tool）
- `/review` — each round's review (core dependency)

### Claude Code Native
- `Read` — read artifact and wiki pages
- `Edit` — fix artifact content
- `Glob` — find artifact and related wiki pages

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — indirect dependency via /review
