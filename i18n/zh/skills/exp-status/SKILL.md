---
name: exp-status
description: 查看所有运行中实验的状态，可选自动收集已完成实验并推进流水线
argument-hint: "[--pipeline <slug>] [--collect-ready] [--auto-advance]"
---

# /exp-status

> 统一的实验状态监控入口。
> 扫描所有 `running` 实验，对每个实验执行实时状态检查（screen session / SSH），
> 输出状态表（alive / anomaly / completed），引导用户下一步操作。
>
> 与 `/research --auto` 配合时作为 CronCreate 调度的定期检查器：
> 当 pipeline 的所有实验都完成时，自动触发 `/research --start-from stage4`。

## Inputs

- 无参数（默认）：检查所有 `running` 实验，输出状态表
- `--pipeline <slug>`（可选）：只检查属于指定 pipeline 的实验，额外输出 pipeline 整体进度
- `--collect-ready`（可选）：对所有"session 已消失"的实验自动调用 `/exp-run --collect` 收集结果
- `--auto-advance`（可选，需配合 `--pipeline <slug>`）：若 pipeline 所有实验均已 `completed`，
  自动触发 `/research --start-from stage4`，无需用户手动运行

## Outputs

- **状态报告**（终端输出，所有模式）：running/anomaly/completed 三种状态的实验列表
- `wiki/experiments/{slug}.md` — `--collect-ready` 触发 Phase 4 时更新（outcome/key_result/status）
- `wiki/outputs/pipeline-progress.md` — `--auto-advance` 时更新 current_stage → stage4（由 /research --start-from stage4 内部完成）
- `wiki/log.md` — 追加状态检查日志

## Wiki Interaction

### Reads
- `wiki/experiments/*.md` — status、remote frontmatter（server/session/started）、date_planned
- `wiki/outputs/pipeline-progress.md` — `--pipeline` 模式下识别目标实验和 monitoring_cron_id

### Writes
- `wiki/experiments/{slug}.md` — `--collect-ready` 模式下通过 /exp-run --collect 触发更新
- `wiki/outputs/pipeline-progress.md` — `--auto-advance` 触发 Stage 4 时由 /research 更新
- `wiki/log.md` — 追加状态检查日志

### Graph edges created
- 无（通过 /exp-run --collect 间接触发的结果写入不产生新 edges）

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 收集目标实验列表

1. **确定检查范围**：
   - 若指定 `--pipeline <slug>`：
     - 读取 `wiki/outputs/pipeline-progress.md`，提取 `stage3a_deployed` 字段的 slug 列表
     - 若文件不存在或 slug 不匹配：报错，建议先运行 `/research` 或手动指定
   - 否则：
     - 用 Glob 扫描 `wiki/experiments/*.md`，过滤 `status == running` 的实验

2. **若无 running 实验**：
   - 输出友好提示：
     ```
     No running experiments found.
     - To start an experiment: /exp-run <slug>
     - To see all experiments: check wiki/experiments/
     ```
   - 返回

### Step 2: 逐实验状态检查

对每个目标实验并行（或依次）执行：

1. **读取实验页面**：从 `wiki/experiments/{slug}.md` 获取：
   - `remote` 块（有则为 remote 实验）
   - `run_log` 路径
   - `started`（来自 `remote.started` 或 `date_planned`，用于计算 elapsed）
   - 部署环境（有 remote 块 → remote，否则 → local）

2. **检查进程状态**：
   - **Local**：`screen -ls | grep "exp-{slug}"`
     - 有结果 → `alive: true`
     - 无结果 → `alive: false`（session 已消失）
   - **Remote**：`python3 tools/remote.py check --name "exp-{slug}"`
     - 解析 JSON：`alive`、`last_lines`、`anomalies`

3. **若 alive == true**：
   - 获取最近日志（最多 20 行）：
     - Local：`tail -20 {run_log}`
     - Remote：使用 `check` 命令返回的 `last_lines`
   - 提取最新 metric（loss、accuracy、step 等——grep 最后一个 metric 行）
   - 检测异常（NaN/OOM/Traceback/Inf）：使用 `remote.py check` 的 `anomalies` 字段（remote），或手动 grep（local）
   - 计算 elapsed time（当前时间 - started）
   - 分类为：`running` 或 `anomaly`

4. **若 alive == false**：
   - 分类为：`completed_pending_collect`（session 消失但 wiki 状态还是 running）
   - 若 wiki status 已经是 `completed`：归为 `collected` 类

