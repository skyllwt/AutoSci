---
description: Multi-phase research idea generation pipeline: landscape scan → dual-model brainstorm → first-pass filter → deep validation → write to wiki
argument-hint: "[research-direction-or-topic] [--max-ideas N] [--skip-validation] [--auto]"
---

# /ideate

> Generates high-quality research ideas through a 5-phase pipeline, grounded in the wiki knowledge base and external search.
> Phase 1 scans the research landscape (wiki + WebSearch + S2), Phase 2 runs a dual-model brainstorm (Claude + Review LLM independently),
> Phase 3 applies a first-pass filter (feasibility + quick novelty check), Phase 4 performs deep validation (calls /novelty + /review),
> Phase 5 writes to the wiki (ideas/ + graph edges), including eliminated ideas (failure reasons recorded as anti-repetition memory).

## Inputs

- `direction` (optional): research direction, keywords, or specific problem description. If omitted, automatically selects the most valuable direction from open_questions.md.
- `--max-ideas N` (optional, default 3): maximum number of ideas to write to the wiki
- `--skip-validation`: skip Phase 4 deep validation (fast mode: Phase 1–3 + Phase 5 only)
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
     - status=failed ideas → **banlist**. Capture `failure_reason` AND the `scope` object (bio-C3 minimal pilot merged 2026-05-12): `scope.species` (list), `scope.disease_area` (list), `scope.data_regime` (high_data / low_data / mixed). When `scope` is absent or empty, treat as "universal" — overlaps with any candidate (legacy behaviour).
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
   - Strategies:
     - Cross-domain combination (method from Topic A + problem from Topic B)
     - Fill gaps in the gap_map and topic/concept open-problem sections
     - Refute or replace assumptions surfaced under `### Methodological gaps`
     - Known limitations of SOTA → improvement directions
   - Each idea includes: title, hypothesis (1–2 sentences), approach sketch (3–5 sentences), `origin_gaps` (concept / topic slugs the idea targets), estimated feasibility (high/medium/low)

2. **Review LLM independently generates 4–6 ideas** (run in parallel):
   ```
   mcp__llm-review__chat:
     system: "You are a creative ML researcher brainstorming research ideas.
              Generate novel, concrete, and feasible ideas based on the given context.
              For each idea, provide: title, hypothesis (1-2 sentences),
              approach sketch (3-5 sentences), and feasibility assessment."
     message: |
       ## Research Landscape
       {landscape report from Phase 1 — gaps, SOTA, trends}

       ## Knowledge Gaps
       {gap_map entries}

       ## Banlist (DO NOT revisit these — but only when scopes overlap)
       {failed ideas with failure_reason AND scope (species / disease_area / data_regime). A failed idea with empty scope blocks everywhere; a failed idea with `scope.species: [human]` only blocks candidates targeting human (or species-agnostic candidates). Spell out the scope per failed idea so Review LLM can route around it.}

       ## Active Ideas (avoid duplicating)
       {proposed/in_progress ideas}

       Generate 4-6 novel research ideas that address the gaps above.
       Focus on ideas that are: (1) genuinely novel, (2) feasible within 3-6 months,
       (3) directly address a knowledge gap.
   ```

3. **Merge and deduplicate**:
   - Combine Claude's and Review LLM's ideas (10–16 candidates)
   - Remove highly similar ideas (merge ideas with the same core method, keep the more specific version)
   - Remove ideas that overlap with the banlist
   - Remove ideas that heavily duplicate the active list
   - Output: 8–12 candidate ideas

### Phase 3: First-Pass Filter

Goal: quickly eliminate ideas that are clearly infeasible or insufficiently novel.

Apply the following checks to each candidate idea:

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
   - Eliminate if: highly correlated with a failure_reason in the banlist **AND** the failed idea's `scope` overlaps the candidate's scope (bio-C3 minimal pilot). Overlap rule: scopes overlap when ANY of (a) failed idea has empty/missing scope (universal block — legacy behaviour); (b) intersection of `scope.species` is non-empty OR either side has empty species; (c) intersection of `scope.disease_area` is non-empty OR either side has empty disease_area; (d) `data_regime` values match OR either side is empty. If scopes do NOT overlap (e.g. failed idea was "phospho prediction in human cancer cell lines, high_data" and candidate is "phospho prediction in plant proteomes, low_data"), do NOT eliminate — record the banlist as a "scope-distinct prior" in the IDEA_REPORT instead.
   - Retain if: feasibility >= medium AND not eliminated
   - Output: 4–6 surviving ideas (ranked)
   - **Infer candidate scope**: for the elimination check, infer the candidate's scope from its hypothesis + tags + origin_gaps. Use this same inferred scope when writing the idea to wiki in Phase 5 if the candidate becomes status: proposed.

### Phase 4: Deep Validation

(Skip if `--skip-validation` is set; proceed directly to Phase 5.)

Apply deep validation to the top 3 ideas from Phase 3:

