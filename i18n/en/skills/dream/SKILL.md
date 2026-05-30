---
description: Run AutoSci's agent-first SciEvolve dream pass: reflect over SciMem and write proposal-first self-evolution artifacts for forgetting, consolidation, and association
argument-hint: "[wiki-root] [--propose-only] [--yolo]"
---

# /dream

Reflect over SciMem with a pluggable memory-evolution policy runtime. `/dream`
is the visible self-evolution loop for reviewers: the system inspects its own
scientific memory, decides what should fade, what should be reorganized, and
what latent associations should be proposed for future work. The autonomy claim
lives in the closed memory loop: SciMem state -> policy judgment -> validated
proposal -> guarded memory mutation -> downstream context rebuild. Claude Code
is the default user-facing policy runtime because AutoSci users already work
there; the same substrate can also be driven by an OpenAI-compatible API call,
a local model, or a supplied JSON response. The Python helper prepares context,
validates evidence, records artifacts, and applies guarded memory updates; it
does not replace the policy judgment.

Use these local references on demand:

- `references/memory-operations.md` — the rubric for forgetting, consolidation, and association proposals
- `references/evidence-and-boundaries.md` — evidence rules, `/check` boundary, and reviewer-facing safety constraints
- `references/agent-response-schema.md` — exact JSON shape expected by the finalizer, plus examples

Open `runtime/schema/scievolve.yaml` for the on-disk signal/proposal contract.
Open `docs/scievolve.md` only when you need reviewer-facing command examples.

## Inputs

- `wiki-root` (optional): default `wiki/`
- `--propose-only` (optional): write validated proposal artifacts but do not
  auto-apply mutations. Without it, the default closed-loop behavior is to
  propose and then auto-apply medium/high-confidence validated proposals.
- `--yolo` (optional): high-confidence proposals may perform irreversible
  page-level mutations. `consolidation` merges the body of related pages into
  the target and archives the sources. `forgetting` archives the target page
  directly. Only `high` confidence proposals are eligible for yolo. This flag
  is explicit opt-in and produces reviewer-visible diffs.
- Existing wiki pages, graph edges, projected frontmatter edges, citations, and
  SciEvolve memory signals.

## Outputs

- Dream run directory: `wiki/outputs/evolution/dream/<run>/`
- Context artifacts: `dream_context.json`, `dream_context.md`
- Prompt artifact: `dream_agent_prompt.md`
- Agent response artifact: `dream_agent_response.json`
- Report artifact: `dream_report.md`
- Optional safe-apply artifacts: `dream_apply_report.json`,
  `dream_apply_report.md`
- Optional shared SciEvolve proposal artifacts under
  `wiki/outputs/evolution/proposals/`

## Wiki Interaction

### Reads

- `wiki/{papers,concepts,topics,people,ideas,experiments,methods,foundations,manuscripts,reviews}/*.md`
- `wiki/graph/edges.jsonl`
- `wiki/graph/citations.jsonl`
- frontmatter-projected links from `runtime/schema/entities.yaml`
- `wiki/outputs/evolution/signals.jsonl`
- optional existing `/check` or lint reports only as supporting context

### Writes

- `wiki/outputs/evolution/dream/<run>/*`
- `wiki/outputs/evolution/proposals/*` only when finalizing with `--propose`
- `wiki/outputs/evolution/proposals.jsonl` only when finalizing with `--propose`
- `wiki/outputs/evolution/applications.jsonl` when safe applications are
  attempted
- entity page frontmatter and an append-only `SciEvolve Memory Evolution Note`
  when safe applications are applied; no body sections are rewritten
- `wiki/graph/context_brief.md` rebuilt after successful safe application so
  downstream skills consume the evolved memory state

Do not rewrite entity page bodies, skills, templates, schemas, graph files,
`index.md`, or `log.md` from `/dream`. The only body change allowed by the safe
apply path is an append-only `SciEvolve Memory Evolution Note`.

## Workflow

**Pre-condition**: work from the AutoSci project root. Resolve `PYTHON_BIN` once:

```bash
if   [ -x .venv/bin/python ];         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then PYTHON_BIN=.venv/Scripts/python.exe
else                                       PYTHON_BIN=python3
fi
export PYTHON_BIN
```

Set the wiki root:

```bash
WIKI_ROOT=wiki
DREAM_PROPOSE_ONLY=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --propose-only) DREAM_PROPOSE_ONLY=true ;;
    --apply-safe) ;;  # legacy alias; safe auto-apply is now the default
    --*) ;;
    *) WIKI_ROOT="$arg" ;;
  esac
done
export WIKI_ROOT DREAM_PROPOSE_ONLY
```

### Step 1: Prepare The Dream Scene

Run:

```bash
"$PYTHON_BIN" tools/research_wiki.py dream "$WIKI_ROOT" --json
```

Read the returned `dream_context.md`, `dream_context.json`, and
`dream_agent_prompt.md`. The context may contain deterministic candidate cues.
**Treat them as observations only; do not copy them mechanically into proposals.**

### Step 2: Perform Agentic Memory Reflection

