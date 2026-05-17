---
description: Full experiment execution pipeline — prepare code → deploy(Confirm with the user before operation and ask the applicant to conduct manual inspection) → monitor → collect results, supporting three run modes
argument-hint: <experiment-slug> [--review] [--collect] [--full] [--env local|remote]
---

# /exp-run

> Execute an experiment that has been planned in wiki/experiments/.
> **No matter which operation mode it is, before preparing the experimental codes and deploying them for operation, confirmation shall be obtained from users. Users need to manually check relevant information such as codes and experimental configurations(Dataset paths, interface parameter selection, API configuration, etc.). The operation can only be launched after confirmation; otherwise, revisions shall be made repeatedly until users approve the execution.**
> **Three run modes** for different scenarios:
> - **Default (deploy)**: Phase 1-2 only — deploy and return immediately. Best for experiments that take hours or days.
> - **`--collect`**: Phase 3-4 only — check whether a deployed experiment has finished; collect results if so (`--check` is an alias).
> - **`--full`**: All four phases end-to-end. Best for short local experiments that finish in minutes.
>
> Recommended flow: `/exp-run <slug>` to deploy → `/exp-status` to monitor → `/exp-run <slug> --collect` to collect.

## Inputs

- `experiment`: slug from wiki/experiments/
  - deploy mode: status must be `planned`
  - --collect mode: status must be `running`
  - --full mode: status must be `planned`
- `--review` (optional): enable Review LLM code review for experiment code in Phase 1 (valid in deploy / full mode)
- `--collect` (optional): collect mode — check if the experiment has finished and collect results; `--check` is an alias
- `--full` (optional): full mode — execute all 4 phases (best for quick local experiments)
- `--env local|remote` (optional, default `local`): deployment environment
  - `local`: run directly on local GPU
  - `remote`: deploy to remote machine via SSH (requires `config/server.yaml`)

## Outputs

- **deploy mode**:
  - Experiment code: `experiments/code/{slug}/` (generated in Phase 1)
  - `wiki/experiments/{slug}.md` — status: planned → running
  - **DEPLOY_REPORT** (printed to terminal) — deployment confirmation, session info, next steps
  - `wiki/log.md` — appended deploy log
- **collect mode** (experiment has finished):
  - `wiki/experiments/{slug}.md` — status: running → completed; outcome/key_result/date_completed filled in
  - **RUN_REPORT** (printed to terminal) — result summary, metrics comparison, next step suggestions
  - `wiki/log.md` — appended collect log
- **collect mode** (experiment still running):
  - Progress report printed to terminal only; wiki is not modified
- **full mode**: all outputs from both deploy and collect

## Wiki Interaction

### Reads
- `wiki/experiments/{slug}.md` — experiment config: setup, metrics, baseline, hypothesis, linked_idea
- `wiki/ideas/{linked-idea}.md` — linked idea's approach sketch (guide code implementation, understand experiment purpose)
- `wiki/papers/*.md` — related papers' method details and hyperparameters (implementation reference)
- `wiki/experiments/*.md` — other experiments on the same idea (reference setup, avoid known mistakes)

### Writes
- `experiments/code/{slug}/` — experiment code directory (Phase 1, deploy / full mode)
  - `experiments/code/{slug}/train.py` — main training/inference script
  - `experiments/code/{slug}/config.yaml` — hyperparameter config file
  - `experiments/code/{slug}/run.sh` — launch wrapper script (includes CUDA_VISIBLE_DEVICES etc.)
  - `experiments/code/{slug}/requirements.txt` — dependencies (if different from main project)
- `wiki/experiments/{slug}.md` — update status, outcome, key_result, date_completed, run_log, remote block (deploy / collect mode)
- `wiki/log.md` — append operation log

### Graph edges created
- **None**. The tested_by edges between experiments and ideas are created by /exp-design.

## Workflow

**Precondition**: confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

---

### Deploy Mode (default, status == planned)

**Phase 1: Prepare**

1. **Read experiment page**:
   - `wiki/experiments/{slug}.md`: extract setup (model, dataset, hardware, framework), metrics, baseline, hypothesis
   - Verify status == `planned`
   - If status is `running`, prompt user to use `--collect` mode
   - If status is `completed`/`abandoned`, refuse to execute

2. **Load implementation context**:
   - Read linked idea's approach sketch (implementation guide)
   - Read related papers' method descriptions (algorithm details)
   - Read other experiments on the same idea (reference code structure)

