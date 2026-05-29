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
