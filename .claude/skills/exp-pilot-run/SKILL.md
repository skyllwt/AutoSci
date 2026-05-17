---
description: Pilot experiment execution — read Pilot Spec YAML, write pilot code, run experiment(Confirm with the user before operation and require the applicant to conduct manual inspection), return results. Called by /ideate Phase 5. Does NOT modify wiki pages or judge pass/fail.
argument-hint: <idea-slug> [--env local|remote]
---

# /exp-pilot-run

> Execute a pilot experiment described by a Pilot Spec YAML file.
> Reads the spec from `experiments/pilot/{slug}.yaml`, writes pilot code, runs the experiment(Confirm with the user before operation and require the applicant to conduct manual inspection), and returns raw results to the caller.
>**No matter which operating mode is adopted, before the experimental code is ready for deployment and operation, confirmation shall be obtained from users. Users need to manually check relevant information including codes and experimental configurations(Such as dataset paths, interface parameter selection, API configuration and so on). The operation can only be launched after confirmation. Otherwise, revisions shall be made repeatedly until users approve the execution.**
> Supports **local** (direct GPU) and **remote** (SSH deployment via `tools/remote.py`) modes.
> Does NOT modify any wiki pages. Does NOT judge pass/fail — results are evaluated by `/exp-pilot-eval`.

## Inputs

- `idea-slug`: slug used to locate `experiments/pilot/{slug}.yaml`
- `--env local|remote` (optional, default `local`): deployment environment
  - `local`: run directly on local GPU
  - `remote`: deploy to remote machine via SSH (requires `config/server.yaml`)

## Outputs

- Pilot code: `experiments/pilot/code/{slug}/` (train.py, config.yaml, run.sh, requirements.txt)
- Pilot results: `experiments/pilot/code/{slug}/results/seed_{N}.json`
- Pilot log: `experiments/pilot/code/{slug}/pilot.log`
- **PILOT_REPORT** (printed to terminal) — results table, run details, anomalies
- Returns raw results and key metrics to caller
- NO wiki page modifications

## Wiki Interaction

### Reads
- `experiments/pilot/{slug}.yaml` — Pilot Spec (all configuration) **If the Pilot Spec for the selected idea does not exist at the corresponding position, remind the user and create it following the steps for creating a Pilot Spec in /ideate Phase 5.**
- `wiki/papers/*.md` — related papers' method descriptions (implementation reference)

### Writes
- `experiments/pilot/code/{slug}/` — pilot code directory
  - `experiments/pilot/code/{slug}/train.py` — main training/evaluation script
  - `experiments/pilot/code/{slug}/config.yaml` — hyperparameter config file
  - `experiments/pilot/code/{slug}/run.sh` — launch wrapper script
  - `experiments/pilot/code/{slug}/requirements.txt` — dependencies
  - `experiments/pilot/code/{slug}/results/seed_{N}.json` — result files
  - `experiments/pilot/code/{slug}/pilot.log` — run log

### Graph edges created
- None. Pilot experiments do not create graph edges.

## Workflow

**Pre-conditions**: Confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

---

**Phase 1: Prepare**

1. **Read Pilot Spec**:
   **If the Pilot Spec for the selected idea does not exist at the corresponding position, remind the user and create it following the steps for creating a Pilot Spec in /ideate Phase 5.**
   - Load `experiments/pilot/{slug}.yaml`
   - The YAML has a `pilot_spec:` root key; all fields below are nested under it
   - Validate required fields exist under `pilot_spec:`: `implementation`, `setup`, `metrics`, `baseline`, `success_criterion`
   - Extract from `pilot_spec:`: repo, entry_point, modifications, files_to_create, setup (model, dataset, hardware, framework, batch_size, max_steps, learning_rate, seeds, other_hparams), metrics, baseline, success_criterion, hypothesis, approach_sketch

2. **Load implementation context**:
   - Use `pilot_spec.hypothesis` and `pilot_spec.approach_sketch` as the primary implementation guide (idea pages are written by `/ideate` Phase 4, before pilot)
   - Read related papers' method descriptions for algorithm details (from `wiki/papers/` if they exist)
   - Read source paper repo for base code reference

3. **Inspect the dataset and other configurations**
   - The dataset is specified in the setup section of the pilot spec.
   - Obtain the dataset path (select local or remote access based on the --env parameter). You may ask users for local or remote dataset paths and perform automatic retrieval independently.
   - If the dataset does not exist, prompt the user, clarify the need to download the dataset, and confirm the installation path and download sources with the user.
   - Verify the integrity and availability of the dataset, and sort out the attached structure specifications and usage instructions of the dataset.
   - Other configurations include the name of the invoked LLM model, URL, API key and other relevant information.

4. **Write pilot code** to `experiments/pilot/code/{slug}/`:

**The modular programming principle for coding: avoid putting a large amount of code into a single file unless the project is small in scale and simple in logic**