3. **Inspect the dataset and other configurations**
   - The dataset is specified in the setup section of `wiki/experiments/{slug}.md`
   - Obtain the dataset path (select local or remote access based on the --env parameter). You may ask users for the local or remote dataset paths and conduct independent retrieval.
   - Prompt users if the dataset is missing, clarify the need to download the dataset, and confirm the installation path and download source with users.
   - Check the integrity and availability of the dataset, and sort out its built-in structure and usage instructions.
   - Other configurations include: LLM model name for invocation, URL, API key, etc.

4. **Write experiment code** to `experiments/code/{slug}/`:
   **Modular thinking in coding: avoid putting a large amount of code in a single file unless the project is small in scale and simple in logic**
   - `train.py`: generate training/evaluation script based on setup config as the entry point of the program including:
     - Argument parsing (argparse, all hyperparameters configurable)
     - Data loading (support setup.dataset)
     - Model initialization (support setup.model and baseline model)
     - Training/inference loop
     - Metric computation (matching metrics list)
     - Result saving (JSON format, path: `results/{slug}/seed_{N}.json`)
     - Random seed control (multi-seed runs)
     - Checkpoint save/restore (`checkpoints/{slug}/`)
   - Other required code folders and files such as utils, tools (e.g., `utils.py`, `data_loader.py`, etc.)
   - `config.yaml`: all hyperparameters (learning_rate, batch_size, epochs, seeds, etc.)
   - `run.sh`: complete launch command wrapper (includes CUDA_VISIBLE_DEVICES, logging, conda activation)
   - `requirements.txt`: experiment-specific dependencies (if different from main project requirements)

5. **Optional Review LLM code review** (`--review`):
   ```
   mcp__llm-review__chat:
     system: "You are a senior ML engineer reviewing experiment code.
              Focus on: correctness of the training loop, proper evaluation protocol,
              fair baseline comparison, reproducibility (seeds, determinism),
              proper metric computation, and common pitfalls (data leakage,
              wrong split, gradient accumulation bugs)."
     message: |
       ## Experiment
       {experiment title and hypothesis}

       ## Code
       {generated code}

       ## Expected Behavior
       {setup details from wiki page}

       Review for correctness and potential issues.
   ```
   Fix code based on Review LLM feedback.

6. **Sanity check (small-scale validation)**:
   - Run at minimal scale (1 epoch / 100 steps / small subset)
   - Verify: no code crash, data loads correctly, GPU available, loss decreases
   - If sanity fails → fix code, retry once; if still failing, report error and stop


**Gate: Manual User Inspection**

> **Note**: Before preparing experimental code for deployment and execution, confirm with users and request them to manually check relevant information including codes and experimental configurations(Dataset paths, interface parameter selection, API configuration, etc.). Proceed with operation only after confirmation; otherwise, make revisions repeatedly until users approve the execution.

**Phase 2: Deploy**

#### Local mode (`--env local` or default)

1. **Check GPU**: `nvidia-smi` to confirm GPU available and sufficient VRAM. If `setup.hardware` is `cpu`/`none`/empty and generated code has no CUDA/GPU keywords, skip GPU check and go to step 2 directly.
2. **Launch**:
   ```bash
   screen -dmS exp-{slug} bash -c \
     "cd $(pwd) && bash experiments/code/{slug}/run.sh 2>&1 | tee logs/exp-{slug}.log"
   ```
3. Update `wiki/experiments/{slug}.md`:
   - status: `running`
   - run_log: `logs/exp-{slug}.log`
4. **Estimate runtime** and write to frontmatter:
   Estimate based on `setup.hardware` (GPU model/count), `setup.model` (parameter count), `setup.dataset` (scale):

   | Typical scenario | Estimated range |
   |-----------------|-----------------|
   | Single GPU + small dataset (CIFAR / small NLP benchmark) | 0.5 – 3h |
   | Single A100 + medium dataset (ImageNet / GLUE) | 4 – 12h |
   | Multi-GPU or large model fine-tuning (≥7B) | 8 – 48h |

   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md started "{YYYY-MM-DDTHH:MM}"
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md estimated_hours {N}
   ```
5. Append log:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | deployed {slug} | env: local | session: exp-{slug} | eta: {N}h"
   ```

#### Remote mode (`--env remote`)

**Prerequisite**: user has configured `config/server.yaml`.

1. **Confirm connectivity**: `python3 tools/remote.py status`
   - If unreachable → report error and suggest checking config/server.yaml
2. **Find free GPU**: `python3 tools/remote.py gpu-status` (skip if `setup.hardware` is `cpu`/`none`/empty and code has no CUDA/GPU keywords)
   - If no free GPU → report each GPU's usage, suggest waiting
