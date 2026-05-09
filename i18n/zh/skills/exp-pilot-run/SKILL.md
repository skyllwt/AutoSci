---
description: 预实验执行 — 读取 Pilot Spec YAML，撰写预实验代码，运行实验，返回结果。由 /ideate Phase 5 调用。不修改 wiki 页面，不判定 pass/fail。
argument-hint: <idea-slug> [--env local|remote]
---

# /exp-pilot-run

> 执行由 Pilot Spec YAML 文件描述的预实验。
> 从 `wiki/experiments/pilot/{slug}.yaml` 读取 spec，撰写预实验代码，运行实验，返回原始结果给调用者。
> 支持 **local**（本地 GPU）和 **remote**（通过 `tools/remote.py` SSH 部署）两种模式。
> 不修改任何 wiki 页面。不判定 pass/fail — 结果由 `/exp-pilot-eval` 评估。

## Inputs

- `idea-slug`：用于定位 `wiki/experiments/pilot/{slug}.yaml` 的 slug
- `--env local|remote`（可选，默认 `local`）：部署环境
  - `local`：在本地 GPU 直接运行
  - `remote`：通过 SSH 部署到远程机器（需要 `config/server.yaml`）

## Outputs

- 预实验代码：`wiki/experiments/pilot/code/{slug}/`（train.py, config.yaml, run.sh, requirements.txt）
- 预实验结果：`wiki/experiments/pilot/code/{slug}/results/seed_{N}.json`
- 预实验日志：`wiki/experiments/pilot/code/{slug}/pilot.log`
- **PILOT_REPORT**（输出到终端）— 结果表格、运行详情、异常
- 轮询日志：`wiki/experiments/pilot/{slug}/check.md`（监控期间实时进度更新）
- 返回原始结果和关键指标给调用者
- 不修改任何 wiki 页面

## Wiki Interaction

### Reads
- `wiki/experiments/pilot/{slug}.yaml` — Pilot Spec（所有配置）
- `wiki/papers/*.md` — 相关论文的方法描述（实现参考）

### Writes
- `wiki/experiments/pilot/code/{slug}/` — 预实验代码目录
  - `wiki/experiments/pilot/code/{slug}/train.py` — 主训练/评估脚本
  - `wiki/experiments/pilot/code/{slug}/config.yaml` — 超参数配置文件
  - `wiki/experiments/pilot/code/{slug}/run.sh` — 启动封装脚本
  - `wiki/experiments/pilot/code/{slug}/requirements.txt` — 依赖
  - `wiki/experiments/pilot/code/{slug}/results/seed_{N}.json` — 结果文件
  - `wiki/experiments/pilot/code/{slug}/pilot.log` — 运行日志
- `wiki/experiments/pilot/{slug}/check.md` — 轮询进度日志（监控期间更新）

### Graph edges created
- 无。预实验不创建 graph edges。

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

---

**Phase 1: 准备**

1. **读取 Pilot Spec**：
   - 加载 `wiki/experiments/pilot/{slug}.yaml`
   - YAML 有 `pilot_spec:` 根键；所有字段嵌套在其下
   - 验证 `pilot_spec:` 下必填字段存在：`implementation`、`setup`、`metrics`、`baseline`、`success_criterion`
   - 从 `pilot_spec:` 提取：repo、entry_point、modifications、files_to_create、setup（model, dataset, hardware, framework, batch_size, max_steps, learning_rate, seeds, other_hparams）、metrics、baseline、success_criterion、hypothesis、approach_sketch

2. **加载实现上下文**：
   - 使用 `pilot_spec.hypothesis` 和 `pilot_spec.approach_sketch` 作为主要实现指南（idea 页面由 `/ideate` Phase 4 在预实验之前写入）
   - 读取相关论文的方法描述（算法细节，来自 `wiki/papers/` 若存在）
   - 读取源论文 repo 获取基础代码参考