>Preliminary Experiment Purpose Reminder: The goal is to **detect obvious failures** (divergence, severe degradation, fundamental incompatibility), **not to measure final performance**. Follow the reduced configuration of the Pilot Spec: batch size = 1/4–1/8 of that in the paper, training steps = 10–30% of full training. This is to judge the implementation value of an idea to a certain extent at a lower cost, with baseline comparison always included. Do not attempt to optimize for optimal results — a preliminary experiment only needs to confirm "no obvious collapse". From the overall performance in the early and middle stages, results that are improved, basically flat, or slightly worse compared with the baseline are all acceptable.

Possible reference paths for the preliminary experiment code:
   - Path A: Refer to the repository of the original method paper, and modify the code based on this repository to obtain the preliminary experiment code.
   - Path B: Implement an integrated version based on the idea of organic fusion (e.g., check whether performance and cost reach a balance).
   - Path C: Detect common blind spots, break existing assumptions based on new settings, and verify whether all existing methods fail under the new settings.

   - `train.py`: training/evaluation script based on Pilot Spec `setup` config, including:
     - Argument parsing (argparse, all hyperparameters from spec configurable)
     - Data loading (support spec's `setup.dataset`)
     - Model initialization (support spec's `setup.model` and baseline model)
     - Training/inference loop (respect `setup.max_steps` for shortened training)
     - Metric computation (matching spec's `metrics` list)
     - Result saving (JSON format, path: `experiments/pilot/code/{slug}/results/seed_{N}.json`)
     - Random seed control
   - Other required code folders and files such as utils, tools (e.g., `utils.py`, `data_loader.py`)
   - `config.yaml`: all hyperparameters from spec (learning_rate, batch_size, max_steps, etc.)
   - `run.sh`: launch wrapper (includes CUDA_VISIBLE_DEVICES, logging, conda activation)
   - `requirements.txt`: dependencies (if different from main project)

5. **Sanity check** (small-scale validation):
   - Run at minimal scale (10 steps / small subset)
   - Verify: no code crash, data loads correctly, GPU available, loss is finite
   - If sanity fails → fix code, retry once; if still failing, report error and stop


**Gate: Manual Inspection by Users**

> **Note**: Before preparing experimental codes for deployment and operation, confirm with users and apply for users to manually inspect relevant information including codes and experimental configurations. Proceed with operation only after confirmation; otherwise, make revisions until users give approval for execution.


**Phase 2: Run**

> **Pilot purpose reminder**: This is a **short, diagnostic run** — not a full experiment. The run should finish quickly (reduced steps). If it diverges or hangs beyond 2× estimated time, that itself is a useful signal. Report it; do not attempt rescue runs.

#### Local mode (`--env local` or default)

1. **Check GPU**: `nvidia-smi` to confirm GPU available and sufficient VRAM. If `setup.hardware` is `cpu`/`none`/empty and generated code has no CUDA/GPU keywords, skip GPU check and go to step 2 directly.
2. **Estimate runtime**: based on `setup.hardware` (GPU model), `setup.model` (parameter count), `setup.dataset` (scale), and `setup.max_steps` (reduced steps):

   | Typical pilot scenario | Estimated duration |
   |------------------------|--------------------|
   | Single GPU + small dataset (CIFAR / small NLP benchmark) | 5 – 30 min |
   | Single A100 + medium dataset (ImageNet / GLUE) | 30 min – 2h |
   | Multi-GPU or large model fine-tuning (≥7B) | 1 – 4h |


3. **Launch**:
   ```bash
   screen -dmS pilot-{slug} bash -c \
     "cd $(pwd) && bash experiments/pilot/code/{slug}/run.sh 2>&1 | tee experiments/pilot/code/{slug}/pilot.log"
   ```
   - Notify user: "Pilot launched."

4. **Monitor until completion**:
   Enable **monitor** in the terminal to poll and monitor the pre-experiment processes

#### Remote mode (`--env remote`)

**Prerequisite**: user has configured `config/server.yaml`.

1. **Confirm connectivity**: `python3 tools/remote.py status`
   - If unreachable → report error and suggest checking `config/server.yaml`

2. **Find free GPU**: `python3 tools/remote.py gpu-status` (skip if `setup.hardware` is `cpu`/`none`/empty and code has no CUDA/GPU keywords)
   - If no free GPU → report each GPU's usage, suggest waiting or using `--env local`

3. **Sync code**: `python3 tools/remote.py sync-code`
   - Pushes pilot code directory to the remote `work_dir`

4. **Estimate runtime** (same estimation logic as local mode — see table above)
   - Set polling interval proportionally (same table)

5. **Install dependencies** (first time or if requirements changed):
   ```bash
   python3 tools/remote.py setup-env --requirements experiments/pilot/code/{slug}/requirements.txt
   ```

6. **Launch remote pilot**:
   ```bash
   python3 tools/remote.py launch \
     --name "pilot-{slug}" \
     --cmd "bash experiments/pilot/code/{slug}/run.sh" \
     --gpu {gpu_index} \
     --log-file "experiments/pilot/code/{slug}/pilot.log"
   ```
   - Notify user: "Pilot launched (remote)."

7. **Monitor until completion**:
   Enable **monitor** in the terminal to poll and monitor the pre-experiment processes

**Phase 3: Collect & Report**

1. **Verify run completed**: confirm screen session `pilot-{slug}` has ended. If still alive after monitoring, report and wait.

2. **Pull remote results** (remote mode only):
   ```bash
   python3 tools/remote.py pull-results \
     --remote-path "experiments/pilot/code/{slug}/results/" \
     --local-path "./experiments/pilot/code/{slug}/results/"

   python3 tools/remote.py pull-results \
     --remote-path "experiments/pilot/code/{slug}/pilot.log" \
     --local-path "./experiments/pilot/code/{slug}/"
   ```
   If pull fails for some files → report which files are missing, continue with available data.

3. **Check result files**: `experiments/pilot/code/{slug}/results/seed_*.json`
   - List available result files
   - If no result files exist → report error "no result files produced (run may have crashed)"
   - If result files exist but are incomplete (partial seeds) → use available seeds, note in report

4. **Read pilot log**: `experiments/pilot/code/{slug}/pilot.log`
   - Scan for errors, warnings, OOM, divergence signals
   - Extract runtime behavior context for the final report
   - Record any anomalies detected during Phase 2 monitoring

5. **Parse results**:
   - Read each result file (JSON)
   - Compute mean ± std per metric (across seeds)
   - Compare with baseline's `expected_value` (from Pilot Spec)
   - Compute delta: `pilot_mean - baseline_expected`

6. **Output PILOT_REPORT to terminal**:
   ```markdown
   # Pilot Report: {slug}

   ## Results
   | Metric | Baseline | Pilot (mean±std) | Δ |
   |--------|----------|------------------|---|
   | {metric} | {baseline-value} | {mean}±{std} | {delta} |

   ## Run Details
   - Steps completed: {max_steps}
   - Runtime: {elapsed}
   - Seeds completed: {N}/{total}
   - Environment: {local | remote}
   - Log: experiments/pilot/code/{slug}/pilot.log

   ## Anomalies
   - {list of anomalies detected during run, or "None"}

   ## Next Steps
   - Proceed to /exp-pilot-eval for verdict assessment and wiki update
   ```

7. **Return** the raw results and key metrics to the caller (e.g., `/ideate` Phase 5). Do NOT modify any wiki pages — pilot results are evaluated by `/exp-pilot-eval`, not by this skill.

## Constraints

- **Does not require a wiki experiment page**: reads from `experiments/pilot/{slug}.yaml` instead
- **Does not write to wiki pages**: pilot results are returned to the caller; idea page updates are handled by `/exp-pilot-eval`
- **Code goes in `experiments/pilot/code/{slug}/`**: do not write to project root or any other location
- **Results must be saved**: all pilot results saved as JSON in `experiments/pilot/code/{slug}/results/seed_{N}.json`
- **Multi-seed results use mean ± std**: report mean ± std, not single-run results
- **Sanity check must pass**: Phase 1 sanity failure reports error and stops (unless user explicitly overrides)
- **Graph edges are not created here**: pilot experiments do not create graph edges
- **Automatic fix attempts are limited to 1**: prevents infinite restart loops

## Error Handling

- **Pilot Spec not found**: report error, suggest running `/ideate` first to generate the spec
- **Pilot Spec missing fields**: report which required fields are missing, suggest re-running `/ideate`
- **GPU unavailable**: report error, suggest waiting for GPU to free up
- **Sanity check fails**: report detailed error, attempt one automatic fix, if still failing report error and stop
- **Result files missing**: report error "no result files produced (run may have crashed)"
- **Screen session timeout**: if screen session persists beyond 2× the estimated time, warn user but do not force-terminate
- **Remote connection fails**: report SSH error, suggest checking connection config and `config/server.yaml`
- **Remote GPU unavailable**: report each GPU's usage, suggest waiting or using `--env local`
- **Remote result pull fails**: report which files are missing, continue with available local data

## Dependencies

### Skills (via Skill tool)
- None

### Tools (via Bash)
- `nvidia-smi` — local GPU status
- `screen` — local background process management
- `python3 tools/remote.py <command>` — remote operations (status, gpu-status, sync-code, setup-env, launch, check, tail-log, pull-results)

### Configuration
- `config/server.yaml` — remote server config (required only with `--env remote`)

### Claude Code Native
- `Read` — read Pilot Spec and wiki pages
- `Write` — write pilot code to `experiments/pilot/code/{slug}/`
- `Bash` — execute pilot code, monitor processes

### Called by
- `/ideate` Phase 5
- User directly
