# Hiera experiment workflow guide

This guide describes the optional Hiera search path for an experiment that already exists in AutoSci. Hiera is a sidecar: it keeps all search state under `runs/hiera/`, reads the wiki and normal experiment design as inputs, and leaves the wiki schema, wiki pages, `$exp-design`, `$exp-run`, `$exp-eval`, and `$research` unchanged.

## Before starting

- Work from the AutoSci project root.
- The experiment slug must already have an experiment/design record that the run can read.
- Decide whether the approved contract is `local` or `remote`. For remote execution, review `config/server.yaml` and the conda/environment fields before approval.
- Replace `<slug>`, `<run-id>`, `<candidate-id>`, `<point-id>`, and `<attempt-id>` in the examples.
- The skill flag selects a workflow stage. Follow-up text supplies context that a flag cannot encode: IDs and parent relations, round/limit/depth, local/remote boundaries, file paths, display-only restrictions, or an explicit approval/recovery decision. It is optional for a default read-only action, but required whenever the agent would otherwise have to guess a parameter or could create files, approve, deploy, run, or recover an attempt. Follow-up text narrows the action; it never replaces the human approval gate.

## Run layout

```text
runs/hiera/<slug>/<run-id>/
├── manifest.json              # read-only links to wiki/design inputs
├── semantic_space.json        # mechanism hypotheses and explored relations
├── task_contract.yaml         # execution, resource, command, metric boundary; frozen after approve
├── ledger.jsonl               # append-only candidates, attempts, results
├── drafts/<candidate-id>/     # source awaiting review/admission
├── candidates/<candidate-id>/ # immutable admitted source + config.json
├── attempts/<attempt-id>/     # receipts, logs, remote handles, results
└── FINAL_REPORT.json          # sidecar summary from finalize
```

A non-trivial draft normally uses a thin `run.py` and focused modules such as `experiment/data.py`, `models.py`, `training.py`, and `evaluation.py`. The candidate spec sits beside the draft source and names the semantic point, config, entrypoint, editable files, evaluation command, metric, and direction.

## Command map

| Stage | Why it is triggered | User skill command | Agent Python command | Gate |
|---|---|---|---|---|
| Initialize | Start a new isolated Hiera run | `$hiera-experiment <slug> --run-id <id> --init` | `python -m tools.hiera.cli --project . init <slug> --run-id <id> [--contract FILE]` | Stop for semantic-space review |
| Complete inputs | The conservative defaults do not express the confirmed mechanism/metric/remote boundary | Continue the init conversation with a text instruction | No dedicated subcommand; agent edits and validates `semantic_space.json` / `task_contract.yaml` | User confirms assumptions |
| Propose | Generate deterministic semantic points for a round | `$hiera-experiment <slug> --run-id <id> --propose` | `... propose <slug> --run-id <id> --round N --limit K` | Review points |
| Author draft | Turn selected points into reviewable source and a spec | `$hiera-experiment <slug> --run-id <id> --propose` plus an authoring instruction | No dedicated subcommand; agent writes under `drafts/` | Review complete source/spec |
| Admit | Snapshot a reviewed draft immutably | `$hiera-experiment <slug> --run-id <id> --admit` | `... admit ... --spec SPEC --source-dir SOURCE` | Candidate exists, still unapproved |
| Approve | Freeze the execution contract digest | `$hiera-experiment <slug> --run-id <id> --approve` | `... approve <slug> --run-id <id>` | Explicit human approval |
| Preflight | Check a candidate before spending an evaluation | `$hiera-experiment <slug> --run-id <id> --preflight` | `... preflight ... --candidate C` | Must pass before run |
| Screen | First bounded comparison of a candidate | `$hiera-experiment <slug> --run-id <id> --run` | `... run ... --candidate C --depth screen` | Consumes one reservation |
| Iterate | Explore new mechanisms, parameter children, or deep bouts | `--propose`, `--tune`, or `--loop` as described below | `propose`, `tune`, or `loop` | Existing approval/budget rules remain |
| Observe/recover | A remote attempt is pending or the client disconnected | `--status` or `--recover` | `status` or `recover --attempt A` | Never resubmit automatically |
| Finalize | No pending work remains and a sidecar report is wanted | `$hiera-experiment <slug> --run-id <id> --finalize` | `... finalize <slug> --run-id <id>` | Exploratory report only |

