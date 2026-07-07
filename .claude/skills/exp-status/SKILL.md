---
name: exp-status
description: View the status of all running experiments; optionally auto-collect completed experiments and advance the pipeline
argument-hint: "[--pipeline <slug>] [--collect-ready] [--auto-advance]"
---

# /exp-status

> Unified experiment status monitoring entry point.
> Scans all `running` experiments, performs a live status check on each (screen session / SSH),
> and outputs a status table (alive / anomaly / completed) to guide the user's next actions.
>
> When used with `/research --auto`, acts as a periodic checker scheduled by CronCreate:
> when all experiments in a pipeline are completed, automatically triggers `/research --start-from stage4`.

## Inputs

- No arguments (default): check all `running` experiments, print status table
- `--pipeline <slug>` (optional): check only experiments belonging to the specified pipeline; additionally print overall pipeline progress
- `--collect-ready` (optional): auto-call `/exp-run --collect` for all experiments whose session has already ended
- `--auto-advance` (optional, requires `--pipeline <slug>`): if all pipeline experiments are `completed`,
  automatically trigger `/research --start-from stage4` without waiting for the user

## Outputs

- **Status report** (terminal output, all modes): list of experiments in running/anomaly/completed states
- `wiki/experiments/{slug}.md` — updated (outcome/key_result/status) when `--collect-ready` triggers Phase 4
- `wiki/outputs/pipeline-progress.md` — `--auto-advance` updates current_stage → stage4 (done internally by /research --start-from stage4)
- `wiki/log.md` — appended status check log

## Wiki Interaction

### Reads
- `wiki/experiments/*.md` — status, remote frontmatter (server/session/started), date_planned
- `wiki/outputs/pipeline-progress.md` — in `--pipeline` mode, identifies target experiments and monitoring_cron_id

### Writes
- `wiki/experiments/{slug}.md` — updated via /exp-run --collect in `--collect-ready` mode
- `wiki/outputs/pipeline-progress.md` — updated by /research when `--auto-advance` triggers Stage 4
- `wiki/log.md` — appended status check log

### Graph edges created
- None (result writes triggered indirectly via /exp-run --collect do not produce new edges)

## Workflow

**Precondition**: confirm working directory is the wiki project root (directory containing `wiki/`, `raw/`, `tools/`).

### Step 1: Collect Target Experiment List

1. **Determine check scope**:
   - If `--pipeline <slug>` is specified:
     - Read `wiki/outputs/pipeline-progress.md`, extract the slug list from the `stage3a_deployed` field
     - If the file does not exist or slug does not match: report error, suggest running `/research` first or specifying manually
   - Otherwise:
     - Use Glob to scan `wiki/experiments/*.md`, filter for `status == running`

2. **If no running experiments**:
   - Print a friendly message:
     ```
     No running experiments found.
     - To start an experiment: /exp-run <slug>
     - To see all experiments: check wiki/experiments/
     ```
   - Return

### Step 2: Check Status of Each Experiment

For each target experiment, execute in parallel (or sequentially):

1. **Read experiment page**: from `wiki/experiments/{slug}.md` get:
   - `remote` block (if present, this is a remote experiment)
   - `run_log` path
   - `started` (from `remote.started` or `date_planned`, used to compute elapsed time)
   - Deployment environment (has remote block → remote, otherwise → local)

2. **Check process status**:
   - **Local**: `screen -ls | grep "exp-{slug}"`
     - Has output → `alive: true`
     - No output → `alive: false` (session is gone)
   - **Remote**: `python3 tools/remote.py check --name "exp-{slug}"`
     - Parse JSON: `alive`, `last_lines`, `anomalies`

3. **If alive == true**:
   - Fetch recent logs (at most 20 lines):
     - Local: `tail -20 {run_log}`
     - Remote: use `last_lines` from the `check` command response
   - Extract latest metric (loss, accuracy, step, etc. — grep the last metric line)
   - Detect anomalies (NaN/OOM/Traceback/Inf): use `anomalies` field from `remote.py check` (remote), or manual grep (local)
   - Compute elapsed time (current time − started)
   - Classify as: `running` or `anomaly`

4. **If alive == false**:
   - Classify as: `completed_pending_collect` (session gone but wiki status is still running)
   - If wiki status is already `completed`: classify as `collected`

5. **Aggregate results**: build status dict `{slug: {state, elapsed, latest_metric, anomalies}}`

### Step 3: Print Status Report

