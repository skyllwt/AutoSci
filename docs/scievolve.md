# SciEvolve

SciEvolve is AutoSci's proposal-first evolution layer. It records feedback
signals from user, task, and open environments, groups them by evolution target,
and writes inspectable proposals before any core file is changed.

This Stage 0 spine does not claim fully autonomous evolution. It creates the
shared substrate that `/dream`, `/forge`, and `/morph` extend:

- `/dream` maps to `dimension: memory` and maintains SciMem organization.
- `/forge` maps to `dimension: workflow` and revises SciFlow skill protocols.
- `/morph` maps to `dimension: orchestration` and revises SciDAG templates.

## Storage

The store is under `wiki/outputs/evolution/`:

- `signals.jsonl` records feedback signals.
- `proposals.jsonl` indexes proposal artifacts.
- `proposals/` stores Markdown/JSON proposal pairs.
- `applications.jsonl` records guarded proposal applications.
- `reports/` stores dry-run evolution reports.

The contract is documented in `runtime/schema/scievolve.yaml`.

## Reviewer Demo

Initialize the store:

```bash
python3 tools/research_wiki.py scievolve-init wiki
```

Record a demo signal, or replace the summary with actual user/task/open
feedback:

```bash
python3 tools/research_wiki.py scievolve-record-signal wiki \
  --source user \
  --dimension memory \
  --target concepts/example \
  --kind other \
  --summary "Manual demo signal to verify the Stage 0 evolution loop." \
  --confidence medium \
  --severity low
```

Generate a dry-run report and proposal:

```bash
python3 tools/research_wiki.py scievolve-report wiki --dimension memory --propose
```

The report and proposal connect signal source, target dimension, evidence,
proposed action, risk, and status. They do not mutate wiki pages, skills,
runtime schemas, or DAG templates.

## `/dream` Agent Loop

Stage 1 adds an agent-first memory evolution path. The natural interface for
interactive users is the Claude Code slash skill:

```text
/dream wiki
```

For an artifact-only reviewer demo, keep validated proposals review-only:

```text
/dream wiki --propose-only
```

`/dream` separates the memory-evolution substrate from the policy runtime. The
policy runtime may be the Claude Code session, an OpenAI-compatible API model
via `--use-llm`, a local model, or any external agent that writes the same
strict JSON response. The deterministic command is the substrate: it prepares
compact memory context, writes a checkpoint prompt, validates the policy
runtime's JSON response, records accepted forgetting/consolidation/association
proposals through the shared SciEvolve store, and can optionally apply
medium/high-confidence proposals as reversible SciEvolve memory metadata.

The reviewer-facing autonomy claim is therefore not that AutoSci ships a
bespoke agent framework. It is that the same closed loop works across policy
runtimes: SciMem state -> policy judgment -> evidence validation -> proposal
store -> guarded memory mutation -> rebuilt downstream context.

For debugging or demos, prepare the same dream context directly:

```bash
python3 tools/research_wiki.py dream wiki --json
```

After the slash skill writes `dream_agent_response.json`, finalize directly and
apply safe medium/high-confidence memory updates:

```bash
python3 tools/research_wiki.py dream wiki \
  --agent-response path/to/dream_agent_response.json \
  --json
```

To finalize without applying mutations:

```bash
python3 tools/research_wiki.py dream wiki \
  --agent-response path/to/dream_agent_response.json \
  --propose-only \
  --json
```

To run the same loop without the Claude Code slash-command policy runtime:

```bash
python3 tools/research_wiki.py dream wiki --use-llm --json
```

Each run writes:

- `wiki/outputs/evolution/dream/<run>/dream_context.json`
- `wiki/outputs/evolution/dream/<run>/dream_context.md`
- `wiki/outputs/evolution/dream/<run>/dream_agent_prompt.md`
- `wiki/outputs/evolution/dream/<run>/dream_agent_response.json` when an agent response exists
- `wiki/outputs/evolution/dream/<run>/dream_report.md`
- `wiki/outputs/evolution/dream/<run>/dream_apply_report.*` when safe
  applications are attempted