3. **Sync code**: `python3 tools/remote.py sync-code`
4. **Install dependencies** (first time or if requirements changed): `python3 tools/remote.py setup-env`
5. **Launch remote experiment**:
   ```bash
   python3 tools/remote.py launch \
     --name "exp-{slug}" \
     --cmd "bash experiments/code/{slug}/run.sh" \
     --gpu {gpu_index}
   ```
6. Update `wiki/experiments/{slug}.md` frontmatter — all of these fields already exist (empty) because `/exp-design` wrote the full CLAUDE.md template:
   ```bash
   # Top-level scalar fields — use set-meta
   python3 tools/research_wiki.py set-meta wiki/experiments/{slug}.md status running
   python3 tools/research_wiki.py set-meta wiki/experiments/{slug}.md run_log "logs/exp-{slug}.log"
   ```

   The nested `remote:` block cannot be updated via `set-meta` (it only handles top-level scalar fields). Use the `Edit` tool directly to replace the five empty sub-field values in place. The pre-existing block in the file looks like:
   ```yaml
   remote:
     server: ""
     gpu: ""
     session: ""
     started: ""
     completed: ""
   ```
   Use five Edit calls (one per sub-field) to set `server`, `gpu`, `session`, `started`. Leave `completed: ""` — Phase 4 fills that. If you find the `remote:` block missing from the file, that means `/exp-design` did not write the full CLAUDE.md template; stop and report the bug rather than trying to append the block here (appending would drift the file away from the canonical order and break future edits).

7. **Estimate runtime** and write to frontmatter (same estimation logic as local mode):
   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md started "{YYYY-MM-DDTHH:MM}"
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md estimated_hours {N}
   ```
8. Append log:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | deployed {slug} | env: remote | server: {host} | gpu: {gpu} | eta: {N}h"
   ```

**Print DEPLOY_REPORT to terminal**:

```markdown
# Deploy Report: {experiment title}

### Status: DEPLOYED ✅

- Session: exp-{slug}
- Environment: local | remote ({host} GPU {gpu})
- Log file: logs/exp-{slug}.log
- Code: experiments/code/{slug}/
- Estimated: ~{N}h (expected completion: {YYYY-MM-DD HH:MM})

### Next Steps

1. Monitor progress: `/exp-status`
2. Check this experiment: `/exp-run {slug} --collect`
3. In /research pipeline: progress saved to wiki/outputs/pipeline-progress.md

### Quick Commands
```bash
# Local: check if still running
screen -ls | grep exp-{slug}

# Local: tail log
tail -f logs/exp-{slug}.log
```
```

---

### Collect Mode (`--collect` or `--check`, status == running)

**Phase 3: Monitor / Check Run Status**

1. **Read deployment info**: from `wiki/experiments/{slug}.md` frontmatter, get environment (local or remote) and session name.

2. **Check whether the process is still alive**:
   - **Local**: `screen -ls | grep exp-{slug}`
   - **Remote**: `python3 tools/remote.py check --name "exp-{slug}"`, parse `alive` field

3. **If experiment is still running (alive == true)**:
   - Fetch recent logs:
     - Local: `tail -30 logs/exp-{slug}.log`
     - Remote: `python3 tools/remote.py tail-log --name "exp-{slug}" --lines 30`
   - **Anomaly detection**:
     - NaN loss: detect `loss: nan`
     - OOM: `CUDA out of memory`
     - Traceback: Python exception stacktrace
     - Inf loss: `loss: inf`
   - **Automatic fix attempt** (if anomaly detected, at most 1 attempt):
     - NaN/exploding → resume from latest checkpoint, reduce learning rate
     - OOM → reduce batch size, restart
   - **Print progress report** (do not modify wiki, report only):
     ```
     Experiment {slug}: RUNNING
     Progress: step {N} / epoch {E}
     Latest metric: {metric} = {value}
     Anomalies: {none | NaN detected | ...}
     Estimated remaining: ~{N} hours
     Run `/exp-status` to monitor all running experiments.
     ```
   - **Return** (do not execute Phase 4)

4. **If experiment has finished (alive == false / session gone)**:
   - Continue to Phase 4

**Phase 4: Collect Results**

1. **Pull remote results** (remote mode only):
   ```bash
   python3 tools/remote.py pull-results \
     --remote-path "results/{slug}/" \
     --local-path "./results/{slug}/"

   python3 tools/remote.py pull-results \
     --remote-path "logs/exp-{slug}.log" \
     --local-path "./logs/"
   ```

2. **Check result files exist**: `results/{slug}/seed_*.json`

3. **Parse results**:
   - Read result files (JSON)
   - Compute mean ± std per metric (across seeds)
   - Compare with baseline, compute improvement delta

