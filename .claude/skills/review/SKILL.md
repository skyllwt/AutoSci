---
description: General-purpose cross-model review — Review LLM independently reviews any research artifact, outputs structured scores, wiki entity mapping, and improvement suggestions
argument-hint: <artifact-path-or-slug> [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /review

> Review any research artifact (idea, proposal, experiment plan, paper draft, method) using cross-model review.
> Uses Review LLM as an independent reviewer. Outputs a structured score, actionable improvement suggestions,
> and a mapping to wiki entities (which ideas/methods need strengthening, which gaps are discovered).
> Supports three difficulty levels (standard / hard / adversarial) and four review focuses.
> Can be used standalone or called by /ideate, /refine, /exp-design.

## Inputs

- `artifact`: the artifact to review, one of:
  - slug of a wiki page (e.g. `sparse-lora-for-edge-devices`, searched in ideas/experiments/methods/)
  - file path (e.g. `wiki/outputs/paper-draft-v1.md`)
  - free text (directly pasted proposal or idea description)
- `--difficulty` (optional, default `standard`):
  - `standard`: single-round review, delivers structured feedback
  - `hard`: multi-round dialogue (up to 3 rounds), Claude rebuts each weakness
  - `adversarial`: multi-round dialogue (up to 3 rounds), Review LLM additionally attempts to find fatal flaws, simulating the harshest reviewer
- `--focus` (optional, default comprehensive review):
  - `method`: focus on technical correctness, novelty, and feasibility of method design
  - `evidence`: focus on sufficiency of evidence, experimental rigor, idea/method support
  - `writing`: focus on clarity, structural organization, and argumentative logic
  - `completeness`: focus on missing content (related work, ablations, baselines)

## Outputs

- **Review Report** (output to terminal):
  - Overall Score (1-10)
  - Strengths (list of positives)
  - Weaknesses (list of issues, ranked by severity)
  - Questions (reviewer questions)
  - Actionable Suggestions (improvement suggestions ranked by priority)
  - Wiki Entity Mapping (which ideas/methods need strengthening, which gaps were found)
  - Verdict: `ready` / `needs-work` / `major-revision` / `rethink`
- If `--difficulty >= hard`: additionally includes multi-round dialogue history and final revised score
- This skill **does not directly modify the wiki**, but outputs a list of suggested wiki updates

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — locate papers cited by the artifact, verify citation accuracy
- `wiki/concepts/*.md` — understand technical concepts involved in the artifact
- `wiki/methods/*.md` — check the current status of methods the artifact depends on
- `wiki/experiments/*.md` — find related experiment results
- `wiki/ideas/*.md` — if reviewing an idea, check its context
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — check completeness against the gap map
- `.claude/skills/shared-references/cross-model-review.md` — reviewer independence principle

### Writes
- **None**. Review is a read-only query operation.
  - Review results are output to terminal; the user or caller (e.g. /refine) decides whether to apply them.

### Graph edges created
- **None**.

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).

### Step 1: Load Context

1. **Parse artifact**:
   - If slug: search sequentially in `wiki/ideas/`, `wiki/experiments/`, `wiki/methods/`, `wiki/papers/`, `wiki/outputs/` for `{slug}.md`
   - If file path: read directly
   - If free text: use directly
2. **Determine artifact type**: idea / experiment / method / paper-draft / proposal / other
3. **Load relevant wiki context**:
   - Read `wiki/graph/context_brief.md` for global perspective
   - Read `wiki/graph/open_questions.md` for knowledge gap list
   - Load relevant wiki pages by artifact type:
     - idea → its origin_gaps (concepts/topics), related papers
     - experiment → its linked_idea, related experiments
     - method → its source_papers and parent_methods
     - paper-draft → all wiki pages it cites