The context includes deterministic memory cues, but those cues are not
proposals. The agent must cite context evidence before the tool will write a
proposal artifact.

Safe auto-apply is intentionally narrow. It never rewrites page bodies, graph
edges, skills, schemas, or templates. It only writes reversible frontmatter
metadata such as `scievolve_memory_weight`,
`scievolve_consolidates_with`, `scievolve_associations`,
`scievolve_last_dream`, and `scievolve_dream_notes`, appends an audit-only
`SciEvolve Memory Evolution Note`, records the application in
`applications.jsonl`, marks the proposal `applied`, and rebuilds
`wiki/graph/context_brief.md` so `/ideate`, `/research`, `/ask`, and other
context-consuming skills can see the evolved memory state.

## Signal Sources

Signals enter the evolution loop through three paths:

1. **Skill-explicit** (primary): After executing a skill, the LLM policy runtime
   reflects on the execution and calls `tools/scievolve_record.py` if there is
   feedback worth recording. This is the LLM-first path: the executing agent
   decides what, if anything, to record. No fixed automatic hooks.

   ```bash
   python3 tools/scievolve_record.py \
     --wiki-root wiki \
     --source {user|task|open} \
     --dimension {memory|workflow|orchestration} \
     --target <skill-or-entity> \
     --kind <kind> \
     --summary "<one-line summary>"
   ```

2. **Manual CLI**: Humans or CI scripts can record signals directly:

   ```bash
   python3 tools/research_wiki.py scievolve-record-signal wiki \
     --source user --dimension memory --target concepts/example \
     --kind correction --summary "User feedback"
   ```

3. **Cross-skill cascade**: A skill may record signals about another skill's
   behavior (e.g. `/dream` recording a signal about high agent-proposal rejection
   rates, which `/forge` may later consume).

The `source` field distinguishes:
- `user` — human corrections, preferences, or redirections
- `task` — execution outcomes, failures, or unexpected tool behavior
- `open` — external changes such as new papers, venue shifts, or SOTA updates

The `dimension` field routes signals to the correct stage skill:
- `memory` -> `/dream`
- `workflow` -> `/forge`
- `orchestration` -> `/morph`

## `/forge` Agent Loop

Stage 2 adds an agent-first **workflow** evolution path. It consumes
`dimension=workflow` signals and proposes concrete patches to skills and
protocols.

```text
/forge wiki
```

Focus on a specific skill:

```text
/forge wiki --target-skill discover
```

`/forge` follows the same agent-first, proposal-first pattern as `/dream`, but
operates on skills instead of memory entities. The default mode is **propose-only**.
Workflow changes affect execution semantics, so automatic application is opt-in:

```text
/forge wiki --auto-apply
```

When `--auto-apply` is used, safe mutations are limited to:
- `scievolve_forge_notes` frontmatter (append-only list)
- `scievolve_last_forge` frontmatter (timestamp)
- Append-only `## SciEvolve Workflow Evolution Note` section in the skill body

Prompt text, workflow steps, handoffs, and recovery protocols are **never**
auto-applied; they always require human review.

For an artifact-only demo:

```bash
python3 tools/research_wiki.py forge wiki --json
```

After writing `forge_agent_response.json`, finalize:

```bash
python3 tools/research_wiki.py forge wiki \
  --agent-response path/to/forge_agent_response.json \
  --json
```

With safe auto-apply:

```bash
python3 tools/research_wiki.py forge wiki \
  --agent-response path/to/forge_agent_response.json \
  --auto-apply \
  --json
```

Each run writes:

- `wiki/outputs/evolution/forge/<run>/forge_context.json`
- `wiki/outputs/evolution/forge/<run>/forge_context.md`
- `wiki/outputs/evolution/forge/<run>/forge_agent_prompt.md`
- `wiki/outputs/evolution/forge/<run>/forge_agent_response.json` when an agent response exists
- `wiki/outputs/evolution/forge/<run>/forge_report.md`
- `wiki/outputs/evolution/forge/<run>/forge_apply_report.*` when safe applications are attempted
