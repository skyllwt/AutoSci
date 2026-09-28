# Hiera experiment workflow guide

This guide is for people who want to run the optional Hiera search path in AutoSci. Hiera is a sidecar search workflow for an existing wiki experiment. It keeps the wiki, the knowledge graph, and the normal `/exp-design` / `/exp-run` / `/exp-eval` workflow unchanged.

## What Hiera does

Hiera explores immutable experiment candidates in repeated rounds. It proposes semantic points, lets the user inspect candidate source, evaluates approved snapshots, tunes bounded configurations, and records the evidence in an append-only ledger. The search result is exploratory evidence. A confirmatory result still goes through the normal experiment workflow and its user gates.

Hiera never writes candidates as wiki entities and never performs wiki writeback. All Hiera state is kept below:

```text
runs/hiera/<experiment-slug>/<run-id>/
├── manifest.json             # links the run to read-only wiki/design inputs
├── semantic_space.json       # hypotheses and relations explored by propose
├── task_contract.yaml        # approved execution and scoring boundary
├── ledger.jsonl              # append-only candidates, attempts, and results
├── drafts/<candidate-id>/    # reviewed source before admission
├── candidates/<candidate-id>/# immutable admitted snapshots
├── attempts/<attempt-id>/   # receipts, logs, and collected results
└── FINAL_REPORT.json         # sidecar search summary from finalize
```

The skill itself is organized as follows:

```text
.claude/skills/hiera-experiment/       # active Claude Code skill
├── SKILL.md                           # agent rules and safety boundaries
├── README.md                          # this user-facing guide
└── references/interface.md            # JSON fields, remote contract, layouts

i18n/en/skills/hiera-experiment/       # English source of the skill
i18n/zh/skills/hiera-experiment/       # Chinese source of the skill
```

## The complete lifecycle

The normal sequence is:

```text
init → inspect and complete semantic space → propose
     → author drafts and candidate specs → admit
     → human review → approve
     → preflight → run(screen)
     → loop/tune/run(deep) repeatedly
     → status or recover when needed → finalize
     → optional formal confirmation through /exp-run and /exp-eval
```

Every command is run from the AutoSci project root. Replace `<slug>`, `<run-id>`, and `<candidate-id>` with the values for the current run.

### 1. Initialize an isolated run
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --init

**Add follow-up text when:** a contract file, semantic-space file, local/remote
choice, or a no-execution boundary is needed. For example:

~~~text
Use contract-overrides.json and config/server.yaml for a remote run.
Only initialize and show manifest.json, semantic_space.json, and
task_contract.yaml. Do not generate candidates, approve, deploy, or run.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . init <slug> --run-id <run-id> --contract contract-overrides.json
~~~

After initialization, the agent must stop and ask for confirmed semantic
hypotheses and relations before editing semantic_space.json. There is no fixed
Python subcommand for that edit; the agent writes and validates the JSON.


```text
python -m tools.hiera.cli --project . init <slug> --run-id <run-id>
```

Use `--contract path/to/contract-overrides.json` when the experiment needs explicit resources, commands, metrics, or a remote environment. `init` reads the linked wiki experiment/design as read-only inputs and creates the sidecar directory. It does not generate candidate source and does not execute an experiment.

Inspect these files before continuing:

```text
runs/hiera/<slug>/<run-id>/semantic_space.json
runs/hiera/<slug>/<run-id>/task_contract.yaml
```

The initial semantic space is conservative. The user must supply mechanism hypotheses and required relations when the baseline is insufficient. Do not invent a method, metric direction, or command on the user's behalf.

Next step after a successful initialization: inspect the two files, add only the confirmed semantic assumptions, then run `propose`.

### 2. Propose semantic points
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --propose

**Add follow-up text when:** you need a non-default round or limit, want to
select particular points, or want display-only behavior:

~~~text
Generate round 0 with at most 4 proposals. Show operation, semantic point,
parents, changes, and coverage only. Do not author source, admit, approve, or run.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . propose <slug> --run-id <run-id> --round 0 --limit 4
~~~

This command creates semantic points only. It does not create candidate source.


```text
python -m tools.hiera.cli --project . propose <slug> \
  --run-id <run-id> --round 1 --limit 4
```

`propose` generates deterministic fresh, improve, or crossover semantic points from the current space and ledger. It does not write source code, admit candidates, approve the contract, or run an experiment. Review the proposed points and choose which ones should become candidates.

Next step: author a source tree and a spec for each selected point, then use `admit`.

### 3. Author a modular draft and candidate spec
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --propose

**Follow-up text is required:** identify the selected proposal point IDs,
parents, source layout, data/seed constraints, and the review boundary:

~~~text
For proposal <point-id>, generate a modular candidate and candidate spec.
Write source only under runs/hiera/<slug>/<run-id>/drafts/<candidate-id>/.
Show complete source, spec, config, parents, semantic point, command, metric,
direction, and result JSON. Do not write candidates/ and do not run.
~~~

**Agent Python command:** none. The agent writes the reviewed draft tree and
spec; the next Python command is admit, only after user inspection.


