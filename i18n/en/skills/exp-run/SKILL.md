---
description: Full experiment execution pipeline — prepare code → deploy → monitor → collect results, supporting three run modes
argument-hint: <experiment-slug> [--review] [--collect] [--full] [--env local|remote]
---

# /exp-run

> Execute an experiment that has been planned in wiki/experiments/.
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
- `experiments/code/{slug}/` — experiment code directory (Phase 1, deploy / full mode). Layout depends on the experiment's A5-full setup fields (bio-C7 minimal pilot merged 2026-05-12) — see Phase 1 Step 3 for the routing rule and per-layout file lists:
  - **ML layout** (default): `train.py`, `config.yaml`, `run.sh`, `requirements.txt`
  - **MD layout** (when `setup.assay_type` matches `\bMD\b|molecular dynamics`): `mdrun.sh`, `system.{gro,pdb}`, `system.top`, `mdp/{em,nvt,npt,md}.mdp`, `analyze.py`, `requirements.txt`
  - **Docking layout** (when `setup.assay_type` matches `docking`): `dock.sh`, `receptor.pdb`, `ligands.sdf`, `config.yaml`, `analyze.py`, `requirements.txt`
  - **Wet-lab layout** (when `setup.in_silico_or_wet == "wet_lab"`): `protocol.md`, `analysis.ipynb`, `data/`, `figures/`, `requirements.txt`
- `wiki/experiments/{slug}.md` — update status, outcome, key_result, date_completed, run_log, remote block
- `wiki/log.md` — append operation log

### Graph edges created
- **None**. The tested_by edges between experiments and ideas are created by /exp-design.

## Workflow

**Precondition**: confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

---

### Deploy Mode (default, status == planned)

**Phase 1: Prepare**

1. **Read experiment page**:
   - `wiki/experiments/{slug}.md`: extract setup (model, dataset, hardware, framework), metrics, baseline, hypothesis. Also read the A5-full bio fields when present: `setup.in_silico_or_wet`, `setup.assay_type`, `setup.force_field`, `setup.solvent_model`, `setup.simulation_length`, `setup.species`, `setup.cell_line`, `setup.weight_version`, `setup.random_seed_protocol` — these drive the Step 3 setup-type routing (bio-C7 minimal pilot).
   - Verify status == `planned`
   - If status is `running`, prompt user to use `--collect` mode
   - If status is `completed`/`abandoned`, refuse to execute

2. **Load implementation context**:
   - Read linked idea's approach sketch (implementation guide)
   - Read related papers' method descriptions (algorithm details)
   - Read other experiments on the same idea (reference code structure)