3. **编写预实验代码**，写入 `wiki/experiments/pilot/code/{slug}/`：

   > **预实验目的提醒**：目标是**检测明显失败**（发散、严重退化、根本性不兼容），**不是衡量最终性能**。遵循 Pilot Spec 的缩减配置：batch size = 论文的 1/4–1/8，训练步数 = 完整训练的 10–30%，以便通过较低成本在一定程度上判定idea执行的价值，始终包含 baseline 对比。不要试图优化取得最优结果 — 通过预实验仅意味着"没有明显崩溃""从前中期整体表现看,相较baseline，有提升，基本持平，略差都是可以接受的"。

   预实验代码可能参考的路径:
   - A路径：可能是在原本的method的论文的repo，基于这个repo进行修改得到预实验代码
   - B路径：基于有机融合的idea实现组合版（比如看性能/cost是不是达到balance）
   - C路径：检测共性盲点，打破假设基于新设定，看现有方法在新设定下是不是都失败

   - `train.py`：根据 Pilot Spec 的 `setup` 配置生成训练/评估脚本，包含：
     - 参数解析（argparse，spec 中所有超参数可配置）
     - 数据加载（支持 spec 的 `setup.dataset`）
     - 模型初始化（支持 spec 的 `setup.model` 和 baseline 模型）
     - 训练/推理循环（遵循 `setup.max_steps` 缩短训练）
     - 指标计算（对应 spec 的 `metrics` 列表）
     - 结果保存（JSON 格式，路径：`wiki/experiments/pilot/code/{slug}/results/seed_{N}.json`）
     - 随机种子控制
   - `config.yaml`：spec 中的所有超参数（learning_rate, batch_size, max_steps 等）
   - `run.sh`：启动封装脚本（含 CUDA_VISIBLE_DEVICES、logging、conda 激活）
   - `requirements.txt`：依赖（若与主项目不同）

4. **Sanity check（小规模验证）**：
   - 用极小规模运行（10 steps / 小 subset）
   - 验证：代码无 crash、数据加载正确、GPU 可用、loss 有限
   - 若 sanity 失败 → 修复代码，重试一次；仍然失败则报告错误并停止

**Phase 2: 运行**

> **预实验目的提醒**：这是一次**短期诊断性运行** — 不是完整实验。运行应快速完成（缩减步数）。若发散或挂起超过预期时间的 2x，这本身就是一个有用的信号。直接报告；不要尝试挽救性重跑。

#### 本地模式（`--env local` 或默认）

1. **检查 GPU**：`nvidia-smi` 确认 GPU 可用、显存足够
2. **估算运行时间**：根据 `setup.hardware`（GPU 型号）、`setup.model`（参数量）、`setup.dataset`（规模）和 `setup.max_steps`（缩减步数）：

   | 典型预实验场景 | 预估时长 |
   |---------------|---------|
   | 单 GPU + 小数据集（CIFAR / 小型 NLP benchmark） | 5 – 30 分钟 |
   | 单 A100 + 中等数据集（ImageNet / GLUE） | 30 分钟 – 2 小时 |
   | 多 GPU 或大模型微调（≥7B） | 1 – 4 小时 |

   轮询间隔设为预估时长的 ~5%，限制在 [120s, 900s]：

   | 预估时长 | 轮询间隔 |
   |---------|---------|
   | < 30 分钟 | 120s（2 分钟） |
   | 30 分钟 – 2 小时 | 300s（5 分钟） |
   | 2 – 4 小时 | 600s（10 分钟） |
   | > 4 小时 | 900s（15 分钟） |

3. **启动**：
   ```bash
   screen -dmS pilot-{slug} bash -c \
     "cd $(pwd) && bash wiki/experiments/pilot/code/{slug}/run.sh 2>&1 | tee wiki/experiments/pilot/code/{slug}/pilot.log"
   ```
   - 提醒用户："预实验已启动。轮询进度将写入 `wiki/experiments/pilot/{slug}/check.md`"