4. **Update experiment page** `wiki/experiments/{slug}.md`:
   - status: `completed`
   - outcome: `succeeded` / `failed` / `inconclusive`
     - succeeded: all success criteria met
     - failed: core metrics did not reach target
     - inconclusive: mixed results or excessive variance
   - key_result: one-sentence summary of the core finding
   - date_completed: today's date
   - Fill `## Results` section: complete results table
   - Fill `## Analysis` section: preliminary analysis
   - If remote mode: update `remote.completed` timestamp

5. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | completed {slug} | outcome: {outcome} | key: {key_result}"
   ```

6. **Print RUN_REPORT to terminal**:
   ```markdown
   # Run Report: {experiment title}

   ## Outcome: {succeeded / failed / inconclusive}

   ## Results
   | Metric | Baseline | Ours (mean±std) | Δ |
   |--------|----------|-----------------|---|
   | {metric} | {baseline-value} | {mean}±{std} | +{delta} |

   ## Key Finding
   {key_result}

   ## Next Steps
   - Run `/exp-eval {slug}` to update the linked idea in wiki
   - {if succeeded: proceed to next experiment in plan}
   - {if failed: analyze failure, consider /exp-design revision}
   ```

---

### Full Mode (`--full`, status == planned)

Execute all 4 phases in sequence (Phase 1 → Phase 2 → Phase 3 → Phase 4) without returning.

Use case: quick local CPU/GPU experiments that finish in minutes (sanity checks, toy dataset validation, etc.).

In Phase 3, instead of checking "is it still running", wait for the screen session to actually exit before executing Phase 4:
```bash
# Wait for session to end (polling)
while screen -ls | grep -q "exp-{slug}"; do
  sleep 30
done
# Session gone, proceed to Phase 4
```

---

## Constraints

- **Deploy mode only accepts planned experiments**: if status is running, prompt to use --collect; if completed, refuse
- **Collect mode only accepts running experiments**: if status is planned, prompt to deploy first; if completed, note it is already done
- **Collect mode: do not write wiki when alive**: only report progress, do not modify any wiki files
- **Code goes in experiments/code/{slug}/**: do not write to project root or any other location
- **Do not update the linked idea's status**: experiment results are written only to experiments/ pages; idea updates are handled by /exp-eval
- **Sanity check must pass**: Phase 1 sanity failure blocks deployment (unless user explicitly overrides)
- **Results must be saved**: all experiment results saved as JSON in `results/{slug}/seed_{N}.json`
- **Multi-seed results use mean**: report mean ± std, not single-run results
- **Graph edges are not created here**: tested_by edges were created by /exp-design
- **Automatic fix attempts are limited to 1**: prevents infinite restart loops

## Error Handling

- **Experiment not found**: prompt user to check slug, list candidates in wiki/experiments/ (status=planned or running)
- **Deploy mode but status == running**: prompt "already running — use `/exp-run {slug} --collect` to check status"
- **Collect mode but status == completed**: prompt "already completed — run `/exp-eval {slug}` directly"
- **GPU unavailable**: report error, suggest using --env remote or waiting for GPU to free up
- **Review LLM unavailable** (--review mode): skip code review, note "unreviewed" in DEPLOY_REPORT
- **Sanity check fails**: report detailed error, attempt one automatic fix, if still failing stop and suggest manual debugging
- **Remote connection fails**: report SSH error, suggest checking connection config and config/server.yaml
- **Result files missing** (collect mode): report which seeds are missing results; summarize available results normally; if successful seeds < 2, mark inconclusive
- **Experiment crashed** (traceback detected in collect mode): include crash info and suggested fix directions in report
- **--full mode wait timeout**: if screen session persists beyond 2× the estimated time, warn user but do not force-terminate

## Dependencies

### Skills（via Skill tool）
- No direct sub-skill calls

### Tools（via Bash）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `python3 tools/remote.py <command>` — remote operations (status, gpu-status, sync-code, setup-env, launch, check, tail-log, pull-results)
- `nvidia-smi` — local GPU status
- `screen` — local background process management

### Configuration
- `config/server.yaml` — remote server config (required only with `--env remote`)

### MCP Servers
- `mcp__llm-review__chat` — Phase 1 code review (optional, when `--review` is used)

### Claude Code Native
- `Read` — read wiki pages and log files
- `Write` — write experiment code to `experiments/code/{slug}/`
- `Bash` — execute deployment commands, monitor processes

### Called by
- `/research` Stage 3a (deploy mode) and Stage 3c (collect mode)
- `/exp-status --collect-ready` (collect mode)
- User directly