Put reviewed source only under the current run's `drafts/` directory. A non-trivial candidate normally looks like:

```text
drafts/<candidate-id>/
├── run.py                 # thin CLI entrypoint
└── experiment/
    ├── __init__.py
    ├── data.py            # data loading and split policy
    ├── models.py          # model definitions or variants
    ├── training.py        # optimization/training loop
    └── evaluation.py      # metrics and JSON result serialization
```

The candidate spec is kept beside the source directory, for example `drafts/<candidate-id>.spec.json`. It must identify the candidate, semantic point, config, entrypoint, source files, evaluation command, metric, and direction. The reviewed source tree must contain exactly the UTF-8 files named by `candidate.editable_files`; it must not contain `config.json`.

This stage is code generation and review preparation only. Do not put source into `candidates/` yourself.

Next step: show the full draft, spec, contract boundary, and evaluation command to the user; after review run `admit`.

### 4. Admit an immutable candidate
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --admit

**Follow-up text is required:** give the exact spec and source directory:

~~~text
Admit using
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json
and
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.
Admit only; do not approve, preflight, deploy, or run.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . admit <slug> --run-id <run-id> --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
~~~

Admission creates the immutable snapshot and config.json; it does not execute
the candidate.


```text
python -m tools.hiera.cli --project . admit <slug> \
  --run-id <run-id> \
  --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json \
  --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
```

`admit` validates the spec and copies the exact reviewed source tree into `candidates/<candidate-id>/`, adds the generated `config.json`, and records file digests in `ledger.jsonl`. A changed source or config requires a new candidate ID. Admission still does not approve the contract or execute the candidate.

Next step: inspect the immutable candidate snapshot and present the approval gate.

### 5. Approve the execution contract (human gate)
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --approve

**Follow-up text is required:** approve only after reviewing source, spec,
entrypoint, command, metric, direction, budget, remote environment, and data:

~~~text
I have reviewed the candidate source and execution contract, including the
metric, direction, resource limits, and local/remote boundary. I explicitly
approve the frozen Hiera execution contract. Run approve only; do not preflight
or run.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
~~~

This freezes the contract digest. A changed contract requires another review.


```text
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
```

Run this only after the user explicitly approves the candidate(s), source, entrypoint, config, resource limits, evaluation command, metric, direction, and local/remote boundary. `approve` freezes a contract digest. Later `preflight`, `run`, `tune`, `loop`, `status`, and `finalize` must use that frozen contract. A changed contract must be reviewed and approved again.

For a remote contract, explicitly check `resources.remote_config`, `remote_python`, `remote_gpu`, the host/work directory, and the configured conda environment or `env_setup` before approval.

Next step after approval: run `preflight` for each admitted candidate.

### 6. Preflight without consuming an evaluation
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --preflight

**Follow-up text is required:** provide the candidate ID and the no-execution
boundary:

~~~text
Preflight candidate <candidate-id> only. Check the frozen contract, source
digest, entrypoint, placeholders, and execution boundary. Do not consume an
evaluation or run the full experiment.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . preflight <slug> --run-id <run-id> --candidate <candidate-id>
~~~


```text
python -m tools.hiera.cli --project . preflight <slug> \
  --run-id <run-id> --candidate <candidate-id>
```

Preflight verifies the frozen contract, candidate snapshot, command placeholders, and execution boundary. It does not reserve an evaluation budget or run the experiment. For a remote contract it checks the remote adapter boundary before deployment.

Next step after a passed preflight: run a bounded screen evaluation.

### 7. Screen a candidate
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --run

**Follow-up text is required:** provide candidate ID, depth, environment, and
collection boundary:

~~~text
Run candidate <candidate-id> at depth screen using the approved <local|remote>
contract. Deploy only the immutable candidate snapshot, collect the declared
result and bounded logs, and do not modify wiki or sync AutoSci source.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth screen
~~~

The command reserves budget, executes, validates the declared JSON score, and
writes the receipt.


```text
python -m tools.hiera.cli --project . run <slug> \
  --run-id <run-id> --candidate <candidate-id> --depth screen
```

`screen` reserves one budget slot, executes the immutable snapshot, collects the declared JSON result, and records a receipt. A failed attempt remains evidence and consumes its reservation; it is not silently retried. Inspect the receipt and score before selecting a candidate for deeper work.

Next step: propose/admit another candidate for comparison, or use `loop`/`tune` on an eligible candidate.

### 8. Iterate with deep bouts
**Repeated deep evaluation:**

**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --loop

**Follow-up text is required:**

~~~text
Run at most 2 deep bouts with at most 1 bout per candidate. Use existing
admitted candidates only. Do not propose, generate source, or tune.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . loop <slug> --run-id <run-id> --rounds 2 --max-bouts 1
~~~

**Parameter children with tune:**

~~~text
Use <candidate-id> as the parent. Generate at most 3 unseen configurations
inside the reviewed config_schema, show the child configs and parent relation,
then run deep evaluation. Do not mutate the parent.
~~~