4. **Read cross-model-review.md**: confirm Review LLM independence principle
5. **Build reviewer system prompt** (based on --focus):

   **Base prompt (all focuses):**
   ```
   You are a senior ML researcher reviewing a research artifact.
   Be thorough, specific, and constructive. For every weakness, suggest a concrete fix.
   Score on a 1-10 scale where:
   - 1-3: Fundamental flaws, not salvageable in current form
   - 4-5: Significant issues but core idea may have merit
   - 6-7: Solid work with clear areas for improvement
   - 8-9: Strong work, minor issues only
   - 10: Exceptional, publication-ready
   ```

   **Focus-specific additions:**
   - `method`: additionally assess technical correctness, novelty of approach, feasibility, comparison to alternatives
   - `evidence`: additionally assess experimental rigor, statistical significance, idea-evidence alignment, missing controls
   - `writing`: additionally assess clarity, logical flow, notation consistency, figure quality, related work coverage
   - `completeness`: additionally assess missing baselines, missing ablations, missing datasets, missing related work, reproducibility

   **Adversarial addition (adversarial mode only):**
   ```
   Additionally: actively search for fatal flaws. A fatal flaw is anything that,
   if true, would make the entire contribution invalid (incorrect proof, data leakage,
   unfair comparison, published prior work). If you find one, flag it clearly.
   ```

### Step 2: Review LLM Initial Review

**Follow cross-model-review.md**: do not send any of Claude's pre-judgments to Review LLM.

```
mcp__llm-review__chat:
  system: {reviewer system prompt from Step 1}
  message: |
    ## Artifact to Review
    {artifact full text}

    ## Context from Knowledge Base
    {relevant wiki context: related ideas/methods with status, related experiments, gap map entries}

    ## Review Instructions
    Please provide:
    1. **Strengths** (3-5 bullet points)
    2. **Weaknesses** (ranked by severity, each with a concrete suggestion to fix)
    3. **Questions** (things that are unclear or need clarification)
    4. **Score** (1-10 with one-sentence justification)
    5. **Verdict**: ready / needs-work / major-revision / rethink
    6. **Idea-/method-level feedback**: For each idea or method referenced in the artifact, assess whether the evidence/justification is sufficient. List any ideas or methods that need stronger support.
    7. **Knowledge gaps identified**: Any open questions or missing knowledge that would strengthen this work.
```

Record the `threadId` returned by Review LLM (for multi-round dialogue in Step 3).

### Step 3: Multi-Round Dialogue (hard / adversarial mode)

Skip this step if `--difficulty` is `standard`.

**Respond to each of Review LLM's weaknesses** (up to 3 rounds):

**Round N (N = 1, 2, 3):**

1. Claude analyzes Review LLM's weaknesses and classifies each:
   - **Rebuttal**: Claude has strong reasoning or wiki evidence to counter it → write a rebuttal
   - **Acknowledge**: the weakness genuinely exists → acknowledge it and propose a fix
   - **Clarify**: the weakness is based on a misunderstanding → provide clarification

2. Send Claude's response to Review LLM:
   ```
   mcp__llm-review__chat-reply:
     threadId: {from Step 2}
     message: |
       Thank you for the review. Here are my responses:

       {for each weakness: rebuttal / acknowledgment / clarification}

       Please re-evaluate considering these responses. Update your score if warranted.
       If --difficulty == adversarial: Also, please try harder to find any remaining
       fatal flaws I may have missed.
   ```

3. Review LLM responds with a new assessment and revised score

4. If Review LLM's score change < 0.5 and no new weaknesses → stop dialogue (converged)
5. If 3 rounds reached → stop dialogue

### Step 4: Structured Output

Synthesize Step 2 + Step 3 results into a structured Review Report:

