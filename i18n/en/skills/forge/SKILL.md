---
description: Run AutoSci's agent-first SciEvolve forge pass: reflect over workflow signals and write proposal-first skill patch artifacts
description-zh: 运行 AutoSci 的 agent-first SciEvolve forge 流程：反思工作流信号并撰写 proposal-first 的技能补丁工件
argument-hint: "[wiki-root] [--target-skill <name>] [--auto-apply]"
---

# /forge

Reflect over SciEvolve workflow signals with a pluggable policy runtime. `/forge`
is the visible self-evolution loop for the **workflow** dimension: the system
inspects feedback about skill execution, decides which skills need patches, and
proposes concrete, evidence-backed updates to prompts, checks, handoffs, and
recovery protocols.

The default mode is **propose-only**. Workflow changes affect execution semantics,
so automatic application is opt-in via `--auto-apply` and is limited to
additive/append-only changes (frontmatter metadata + append-only notes). Destructive
rewrites of prompts or workflow steps always require human review.

Use these local references on demand:

- `references/workflow-operations.md` — the rubric for patch-prompt, add-check,
  adjust-handoff, and add-recovery operations
- `references/evidence-and-boundaries.md` — evidence rules and safety constraints
- `references/agent-response-schema.md` — exact JSON shape expected by the finalizer

Open `runtime/schema/scievolve.yaml` for the on-disk signal/proposal contract.

## Inputs

- `wiki-root` (optional): default `wiki/`
- `--target-skill` (optional): focus on a specific skill; default is all skills
  that have `dimension=workflow` signals
- `--auto-apply` (optional): apply additive safe mutations (append-only notes +
  frontmatter metadata). Without it, the default is propose-only.
- `--agent-response` (optional): path to strict JSON returned by the /forge agent
- `--use-llm` (optional): call an OpenAI-compatible LLM for the agent reflection

## Outputs

- Forge run directory: `wiki/outputs/evolution/forge/<run>/`
- Context artifacts: `forge_context.json`, `forge_context.md`
- Prompt artifact: `forge_agent_prompt.md`
- Agent response artifact: `forge_agent_response.json`
- Report artifact: `forge_report.md`
- Optional safe-apply artifacts: `forge_apply_report.json`, `forge_apply_report.md`
- Shared SciEvolve proposal artifacts under `wiki/outputs/evolution/proposals/`

## Wiki Interaction

### Reads

- `wiki/outputs/evolution/signals.jsonl` — `dimension=workflow` signals
- `i18n/en/skills/<target>/SKILL.md` and `.claude/skills/<target>/SKILL.md` —
  skill content for targeted skills
- `wiki/log.md` — skill invocation frequency (signal density hint)

### Writes

- `wiki/outputs/evolution/forge/<run>/*`
- `wiki/outputs/evolution/proposals/*` when finalizing
- `wiki/outputs/evolution/proposals.jsonl` when finalizing
- `wiki/outputs/evolution/applications.jsonl` when safe applications are attempted
- Skill file frontmatter (`scievolve_forge_notes`, `scievolve_last_forge`) and
  append-only `## SciEvolve Workflow Evolution Note` section when `--auto-apply`
  is used. No prompt text or workflow steps are rewritten.

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
FORGE_TARGET=""
FORGE_AUTO_APPLY=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --target-skill=*) FORGE_TARGET="${arg#*=}" ;;
    --target-skill)   FORGE_TARGET="${arg}" ;;
    --auto-apply)     FORGE_AUTO_APPLY=true ;;
    --*) ;;
    *) WIKI_ROOT="$arg" ;;
  esac
done
export WIKI_ROOT FORGE_TARGET FORGE_AUTO_APPLY
```

### Step 1: Prepare The Forge Scene

Run:

```bash
"$PYTHON_BIN" tools/research_wiki.py forge "$WIKI_ROOT" \
  ${FORGE_TARGET:+--target-skill "$FORGE_TARGET"} \
  --json