~~~powershell
python -m tools.hiera.cli --project . tune <slug> --run-id <run-id> --candidate <candidate-id> --limit 3 --depth deep
~~~

Use tune only when config_schema was reviewed. loop evaluates existing
candidates; it does not call propose or generate source.


Use a bounded loop for repeated deep evaluation and tuning:

```text
python -m tools.hiera.cli --project . loop <slug> \
  --run-id <run-id> --rounds 2 --max-bouts 1
```

`loop` chooses eligible candidates, runs deep evaluations, and records tuning bouts until the requested round/bout limit or contract budget. It does not bypass approval and does not write to the wiki.

For an explicit bounded parameter search, when `candidate.config_schema` is present:

```text
python -m tools.hiera.cli --project . tune <slug> \
  --run-id <run-id> --candidate <candidate-id> \
  --limit 3 --depth deep
```

`tune` creates immutable child candidates for configurations within the reviewed schema, skips configurations already tried, evaluates each child, and records the parent relation. It never mutates the parent snapshot.

Next step: inspect scores, seed/stability diagnostics, and tuning decisions; if the search needs a new semantic direction, return to `propose` and repeat admission and approval for the new candidate.

### 9. Check or recover remote attempts
**Status user skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --status

**Optional follow-up text:**

~~~text
Poll all pending remote attempts once and collect terminal receipts. Never
resubmit a worker or reserve a replacement attempt.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
~~~

**Recover after a client interruption:**

~~~text
/hiera-experiment <slug> --run-id <run-id> --recover
~~~

Add:

~~~text
Recover the existing remote attempt <attempt-id>. Do not reserve a new budget
slot and do not resubmit the worker.
~~~

~~~powershell
python -m tools.hiera.cli --project . recover <slug> --run-id <run-id> --attempt <attempt-id>
~~~


For a non-blocking status check of all pending remote attempts:

```text
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
```

`status` polls each pending handle once and collects terminal receipts. It never submits a replacement attempt. If the local client disconnected after reserving an attempt, recover that same attempt:

```text
python -m tools.hiera.cli --project . recover <slug> \
  --run-id <run-id> --attempt <attempt-id>
```

`recover` verifies the frozen contract and candidate digest, resumes the existing remote handle, and reconciles a completed deep evaluation exactly once. A `missing` or `unknown` attempt is finalized as failed only through explicit recovery; it is never reported as a success or relaunched automatically.

Next step: after a terminal receipt, continue the bounded iteration or finalize the exploratory search.

### 10. Finalize the exploratory search
**User skill command (/hiera-experiment):** /hiera-experiment <slug> --run-id <run-id> --finalize

**Follow-up text is required:**

~~~text
Confirm all remote attempts are collected or recovered, then write the Hiera
sidecar report only. Do not write results to wiki or declare a formal claim.
~~~

**Agent Python command:**

~~~powershell
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
~~~

For formal confirmation, return to the normal experiment workflow after
reviewing FINAL_REPORT.json.


```text
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
```

`finalize` writes `FINAL_REPORT.json` with candidate/evaluation coverage, the best recorded score, experience revision, and wiki isolation state. It does not declare a scientific conclusion and does not write anything to the wiki.

Next step for a confirmatory claim: copy the selected method into the normal experiment path and use the existing user-gated `/exp-run` and `/exp-eval` workflow.

## Local and remote execution

Set `resources.environment` to `local` for local execution. Set it to `remote` only in the approved contract for remote execution. Remote Hiera uses the project-relative `config/server.yaml` through the Hiera adapter. The adapter:

- uploads only the immutable candidate snapshot into one per-attempt sidecar directory;
- applies the reviewed `conda.path` + `conda.env`, or the reviewed `env_setup`, on the remote host;
- runs the reviewed preflight/evaluation command and collects bounded logs plus the declared JSON result;
- keeps a local `remote.json` handle so `status` and `recover` can continue the same attempt.

It does not call the project-wide `sync-code`, `setup-env`, `launch`, or `pull-results` workflow, sync the AutoSci source tree, install arbitrary candidate dependencies, or transfer the wiki. Dependencies and data must already be available in the reviewed environment or be handled by the reviewed candidate command.

The evaluation command is an argv list, for example:

```json
["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]
```

Only these placeholders are allowed: `{candidate_dir}`, `{run_dir}`, `{attempt_dir}`, `{result_file}`, `{config_file}`, and `{entrypoint}`. The result file must be JSON and its `score_path` must resolve to a finite number.

## Human gates and safe stopping points

The agent may inspect, propose, author drafts, admit, preflight, run approved evaluations, monitor, recover, tune, loop, and finalize within the approved boundary. It must stop for explicit user input when:

- the semantic space needs a mechanism hypothesis or relation;
- candidate source or a candidate spec needs review;
- the execution contract or remote environment needs approval;
- a result requires a confirmatory decision outside exploratory Hiera.

After every command, the agent should state what happened and provide the next concrete command when it is safe and unblocked. This keeps the workflow navigable without allowing a gate to be skipped.
