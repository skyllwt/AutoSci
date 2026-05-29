# SciEvolve Store

This directory is managed by `tools/research_wiki.py scievolve-*` commands.

- `signals.jsonl` records user/task/open-environment signals.
- `proposals.jsonl` indexes proposal artifacts.
- `proposals/` stores proposal Markdown/JSON pairs.
- `reports/` stores dry-run evolution reports.

Stage-specific skills extend this same substrate:

- `/dream` uses `dimension: memory`.
- `/forge` uses `dimension: workflow`.
- `/morph` uses `dimension: orchestration`.

The default mode is proposal-first. Recording signals and generating reports
does not mutate wiki entity pages, skills, templates, or DAGs.