The `...` in the table means the common prefix `python -m tools.hiera.cli --project .`.

## The ordered workflow

### 1. Initialize the isolated run

**When to use.** Use this once for a new `<run-id>`, before proposing or writing candidate source.

**Purpose.** `init` creates the sidecar directory, links the run to the existing wiki/design as read-only inputs, and materializes the initial semantic space and task contract. It establishes a Hiera boundary without changing wiki state or running code.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --init
```

**Text to add, and why.** Add text when the default contract is insufficient or you need a strict no-side-effect boundary. The text tells the agent which confirmed resources, metric, command, environment, and files to use; the CLI flag alone cannot carry those details.
```text
Use contract-overrides.json and config/server.yaml for a remote CPU run.
Initialize only. Show manifest.json, semantic_space.json, and
task_contract.yaml; do not propose, generate source, admit, approve,
deploy, or run.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . init <slug> --run-id <run-id> --contract contract-overrides.json
```
Omit `--contract` when the generated contract is sufficient.

**Output and stop.** The run contains `manifest.json`, `semantic_space.json`, and `task_contract.yaml`. The agent stops if mechanism hypotheses, relations, metric direction, or execution fields are still missing.

### 2. Complete the semantic space and contract

**When to use.** Use this only when initialization leaves a confirmed design decision that cannot be represented by the conservative defaults.

**Purpose.** This transfers the already-approved experiment design into machine-readable hypotheses and relations. It prevents Hiera from inventing a method, score direction, seed policy, or remote boundary.

**User skill/text instruction.** There is no separate Python command or skill flag. Give an explicit instruction such as:
```text
Update only runs/hiera/<slug>/<run-id>/semantic_space.json with the
confirmed A and B mechanism hypotheses, their relations, and the metric
direction. Do not generate candidates, write drafts, admit, approve,
preflight, deploy, or run.
```
The “only” clause is essential: editing semantic space is a planning action, not permission to continue the lifecycle.

**Agent action.** The agent edits and validates the JSON/YAML files; there is no fixed CLI subcommand for this step.

**Output and stop.** Review the resulting hypotheses and relations. Continue to `propose` only after they match the design.

### 3. Propose semantic points

**When to use.** Use after the semantic space is confirmed, or when a later iteration needs a new mechanism direction.

**Purpose.** `propose` deterministically creates semantic points, not executable code. Depending on the current round and ledger, the graph selects fresh points, local improvements, or crossover points and records coverage/parent information.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --propose
```

**Text to add, and why.** Add round, limit, and display-only constraints because they are not encoded in the skill flag. This prevents an accidental large proposal set or an unintended transition to source generation.
```text
Generate round 0 with at most 4 semantic proposals. Show each point's
operation, parents, changes, and coverage. Do not author source, admit,
approve, preflight, deploy, or run.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . propose <slug> --run-id <run-id> --round 0 --limit 4
```

**Output and stop.** The output is a set of point IDs and metadata. Select the points to implement; do not treat them as admitted candidates.

### 4. Author a modular draft and candidate spec

**When to use.** Use after the user selects one or more point IDs. This stage is also reached when a later proposal needs a new implementation.

**Purpose.** The agent converts a semantic point into reviewable source and metadata while keeping unreviewed code out of `candidates/`. This is the only stage that generates experiment code.

**User skill command.** The skill entry is still `--propose`, but the follow-up text must switch the agent from point generation to authoring:
```text
For point <point-id> (parents: <parent-ids>), generate a modular candidate
and spec. Write source only to
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>/ using the reviewed
layout. Show the complete source, config, command, metric, direction, and
remote CPU contract. Do not call the propose CLI again, write candidates/,
admit, approve, preflight, deploy, or run.
```
The explicit “do not call propose CLI again” removes the ambiguity of reusing the same skill flag.

**Agent action.** There is no dedicated Python subcommand. The agent writes the draft tree and spec, then validates the editable-file whitelist and command placeholders.

**Output and stop.** Review every source file, the candidate spec, config, evaluation command, metric/direction, and local/remote boundary. Only then continue to `admit`.

### 5. Admit an immutable candidate

**When to use.** Use only after the draft and spec have passed the source review.