4. **监控直到完成**：
   - 初始化 `wiki/experiments/pilot/{slug}/check.md`，写入头部信息（时间戳、slug、预估时长、轮询间隔）
   - 轮询 screen session 并 tail 日志以跟踪进度和检测异常：
     ```bash
     while screen -ls | grep -q "pilot-{slug}"; do
       tail -5 wiki/experiments/pilot/code/{slug}/pilot.log
       sleep {轮询间隔秒数}
     done
     ```
   - **异常检测**（每次轮询时检查）：
     - NaN loss：检测 `loss: nan` 或指标输出中的 `nan`
     - OOM：`CUDA out of memory` 或 `torch.cuda.OutOfMemoryError`
     - Traceback：Python 异常堆栈
     - Inf loss：`loss: inf` 或指标输出中的 `inf`
     - 发散：loss 未有收敛趋势(持续增长或震荡)
   - **若检测到异常**：记录异常，继续监控（不要 kill 进程 — 让它自行恢复或崩溃，两者都是有用信号）。记录异常供最终报告使用。
   - **若 session 超过预期运行时间的 2x 仍存在**：警告用户但不强制终止 — 挂起的 pilot 本身就是有用的诊断信号。
   - **进度报告**（每次轮询时追加到 `wiki/experiments/pilot/{slug}/check.md`，不输出到终端）：
     ```
     ## {timestamp}
     - 步数: {current_step} / {max_steps}
     - 最新 loss: {value}
     - 异常: {无 | 检测到 NaN | 检测到 OOM | ...}
     - 预计剩余: ~{N} 分钟
     ```

#### 远程模式（`--env remote`）

**前置条件**：用户已配置 `config/server.yaml`。

1. **确认连接**：`python3 tools/remote.py status`
   - 若不可达 → 报告错误，建议检查 `config/server.yaml`

2. **查找空闲 GPU**：`python3 tools/remote.py gpu-status`
   - 若无空闲 GPU → 报告各 GPU 使用情况，建议等待或使用 `--env local`

3. **同步代码**：`python3 tools/remote.py sync-code`
   - 将 pilot 代码目录推送到远程 `work_dir`

4. **估算运行时间**（与本地模式相同的估算逻辑 — 参见上方表格）
   - 按比例设定轮询间隔（同一表格）

5. **安装依赖**（首次或 requirements 变更时）：
   ```bash
   python3 tools/remote.py setup-env --requirements wiki/experiments/pilot/code/{slug}/requirements.txt
   ```

6. **启动远程预实验**：
   ```bash
   python3 tools/remote.py launch \
     --name "pilot-{slug}" \
     --cmd "bash wiki/experiments/pilot/code/{slug}/run.sh" \
     --gpu {gpu_index} \
     --log-file "wiki/experiments/pilot/code/{slug}/pilot.log"
   ```
   - 提醒用户："预实验已启动（远程）。轮询进度将写入 `wiki/experiments/pilot/{slug}/check.md`"

7. **监控直到完成**：
   - 初始化 `wiki/experiments/pilot/{slug}/check.md`，写入头部信息（时间戳、slug、预估时长、轮询间隔、环境：远程）
   - 轮询远程 session 并 tail 日志：
     ```bash
     while true; do
       python3 tools/remote.py check --name "pilot-{slug}"
       python3 tools/remote.py tail-log --name "pilot-{slug}" --lines 10
       sleep {轮询间隔秒数}
     done
     ```
   - `remote.py check` 已内置异常检测（NaN、OOM、traceback、infinite loss）并在 session 结束时报告 `exit_reason`。
   - **若检测到异常**：记录异常，继续监控。记录异常供最终报告使用。
   - **若 session 超过预期运行时间的 2x 仍存在**：警告用户但不强制终止。
   - **进度报告**（每次轮询时追加到 `wiki/experiments/pilot/{slug}/check.md`，不输出到终端）：
     ```
     ## {timestamp}
     - 最新日志: {tail 输出}
     - 异常: {check 输出}
     - 预计剩余: ~{N} 分钟
     ```
   - 当 `remote.py check` 报告 `alive == false`（session 已结束）时退出监控循环。

**Phase 3: 收集与报告**

1. **验证运行完成**：确认 screen session `pilot-{slug}` 已结束。若监控后仍在运行，报告并等待。

2. **拉取远程结果**（仅远程模式）：
   ```bash
   python3 tools/remote.py pull-results \
     --remote-path "wiki/experiments/pilot/code/{slug}/results/" \
     --local-path "./wiki/experiments/pilot/code/{slug}/results/"

   python3 tools/remote.py pull-results \
     --remote-path "wiki/experiments/pilot/code/{slug}/pilot.log" \
     --local-path "./wiki/experiments/pilot/code/{slug}/"
   ```
   若部分文件拉取失败 → 报告缺失的文件，继续使用可用数据。

