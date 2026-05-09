---
description: Scan the full wiki to detect health issues and produce a tiered fix-recommendation report (covers all entity types in runtime/schema/entities.yaml + graph consistency)
---

# /check

> Scans the full wiki to detect structural, link, field, and graph health issues, and generates a tiered fix-recommendation report.
> Covers every entity type declared in `runtime/schema/entities.yaml` (papers, concepts, topics, people, ideas, experiments, methods, Summary, foundations), plus graph edge / citation consistency. Highlights include: idea novelty-score plausibility, idea failure-reason completeness, experiment `linked_idea` validity.

## Inputs

- Full wiki directory (default `wiki/`)
- Optional: `--json` flag (output JSON format via `tools/lint.py`)
- Optional: `--fix` flag (auto-fix deterministic issues)
- Optional: `--fix --dry-run` (preview fixes without applying them)
- Optional: `--suggest` flag (show recommendations for issues that cannot be auto-fixed)

## Outputs

- Lint report (reported directly to the user)
- Optional file write: `wiki/outputs/lint-report-{date}.md`

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — paper page fields and links
- `wiki/concepts/*.md` — concept page fields and links
- `wiki/topics/*.md` — topic page fields and links
- `wiki/people/*.md` — people page fields and links
- `wiki/ideas/*.md` — idea status, novelty_score, failure_reason, origin_gaps, target_venue
- `wiki/experiments/*.md` — experiment status, linked_idea, outcome
- `wiki/methods/*.md` — method type, source_papers, parent/child chains
- `wiki/Summary/*.md` — survey page fields
- `wiki/foundations/*.md` — foundations (terminal — incoming-link checks only)
- `wiki/graph/edges.jsonl` — semantic graph edge consistency check
- `wiki/graph/citations.jsonl` — bibliographic citation consistency check
- `wiki/index.md` — cross-check page completeness

### Writes
- Does not directly modify wiki content (reports only, unless `--fix` is set)
- `wiki/log.md` — records lint result summary via `tools/research_wiki.py log`

## Workflow

**Pre-conditions**: confirm the working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).
Set `WIKI_ROOT=wiki/`.

### Step 1: Run the Automated Lint Tool

**Default mode (report only)**:
```bash
python3 tools/lint.py --wiki-dir wiki/ --json
```

**Auto-fix mode** (when user specifies `--fix`):
```bash
python3 tools/lint.py --wiki-dir wiki/ --fix --json
```
Auto-fixes deterministic issues (xref reverse-link completion, missing fields filled with default values) and outputs a fix report.

**Preview mode** (when user specifies `--fix --dry-run`):
```bash
python3 tools/lint.py --wiki-dir wiki/ --fix --dry-run --json
```
Previews what would be fixed without applying any changes.

Parse the JSON output to obtain all automatically detected issues (and fix results).

### Step 2: Structural Completeness (automated coverage)

The automated tool checks:

1. **Broken wikilinks**: `[[slug]]` target file does not exist
2. **Orphan pages**: pages with no incoming links
3. **Missing required fields** (per entity declared in `runtime/schema/entities.yaml`). Authoritative source: `runtime.loader.REQUIRED_FIELDS`. Current set:
   - papers: title, slug, tags, importance
   - concepts: title, tags, maturity, key_papers
   - topics: title, tags
   - people: name
   - methods: name, slug, type, tags
   - Summary: title, scope, key_topics
   - ideas: title, slug, status, origin, tags, priority
   - experiments: title, slug, status, linked_idea, hypothesis, tags
   - foundations: title, slug, domain, status

### Step 3: Field Value Validation (automated coverage)

1. **Enum value checks** (sourced from `runtime.loader.VALID_VALUES`):
   - papers.importance ∈ {1,2,3,4,5}
   - concepts.maturity ∈ {stable, active, emerging, deprecated}
   - ideas.status ∈ {proposed, in_progress, tested, validated, failed}
   - ideas.priority ∈ {1,2,3,4,5}
   - experiments.status ∈ {planned, running, completed, abandoned}
   - experiments.outcome ∈ {succeeded, failed, inconclusive}
   - methods.type ∈ {architecture, training, inference, evaluation, data, benchmark, system, optimization, prompting, protocol, other}
   - foundations.status ∈ {mainstream, historical}
2. **Idea novelty_score** (when present) ∈ [1, 5] (integer)
3. **Idea failure_reason**: must be non-empty when status=failed (anti-repetition memory)
4. **Experiment linked_idea**: the referenced idea page must exist

### Step 4: Cross Reference Symmetry (automated coverage)

