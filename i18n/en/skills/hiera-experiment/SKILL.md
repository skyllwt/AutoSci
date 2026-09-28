---
name: hiera-experiment
description: Run the optional Hiera-style iterative candidate search for an existing AutoSci experiment while keeping wiki knowledge and the default experiment workflow unchanged
argument-hint: <experiment-slug> [--run-id <id>] [--init|--propose|--admit|--approve|--run|--recover|--tune|--loop|--status|--finalize]
---

# $hiera-experiment

Use this skill only when the user explicitly chooses the optional Hiera search path for an existing planned experiment. It is a sidecar workflow: all state is under `runs/hiera/<experiment>/<run-id>/`; it does not add wiki entities, change the wiki schema, transition wiki experiment status, or replace `$exp-design`, `$exp-run`, `$exp-eval`, or `$research`.

For exact JSON fields and the run directory contract, read [references/interface.md](references/interface.md) before creating a run.

The search has real repeated iterations:

1. **Initialize and inspect.** Read the linked wiki experiment, idea, and design as read-only inputs. Run `python -m tools.hiera.cli init <slug> --run-id <id>`. Review `semantic_space.json` and `task_contract.yaml`. The generated semantic space contains only a conservative baseline until the user supplies mechanism hypotheses and relations. Do not invent methods, score direction, or commands.
2. **Author candidates.** Run `propose --round N` to obtain deterministic fresh, improve, or crossover points. Organize non-trivial candidates as a small source tree: keep `run.py` as a thin entrypoint, put data loading in `experiment/data.py`, model variants in `experiment/models/`, training in `experiment/training.py`, and metric/result handling in `experiment/evaluation.py`; add only modules the experiment needs. Write the candidate metadata spec separately, place the reviewed source tree under this run's `drafts/<candidate-id>/`, and run `admit --spec ... --source-dir runs/hiera/<experiment>/<run-id>/drafts/<candidate-id>`. The older inline `files` map remains supported for small candidates. Candidate IDs, parent IDs, semantic points, code digests, and configs are recorded in the ledger. A candidate is a new snapshot when its code or config changes.
3. **Approval gate.** Present the candidate files, contract, command, resource limit, metric, direction, and evaluation boundary to the user. Only after explicit approval run `approve`; this freezes the task contract digest. Never execute an unapproved or changed contract.
4. **Screen and iterate.** Run `preflight --candidate ID`, then `run --candidate ID --depth screen`. Inspect the receipt and ledger. Repeat proposal → admission → preflight → screen; use the same candidate for multiple `loop` deep-tuning bouts only when it remains eligible. The scheduler records anchor/challenger decisions and stops at budget or bout limits. Failed evaluations remain evidence and count toward the budget; they are not silently retried without a new scheduled attempt.
   When the reviewed contract has a non-empty `candidate.config_schema`, use `tune --candidate ID --limit N --depth deep` to create immutable parameter variants. The tuner validates bounds, skips tried configurations, evaluates each variant, and records each variant as a child candidate. A new tuning round can select the best child as the next parent.
   `resources.environment` selects the approved execution adapter. `local` keeps the existing local behavior. `remote` uses the Hiera-specific remote adapter described in [references/interface.md](references/interface.md): it deploys only the immutable candidate snapshot to one per-attempt sidecar directory, runs preflight and evaluation there, and collects bounded logs plus the declared JSON result. It does not invoke the project-wide remote experiment workflow.
   `status` performs a non-blocking remote poll for each pending attempt and collects terminal receipts, so it is the Hiera-sidecar equivalent of the check/collect part of `$exp-status`. If a remote client disconnects after reserving an attempt, use `recover --attempt ID` for that same run. Recovery verifies the frozen contract and candidate snapshot, then polls and collects the existing handle without resubmitting or reserving another attempt; it also repairs the deep tuning ledger record so a resumed loop cannot spend a duplicate bout.
5. **Finalize carefully.** `status` and `finalize` produce sidecar JSON reports only. The best search result is exploratory evidence. To make a confirmatory claim, copy the selected method into the normal experiment code path and invoke the existing user-gated `$exp-run` and `$exp-eval` workflow. Do not write search results into wiki pages automatically.

## Contract rules

- Use argv lists, never shell strings. `{candidate_dir}`, `{run_dir}`, `{attempt_dir}`, `{result_file}`, `{config_file}`, and `{entrypoint}` are the only command placeholders.
- `result_file` must be created inside the fresh attempt directory and contain JSON. `score_path` must resolve to a finite number. Set `direction` explicitly to `minimize` or `maximize`.
- `resources.max_evaluations` counts reservations made before execution, so crashes cannot spend untracked budget. Logs and receipts remain in the attempt directory.
- `evaluation.prepare_command` and `evaluation.collect_command` must remain empty for both adapters; non-empty values are rejected. The local adapter executes the reviewed argv directly. The remote adapter owns snapshot deployment and result collection.
- Keep candidate source modular and explicit. `candidate.editable_files` is the reviewed file whitelist; nested relative paths are supported. Prefer a thin entrypoint and focused modules over one large `run.py` or duplicated source strings. `admit --source-dir` imports exactly that UTF-8 source tree from the current run's `drafts/` directory; generated `config.json` is supplied from the candidate `config` object and is never authored in the source tree.
- Before approving a remote contract, also review `resources.remote_config`, `remote_python`, `remote_gpu`, the selected server configuration, and any `conda` or `env_setup` it supplies. The adapter automatically activates that reviewed environment for the worker and candidate command. It does not run project-wide `sync-code`/`setup-env`, install candidate dependencies, or transfer datasets; those dependencies and data must already be available in the reviewed remote environment or be handled explicitly by the reviewed candidate command. `env_setup` is trusted shell setup from the reviewed server configuration; it is not candidate-authored contract text.
- Every local or remote execution reserves its attempt in the append-only ledger before launch. A remote attempt has a durable local handle and remote execution receipt. After a client interruption, recover that same attempt; do not allocate a replacement attempt or launch a second worker. `missing` or `unknown` state requires inspection, and a failed remote execution must never be accepted as a successful completion.
- The proposal output reports coverage priorities, and status/finalize report the derived experience revision.

## Safety boundaries

Read-only inputs include `wiki/`, `raw/`, and runtime contracts. Never modify `wiki/graph/` directly, rewrite `wiki/log.md`, or add Hiera candidates as wiki entities. Never push a remote branch. Keep `revise.md` append-only after every implementation batch.
