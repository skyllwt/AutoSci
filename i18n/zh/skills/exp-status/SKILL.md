---
name: exp-status
description: 查看运行中实验状态；当 agent runtime 能调用 $exp-run 时可收集已完成实验，外部调度器则报告 collect-ready 命令；当 $research 可调用时推进流水线
argument-hint: "[--pipeline <slug>] [--collect-ready] [--auto-advance]"
---

# /exp-status

> 统一的实验状态监控入口。
> 扫描所有 `running` 实验，对每个实验执行实时状态检查（screen session / SSH），
> 输出状态表（alive / anomaly / completed），引导用户下一步操作。
>
> 与 `/research --auto` / `$research --auto` 配合时作为定期检查器。支持调度器的 runtime 可直接调度；Codex 在配置 Codex-native 调度器前，应手动运行 `$exp-status --collect-ready` 或使用外部调度器：
> 当 pipeline 的所有实验都完成时，只有当前 agent runtime 能调用该 skill workflow 时才继续到 `/research --start-from stage4` / `$research --start-from stage4`。外部调度器必须报告 "stage4 ready" 并输出精确恢复命令，不要假装已经调用了 skill。

## Inputs

- 无参数（默认）：检查所有 `running` 实验，输出状态表
- `--pipeline <slug>`（可选）：只检查属于指定 pipeline 的实验，额外输出 pipeline 整体进度
- `--collect-ready`（可选）：对所有"session 已消失"的实验，在当前 agent runtime 可调用 skills 时调用 `/exp-run --collect` / `$exp-run --collect` 收集结果；否则输出精确收集命令并记录 collection ready
- `--auto-advance`（可选，需配合 `--pipeline <slug>`）：若 pipeline 所有实验均已 `completed`，
  在可调用 skill 的 agent runtime 内推进到 `/research --start-from stage4` / `$research --start-from stage4`；否则输出恢复命令并记录 Stage 4 ready

## Outputs

- **状态报告**（终端输出，所有模式）：running/anomaly/completed 三种状态的实验列表
- `wiki/experiments/{slug}.md` — 仅当 `--collect-ready` 实际调用 `/exp-run --collect` / `$exp-run --collect` 时更新（outcome/key_result/status）；外部调度器运行保持实验页面不变并报告收集命令
- `wiki/outputs/pipeline-progress.md` — 仅当 `/research --start-from stage4` / `$research --start-from stage4` 实际被调用时，`--auto-advance` 才会更新 current_stage → stage4；外部调度器运行保持不变并报告恢复命令
- `wiki/log.md` — 追加状态检查日志

## Wiki Interaction

### Reads
- `wiki/experiments/*.md` — status、remote frontmatter（server/session/started）、date_planned
- `wiki/outputs/pipeline-progress.md` — `--pipeline` 模式下识别目标 pipeline 和已部署实验 slug

### Writes
- `wiki/experiments/{slug}.md` — 仅当 active agent runtime 能调用 skills 时，`--collect-ready` 模式下才通过 `/exp-run --collect` / `$exp-run --collect` 触发更新
- `wiki/outputs/pipeline-progress.md` — `--auto-advance` 能调用 Stage 4 时由 `/research` / `$research` 更新；外部调度器的状态检查不直接编辑它
- `wiki/log.md` — 追加状态检查日志

### Graph edges created
- 无（通过 `/exp-run --collect` / `$exp-run --collect` 间接触发的结果写入不产生新 edges）

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

### Step 1: 收集目标实验列表

1. **确定检查范围**：
   - 若指定 `--pipeline <slug>`：
     - 读取 `wiki/outputs/pipeline-progress.md`，提取 `stage3a_deployed` 字段的 slug 列表
     - 若文件不存在或 slug 不匹配：报错，建议先运行 Claude Code 的 `/research` 或 Codex 的 `$research`，或手动指定
   - 否则：
     - 用 Glob 扫描 `wiki/experiments/*.md`，过滤 `status == running` 的实验

2. **若无 running 实验**：
   - 输出友好提示：
     ```
     No running experiments found.
     - To start an experiment: Claude Code 的 `/exp-run <slug>` 或 Codex 的 `$exp-run <slug>`
     - To see all experiments: check wiki/experiments/
     ```
   - 返回

### Step 2: 逐实验状态检查

检查每个目标实验。只有 runtime 能保证各进程检查彼此独立且安全时才并行；
否则顺序执行，这是 Codex-safe 默认路径：

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
$exp-status --collect-ready

# Collect a specific experiment:
/exp-run exp-foo-sanity --collect
$exp-run exp-foo-sanity --collect

