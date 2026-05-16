---
description: Multi-phase research idea generation pipeline: landscape scan → dual-model brainstorm → filter & validation → write to wiki → pilot
argument-hint: "[research-direction-or-topic] [--max-ideas N] [--skip-validation] [--skip-pilot] [--auto]"
---

# /ideate

> Generates high-quality research ideas through a 5-phase pipeline, grounded in the wiki knowledge base and external search.
> Phase 1 scans the research landscape (wiki + WebSearch + S2), Phase 2 runs a dual-model brainstorm (Claude + Review LLM independently),
> Phase 3 applies first-pass filter + deep validation (feasibility, novelty, review), Phase 4 writes ideas to the wiki (including eliminated ideas, with failure reasons recorded as anti-repetition memory),
> Phase 5 runs pilot experiments on surviving ideas (idea pages already exist) and updates results.

## Inputs

- `direction` (optional): research direction, keywords, or specific problem description. If omitted, automatically selects the most valuable direction from open_questions.md.
- `--max-ideas N` (optional, default 3): maximum number of ideas to write to the wiki
- `--skip-validation`: skip Phase 3 Step 2 deep validation (skip /novelty and /review; fast mode: first-pass filter only)
- `--skip-pilot`: skip Phase 5 pilot experiments (fast mode: Phase 1–4 only)
- `--auto`: fully automatic mode, no pause for user confirmation (used when called by /research)

## Outputs

- `wiki/ideas/{slug}.md` — one page per idea (status: proposed), covering both top ideas and eliminated ideas
- `wiki/graph/edges.jsonl` — new idea → concept/topic relationship edges
- `wiki/graph/context_brief.md` — rebuilt compressed context
- `wiki/graph/open_questions.md` — rebuilt knowledge gap map
- **IDEA_REPORT** (printed to terminal) — pipeline execution summary, ranked results, novelty scores

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps, drives idea direction
- `wiki/ideas/*.md` — existing ideas, especially status=failed ideas and their failure_reason (banlist)
- `wiki/papers/*.md` — existing paper methods and results
- `wiki/concepts/*.md` — technical concepts, find cross-domain combination opportunities
- `wiki/methods/*.md` — reusable methods, scope candidate inspirations
- `wiki/topics/*.md` — research direction maps, SOTA and open problems (including `### Known gaps` and `### Methodological gaps`)
- `wiki/experiments/*.md` — existing experiment results, avoid duplication