Check all bidirectional link rules defined in `runtime/schema/xref.yaml`:

| Forward link | Reverse link checked |
|--------------|---------------------|
| `papers ## Related → concepts` | `concepts.key_papers` contains paper slug |
| `papers wikilink → people` | `people ## Recent work` contains paper slug |
| `topics.key_people → people` | `people ## Research areas` contains topic slug |
| `concepts.key_papers → papers` | `papers ## Related` contains concept slug |
| `ideas.origin_gaps → concepts` | `concepts.linked_ideas` contains idea slug |
| `ideas.origin_gaps → topics` | `topics.linked_ideas` contains idea slug |
| `experiments.linked_idea → ideas` | `ideas.linked_experiments` contains experiment slug |
| `methods.source_papers → papers` | `papers ## Related` contains method slug |
| `methods.parent_methods ↔ methods.child_methods` | reciprocity |

### Step 5: Graph Edge Consistency (automated coverage)

1. **JSON format validity**: every line is valid JSON
2. **Required fields**: each edge has from, to, type
3. **Edge type validity**: semantic edges use the current endpoint-aware type sets; legacy paper-paper / paper-concept types produce migration warnings
4. **Edge confidence**: `/ingest` paper-paper and paper-concept semantic edges use `confidence: high|medium|low`
5. **Citation layer**: `graph/citations.jsonl` rows use `type: cites`, valid source/date, paper endpoints, and no confidence field
6. **Dangling nodes**: wiki pages referenced by from/to must exist

### Step 6: Content Quality (LLM-assisted)

Items detectable by the automated tool:
1. Papers with importance=5 have no concept page referencing them
2. Concepts with maturity=stable have only 1 key_paper
3. Topics have empty `## Open problems` sections (also flag empty `### Known gaps` / `### Methodological gaps` subsections)

Additional LLM judgments (require reading content):
1. **Concept near-duplicate detection**: scan all concept page titles + aliases and assess whether any pairs are semantically identical or highly similar (e.g. "attention mechanism" and "self-attention"). Output merge recommendations for suspected duplicates.
2. **Method near-duplicate detection**: same exercise across `wiki/methods/*.md`, comparing `name` + `tags` + `## Mechanism` summaries.
3. Contradictory statement detection (inconsistent descriptions of the same fact across different pages)
4. SOTA records not updated in over 6 months
5. People `## Recent work` not updated in over 6 months
6. Idea novelty_score inconsistent with the strength of its `## Novelty argument` (low score + bold argument, or high score + thin argument)
7. High-priority idea stuck in proposed status for a long time without `linked_experiments`

### Step 7: Generate Report

Output sorted by priority:

```
## Lint Report — YYYY-MM-DD

**Summary**: N 🔴, M 🟡, K 🔵

### 🔴 Fix Immediately
1. [file] — {issue description}

### 🟡 Recommended Fixes
1. [file] — {issue description}

### 🔵 Optional Improvements
1. [file] — {issue description}
```

Classification:
- **🔴 Fix Immediately**: broken links, missing required fields, invalid enum values, failed idea without failure_reason, invalid JSON in edges, novelty_score out of range
- **🟡 Recommended Fixes**: xref asymmetry, dangling graph edges, broken `linked_idea` references, unknown edge types
- **🔵 Optional Improvements**: orphan pages, quality suggestions, empty sections

Append log:
```bash
python3 tools/research_wiki.py log wiki/ "check | report: N 🔴, M 🟡, K 🔵"
```

## Constraints

- **Report-only by default**: without `--fix`, only reports, no modifications
- **`--fix` only repairs deterministic issues**: xref reverse-link completion, missing fields filled with safe default values. Non-deterministic issues output recommendations (`--suggest`) for user approval
- **raw/ is read-only**: do not modify files under `raw/`
- **graph/ is read-only**: lint does not modify graph files, checks consistency only
- **LLM judgments labeled by source**: automated checks and LLM judgments are clearly distinguished in the report
- **Idempotent**: running multiple times produces the same result (unless wiki content changes)

## Error Handling

- **wiki/ does not exist**: report error and suggest running `/init`
- **graph files do not exist**: skip the missing graph-file checks, note in report
- **Partial directory missing**: skip checks for missing directories, list missing directories in report

## Dependencies

### Tools（via Bash）
- `python3 tools/lint.py --wiki-dir wiki/ [--json] [--fix] [--dry-run] [--suggest]` — automated structural check + fix (core dependency)
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `python3 tools/research_wiki.py stats wiki/` — get statistics (optional, for the report)