# Pipeline progress (if in /research):
/exp-status --pipeline {pipeline-slug}
$exp-status --pipeline {pipeline-slug}
```
```

追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "exp-status | running: {N}, anomaly: {M}, pending-collect: {K}"
```

### Step 4: --collect-ready 收集或报告（若指定）

对每个 `completed_pending_collect` 实验：

1. 若正在 Claude Code 或 Codex 里运行，并且 runtime 能调用另一个 skill workflow，则依次（不并行，避免并发写入 wiki）收集每个完成的实验：
   ```bash
   /exp-run {slug} --collect
   $exp-run {slug} --collect
   ```

2. 若来自外部调度器、CI job 或任何不能调用 skill 的非交互进程，不要编辑 `wiki/experiments/{slug}.md`。为每个 pending 实验输出精确收集命令：
   ```bash
   $exp-run {slug} --collect
   ```
   追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-status | collect-ready: {K} experiments need $exp-run --collect"
   ```

agent-runtime 收集完成后，重新输出更新的状态报告。外部调度器运行则重新输出同一状态报告和收集命令列表。

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

   a. **输出通知，并触发或报告 Stage 4 ready**：
   - 输出：
     ```
     ✅ All experiments completed for pipeline {slug}!
     Stage 4 (Verdict & Iteration) is ready.
     ```
   - 追加日志：
     ```bash
     python3 tools/research_wiki.py log wiki/ \
       "exp-status | pipeline {slug}: all experiments done, stage4 ready"
     ```
   - 若正在 Claude Code 或 Codex 里运行，并且 runtime 能调用另一个 skill workflow，则调用下一阶段：
     ```
     Claude Code: /research --start-from stage4
     Codex:       $research --start-from stage4
     ```
   - 若来自外部调度器、CI job 或任何不能调用 skill 的非交互进程，不要直接编辑 `pipeline-progress.md`。输出并记录精确恢复命令：
     ```bash
     $research --start-from stage4
     ```

## Constraints

- **只读非 --collect-ready 模式**：无 `--collect-ready` 时不修改任何 wiki 文件
- **`--auto-advance` 必须配合 `--pipeline`**：单独使用 `--auto-advance` 无效，报错提示
- **状态检查不阻塞**：每个实验的检查应快速完成（单次 SSH check 或 screen -ls）
- **anomaly 不自动修复**：`/exp-status` / `$exp-status` 只报告 anomaly，修复由用户手动调用 `/exp-run --collect` / `$exp-run --collect` 处理
- **pipeline-progress.md 必须存在**：`--pipeline` 模式下，文件不存在则报错
- **外部调度器不调用 skills**：它们可以输出并记录 collect-ready 命令或 Stage 4 ready，但除非 agent runtime 实际调用了 `$exp-run --collect` 或 `$research --start-from stage4`，否则不得声称已经运行

## Error Handling

- **无运行中实验（No running experiments）**：友好提示，不报错，给出下一步建议
- **`--pipeline` 但 pipeline-progress.md 不存在**：报错 "Pipeline progress file not found. Run `/research <direction>` in Claude Code or `$research <direction>` in Codex first, or check wiki/outputs/"
- **`--auto-advance` 无 `--pipeline`**：报错 "–-auto-advance requires --pipeline <slug>"
- **SSH 连接失败**（remote 实验）：标记该实验为 `check_failed`，在报告中注明，继续检查其他实验
- **screen -ls 无输出**：不代表实验失败，可能是轻微延迟；标记为 `completed_pending_collect`
- **`/exp-run --collect` / `$exp-run --collect` 失败**（agent runtime 内的 `--collect-ready` 模式）：记录失败，继续收集其他实验，最后报告失败列表

## Dependencies

### Skills
- `/exp-run`（Claude Code）或 `$exp-run`（Codex）— 仅当 active agent runtime 能调用 skills 时，`--collect-ready` 模式下调用 collect 阶段
- `/research`（Claude Code）或 `$research`（Codex）— 仅当 active agent runtime 能调用 skills 时，`--auto-advance` 才继续 Stage 4

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
- slash command 或 Codex `$skill` workflow 调用 — 调用 `/exp-run --collect` / `$exp-run --collect`，并在可用时调用 `/research` / `$research`

### Called by
- 可选 runtime 调度器（已配置时）；否则在 Codex 中手动运行或使用外部调度器
- 用户手动调用
- `/research`（Claude Code）或 `$research`（Codex）Stage 3b（交互模式下建议用户调用）