```markdown
# Experiment Status — {YYYY-MM-DD HH:MM}

### 🔄 Running ({N})
| Experiment | Elapsed | Latest | Env |
|-----------|---------|--------|-----|
| [[exp-foo-baseline]] | 2.3h | loss: 0.42 | local |
| [[exp-foo-validation]] | 1.1h | step: 1200 | remote (gpu1) |

### ⚠️ Anomaly Detected ({N})
| Experiment | Elapsed | Issue | Action |
|-----------|---------|-------|--------|
| [[exp-foo-ablation]] | 0.8h | NaN loss at step 500 | Inspect with `/exp-run exp-foo-ablation --collect` in Claude Code or `$exp-run exp-foo-ablation --collect` in Codex |

### ✅ Completed — Pending Collect ({N})
| Experiment | Finished (estimate) |
|-----------|---------------------|
| [[exp-foo-sanity]] | session gone |

### 📦 Already Collected ({N})
| Experiment | Outcome |
|-----------|---------|
| [[exp-foo-old]] | succeeded |

---
### Actions
```bash
# Collect all completed experiments at once:
/exp-status --collect-ready

# Collect a specific experiment:
/exp-run exp-foo-sanity --collect

# Pipeline progress (if in /research):
/exp-status --pipeline {pipeline-slug}
```
```

Append log:
```bash
python3 tools/research_wiki.py log wiki/ \
  "exp-status | running: {N}, anomaly: {M}, pending-collect: {K}"
```

### Step 4: --collect-ready Auto-Collect (if specified)

For each `completed_pending_collect` experiment, call `/exp-run --collect`:

```
Skill: exp-run
Args: "{slug} --collect"
```

Collect each completed experiment sequentially (not in parallel, to avoid concurrent wiki writes).

After all collections are done, re-print the updated status report.

### Step 5: --auto-advance Pipeline Advance (if both --pipeline and --auto-advance are specified)

1. **Check pipeline completion condition**:
   - Read `stage3a_deployed` list from `wiki/outputs/pipeline-progress.md`
   - Check the status of each slug's `wiki/experiments/{slug}.md`
   - **Condition met**: all experiments have status == `completed`

2. **If condition is not met** (some experiments still running or pending collect):
   - Print current progress: `Pipeline {slug}: {M}/{N} experiments completed`
   - Return (do not advance)
   - Cron will trigger again in 30 minutes

3. **If condition is met (all experiments completed)**:

   a. **Print notification and trigger Stage 4**:
   - Print:
     ```
     ✅ All experiments completed for pipeline {slug}!
     Advancing to Stage 4 (Verdict & Iteration)...
     ```
   - Append log:
     ```bash
     python3 tools/research_wiki.py log wiki/ \
       "exp-status | pipeline {slug}: all experiments done, advancing to stage4"
     ```
   - Trigger next stage:
     ```
     Skill: research
     Args: "--start-from stage4"
     ```

## Constraints

- **Read-only in non --collect-ready mode**: without `--collect-ready`, do not modify any wiki files
- **`--auto-advance` requires `--pipeline`**: using `--auto-advance` alone is invalid, report an error
- **Status checks must be non-blocking**: each experiment check should complete quickly (single SSH check or screen -ls)
- **Anomalies are not auto-fixed**: `/exp-status` only reports anomalies; fixes require the user to manually call `/exp-run --collect`
- **pipeline-progress.md must exist**: in `--pipeline` mode, if the file is missing, report an error

## Error Handling

- **No running experiments**: print friendly message, not an error; provide next step suggestions
- **`--pipeline` but pipeline-progress.md does not exist**: report error "Pipeline progress file not found. Run `/research <direction>` first or check wiki/outputs/"
- **`--auto-advance` without `--pipeline`**: report error "--auto-advance requires --pipeline <slug>"
- **SSH connection fails** (remote experiment): mark that experiment as `check_failed`, note it in the report, continue checking other experiments
- **screen -ls returns nothing**: does not mean the experiment failed — may be a brief delay; mark as `completed_pending_collect`
- **`/exp-run --collect` fails** (`--collect-ready` mode): record the failure, continue collecting other experiments, report all failures at the end

## Dependencies

### Skills（via Skill tool）
- `/exp-run` — call collect phase in `--collect-ready` mode
- `/research` — trigger Stage 4 via `--auto-advance`

### Tools（via Bash）
- `python3 tools/remote.py check --name "exp-{slug}"` — remote experiment status check
- `python3 tools/remote.py tail-log --name "exp-{slug}" --lines 20` — fetch remote logs
- `python3 tools/research_wiki.py set-meta <path> <field> <value>` — update pipeline-progress
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `screen -ls` — local process status
- `tail -20 {log}` — fetch local logs

### Agent Runtime Capabilities
- `Read` — read experiment pages and pipeline-progress
- `Write` — update pipeline-progress status
- `Glob` — scan wiki/experiments/*.md
- `Bash` — screen/tail and other system commands
- `Skill` — call /exp-run --collect and /research

### Called by
- CronCreate schedule (created by `/research --auto` Stage 3b: triggers every 30 minutes)
- User directly
- `/research` Stage 3b (in interactive mode, suggested to user)