1. **Call /novelty `--write`** (one at a time):
   ```
   For each top idea:
   Skill: novelty
   Args: "<idea-slug>" --write
   ```
   The `--write` flag persists the resulting `novelty_score` (1–5) into the idea's frontmatter. Record the score for the IDEA_REPORT.

2. **Call /review** (for top 2 ideas):
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

4. **If `--auto` is not set**: display ranked results in terminal, wait for user confirmation or adjustment

### Phase 5: Write to Wiki

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
   novelty_score: ""         # 1-5 — written by /novelty --write in Phase 4; leave empty otherwise
   priority: 3               # 1-5 — see Priority computation below
   pilot_result: ""          # empty until /exp-eval fills it
   failure_reason: ""        # empty for proposed ideas
   linked_experiments: []    # empty until /exp-design creates experiments
   date_proposed: YYYY-MM-DD
   date_resolved: ""         # empty until validated/failed
   # bio-C3 (pilot merged 2026-05-12): optional scope object. Empty/absent scope means
   # "universal" — the idea (and, if it fails, its banlist entry) applies everywhere.
   # Populate from Phase 3's inferred candidate scope. Empty sub-fields stay empty.
   scope:
     species: []              # ["human"] | ["mouse", "human"] | ["plant"] | … (empty = universal)
     disease_area: []         # ["cancer"] | ["neurodegenerative"] | … (empty = disease-agnostic)
     data_regime: ""          # high_data | low_data | mixed (empty = data-regime-agnostic)
   ---
   ```

   **Priority computation** (maps Phase 4 signals into the 1-5 scale):
   - If `--skip-validation`: default `priority = 3`
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
   (empty — filled by /exp-eval after running the experiment)

   ## Lessons learned
   (empty — filled by /exp-eval after the idea reaches a terminal status)
   ```

2. **Write eliminated ideas** (status: failed):
   For ideas eliminated in Phase 3/4, also create `wiki/ideas/{slug}.md` using the **same template above**, with these overrides:
   - `status: failed`
   - `priority: 1` (eliminated ideas never block higher-priority work)
   - `date_resolved: YYYY-MM-DD` (today)
   - `failure_reason: "[filter] <specific elimination reason>"` — the `[filter]` prefix distinguishes ideate-stage eliminations from post-experiment failures (which /exp-eval tags differently). Examples: `"[filter] highly similar published work exists: <paper-title>"`, `"[filter] insufficient feasibility: GPU requirements too high"`
   - **`scope` is mandatory on failed ideas** (bio-C3 minimal pilot): populate the sub-fields explicitly even if empty — empty species/disease_area/data_regime means "universal block, applies everywhere", and future `/ideate` runs need that to be a deliberate choice rather than a missing-field accident. When the elimination cited a specific saturated subspace (e.g. "saturated by SAPP / PhosAF / GraphPhos … on phospho prediction"), set `scope.species: [human, mouse]`, `scope.data_regime: high_data` — so a future idea targeting plant phospho or cross-species low-data transfer is NOT blocked.
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
   - Phase 3: {Y} survived initial filter (from {X})
   - Phase 4: Deep validation on top {Z}
   - Phase 5: {K} ideas written to wiki

   ## Top Ideas (ranked)

   | Rank | Idea | Novelty | Review | Gap Align | Status |
   |------|------|---------|--------|-----------|--------|
   | 1 | [[slug]] | 4/5 | 7/10 | +2 | proposed |
   | 2 | [[slug]] | 3/5 | 6/10 | +0 | proposed |

   ## Filtered Out
   | Idea | Reason | Status |
   |------|--------|--------|
   | [[slug]] | Similar published work exists | failed |
   | [[slug]] | GPU requirements too high | failed |

   ## Suggested Next Steps
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

## Constraints

- **Auto-switch to cold-start mode when wiki is cold**: expand external search (WebSearch 8 queries, S2/DeepXiv limit 30), do not block execution
- **Every idea must have wiki grounding**: each idea must reference at least 2 wiki pages (paper / concept / method / topic)
- **Banlist must be loaded**: Phase 1 must read failed ideas' failure_reason; Phase 2/3 must check for overlap
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
- **/novelty fails**: if novelty fails for a single idea in Phase 4, mark "novelty unverified" and continue
- **/review fails**: if review fails in Phase 4, mark "unreviewed" and continue; recommend user manually runs /review
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
- `/novelty` — Phase 4 deep novelty validation
- `/review` — Phase 4 cross-model review

### MCP Servers
- `mcp__llm-review__chat` — Phase 2 Review LLM independent brainstorm

### Claude Code Native
- `WebSearch` — Phase 1 external search, Phase 3 quick novelty screening
- `Agent` tool — Phase 1 parallel search, Phase 2 parallel brainstorm

### Shared References
- `.claude/skills/shared-references/cross-model-review.md` — Phase 2 Review LLM independence principle
