---
description: Run the optional Hiera-style iterative candidate search for an existing AutoSci experiment while keeping wiki knowledge and the default experiment workflow unchanged
argument-hint: <experiment-slug> [--run-id <id>] [--init|--propose|--admit|--approve|--run|--recover|--tune|--loop|--status|--finalize]
---

# /hiera-experiment

## Purpose and activation boundary

Use this skill only after the user explicitly selects the optional Hiera path for an existing AutoSci experiment. Hiera is an isolated search sidecar:

- It reads the linked wiki experiment/design and runtime contract as inputs.
- It stores all Hiera state below runs/hiera/<experiment>/<run-id>/.
- It searches immutable candidate snapshots and records evidence in the sidecar ledger.
- It never creates wiki entities, changes wiki schema or experiment status, rewrites wiki/log.md, or writes search results back to the wiki.
- It does not replace /exp-design, /exp-run, /exp-eval, or /research. A confirmatory result must return to the normal, user-gated workflow.

Before creating or changing a run, read:

1. README.md for the user-facing sequence and command examples.
2. references/interface.md for contract fields, source layouts, and remote receipts.
3. The relevant runtime contract files when a field or permission is unclear.

Never infer a method, metric direction, resource boundary, seed policy, or remote environment from a vague request. Ask for the missing decision or ask the user to provide a text constraint.

## State model and command ownership

Treat the lifecycle as a state machine, not as one automatic command:

~~~text
init
  -> inspect/complete semantic_space and task_contract
  -> propose semantic points
  -> author drafts and candidate specs
  -> admit immutable candidates
  -> explicit human source/contract review
  -> approve frozen contract
  -> preflight
  -> run(screen)
  -> choose one iteration branch:
       propose a new semantic direction
       tune reviewed config_schema children
       loop existing candidates at deep depth
       status/recover pending remote attempts
  -> finalize sidecar report
  -> optional formal confirmation through /exp-run and /exp-eval
~~~

The CLI subcommand and the agent action are different:

| Stage | CLI command | Agent-owned action |
|---|---|---|
| Initialize | init | Create the sidecar and show readiness errors. |
| Complete inputs | none | Edit only user-confirmed semantic or contract inputs; validate them. |
| Propose | propose | Show point IDs and metadata; do not create source. |
| Author | none | Write reviewed source/spec under this run's drafts; do not call propose again. |
| Admit | admit | Import exactly the reviewed draft into an immutable snapshot. |
| Approve | approve | Run only after explicit human approval of the execution boundary. |
| Preflight | preflight | Check a candidate without reserving evaluation budget. |
| Evaluate | run | Execute one immutable snapshot at screen or deep depth. |
| Tune | tune | Create and evaluate bounded immutable config children. |
| Loop | loop | Schedule deep bouts among existing eligible candidates only. |
| Observe/recover | status / recover | Poll or reconcile an existing remote attempt; never resubmit it. |
| Finalize | finalize | Write the exploratory sidecar report only. |

The --propose skill flag can appear in both the semantic-point and authoring stages. In the authoring stage, follow-up text overrides the default stage intent: do not invoke the Python propose subcommand; write the selected point's draft instead.

## User interaction protocol

The skill flag selects a stage. Follow-up text supplies information that a flag cannot encode:

- point, candidate, parent, and attempt IDs;
- round, limit, depth, metric, direction, seed, or resource constraints;
- local/remote selection and the intended server/environment;
- exact paths and files that may be written;
- display-only or no-execution boundaries;
- the fact that the user has reviewed and approved a contract;
- recovery of a specific existing remote attempt.

Use this rule:

- A default read-only action may proceed with only the skill flag.
- If a parameter is missing, ask instead of guessing.
- Before writing drafts, admitting, approving, deploying, running, tuning, recovering, or finalizing, state the exact scope and stop if the user must decide.
- Follow-up text narrows the operation; it is not approval by itself. approve still requires explicit human confirmation.

After every command or agent-owned file action, report:

1. What was read or changed.
2. The resulting state, IDs, score, receipt, or readiness error.
3. Any remaining gate or missing input.
4. One exact next command when the next step is safe and unblocked.