**Purpose.** `admit` copies the exact reviewed UTF-8 source into an immutable snapshot, generates its `config.json`, records digests, and links parents/semantic points in the ledger. It does not approve or execute anything.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --admit
```

**Text to add, and why.** Provide exact paths so the agent cannot admit the wrong draft, and state the no-execution boundary because admission itself is not approval.
```text
Admit only
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json
from
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.
Do not approve, preflight, deploy, or run.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . admit <slug> --run-id <run-id> --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
```

**Output and stop.** Inspect `candidates/<candidate-id>/`, its generated `config.json`, and the ledger record. Any code/config change requires a new candidate ID. Continue to the approval gate.

### 6. Approve the execution contract

**When to use.** Use after all admitted candidate files and the contract have been reviewed. This is a human gate.

**Purpose.** `approve` freezes the `task_contract` digest used by every later preflight, run, tune, loop, status, and finalize operation. It is a contract approval, not a substitute for reviewing the source, and it does not itself deploy or run.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --approve
```

**Required text confirmation, and why.** The agent must receive an explicit statement that the user reviewed the executable boundary. This records intent for a consequential action that the flag alone cannot prove.
```text
I reviewed the admitted source, entrypoint, config, evaluation command,
metric, direction, resource limits, data assumptions, and local/remote
environment. I explicitly approve this frozen Hiera execution contract.
Run approve only; do not preflight or run.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
```

**Output and stop.** A frozen contract digest is recorded. For remote runs, verify `resources.remote_config`, `remote_python`, `remote_gpu`, host/work directory, and conda/`env_setup` before proceeding.

### 7. Preflight without spending an evaluation

**When to use.** Use once per admitted candidate after approval and before its first `screen` run.

**Purpose.** `preflight` checks the frozen contract, source digest, entrypoint, placeholders, and adapter boundary. It reserves no budget and runs no full experiment.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --preflight
```

**Text to add, and why.** Identify the candidate and repeat the no-execution boundary; the flag does not identify a candidate.
```text
Preflight candidate <candidate-id> only. Check the frozen contract,
source digest, entrypoint, placeholders, and local/remote boundary.
Do not reserve an evaluation or run the experiment.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . preflight <slug> --run-id <run-id> --candidate <candidate-id>
```

**Output and stop.** Fix a failed contract/source check before scheduling a run. A passed preflight unlocks `screen`.

### 8. Run a bounded screen evaluation

**When to use.** Use for the first comparison of each admitted candidate. Choose `remote` only when the approved contract says remote.

**Purpose.** `screen` reserves one evaluation, executes the immutable snapshot, validates the declared JSON score, and records a receipt. It is the evidence used to select candidates for deeper work.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --run
```

**Text to add, and why.** State candidate, depth, adapter, and collection boundary. These details determine where code runs and what may be transferred.
```text
Run candidate <candidate-id> at depth screen with the approved <local|remote>
contract. Deploy only the immutable candidate snapshot, collect the declared
JSON result and bounded logs, and do not modify wiki or sync AutoSci source.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth screen
```

**Output and stop.** Read the attempt receipt, score, failure state, and ledger. Failed attempts remain evidence and consume their reservation; they are not silently retried. Choose another candidate, return to `propose`, or continue to deep iteration.

### 9. Choose the iteration branch

Use exactly one branch after reviewing screen evidence.

#### 9a. New mechanism: return to propose

Use the stage 3 command and text when the current semantic directions are inadequate. A new point must go through author → admit → approve → preflight → screen again.

#### 9b. Parameter children: tune

**Trigger.** Use only when the approved candidate has a non-empty reviewed `candidate.config_schema`.

**Purpose.** `tune` creates immutable child candidates within that schema, skips configurations already tried, evaluates each child at the requested depth, and records the parent relation. It never mutates the parent.

**User skill command and text.**
```text
$hiera-experiment <slug> --run-id <run-id> --tune
Use <candidate-id> as the parent. Generate at most 3 unseen configurations
inside its reviewed config_schema, show the child configs and parent
relation, then run deep evaluation. Do not mutate the parent or change the
contract.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . tune <slug> --run-id <run-id> --candidate <candidate-id> --limit 3 --depth deep
```
The tune command validates the frozen contract and performs the bounded child evaluations; it is not a preview-only command.

