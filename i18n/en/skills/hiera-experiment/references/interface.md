# Hiera sidecar interfaces

The CLI is run from the AutoSci project root:

```text
python -m tools.hiera.cli --project . init <experiment-slug> --run-id <run-id> \
  --contract path/to/contract-overrides.json
```

After a remote client interruption, resume the already-reserved attempt with:

```text
python -m tools.hiera.cli --project . recover <experiment-slug> --run-id <run-id> \
  --attempt <attempt-id>
```

For a quick, non-blocking remote check of all pending attempts in one Hiera
run, use:

```text
python -m tools.hiera.cli --project . status <experiment-slug> --run-id <run-id>
```

The command polls each pending remote handle once and collects a terminal
receipt when available. It never submits a new attempt. `recover` remains the
blocking path for resuming one interrupted attempt; its reconciliation records
the completed deep attempt as a tuning bout exactly once.

`init` creates this isolated directory:

```text
runs/hiera/<experiment-slug>/<run-id>/
├── manifest.json
├── semantic_space.json
├── task_contract.yaml       # JSON syntax that is valid YAML 1.2
├── ledger.jsonl              # append-only event source
├── drafts/<candidate-id>/    # reviewed modular source before admission
├── candidates/<candidate-id>/
├── attempts/<attempt-id>/
└── FINAL_REPORT.json         # created by finalize
```

The contract override is a JSON object merged into the generated contract. The executable minimum is:

```json
{
  "candidate": {
    "entrypoint": "run.py",
    "editable_files": ["run.py"]
  },
  "evaluation": {
    "evaluate_command": ["python", "-c", "..."],
    "result_file": "results/result.json",
    "score_path": "score",
    "metric": "validation_loss",
    "direction": "minimize"
  },
  "resources": {
    "environment": "local",
    "timeout_seconds": 3600,
    "max_evaluations": 20
  }
}
```

Commands are argv arrays. They may use only `{candidate_dir}`, `{run_dir}`, `{attempt_dir}`, `{result_file}`, `{config_file}`, and `{entrypoint}`. The evaluator runs with `shell=False`. The result file is created inside a new attempt directory and must be JSON with a finite number at `score_path`.

Both adapters accept `preflight_command`. `prepare_command` and `collect_command` must remain empty: the local adapter needs no transfer phase, while the Hiera remote adapter deploys the candidate snapshot and collects declared artifacts itself.

## Remote execution

Set `resources.environment` to `remote` only in a contract whose remote boundary has been reviewed before `approve`. The remote-specific resource fields are:

| Field | Default | Meaning |
|---|---|---|
| `remote_config` | `config/server.yaml` | Project-relative server configuration read through `tools.remote`; it supplies `host`, `user`, `work_dir`, SSH options, and the reviewed runtime setup. |
| `remote_python` | `python3` | One remote Python executable used for the worker RPC and to replace a leading `python` or `python3` in candidate argv. It is an executable path/name, not a shell command. |
| `remote_poll_seconds` | `5` | Positive interval between status checks. |
| `remote_gpu` | empty | Explicit comma-separated GPU indices. When empty and `accelerator` is neither empty, `cpu`, nor `none`, the adapter selects one currently free GPU; CPU runs do not select a GPU. |

`config/server.yaml` must satisfy the existing remote helper contract and provide either `conda.path` plus `conda.env`, or `env_setup`. With `conda`, the worker prefixes candidate argv with `conda run`. Without it, the reviewed `env_setup` is run by `bash -lc` before a shell-quoted form of the candidate argv. This is automatic environment activation; Hiera does not invoke project-wide `sync-code` or `setup-env`, install candidate requirements, or transfer datasets. Candidate dependencies and data therefore need to be present in the reviewed remote environment, or be handled by the reviewed candidate command. Treat changes to this server configuration as changes to the reviewed execution environment. Credentials remain outside Hiera artifacts.

For attempt `<attempt-id>`, the adapter transfers only the admitted candidate file map to:

```text
<work_dir>/runs/hiera/<experiment-slug>/<run-id>/<attempt-id>/
├── candidate/               # immutable admitted file map
├── job.json                 # token-bound deployment receipt
├── worker.py
├── worker.pid
├── execution.json           # durable running/terminal state
├── preflight_stdout.log
├── preflight_stderr.log
├── stdout.log
├── stderr.log
└── <evaluation.result_file>
```

No project sync, branch push, or wiki transfer is performed. The worker runs `preflight_command` and `evaluate_command` with the candidate directory as `cwd`. Commands should write their JSON result through the absolute `{result_file}` placeholder. Collection is limited to the four logs and the declared result file; a successful score is accepted only when the remote execution receipt reports a successful evaluation with return code zero and `score_path` resolves to a finite number.

Budget is reserved in `ledger.jsonl` before remote deployment. The local attempt directory persists `remote.json`, which binds the attempt ID, candidate, token, host, server-configuration digest, and remote path. Deployment with the same token is idempotent and never launches a second worker. `status` polls pending handles once and collects terminal results without blocking; `recover --attempt <attempt-id>` verifies the frozen contract and candidate snapshot, then polls and collects that same attempt without another reservation or submission. Both paths reconcile a completed deep evaluation to its tuning bout by attempt ID. A `running` attempt remains pending; a terminal execution failure is collected as a failed evaluation; `missing` or `unknown` state is finalized as failed only by the explicit recovery action and must never be reported as successful completion or cause an automatic relaunch.

## Modular candidate source

For a non-trivial experiment, keep the metadata spec small and store source files in a reviewed tree:

```text
runs/hiera/<experiment-slug>/<run-id>/drafts/method-variant-a/
├── run.py                    # thin CLI/training entrypoint
└── experiment/
    ├── __init__.py
    ├── data.py               # data loading and split policy
    ├── models/
    │   ├── __init__.py
    │   └── method.py          # method-specific model variant
    ├── training.py           # optimization loop
    └── evaluation.py         # metrics and result serialization
```

The exact tree is experiment-specific; do not create empty modules just to match this illustration. List every source file in `candidate.editable_files`, then keep the metadata spec free of large source strings and import the tree with:

```text
python -m tools.hiera.cli --project . admit <experiment-slug> --run-id <run-id> \
  --spec path/to/method-variant-a.json \
  --source-dir runs/hiera/<experiment-slug>/<run-id>/drafts/method-variant-a
```

`--source-dir` and `spec.files` are mutually exclusive. The source directory must be inside this run's `drafts/` directory, contain exactly the UTF-8 files named by `candidate.editable_files`, and must not contain `config.json`; the tool creates that file from the spec's `config`. Nested paths remain nested in the immutable candidate snapshot. The inline `files` form below remains useful for a small one-file candidate.

Each inline `admit --spec` file has this shape:

```json
{
  "candidate_id": "method-variant-a",
  "operation": "fresh",
  "parents": [],
  "semantic_point": {"dim-method": "hyp-baseline-method"},
  "config": {"learning_rate": 0.001},
  "files": {"run.py": "# complete candidate source\n"}
}
```

The tool adds `config.json`, records every file digest, and refuses to execute if any admitted file changes. `parents` must name earlier candidates. A changed source or config gets a new candidate ID and a new snapshot. The command should use the reviewed entrypoint and config placeholders, for example `{"evaluate_command": ["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]}`.

`propose` only proposes semantic points. OpenCode or the user authors the candidate files, reviews them, and admits them. `approve` freezes the contract digest; `preflight`, `run`, `recover`, `tune`, and `loop` require that frozen digest. With a reviewed `candidate.config_schema`, `tune --candidate ID --limit N` copies the immutable code snapshot, materializes bounded config variants, evaluates them, and records each as a child candidate. `loop` repeatedly chooses eligible deep candidates and records tuning bouts until its round limit or the contract budget is reached.