5. **汇总结果**：构建状态字典 `{slug: {state, elapsed, latest_metric, anomalies}}`

### Step 3: 输出状态报告

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
| [[exp-foo-ablation]] | 0.8h | NaN loss at step 500 | 用 Claude Code 的 `/exp-run exp-foo-ablation --collect` 或 Codex 的 `$exp-run exp-foo-ablation --collect` 检查 |

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

追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "exp-status | running: {N}, anomaly: {M}, pending-collect: {K}"
```

### Step 4: --collect-ready 自动收集（若指定）

对每个 `completed_pending_collect` 实验，调用 `/exp-run --collect`：

```
Skill: exp-run
Args: "{slug} --collect"
```

依次（不并行，避免并发写入 wiki）收集每个完成的实验。

收集完成后，重新输出更新的状态报告。

### Step 5: --auto-advance Pipeline 推进（若同时指定 --pipeline 和 --auto-advance）

1. **检查 pipeline 完成条件**：
   - 读取 `wiki/outputs/pipeline-progress.md` 的 `stage3a_deployed` 列表
   - 检查每个 slug 对应的 `wiki/experiments/{slug}.md` 的 status
   - **条件成立**：所有 experiments 的 status == `completed`

2. **若条件不成立**（仍有 running 或 pending-collect 实验）：
   - 输出当前进度：`Pipeline {slug}: {M}/{N} experiments completed`
   - 返回（不推进）
   - cron 将在 30 分钟后再次运行

3. **若条件成立（所有实验已 completed）**：

   a. **输出通知并触发 Stage 4**：
   - 输出：
     ```
     ✅ All experiments completed for pipeline {slug}!
     Advancing to Stage 4 (Verdict & Iteration)...
     ```
   - 追加日志：
     ```bash
     python3 tools/research_wiki.py log wiki/ \
       "exp-status | pipeline {slug}: all experiments done, advancing to stage4"
     ```
   - 触发下一阶段：
     ```
     Skill: research
     Args: "--start-from stage4"
     ```

## Constraints

- **只读非 --collect-ready 模式**：无 `--collect-ready` 时不修改任何 wiki 文件
- **`--auto-advance` 必须配合 `--pipeline`**：单独使用 `--auto-advance` 无效，报错提示
- **状态检查不阻塞**：每个实验的检查应快速完成（单次 SSH check 或 screen -ls）
- **anomaly 不自动修复**：`/exp-status` 只报告 anomaly，修复由用户手动调用 `/exp-run --collect` 处理
- **pipeline-progress.md 必须存在**：`--pipeline` 模式下，文件不存在则报错

## Error Handling

- **无运行中实验（No running experiments）**：友好提示，不报错，给出下一步建议
- **`--pipeline` 但 pipeline-progress.md 不存在**：报错 "Pipeline progress file not found. Run `/research <direction>` first or check wiki/outputs/"
- **`--auto-advance` 无 `--pipeline`**：报错 "–-auto-advance requires --pipeline <slug>"
- **SSH 连接失败**（remote 实验）：标记该实验为 `check_failed`，在报告中注明，继续检查其他实验
- **screen -ls 无输出**：不代表实验失败，可能是轻微延迟；标记为 `completed_pending_collect`
- **`/exp-run --collect` 失败**（`--collect-ready` 模式）：记录失败，继续收集其他实验，最后报告失败列表

## Dependencies

### Skills（via Skill tool）
- `/exp-run` — `--collect-ready` 模式下调用 collect 阶段
- `/research` — `--auto-advance` 触发 Stage 4

### Tools（via Bash）
- `python3 tools/remote.py check --name "exp-{slug}"` — remote 实验状态检查
- `python3 tools/remote.py tail-log --name "exp-{slug}" --lines 20` — remote 日志获取
- `python3 tools/research_wiki.py set-meta <path> <field> <value>` — 更新 pipeline-progress
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `screen -ls` — local 进程状态
- `tail -20 {log}` — local 日志获取

### Agent Runtime Capabilities
- `Read` — 读取实验页面和 pipeline-progress
- `Write` — pipeline-progress 状态更新
- `Glob` — 扫描 wiki/experiments/*.md
- `Bash` — screen/tail 等系统命令
- `Skill` — 调用 /exp-run --collect 和 /research

### Called by
- CronCreate 调度（由 `/research --auto` Stage 3b 创建：每 30 分钟触发一次）
- 用户手动调用
- `/research` Stage 3b（交互模式下建议用户调用）