### Writes
- `wiki/ideas/{slug}.md` — create new idea pages
- `wiki/graph/edges.jsonl` — add idea → concept/topic relationship edges (addresses_gap, inspired_by)
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log.md` — append operation log

### Graph edges created
- `addresses_gap`: idea → concept/topic (knowledge gap the idea targets — `origin_gaps` field)
- `inspired_by`: idea → paper/method/concept (source of inspiration for the idea)

## Workflow

**Pre-conditions**:
1. Confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).
2. **Check wiki maturity**:
   ```bash
   python3 tools/research_wiki.py maturity wiki/ --json
   ```
   Adjust subsequent behavior based on maturity level:
   - **cold**: expand Phase 1 external search (WebSearch queries from 5 to 8, S2/DeepXiv limit from 20 to 30),
     skip wiki internal context loading (empty, no value), annotate "cold-start mode: heavier external search"
   - **warm**: standard behavior (current default)
   - **hot**: reduce Phase 1 external search (WebSearch queries from 5 to 2, S2/DeepXiv limit from 20 to 10),
     raise Phase 3 gap_alignment_bonus from +2 to +3, prioritize ideas that close gaps already enumerated in topic / concept open-problem sections
3. **Snapshot wiki state** (for the Growth Report at the end):
   Save the JSON returned by maturity to memory variable `maturity_before`

### Phase 1: Landscape Scan

Goal: build a comprehensive view of the target domain, including existing work, knowledge gaps, and recent advances.

1. **Load wiki internal context**:
   - Read `wiki/graph/context_brief.md` (global compressed context)
   - Read `wiki/graph/open_questions.md` (knowledge gap list)
   - Read all `wiki/ideas/*.md`, extract:
     - status=failed ideas → **banlist** (with failure_reason)
     - status=proposed/in_progress ideas → **active list** (avoid duplication)
   - Read `wiki/topics/*.md` and `wiki/concepts/*.md`: collect bullet items under `## Open problems` (including `### Known gaps` and `### Methodological gaps`) → **gap candidates list**
   - If `direction` is specified, filter to the relevant subset

2. **External search** (run in parallel using Agent tool):
   - **WebSearch**: search for recent 6-month papers and advances in the target direction (3–5 queries)
   - **Semantic Scholar**:
     ```bash
     python3 tools/fetch_s2.py search "<direction-keywords>" --limit 20
     ```
     Fetch details for the top 5 highly-cited papers
   - **DeepXiv semantic search**:
     ```bash
     python3 tools/fetch_deepxiv.py search "<direction-keywords>" --mode hybrid --limit 20
     ```
     Fetch TLDR and keywords for top 5 most relevant results:
     ```bash
     python3 tools/fetch_deepxiv.py brief <arxiv_id>
     ```
     Semantic search supplements S2 keyword search for conceptually related papers that keyword search may miss.
   - **DeepXiv trending papers**:
     ```bash
     python3 tools/fetch_deepxiv.py trending --days 14
     ```
     Trending papers indicate community focus areas, useful for discovering trend-driven gaps.
   - **arXiv latest**: `site:arxiv.org <direction> 2025 2026`
   - **If DeepXiv is unavailable**: skip DeepXiv search and trending, rely on S2 + WebSearch only (fallback to original behavior).

3. **Compile landscape report** (internal use, not written to wiki):
   - Current SOTA methods and performance
   - Known open problems / unresolved challenges
   - Recent trends and hot topics
   - Knowledge gaps in the wiki (from gap_map)
   - Prohibited directions (from banlist)

### Phase 2: Dual-Model Brainstorm

Goal: generate ideas independently with Claude and Review LLM, exploiting the diversity that comes from different model perspectives.

**Follow `shared-references/cross-model-review.md`**: Claude and Review LLM generate independently without seeing each other's output.

1. **Claude generates 6–10 ideas**:
   - Input: landscape report + wiki gaps + active list + banlist
   - **Structured generation paths** — each idea must follow one of these four paths:

     | Path | Name | Wiki input to read | Output form |
     |------|------|--------------------|-------------|
     | A | Landscape-driven | `direction` + landscape report from Phase 1 (no dependency on existing methods) | "Design directly from topic/research description" |
     | B | Incremental | `method.limitations` in `wiki/methods/*.md` | "Fix limitation L in method M" |
     | C | Combination | `tradeoff_profile` of two methods under the same topic in `wiki/methods/*.md` | "Combine strengths of M1 + M2" |
     | D | Innovation | Intersection of `assumptions` across N methods under the same topic in `wiki/methods/*.md` | "Break shared assumption P" |
     | E | Cross-domain transfer | `mechanism` similarity of methods across different topics in `wiki/methods/*.md` | "Transfer mechanism M from domain X to Y" |

     For each path, first extract the relevant wiki fields, then generate the idea. Every idea must declare which path (A/B/C/D/E) it comes from.

   - Additional strategies (applied on top of paths A–E):
     - Fill gaps in the gap_map and topic/concept open-problem sections
     - Known limitations of SOTA → improvement directions
   - Each idea includes: title, hypothesis (1–2 sentences), approach sketch (3–5 sentences), `origin_gaps` (concept / topic slugs the idea targets), estimated feasibility (high/medium/low), generation_path (A/B/C/D/E)

2. **Review LLM independently generates 4–6 ideas** (run in parallel):
   ```
   mcp__llm-review__chat:
     system: "You are a creative ML researcher brainstorming research ideas.
              Generate novel, concrete, and feasible ideas based on the given context.
              Each idea MUST follow one of the five structured generation paths below.
              For each idea, provide: title, hypothesis (1-2 sentences),
              approach sketch (3-5 sentences), feasibility assessment,
              and generation_path (A/B/C/D/E)."
     message: |
       ## Structured Generation Paths

       Each idea must follow exactly one of these paths:

       | Path | Name | Wiki input | Output form |
       |------|------|------------|-------------|
       | A | Landscape-driven | direction + landscape report (no dependency on existing methods) | "Design directly from topic/research description" |
       | B | Incremental | method.limitations | "Fix limitation L in method M" |
       | C | Combination | tradeoff_profile of two methods under same topic | "Combine strengths of M1 + M2" |
       | D | Innovation | Intersection of assumptions across N methods under same topic | "Break shared assumption P" |
       | E | Cross-domain transfer | mechanism similarity across different topics | "Transfer mechanism M from domain X to Y" |

       ## Research Landscape
       {landscape report from Phase 1 — gaps, SOTA, trends}

       ## Methods (for paths B–E)
       {wiki/methods/*.md — limitations, tradeoff_profile, assumptions, mechanism fields}

       ## Knowledge Gaps
       {gap_map entries}

       ## Banlist (DO NOT revisit these)
       {failed ideas with failure_reason}

       ## Active Ideas (avoid duplicating)
       {proposed/in_progress ideas}

       Generate 4-6 novel research ideas that address the gaps above.
       Focus on ideas that are: (1) genuinely novel, (2) feasible within 3-6 months,
       (3) directly address a knowledge gap.
       Each idea MUST declare its generation_path (A/B/C/D/E).
   ```

3. **Merge and deduplicate**:
   - Combine Claude's and Review LLM's ideas (10–16 candidates)
   - Remove highly similar ideas (merge ideas with the same core method, keep the more specific version)
   - Remove ideas that overlap with the banlist
   - Remove ideas that heavily duplicate the active list
   - Output: 8–12 candidate ideas

### Phase 3: Filter & Validation

Goal: eliminate infeasible or insufficiently novel ideas, then deeply validate survivors.

**Step 1 — First-pass filter** (apply to all 8–12 candidates):

1. **Feasibility check**:
   - Are GPU/compute requirements within reasonable range? (reference experiment setups already in the wiki)
   - Data availability (public datasets vs. private data)
   - Implementation complexity (achievable within 3–6 months?)
   - Label as feasibility: high/medium/low

2. **Quick novelty screening** (2–3 WebSearch queries per idea):
   - `"<idea-core-method>" + "<task>"` exact-match search
   - `<component-1> + <component-2>` component-combination search
   - If a highly similar published work is found → eliminate or flag

3. **Wiki alignment check**:
   - Does the idea address a known gap in the gap_map? (+score)
   - Does the idea target a concept's `## Open problems` or a topic's methodological gap? (+score)
   - Does the idea build on existing wiki knowledge (papers / methods / concepts)? (+score)

4. **Filter decision**:
   - Eliminate if: feasibility=low AND quick novelty screening found similar published work
   - Eliminate if: highly correlated with a failure_reason in the banlist
   - Retain if: feasibility >= medium AND not eliminated
   - Output: 4–6 surviving ideas

**Step 2 — Deep validation** (apply to surviving ideas; skip if `--skip-validation` is set):

(Skip if `--skip-validation`: proceed directly to Phase 4: Write to Wiki with default priority = 3 for all survivors.)

1. **Call /novelty `--write`** (one at a time):
   ```
   For each surviving idea:
   Skill: novelty
   Args: "<idea-slug>" --write
   ```
   The `--write` flag persists the resulting `novelty_score` (1–5) into the idea's frontmatter. Record the score for the IDEA_REPORT.

2. **Call /review** (for top ideas):
   ```
   Skill: review
   Args: "<idea-full-description>" --difficulty hard --focus method
   ```
   Record review score (1–10) and weaknesses

3. **Composite ranking**:
   - Final score = novelty_score × 2 + review_score + gap_alignment_bonus
   - gap_alignment_bonus: +2 if the idea directly targets a gap_map entry
   - If novelty_score <= 2 → downgrade to "modify needed"
   - If review_score <= 4 → downgrade to "major issues"

4. **Post-validation filter**:
   - Eliminate ideas with novelty_score <= 2 AND review_score <= 4
   - Output: ranked survivors (passed both first-pass and deep validation)

5. **If `--auto` is not set**: display ranked results in terminal, wait for user confirmation or adjustment

### Phase 4: Write to Wiki

Write the validated ideas to the wiki (including eliminated ideas, with their elimination reasons recorded).

1. **Write top ideas** (status: proposed):
   For the top `--max-ideas` ideas:
   ```bash
   # generate slug
   python3 tools/research_wiki.py slug "<idea-title>"
   ```
   Create `wiki/ideas/{slug}.md` **following the schema exactly** — frontmatter mirrors `runtime/schema/entities.yaml::ideas`, body matches `runtime/templates/ideas.md.tmpl`:
   ```yaml
   ---
   title: "<idea title>"
   slug: "<idea-slug>"
   status: proposed
   origin: "ideate: <short description of the driving gap / open problem / paper>"
   origin_gaps: []           # [[concept-slug]] or [[topic-slug]] list — concepts/topics this idea targets
   tags: []                  # 2-5 topic tags (inherit from origin_gaps / direction)
   target_venue: ""          # NeurIPS / ICLR / ICML / ACL / COLM — leave empty if undecided
   novelty_score: ""         # 1-5 — written by /novelty --write in Phase 3 Deep Validation; leave empty otherwise
   priority: 3               # 1-5 — see Priority computation below
   pilot_result: ""          # Leave blank; pilots run in Phase 5, results filled in by /exp-pilot-eval after.
   failure_reason: ""        # empty for proposed ideas
   linked_experiments: []    # empty until /exp-design creates experiments
   date_proposed: YYYY-MM-DD
   date_resolved: ""         # empty until validated/failed
   ---
   ```

   **Priority computation** (maps Phase 3 validation signals into the 1-5 scale):
   - If `--skip-validation`: default `priority = 3` (skip novelty/review scoring)
   - Otherwise start from `novelty_score` (1-5 from /novelty)
   - `+1` if `gap_alignment_bonus > 0` (directly targets a gap_map entry)
   - `-1` if `review_score <= 4` (major issues downgrade)
   - Clamp to `[1, 5]`

   **Body sections** (exactly match `runtime/templates/ideas.md.tmpl` — do not rename):
   ```markdown
   ## Motivation
   Which gap / open problem / paper limitation drives this idea. Reference wiki pages via `[[slug]]`.

   ## Hypothesis
   1-2 sentences stating the testable proposition.

   ## Approach sketch
   3-5 sentences on the proposed method. Reference `[[paper-slug]]`, `[[method-slug]]`, or `[[concept-slug]]` for any component borrowed from existing work.

   ## Novelty argument
   Why this idea is genuinely new — what closest prior work (from /novelty) it differs from, and on which axis. One short paragraph.

   ## Target venue
   The intended publication target (e.g. NeurIPS 2026 / ICLR / ICML / ACL / COLM). May be left blank for ideas still being scoped.

   ## Risks
   Feasibility rating (high/medium/low) + top 2-3 risks. Include the main weaknesses surfaced by /review.

   ## Pilot results
   Leave blank; filled in by /exp-pilot-eval in Phase 5.

   ## Lessons learned
   (empty — filled by /exp-eval after the idea reaches a terminal status)
   ```

2. **Write eliminated ideas** (status: failed):
   For ideas eliminated in Phase 3, also create `wiki/ideas/{slug}.md` using the **same template above**, with these overrides:
   - `status: failed`
   - `priority: 1` (eliminated ideas never block higher-priority work)
   - `date_resolved: YYYY-MM-DD` (today)
   - `failure_reason: "[filter] <specific elimination reason>"` — the `[filter]` prefix distinguishes Phase 3 filter eliminations from post-experiment failures from /exp-eval. Example: `"[filter] highly similar published work exists: <paper-title>"`. Pilot failures (Phase 5) are handled by `/exp-pilot-eval` which writes `[pilot]` failure_reason directly to the existing idea page.
   - Body `## Motivation` and `## Hypothesis` should still be filled (so future banlist matching has content); `## Approach sketch` may be brief; `## Expected outcome` and `## Risks` can note why the idea was eliminated
   - These failed ideas become the banlist for future ideate runs

3. **Add graph edges**:
   ```bash
   # for each idea: addresses_gap edge for every concept/topic in origin_gaps
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{slug}" --to "concepts/{origin-gap-slug}" \
     --type addresses_gap --evidence "Generated by ideate"
   # ...or topics/{origin-gap-slug} when the gap target is a topic.

   python3 tools/research_wiki.py add-edge wiki/ \
     --from "ideas/{slug}" --to "papers/{source-paper}" \
     --type inspired_by --evidence "Inspired by method in {paper-title}"
   ```

4. **Rebuild derived data**:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

5. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "ideate | {N} ideas proposed, {M} ideas filtered out | direction: {direction}"
   ```

6. **Print IDEA_REPORT to terminal**:
   ```markdown
   # Idea Generation Report

   ## Pipeline Summary
   - Direction: {direction}
   - Phase 1: Scanned {N} external papers, {M} wiki gaps identified
   - Phase 2: Generated {X} candidates (Claude: {a}, Review LLM: {b})
   - Phase 3: {Y} survived filter & validation (from {X})
   - Phase 4: {K} ideas written to wiki

   ## Top Ideas (ranked)

   | Rank | Idea | Novelty | Review | Gap Align | Pilot | Status |
   |------|------|---------|--------|-----------|-------|--------|
   | 1 | [[slug]] | 4/5 | 7/10 | +2 | pass | proposed |
   | 2 | [[slug]] | 3/5 | 6/10 | +0 | pass | proposed |

   ## Filtered Out
   | Idea | Reason | Status |
   |------|--------|--------|
   | [[slug]] | Similar published work exists | failed [filter] |
   | [[slug]] | Method diverged in pilot | failed [pilot] |
   | [[slug]] | GPU requirements too high | failed [filter] |

   ## Suggested Next Steps
   - If --skip-pilot is not specified, run the pilot experiment for further screening.
   - Run `/exp-design {top-idea-slug}` to design experiments
   - Run `/novelty` on any idea before investing time

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Papers | {before} | {after} | +{delta} |
   | Methods | {before} | {after} | +{delta} |
   | Ideas | {before} | {after} | +{delta} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {before_level} | {after_level} | {unchanged/upgraded} |
   (Only rows with delta != 0 are shown. Data is computed by comparing `maturity_before` from the pre-condition step against a fresh `maturity --json` call here.)
   ```
7. **If the user enters `--skip-pilot`, the pilot experiment section will be skipped. Otherwise, confirm with the user whether to conduct a pilot experiment and let the user select the surviving ideas that require pilot experiments.**


### Phase 5: Pilot Experiments

(Skip if `--skip-pilot` is set; pipeline ends after Phase 4.)

Objective: Conduct lightweight pre-experiments on **user-selected** surviving ideas to detect obvious failures before launching full-scale experiments.

**Per-idea pilot strategy** (based on `generation_path`):

| Path | Pilot approach |
|------|---------------|
| A (Landscape-driven) | Implement the proposed method directly from the topic/research description. Run on a small benchmark to verify the idea is feasible and produces non-degenerate output. Compare against a simple baseline. |
| B (Incremental) | Start from the original method's paper repo; apply the proposed fix and run a minimal evaluation. Compare against the original method to verify the limitation is addressed. |
| C (Combination) | Implement the combined version of M1 + M2. Run on a small benchmark to check whether the performance/cost tradeoff reaches the expected balance (not dominated by either pure M1 or M2). |
| D (Innovation) | Run existing methods under the new setting (where the shared assumption P is broken). Verify that they indeed fail or degrade, confirming the gap is real. |
| E (Cross-domain transfer) | Implement the transferred mechanism in the target domain. Run a minimal evaluation to check whether the mechanism is compatible and produces non-degenerate output. |

**Pilot Spec — structured output for each idea**:(**Multiple pilot experiments can be executed in parallel** when GPU resources are sufficient.)

Before writing pilot code, generate a structured Pilot Spec block per idea selected by the user and write it to `experiments/pilot/{slug}.yaml`. This spec is the contract that guides pilot code generation (analogous to how `/exp-design` experiment pages guide `/exp-run`). Include the following fields:

```yaml
# Pilot Spec for: {idea-slug}
pilot_spec:
  # --- Core context (from idea Phase 2) ---
  hypothesis: "<testable proposition>"
  approach_sketch: "<proposed method description>"

  # --- What to implement ---
  implementation:
    repo: "<base code repo URL or 'from-scratch'>"
    entry_point: "<main script, e.g. train.py / eval.py>"
    modifications: "<specific code changes to apply on top of the base>"
    files_to_create:
      - "<file1>: <purpose>"
      - "<file2>: <purpose>"

  # --- What to run ---
  setup:
    model: "<model name / architecture>"
    dataset: "<dataset name, split, size>"
    hardware: "<GPU type, count>"
    framework: "<PyTorch / JAX / TF>"
    batch_size: "<reduced batch size, typically 1/4 to 1/8 of paper's>"
    max_steps: "<shortened training steps, 10-30% of full>"
    learning_rate: "<lr>"
    seeds: "<number of seeds, default 1 for pilot>"
    other_hparams: "<key hyperparams only>"

  # --- What to measure ---
  metrics:
    - name: "<metric-1>"
      why: "<what this metric tells us>"
    - name: "<metric-2>"
      why: "<what this metric tells us>"

  # --- What to compare against ---
  baseline:
    method: "<baseline method name>"
    source: "<paper repo or wiki slug>"
    expected_value: "<known performance on this setting, if available>"

  # --- What counts as success ---
  success_criterion:
    pass: "<specific condition, e.g. 'accuracy >= baseline + 1%' or 'loss converges below 0.5 within max_steps'>"
    fail: "<specific condition, e.g. 'diverges (loss > 10x initial) or accuracy < baseline - 5%'>"
    inconclusive: "<everything else>"
```

**How to build the Pilot Spec**:
- **hypothesis / approach_sketch**: copy from the idea generated in Phase 2 (these are the same 1-2 sentence hypothesis and 3-5 sentence approach sketch)
- **repo / base code**: check `wiki/papers/{source-paper}.md` for code links; if the idea combines two methods, pick the primary method's repo as base
- **model / dataset / hardware**: inherit from the source paper's experiment setup in wiki, reduce batch_size and max_steps per pilot requirements below
- **seeds**: default 1 for pilot (single run is sufficient for pass/fail detection)
- **metrics**: choose 1-2 metrics that directly test the hypothesis (not a full metric suite)
- **baseline**: for path A use a simple default baseline; path B use the original method; path C use pure M1 and pure M2; path D use existing SOTA under the new setting; path E use target-domain SOTA
- **success_criterion**: must be quantitative and checkable — avoid vague conditions like "improves performance"

**Pilot requirements** (encoded in the Pilot Spec `setup` and `success_criterion` fields):
- **Reduced batch size**: use the smallest batch size that still produces meaningful gradients (typically 1/4 to 1/8 of the paper's reported batch size)
- **Shortened training**: train to early-mid stage (10–30% of full training steps), not full convergence
- **Goal**: detect obvious degradation or failure, NOT achieve SOTA. The window should be meaningful enough to compare proposed method vs. baseline, but short enough to save time.
- **Comparison**: always include a baseline (the original method for path A, pure M1/M2 for path B, existing methods for path C, target-domain SOTA for path D)
- **Success criterion**: must be quantitative and checkable in the Pilot Spec

**Run pilots via `/exp-pilot-run`**:

User-selected surviving idea, after writing the Pilot Spec to `experiments/pilot/{slug}.yaml`:

```
Skill: exp-pilot-run
Args: "{idea-slug}"
```

`/exp-pilot-run` reads the Pilot Spec, writes pilot code to `experiments/pilot/code/{slug}/`, runs the experiment, and returns a PILOT_REPORT with:
- **Results**: metric values vs baseline (mean ± std)
- **Details**: steps completed, runtime, log path

**Evaluate pilot results via `/exp-pilot-eval`**:

After `/exp-pilot-run` returns the PILOT_REPORT, evaluate results and update the idea page (which already exists from Phase 4):

```
Skill: exp-pilot-eval
Args: "{idea-slug}"
```

`/exp-pilot-eval` reads the pilot results, applies the verdict logic (pass/fail/inconclusive with lenient thresholds — the purpose is to detect obvious failures, not measure final performance), and updates the idea page:
- **Pass**: sets `pilot_result: "pass — ..."`, status unchanged
- **Fail**: sets `failure_reason: "[pilot] ..."`, transitions status to `failed`.Meanwhile set pilot_result: "fail — ..."
- **Inconclusive**: sets `pilot_result: "inconclusive — needs full experiment"`, status unchanged

**If `--auto` is not set**: display pilot results in terminal, wait for user confirmation on borderline cases

**After all pilots complete**: print the final IDEA_REPORT (see Phase 4 Step 6).

## Constraints

- **Auto-switch to cold-start mode when wiki is cold**: expand external search (WebSearch 8 queries, S2/DeepXiv limit 30), do not block execution
- **Every idea must have wiki grounding**: each idea must reference at least 2 wiki pages (paper / concept / method / topic)
- **Banlist must be loaded**: Phase 1 must read failed ideas' failure_reason; Phase 2/3/5 must check for overlap
- **Review LLM independence**: in Phase 2, Review LLM does not see Claude's idea list (cross-model-review.md)
- **Eliminated ideas are also written to wiki**: status=failed + failure_reason, as anti-repetition memory
- **No fabrication**: all ideas must be derived from existing wiki knowledge or external search results; do not invent non-existent papers or methods
- **Slug uniqueness**: check whether the same slug already exists in wiki/ideas/ before creating
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl

## Error Handling

- **Wiki is empty**: proceed with external search (Phase 1 sources B/C/D), but skip wiki internal context; prompt user to build the knowledge base first
- **WebSearch unavailable**: skip external search, generate ideas from wiki internal knowledge only (degraded mode, noted in report)
- **Semantic Scholar API unavailable**: skip S2 search, rely on DeepXiv + WebSearch for compensation
- **DeepXiv API unavailable**: skip DeepXiv search and trending, fall back to S2 + WebSearch (original behavior)
- **Review LLM unavailable**: Phase 2 uses Claude only (no dual-model diversity, noted in report)
- **/novelty fails**: if novelty fails for a single idea in Phase 3, mark "novelty unverified" and continue
- **/review fails**: if review fails in Phase 3, mark "unreviewed" and continue; recommend user manually runs /review
- **Pilot fails for an idea**: mark as failed with `[pilot]` prefix in failure_reason; remaining ideas continue
- **All pilots fail**: idea pages already exist (written in Phase 4); report recommends user review pilot logs and adjust approach
- **Slug conflict**: if the same slug already exists in wiki/ideas/, append a numeric suffix (e.g. `sparse-lora-v2`)
- **All ideas eliminated**: still write to wiki (status: failed); report recommends user broaden the search direction or /ingest more papers

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py maturity wiki/ --json` — check wiki maturity + Growth Report
- `python3 tools/research_wiki.py slug "<title>"` — generate slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild query_pack
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild gap_map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `python3 tools/fetch_s2.py search "<query>" --limit 20` — Semantic Scholar search
- `python3 tools/fetch_deepxiv.py search "<query>" --mode hybrid --limit 20` — DeepXiv semantic search
- `python3 tools/fetch_deepxiv.py brief <arxiv_id>` — fetch paper TLDR
- `python3 tools/fetch_deepxiv.py trending --days 14` — trending paper trends

### Skills（via Skill tool）
- `/novelty` — Phase 3 deep novelty validation
- `/review` — Phase 3 cross-model review
- `/exp-pilot-run` — Phase 5 pilot experiment execution
- `/exp-pilot-eval` — Phase 5 pilot result evaluation and idea page update

### MCP Servers
- `mcp__llm-review__chat` — Phase 2 Review LLM independent brainstorm

### Claude Code Native
- `WebSearch` — Phase 1 external search, Phase 3 quick novelty screening, Phase 5 pilot validation
- `Agent` tool — Phase 1 parallel search, Phase 2 parallel brainstorm

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Phase 2 Review LLM independence principle