3. **Write experiment code** to `experiments/code/{slug}/`.

   **Setup-type routing** (bio-C7 minimal pilot merged 2026-05-12) — pick the layout from the A5-full setup fields:

   ```
   if setup.in_silico_or_wet == "wet_lab":          → wet-lab layout
   elif setup.assay_type matches \bMD\b|molecular dynamics:  → MD layout
   elif setup.assay_type contains "docking":         → docking layout
   else (default, includes in_silico/mixed without MD/docking, or empty fields):
                                                     → ML layout (current behaviour)
   ```

   For `setup.in_silico_or_wet == "mixed"`, default to the in-silico routing above; if the wet-lab side is non-trivial, also scaffold a sibling `wet-lab/` sub-directory using the wet-lab layout below.

   **ML layout** (default — backward-compatible):
   - `train.py`: training/evaluation script (argparse, data loading per `setup.dataset`, model init per `setup.model` and baseline, training/inference loop, metric computation, JSON result save to `results/{slug}/seed_{N}.json`, random seed control, checkpoint save/restore in `checkpoints/{slug}/`)
   - `config.yaml`: all hyperparameters (learning_rate, batch_size, epochs, seeds, …)
   - `run.sh`: launch wrapper (CUDA_VISIBLE_DEVICES, logging, conda activation)
   - `requirements.txt`: experiment-specific dependencies

   **MD layout** (when `setup.assay_type` matches MD):
   - `mdrun.sh`: launch wrapper — GROMACS (`gmx grompp` + `gmx mdrun`) or OpenMM Python runner per `setup.framework`; sources force-field params from `setup.force_field`; sets simulation length from `setup.simulation_length`; runs across the seed budget from `setup.random_seed_protocol`
   - `system.gro` (GROMACS) or `system.pdb` (OpenMM / generic): initial structure file; for PROTAC ternary complexes, document the source PDB / AlphaFold-DB version inline
   - `system.top`: topology with the force field declared in `setup.force_field` (e.g. AMBER ff14SB + phosaa14SB for phospho-residue MD)
   - `mdp/em.mdp`, `mdp/nvt.mdp`, `mdp/npt.mdp`, `mdp/md.mdp` (GROMACS): minimisation + equilibration + production parameters; production length matches `setup.simulation_length`. For OpenMM, replace with a single `system_setup.py` that constructs the System object.
   - `analyze.py`: trajectory analysis (RMSD / RMSF / per-residue distance / interface SASA depending on hypothesis); writes JSON results to `results/{slug}/seed_{N}.json` to keep the downstream `/exp-eval` consumer shape identical
   - `requirements.txt`: GROMACS / OpenMM / MDAnalysis / mdtraj as appropriate

   **Docking layout** (when `setup.assay_type` contains "docking"):
   - `dock.sh`: launch wrapper — AutoDock Vina / Glide / DiffDock per `setup.framework`; reads receptor + ligand inputs, runs multiple seeds per `setup.random_seed_protocol`, writes per-pose scores
   - `receptor.pdb`: prepared receptor structure (typically the POI; for PROTAC docking, the POI + E3 complex from Boltz-2 / AlphaFold-3)
   - `ligands.sdf`: docking library (single or batch of compounds)
   - `config.yaml`: docking parameters (search box centre + size, exhaustiveness, scoring function, output count)
   - `analyze.py`: pose ranking + clustering; writes `results/{slug}/seed_{N}.json` in the same shape as the ML / MD routes
   - `requirements.txt`: docking framework + RDKit + analysis libs

   **Wet-lab layout** (when `setup.in_silico_or_wet == "wet_lab"`):
   - `protocol.md`: full procedure — reagents (with RRID / Cellosaurus / Addgene IDs from a future A8 reproducibility block), step-by-step instructions, controls, expected readouts. Cite `setup.assay_type` (Y2H / AP-MS / cryo-EM / NMR / binding_assay / …), `setup.cell_line`, `setup.species` directly.
   - `analysis.ipynb`: notebook that ingests the raw result CSV under `data/`, applies the statistical protocol from C6's table (bootstrap CI / stratified k-fold / bio×tech replicates per `setup.random_seed_protocol`), and writes summary results to `results/{slug}/run.json` in the same shape as the in-silico routes.
   - `data/`: empty placeholder for raw assay output (will be populated during the wet-lab run; gitignored or committed depending on data-sharing policy)
   - `figures/`: rendered figures from `analysis.ipynb`
   - `requirements.txt`: pandas / scipy / matplotlib / seaborn etc. for analysis only — wet-lab itself has no Python deps

   In all 4 layouts, `results/{slug}/...` output stays JSON-shaped so the downstream `/exp-eval` verdict gate and `/paper-draft` consumers do not branch on setup type. Full C7 (concrete template files under `skills/exp-run/references/templates/{ml,md,wet-lab,docking}/`) is deferred — minimal pilot uses the agent to scaffold per the file lists above.

4. **Optional Review LLM code review** (`--review`):
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

5. **Sanity check (small-scale validation)**:
   - Run at minimal scale (1 epoch / 100 steps / small subset)
   - Verify: no code crash, data loads correctly, GPU available, loss decreases
   - If sanity fails → fix code, retry once; if still failing, report error and stop

**Phase 2: Deploy**

#### Local mode (`--env local` or default)

1. **Check GPU**: `nvidia-smi` to confirm GPU available and sufficient VRAM
2. **Launch** — the entry-point name varies by setup-type layout (bio-C7 minimal pilot): `run.sh` (ML, default), `mdrun.sh` (MD), `dock.sh` (docking). Wet-lab experiments do NOT auto-launch — `/exp-run` for wet-lab just scaffolds `protocol.md` and prompts the user to execute the protocol manually, then re-enter with `--collect` once `data/` is populated.
   ```bash
   ENTRY=run.sh   # set to mdrun.sh / dock.sh per the Step 3 layout for this experiment
   screen -dmS exp-{slug} bash -c \
     "cd $(pwd) && bash experiments/code/{slug}/${ENTRY} 2>&1 | tee logs/exp-{slug}.log"
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
2. **Find free GPU**: `python3 tools/remote.py gpu-status`
   - If no free GPU → report each GPU's usage, suggest waiting
3. **Sync code**: `python3 tools/remote.py sync-code`
4. **Install dependencies** (first time or if requirements changed): `python3 tools/remote.py setup-env`
5. **Launch remote experiment** — entry-point name varies per Step 3 layout (`run.sh` for ML, `mdrun.sh` for MD, `dock.sh` for docking; wet-lab is local-only and does not deploy remotely):
   ```bash
   ENTRY=run.sh   # set per Step 3 layout
   python3 tools/remote.py launch \
     --name "exp-{slug}" \
     --cmd "bash experiments/code/{slug}/${ENTRY}" \
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