```

Read the returned `forge_context.md`, `forge_context.json`, and
`forge_agent_prompt.md`. The context contains workflow signals grouped by target
skill, plus skill content previews. **Treat signals as evidence, not decisions.**

### Step 2: Perform Agentic Workflow Reflection

Use the active policy runtime to act as the `/forge` workflow-evolution agent. In
the slash-command path, Claude Code is the policy runtime; in headless demos,
`tools/research_wiki.py forge --use-llm` can call an OpenAI-compatible model.

Ask these questions:

1. Which skills have the highest signal density? Are the signals correlated?
2. What concrete patch would address the root cause, not the symptom?
3. Is the patch additive (append check, add recovery) or destructive (rewrite prompt)?
4. Does the patch change the skill's core purpose? If yes, reject it.
5. What evidence supports each proposal? Cite signal ids and skill line hints.
6. What should be left alone because the evidence is too thin?

Prefer additive changes. A good `/forge` run usually has 0–3 proposals.

### Step 3: Write The Agent Response

Read `references/agent-response-schema.md`, then write strict JSON to:

```text
wiki/outputs/evolution/forge/<run>/forge_agent_response.json
```

Use the same run directory returned by Step 1. Every proposal must cite known
evidence: signal ids and skill file paths from the prepared context.

### Step 4: Finalize Through The Shared SciEvolve Store

The default behavior is **propose-only**. Run:

```bash
"$PYTHON_BIN" tools/research_wiki.py forge "$WIKI_ROOT" \
  ${FORGE_TARGET:+--target-skill "$FORGE_TARGET"} \
  --agent-response wiki/outputs/evolution/forge/<run>/forge_agent_response.json \
  --json
```

The finalizer validates references and writes proposal artifacts. Status remains
`proposed`; no skill files are mutated.

If the user passed `--auto-apply` (`FORGE_AUTO_APPLY=true`), additive safe
mutations are applied:

```bash
"$PYTHON_BIN" tools/research_wiki.py forge "$WIKI_ROOT" \
  ${FORGE_TARGET:+--target-skill "$FORGE_TARGET"} \
  --agent-response wiki/outputs/evolution/forge/<run>/forge_agent_response.json \
  --auto-apply \
  --json
```

Safe auto-apply writes:
- `scievolve_forge_notes` frontmatter (append-only list)
- `scievolve_last_forge` frontmatter (timestamp)
- Append-only `## SciEvolve Workflow Evolution Note` section in the skill body

It does **not** rewrite prompts, workflow steps, handoffs, or recovery protocols.

If the finalizer rejects an item, fix the response JSON rather than loosening
the tool.

### Step 5: Report To The User

Report:

- forge run directory
- number of workflow signals loaded
- signal density per targeted skill
- proposal count by operation
- safe application count, when `--auto-apply` was used
- rejected agent items, if any
- proposal artifact paths
- whether any skill frontmatter or append-only note was applied

## Constraints

- `/forge` is agent-first. Deterministic scans prepare context; they do not make
the workflow judgment.
- `/forge` is policy-runtime agnostic. Claude Code, an API model, a local model,
or a supplied response can provide the judgment as long as it satisfies the same
evidence-grounded JSON contract.
- Show self-evolution, not maintenance. A good proposal changes the future shape
of workflow execution by fixing a real failure mode or coordination gap.
- Proposal-first by default. Destructive changes to prompts or steps are
propose-only; additive changes may be auto-applied with `--auto-apply`.
- Do not turn `/forge` into `/check`. Structural issues (broken links, malformed
markdown) remain `/check` concerns.
- Do not change a skill's core purpose. `/forge` improves robustness and clarity;
it does not re-scope the skill.
- Preserve provenance. Every proposal should make it easy for a reviewer to see
why the agent made the workflow-organization judgment.
- Safe auto-apply is additive only. Frontmatter metadata and append-only notes
are allowed; prompt rewrites are not.

## Reflection & Signal Recording

After the forge run completes, reflect on whether the run revealed systemic
workflow issues worth recording. Record at most 1 signal if warranted.

```bash
python3 tools/scievolve_record.py \
  --wiki-root wiki \
  --source task \
  --dimension workflow \
  --target /forge \
  --kind {review|warning|success} \
  --summary "<concise summary>" \
  --severity {info|low|medium|high|critical} \
  --confidence {low|medium|high}
```

Record a signal when:
- High agent-proposal rejection rate (>2x accepted) → `kind=review`
- A skill accumulates >5 workflow signals without a forge run → `kind=warning`
- Run completed with meaningful proposals → `kind=success` (use sparingly)

If nothing notable happened, skip signal recording.