#### 9c. Existing candidates: loop deep bouts

**Trigger.** Use when admitted, approved candidates are eligible for more deep evidence and no new source is needed.

**Purpose.** `loop` schedules deep bouts among existing candidates, records anchor/challenger and tuning decisions, and stops at the requested rounds, bout limit, or contract budget. It does not propose, generate source, or tune.

**User skill command and text.**
```text
$hiera-experiment <slug> --run-id <run-id> --loop
Run at most 2 deep bouts with at most 1 bout per candidate. Use existing
admitted candidates only. Do not propose, generate source, or tune.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . loop <slug> --run-id <run-id> --rounds 2 --max-bouts 1
```

#### 9d. Pending or interrupted remote work: status/recover

**Trigger.** Use `status` only when a remote attempt is pending or may have completed; use `recover` only when the client disconnected and you have the existing attempt ID.

**Purpose.** `status` polls and collects terminal receipts without submitting replacement work. `recover` resumes the same remote handle and reconciles its receipt without reserving or launching a second attempt.

**User skill commands and text.**
```text
$hiera-experiment <slug> --run-id <run-id> --status
Poll pending remote attempts once and collect terminal receipts. Never
resubmit a worker or reserve a replacement attempt.
```
```text
$hiera-experiment <slug> --run-id <run-id> --recover
Recover existing remote attempt <attempt-id>. Do not reserve a new budget
slot or resubmit the worker.
```

**Agent Python commands.**
```powershell
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
python -m tools.hiera.cli --project . recover <slug> --run-id <run-id> --attempt <attempt-id>
```

**Output and stop.** Status/recovery may update ledger and receipts, but do not interpret a missing/unknown attempt as success. After terminal receipts, return to an iteration branch or finalize.

### 10. Finalize the exploratory search

**When to use.** Use when no pending attempts remain and the sidecar search report is ready.

**Purpose.** `finalize` summarizes candidates, evaluation coverage, best recorded score, experience revision, and isolation state. It does not write wiki pages or turn exploratory evidence into a formal claim.

**User skill command.**
```text
$hiera-experiment <slug> --run-id <run-id> --finalize
```

**Text to add, and why.** Confirm collection and prohibit an accidental wiki writeback or scientific declaration.
```text
All remote attempts are collected or explicitly recovered. Write only
FINAL_REPORT.json in the Hiera sidecar. Do not write results to wiki or
declare a formal claim.
```

**Agent Python command.**
```powershell
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
```

**Next path.** For a confirmatory claim, move the selected method into the normal experiment path and use the existing user-gated `$exp-run` and `$exp-eval` workflow.

## Local and remote execution

Set `resources.environment` to `local` or `remote` in the approved contract. For remote runs, the Hiera adapter reads the reviewed project-relative `config/server.yaml`, uploads only the immutable candidate snapshot into a per-attempt sidecar directory, activates the reviewed `conda.path` + `conda.env` or `env_setup`, runs the reviewed preflight/evaluation argv, and collects bounded logs plus the declared JSON result. It keeps `remote.json` so `status` and `recover` can continue the same attempt.

The adapter does not run the project-wide `sync-code`, `setup-env`, `launch`, or `pull-results` workflow; it does not sync AutoSci source/wiki or install arbitrary candidate dependencies. Required data and dependencies must already be available in the reviewed environment or be handled by the reviewed candidate command.

Evaluation commands are argv lists, for example:
```json
["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]
```
Only `{candidate_dir}`, `{run_dir}`, `{attempt_dir}`, `{result_file}`, `{config_file}`, and `{entrypoint}` are allowed. The result file must be JSON and `score_path` must resolve to a finite number.

## Human gates and safe stopping points

The agent must stop for user input when the semantic space needs a mechanism hypothesis/relation, source/spec review is incomplete, the contract or remote environment has not been approved, or a result needs a confirmatory decision. After every stage it should report the changed files/state and give one exact next command when safe and unblocked. It must never silently advance through `approve`, deployment, execution, recovery, or result acceptance.

Hiera never creates wiki entities, changes wiki schema/status, rewrites `wiki/log.md`, or writes search results back to the wiki. Its ledger and reports are sidecar evidence; the normal AutoSci workflow remains available for confirmation.