3. **检查结果文件**：`wiki/experiments/pilot/code/{slug}/results/seed_*.json`
   - 列出可用的结果文件
   - 若无结果文件存在 → 报告错误 "未产生结果文件（运行可能已崩溃）"
   - 若结果文件存在但不完整（部分 seeds）→ 使用可用 seeds，在报告中注明

4. **读取预实验日志**：`wiki/experiments/pilot/code/{slug}/pilot.log`
   - 扫描错误、警告、OOM、发散信号
   - 提取运行时行为上下文供最终报告
   - 记录 Phase 2 监控期间检测到的异常

5. **解析结果**：
   - 读取每个结果文件（JSON）
   - 计算每个 metric 的 mean ± std（跨 seeds）
   - 与 baseline 的 `expected_value`（来自 Pilot Spec）对比
   - 计算 delta：`pilot_mean - baseline_expected`

6. **输出 PILOT_REPORT 到终端**：
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
   - Log: wiki/experiments/pilot/code/{slug}/pilot.log

   ## Anomalies
   - {运行期间检测到的异常列表，或"无"}

   ## Next Steps
   - 进入 /exp-pilot-eval 进行判定评估和 wiki 更新
   ```

7. **返回**原始结果和关键指标给调用者（如 `/ideate` Phase 5）。**不修改任何 wiki 页面** — 预实验结果由 `/exp-pilot-eval` 评估，不由本 skill 负责。

## Constraints

- **不需要 wiki 实验页面**：从 `wiki/experiments/pilot/{slug}.yaml` 读取配置
- **不写入 wiki 页面**：结果返回给调用者；idea 页面更新由 `/exp-pilot-eval` 负责
- **代码统一写入 `wiki/experiments/pilot/code/{slug}/`**：不写到项目根目录或其他位置
- **结果文件必须保存**：所有预实验结果以 JSON 格式保存在 `wiki/experiments/pilot/code/{slug}/results/seed_{N}.json`
- **多 seed 结果取均值**：报告 mean ± std，不报告单次运行
- **sanity check 必须通过**：Phase 1 sanity 失败则报告错误并停止（除非用户明确 override）
- **graph edges 不在此 skill 创建**：预实验不创建 graph edges
- **自动修复最多尝试 1 次**：防止无限重启循环

## Error Handling

- **Pilot Spec 找不到**：报告错误，建议先运行 `/ideate` 生成 spec
- **Pilot Spec 缺少字段**：报告缺失的必填字段，建议重新运行 `/ideate`
- **GPU 不可用**：报告错误，建议等待 GPU 释放
- **sanity check 失败**：详细报告错误信息，尝试自动修复一次，仍失败则报告错误并停止
- **结果文件缺失**：报告错误 "未产生结果文件（运行可能已崩溃）"
- **screen session 超时**：若 session 超过预期时间的 2x 仍存在，警告用户但不强制终止
- **远程连接失败**：报告 SSH 错误，建议检查连接配置和 `config/server.yaml`
- **远程 GPU 不可用**：报告各 GPU 使用情况，建议等待或使用 `--env local`
- **远程结果拉取失败**：报告缺失的文件，继续使用可用的本地数据

## Dependencies

### Skills (via Skill tool)
- 无

### Tools (via Bash)
- `nvidia-smi` — 本地 GPU 状态
- `screen` — 本地后台运行管理
- `python3 tools/remote.py <command>` — 远程操作（status, gpu-status, sync-code, setup-env, launch, check, tail-log, pull-results）

### Configuration
- `config/server.yaml` — 远程服务器配置（仅 `--env remote` 时需要）

### Claude Code Native
- `Read` — 读取 Pilot Spec 和 wiki 页面
- `Write` — 写入预实验代码到 `wiki/experiments/pilot/code/{slug}/`
- `Bash` — 执行预实验代码、监控进程

### Called by
- `/ideate` Phase 5
- 用户手动调用