Use the active policy runtime to act as the `/dream` memory-evolution agent. In
the slash-command path, Claude Code is the policy runtime; in headless demos,
`tools/research_wiki.py dream --use-llm` can call an OpenAI-compatible model;
in tests or local-model runs, `--agent-response` can supply the same strict JSON
contract. These runtimes are interchangeable at the `/dream` boundary: the
reviewer-visible mechanism is the validated memory-evolution loop, not a claim
that AutoSci ships a bespoke agent framework. Read
`references/memory-operations.md` before deciding proposal types. Read
`references/evidence-and-boundaries.md` before accepting any proposal that looks
like lint repair, deletion, or unsupported science.

Make a small, high-signal set of proposals. A good `/dream` run usually has
0-5 proposals, not a sweep of every weak cue.

Ask these questions:

1. Which memories are polluting retrieval or repeating failed traces?
2. Which scattered pages are really one memory neighborhood?
3. Which non-obvious associations would help future research if reviewed?
4. What evidence already exists in the wiki or signal store?
5. How would this proposal improve the next research or retrieval cycle?
6. What should be left alone because the evidence is too thin?

### Step 3: Write The Agent Response

Read `references/agent-response-schema.md`, then write strict JSON to:

```text
wiki/outputs/evolution/dream/<run>/dream_agent_response.json
```

Use the same run directory returned by Step 1. Every proposal must cite known
context evidence: entity ids, candidate ids, signal ids, or edge ids from the
prepared context.

### Step 4: Finalize Through The Shared SciEvolve Store

The default closed-loop behavior is to finalize **and auto-apply** when an
agent response is provided. Run:

```bash
"$PYTHON_BIN" tools/research_wiki.py dream "$WIKI_ROOT" \
  --agent-response wiki/outputs/evolution/dream/<run>/dream_agent_response.json \
  --json
```

The finalizer validates references, writes proposal artifacts, and auto-applies
medium/high-confidence proposals as reversible memory metadata **and visible body
notes**. This is the self-evolution path: it mutates both frontmatter
(`scievolve_*`, `tags`, `related_concepts`, `maturity`, etc.) and page body
(appending a `SciEvolve Memory Evolution Note` section), logs the application
event, rebuilds downstream context, and marks applied proposals as `applied`.

If the user passed `--propose-only` (`DREAM_PROPOSE_ONLY=true`), stop after
writing proposal artifacts and summarize what would be applied:

```bash
"$PYTHON_BIN" tools/research_wiki.py dream "$WIKI_ROOT" \
  --agent-response wiki/outputs/evolution/dream/<run>/dream_agent_response.json \
  --propose-only \
  --json
```

If the finalizer rejects an item, fix the response JSON rather than loosening
the tool.

### Step 5: Report To The User

Report:

- dream run directory
- number of candidate cues read
- proposal count by operation
- safe application count, when safe applications were attempted
- whether `context_brief.md` was rebuilt for downstream skills
- rejected agent items, if any
- proposal artifact paths
- whether any memory metadata or append-only body note was applied

## Constraints

- `/dream` is agent-first. Deterministic scans prepare context; they do not make
  the memory judgment.
- `/dream` is policy-runtime agnostic. Claude Code, an API model, a local model,
  or a supplied response can provide the judgment as long as it satisfies the
  same evidence-grounded JSON contract.
- Show self-evolution, not maintenance. A good proposal changes the future shape
  of memory by fading noise, consolidating fragments, or opening a useful new
  research association.
- Proposal-first by default. No deletion, archival, or edge write.
- Closed-loop auto-apply is the default when an agent response is provided.
  It mutates both `scievolve_*` metadata and standard frontmatter fields
  (`tags`, `related_concepts`, `maturity`, etc.), and appends a visible
  `SciEvolve Memory Evolution Note` to the page body.
- `--yolo` enables page-level mutations: `consolidation` merges related page
  bodies into the target and archives the sources; `forgetting` archives the
  target page. Both require `high` confidence.
- Low-confidence proposals remain review-only and are never auto-applied.
- Do not turn `/dream` into `/check`. Broken links, malformed graph rows,
  missing required fields, and xref asymmetry remain `/check` concerns.
- Do not fabricate scientific associations. Low confidence is acceptable only
  when evidence is cited and the proposal is clearly marked for review.
- Preserve provenance. Every proposal should make it easy for a reviewer to see
  why the agent made the memory-organization judgment.

## Reflection & Signal Recording

After the dream run completes, reflect on whether the run revealed systemic memory issues worth recording. Record at most 1 signal if warranted.

```bash
python3 tools/scievolve_record.py \\
  --wiki-root wiki \\
  --source task \\
  --dimension memory \\
  --target /dream \\
  --kind {review|warning|success} \\
  --summary "<concise summary>" \\
  --severity {info|low|medium|high|critical} \\
  --confidence {low|medium|high}
```

Record a signal when:
- High agent-proposal rejection rate (>2x accepted) → `kind=review`, summary rejection ratio
- All proposals skipped safe apply despite validated evidence → `kind=warning`
- The user corrected a dream proposal before or during apply → `source=user, kind=correction`
- Run completed smoothly with meaningful mutations applied → `kind=success` (use sparingly)

If nothing notable happened, skip signal recording.