Do not silently chain across admit, approve, preflight, deployment, execution, result acceptance, or formal confirmation.

## Stage rules

### 1. Initialize

Run:

~~~text
python -m tools.hiera.cli --project . init <experiment-slug> --run-id <run-id> [--contract FILE] [--space FILE]
~~~

Use --contract only for a reviewed JSON object that should be merged into the generated task contract. Use --space only for a reviewed semantic-space JSON file. These inputs override or complete defaults; they do not approve execution.

Initialization:

- reads the linked wiki/design as read-only;
- creates manifest.json, semantic_space.json, task_contract.yaml, drafts/, candidates/, attempts/, and preflight/;
- records the source snapshot used to bind the run;
- reports readiness_errors instead of inventing missing fields.

Stop after init when the semantic space still contains only the conservative baseline, when relations are missing, or when the contract is not ready. Ask the user to confirm mechanism hypotheses, relations, metric/direction, command, resources, and environment. Do not propose or author source in the same turn unless the user explicitly requests that next stage.

### 2. Complete semantic space or contract inputs

There is no dedicated Python subcommand. The agent may edit only the file explicitly named by the user, usually:

- runs/hiera/<slug>/<run-id>/semantic_space.json; or
- a user-provided contract override file before rerunning init.

For a semantic-space edit, preserve the schema, dimension/hypothesis ownership, and requires, activates, and excludes relations. Validate point closure and do not add an unconfirmed method. For a contract edit, preserve generated source/state fields and do not fabricate credentials or server settings.

After editing, show the changed JSON/YAML and stop for confirmation. This step is planning only; it does not propose, write candidate source, admit, approve, preflight, deploy, or run.

### 3. Propose semantic points

Run:

~~~text
python -m tools.hiera.cli --project . propose <slug> --run-id <run-id> --round N --limit K
~~~

The operation is deterministic:

- no admitted candidates: fresh;
- existing scored candidates and a non-crossover round: improve;
- round index divisible by the crossover schedule (round % 3 == 2) with at least two scored candidates: crossover.

The command writes a proposal decision to ledger.jsonl and prints point IDs, semantic points, changes, parents as available, and coverage. It does not write source or candidate snapshots. Ask the user which point IDs to implement. Do not treat a point ID as an admitted candidate.

### 4. Author a modular draft

This is an agent-owned file-generation stage; there is no Python subcommand. The user may invoke the skill with --propose, but follow-up text must identify the selected point and say that the request is authoring, not point generation.

Write only inside:

~~~text
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>/
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json
~~~

For non-trivial code, prefer a thin run.py and focused modules such as experiment/data.py, experiment/models.py, experiment/training.py, and experiment/evaluation.py. Do not add empty modules solely to match an example.

The draft/spec review must show:

- candidate_id, operation, parents, and exact semantic_point;
- complete source tree and candidate.editable_files whitelist;
- config and any reviewed candidate.config_schema;
- contract entrypoint and argv evaluation command;
- result-file path, score_path, metric, direction, timeout, budget, accelerator, and local/remote environment;
- for remote runs, remote_config, remote Python, GPU policy, work directory source, and conda/env_setup boundary.

Do not write to candidates/, include config.json in the draft source, call admit, or run code during this stage.

### 5. Admit an immutable candidate

Before admission, the user must inspect the full draft and spec. Then run:

~~~text
python -m tools.hiera.cli --project . admit <slug> --run-id <run-id> --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
~~~

Admission enforces that:

- source-dir is inside this run's drafts/ directory;
- source files are UTF-8, non-symlink files and exactly match candidate.editable_files;
- the entrypoint is present and config.json is absent from source;
- candidate_id, semantic point, operation, parents, config, and schema are valid;
- parents name candidates already present in the ledger.

It copies reviewed files into candidates/<candidate-id>/, creates config.json, calculates file/code digests, and appends the candidate record. It does not approve the contract, run preflight, reserve budget, or execute code. Any source/config change requires a new candidate ID and a new admission.

### 6. Approve the frozen execution contract

Approval is a human gate. Before running:

~~~text
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
~~~

The user must have reviewed the admitted source and full contract, including:

- entrypoint, editable/readonly files, config, and config schema;
- evaluation/preflight argv, result file, score path, metric, and direction;
- timeout, maximum evaluations, accelerator, and data assumptions;
- local/remote environment and all remote server/conda fields.

approve validates readiness, computes a digest over immutable contract fields, sets state.approved, and updates the manifest. It does not mean source review was skipped, and it does not deploy or execute. Approval is run-level: a later candidate can be admitted under the same frozen contract. If the contract changes, stop, show the changed fields, obtain a new human review, and run approve again before execution; if the linked wiki/design source snapshot changes, start a new run. Execution must fail closed if the digest no longer matches.

### 7. Preflight

Run once per candidate after approval and before its first evaluation:

~~~text
python -m tools.hiera.cli --project . preflight <slug> --run-id <run-id> --candidate <candidate-id>
~~~

Preflight verifies the frozen contract, manifest source snapshot, candidate file digests, entrypoint, and placeholders. For local execution it runs the reviewed preflight_command when present without reserving budget. For remote execution it performs local structural checks only; the remote preflight command runs during remote submission. A failed preflight blocks the run until the cause is fixed and, if the contract changed, re-approved.

### 8. Run one evaluation

Run:

~~~text
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth screen
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth deep
~~~

Use screen for the first bounded comparison. Use deep only when the user wants deeper evidence. depth is an orchestration label; it does not automatically change seeds, steps, or model settings. Those policies belong in the reviewed candidate config/code.

Every run:

1. verifies the frozen contract and immutable snapshot;
2. reserves one evaluation in ledger.jsonl before launching;
3. executes the reviewed argv with shell=False locally or via the Hiera remote adapter;
4. requires return code zero, a declared JSON result, and a finite value at score_path;
5. writes a receipt, logs, score, and result digest.

A failed, timed-out, malformed, or missing-result attempt remains evidence and consumes its reservation. Do not silently retry it or reinterpret it as success.

### 9. Iterate with one explicit branch

After reviewing receipts and coverage, select one branch.

New semantic direction: return to propose, then author → admit → preflight → screen. Do not mutate an admitted snapshot. The run-level contract remains reusable unless its fields must change.

Parameter tuning:

~~~text
python -m tools.hiera.cli --project . tune <slug> --run-id <run-id> --candidate <candidate-id> --limit K --depth deep
~~~

Use tune only when the approved contract has a non-empty reviewed candidate.config_schema. The tuner validates bounds/types, creates deterministic unseen configurations, copies the parent's immutable source, writes each child config.json, evaluates the child, and records the parent relation. It never mutates the parent and is not a preview-only command. A failed child still consumes budget and remains evidence.

Deep loop:

~~~text
python -m tools.hiera.cli --project . loop <slug> --run-id <run-id> --rounds R --max-bouts B
~~~

loop only selects existing candidates with a finite best score and fewer than B prior tuning bouts. It records scheduler decisions, runs deep evaluations, records bouts, and stops at the round, bout, or budget limit. It does not call propose, generate source, or create config children.

Before selecting a branch, reconcile any terminal deep evaluation recorded without a tuning-bout event. Scheduler and recovery logic use the attempt ID to avoid duplicate deep bouts.

### 10. Observe or recover remote attempts

Use:

~~~text
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
python -m tools.hiera.cli --project . recover <slug> --run-id <run-id> --attempt <attempt-id>
~~~

status is a non-blocking poll for pending remote handles. It may collect terminal receipts and update the ledger, coverage, experience revision, and reconciliation records. It never submits a replacement attempt. On local runs it only reports/reconciles local ledger state; it does not poll a remote host.

Use recover only for an existing remote attempt after a client interruption or explicit inspection. It validates the attempt token, candidate digest, contract digest, worker digest, host, and canonical remote path, then polls and collects the same handle. It never reserves another evaluation or launches a second worker. recover is remote-only.

Treat running as pending. Treat terminal failure as failed evidence. A missing or unknown state requires explicit inspection/recovery and must never be reported as success.