```markdown
# Review Report: {artifact title}

## Meta
- **Artifact type**: {idea / experiment / method / paper-draft / proposal}
- **Difficulty**: {standard / hard / adversarial}
- **Focus**: {method / evidence / writing / completeness / comprehensive}
- **Reviewer**: Review LLM (configured in `.env`)
- **Rounds**: {1 for standard, N for hard/adversarial}

## Score: {final score}/10 — {verdict}

| Verdict | Meaning |
|---------|---------|
| ready | Ready to use or submit directly |
| needs-work | Clear improvement points; usable after fixes |
| major-revision | Core sections need significant revision |
| rethink | Fundamental direction may be flawed; reconsider |

## Strengths
1. {strength 1}
2. {strength 2}
...

## Weaknesses (by severity)

### Critical
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Major
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Minor
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

## Questions
1. {question}
...

## Wiki Entity Mapping

### Ideas / methods needing stronger support
| Entity | Signal | Issue | Suggested action |
|--------|--------|-------|------------------|
| [[idea-slug]] | novelty_score 2/5 | Novelty argument is thin | Run /novelty rerun |
| [[method-slug]] | source_papers sparse | Missing source paper backing | Ingest the missing paper, then rerun /check |

### Knowledge gaps identified
| Gap | Related to | Suggested action |
|-----|-----------|------------------|
| {description} | [[slug]] | /ingest, /exp-run, or /query |

### Suggested wiki updates
- `wiki/ideas/{slug}.md`: add risk factor from review
- `wiki/methods/{slug}.md`: tighten Tradeoff profile / Limitations
- `wiki/graph/open_questions.md`: will be updated on next rebuild

## Dialogue History (hard/adversarial only)

### Round 1
**Review LLM**: {summary of initial review}
**Claude**: {summary of rebuttals/acknowledgments}

### Round 2
**Review LLM**: {updated assessment}
...

## Actionable Items (ranked)
1. [CRITICAL] {action item}
2. [MAJOR] {action item}
3. [MINOR] {action item}
```

## Constraints

- **Reviewer independence**: strictly follow `shared-references/cross-model-review.md`; do not leak Claude's pre-judgments to Review LLM
- **Do not modify wiki**: review only outputs suggestions; it does not directly modify any wiki pages. Wiki modifications are handled by the caller (e.g. /refine)
- **Scores must have justification**: scores without a rationale are not accepted
- **Weaknesses must have fixes**: every weakness must include a specific, actionable fix suggestion; vague criticism is not accepted
- **Entity-level mapping is required**: output must include the Wiki Entity Mapping section, mapping review findings to specific wiki entities (ideas, methods, etc.)
- **Adversarial mode must search for fatal flaws**: e.g. fully published identical work, incorrect proofs, data leakage
- **Multi-round dialogue capped at 3 rounds**: prevents infinite loops; output current state if 3 rounds do not converge
- **Use [[slug]] when referencing wiki pages**: all references to wiki pages use wikilink syntax

## Error Handling

- **Artifact not found**: prompt user to check slug or path, list likely candidate pages
- **Review LLM unavailable**: downgrade to Claude self-review mode; annotate report with "single-model review, cross-model verification unavailable"; recommend the user retry with Review LLM later
- **Wiki empty**: proceed with review normally, but annotate Wiki Entity Mapping section with "wiki empty, no entity mapping available"
- **Artifact too long**: if it exceeds Review LLM's context window, review section by section and merge at the end
- **Review LLM returns invalid response**: retry once; if still invalid, use Claude self-review fallback
- **Review LLM does not converge in multi-round dialogue**: force-stop after 3 rounds; output the last round's score and summary

## Dependencies

### Tools（via Bash）
- No direct tool calls (review does not require deterministic tools)

### MCP Servers
- `mcp__llm-review__chat` — Review LLM initial review (Step 2)
- `mcp__llm-review__chat-reply` — Review LLM multi-round dialogue (Step 3)

### Claude Code Native
- `Read` — read artifact and wiki pages
- `Glob` — find wiki page corresponding to artifact

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — reviewer independence principle (required reading)

### Called by
- `/ideate` Phase 4 (review top ideas)
- `/refine` each iteration round (review current version)
- `/exp-design --review` (review experiment plan)