### 11. Finalize the exploratory search

Before finalizing, run status for remote runs and confirm that no attempt is pending. Then run:

~~~text
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
~~~

finalize writes FINAL_REPORT.json with ledger summary, coverage, experience revision, contract digest, source-isolation check, and wiki_writeback: none. It does not wait for remote jobs, verify pending work, select a formal winner, or update wiki pages. If a pending attempt exists, collect or recover it first.

For a confirmatory claim, copy the selected method into the normal experiment path and use the existing user-gated /exp-run and /exp-eval workflow. Do not convert an exploratory Hiera score into a formal result automatically.

## Contract and command invariants

The task contract is JSON-compatible YAML. Generated source/state fields are authoritative and must not be replaced by arbitrary overrides. The executable contract must include:

- candidate.entrypoint and a non-empty relative candidate.editable_files;
- evaluation.kind: command;
- non-empty evaluation.evaluate_command;
- relative evaluation.result_file;
- non-empty evaluation.score_path and metric, plus explicit direction (minimize or maximize);
- positive resources.timeout_seconds and max_evaluations;
- resources.environment equal to local or remote.

Commands are argv lists, never shell strings. Only these placeholders are allowed:

~~~text
{candidate_dir} {run_dir} {attempt_dir} {result_file} {config_file} {entrypoint}
~~~

The evaluator uses shell=False locally. evaluation.prepare_command and evaluation.collect_command must remain empty; snapshot deployment and result collection belong to the adapters. The result file must remain inside the fresh attempt directory, be valid UTF-8 JSON, and contain a finite number at score_path.

## Local and remote execution

For local execution, the evaluator runs the reviewed command with the candidate snapshot as its working directory and writes logs/receipts below the local attempt directory.

For remote execution, the Hiera adapter reads the project-relative resources.remote_config (default config/server.yaml) through tools.remote. It transfers only the admitted candidate file map to a per-attempt remote sidecar, sends the worker, runs the reviewed preflight/evaluation command, and collects bounded logs plus the declared result file. It does not call project-wide sync-code, setup-env, launch, or pull-results; it does not sync the AutoSci source tree or wiki and does not install arbitrary candidate dependencies.

Review these fields before approval:

- remote_config: relative project path, normally config/server.yaml;
- remote_python: one executable path/name, not a shell command;
- remote_poll_seconds: positive polling interval;
- remote_gpu: empty or comma-separated GPU indices;
- server host, user, work_dir, SSH settings, and exactly one reviewed runtime setup: conda.path + conda.env, or env_setup.

The adapter activates the reviewed conda/environment setup on the remote worker. Data and dependencies must already be available there or be explicitly handled by the reviewed candidate command. Credentials stay in server configuration and must not be copied into Hiera artifacts. A server configuration change changes the reviewed execution environment and requires contract review before the next execution.

## Failure, idempotency, and safety

- Keep candidate snapshots immutable. Never edit candidates/<candidate-id>/ in place.
- Use a new candidate ID for changed source/config and a new run ID when the linked wiki/design source snapshot changes.
- Never spend a replacement budget slot for a client interruption; use recover for the same attempt.
- Never accept a remote receipt without matching attempt, candidate, contract, worker, host, and path digests.
- Preserve append-only ledger.jsonl; do not rewrite history to hide failed attempts.
- Keep user-owned raw/{papers,notes,web} read-only.
- Do not modify wiki/graph/ directly or rewrite wiki/log.md.
- Do not push branches or publish remote changes.
- Follow the current repository's change-recording policy. Do not create revise.md inside a Hiera run or add testing/user records to a clean release branch unless explicitly requested.

## Required result after each action

Use concise, concrete reporting:

~~~text
Changed/read: <files or command>
State: <run/candidate/attempt status and IDs>
Gate: <what the user must review, or “none”>
Next: <one exact safe command, or why the workflow must stop>
~~~

If a command fails, preserve its output and identify whether the failure is a contract/readiness error, source-digest mismatch, budget exhaustion, local process failure, remote transport failure, or result-validation failure. Do not retry or change the contract silently.
