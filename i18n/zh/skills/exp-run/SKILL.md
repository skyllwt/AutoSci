---
description: 实验执行全流程：准备代码 → 部署运行(运行前需向用户确认，申请用户手动检查) → 监控状态 → 收集结果，支持三种运行模式
argument-hint: <experiment-slug> [--review] [--collect] [--full] [--env local|remote]
---

# /exp-run

> 执行 wiki/experiments/ 中已规划的实验。
> **不论是哪种运行模式，在准备好实验代码，准备部署运行前需向用户确认，申请用户手动检查代码、实验配置(如数据集路径，接口参数选择，API 配置等)相关信息，确认无误后运行，否则需执行修改直到用户确认执行**
> **三种运行模式**，适应不同场景：
> - **默认（deploy）**：仅 Phase 1-2，部署后立即返回，适合需要数小时/天的实验。
> - **`--collect`**：仅 Phase 3-4，检查已部署实验是否完成，完成则收集结果（`--check` 为 alias）。
> - **`--full`**：完整 Phase 1-4，适合几分钟内即可完成的本地快速实验。
>
> 推荐流程：`/exp-run <slug>` 部署 → `/exp-status` 监控 → `/exp-run <slug> --collect` 收集。

## Inputs

- `experiment`：wiki/experiments/ 中的 slug
  - deploy 模式：status 必须为 `planned`
  - --collect 模式：status 必须为 `running`
  - --full 模式：status 必须为 `planned`
- `--review`（可选）：Phase 1 中启用 Review LLM code review 审查实验代码（deploy / full 模式有效）
- `--collect`（可选）：collect 模式——检查实验是否完成，完成则收集结果；`--check` 是 alias
- `--full`（可选）：完整模式——执行全部 4 个 Phase（适合快速本地实验）
- `--env local|remote`（可选，默认 `local`）：部署环境
  - `local`：本机 GPU 直接运行
  - `remote`：通过 SSH 部署到远程机器（需 `config/server.yaml`）

## Outputs

- **deploy 模式**：
  - 实验代码：`experiments/code/{slug}/`（Phase 1 生成）
  - `wiki/experiments/{slug}.md` — status: planned → running
  - **DEPLOY_REPORT**（输出到终端）— 部署确认、session 信息、下一步指引
  - `wiki/log.md` — 追加部署日志
- **collect 模式**（实验已完成时）：
  - `wiki/experiments/{slug}.md` — status: running → completed，填充 outcome/key_result/date_completed
  - **RUN_REPORT**（输出到终端）— 结果摘要、metrics 对比、下一步建议
  - `wiki/log.md` — 追加收集日志
- **collect 模式**（实验仍在运行时）：
  - 仅输出进度报告到终端，不修改 wiki
- **full 模式**：同 deploy + collect 的全部输出

## Wiki Interaction

### Reads
- `wiki/experiments/{slug}.md` — 实验配置：setup、metrics、baseline、hypothesis、linked_idea
- `wiki/ideas/{linked-idea}.md` — 关联 idea 的 approach sketch（指导代码实现，理解实验目的）
- `wiki/papers/*.md` — 相关论文的方法细节和超参数（参考实现）
- `wiki/experiments/*.md` — 同一 idea 的其他实验（参考 setup、避免重复错误）

### Writes
- `experiments/code/{slug}/` — 实验代码目录（Phase 1 生成，deploy / full 模式）
  - `experiments/code/{slug}/train.py` — 主训练/推理脚本
  - `experiments/code/{slug}/config.yaml` — 超参数配置文件
  - `experiments/code/{slug}/run.sh` — 启动封装脚本（含 CUDA_VISIBLE_DEVICES 等）
  - `experiments/code/{slug}/requirements.txt` — 依赖（若与主项目不同）
- `wiki/experiments/{slug}.md` — 更新 status、outcome、key_result、date_completed、run_log、remote 块（deploy / collect 模式）
- `wiki/log.md` — 追加操作日志

### Graph edges created
- **无**。实验与 idea 之间的 tested_by 边已在 /exp-design 中创建。

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

---

### Deploy 模式（默认，status == planned）

**Phase 1: 准备（Prepare）**

1. **读取实验页面**：
   - `wiki/experiments/{slug}.md`：提取 setup（model, dataset, hardware, framework）、metrics、baseline、hypothesis
   - 验证 status == `planned`
   - 若 status 为 `running`，提示用户使用 `--collect` 模式
   - 若 status 为 `completed`/`abandoned`，拒绝执行

2. **加载实现上下文**：
   - 读取关联 idea 的 approach sketch（实现指南）
   - 读取相关论文的方法描述（算法细节）
   - 读取同一 idea 的其他实验（参考代码结构）

3. **检验数据集以及其余配置**
   - 数据集在`wiki/experiments/{slug}.md`的setup 中有指定
   - 获取数据集路径(根据 --env 参数选择在本地或远程获取)，**可向用户询问本地(远程)的数据集的路径以及自行检索**
   - 若 数据集不存在，向用户提示，明确**下载数据集的需求**，向用户确认**安装路径**及**下载渠道**
   - 检查数据集是否完整、可用，明确数据集附带的一些结构、使用说明
   - 其余配置如：调用LLM的模型名称，url，api key等

4. **编写实验代码**，统一写入 `experiments/code/{slug}/`：
   **代码的编写模块化思想，除非实验规模较小，逻辑简单，否则不要把大量代码放在一个文件里**
   - `train.py`：根据 setup 配置生成训练/评估脚本，作为程序的入口，包含：
     - 参数解析（argparse，所有超参数可配置）
     - 数据加载（支持 setup.dataset）
     - 模型初始化（支持 setup.model 和 baseline 模型）
     - 训练/推理循环
     - 指标计算（对应 metrics 列表）
     - 结果保存（JSON 格式，路径：`results/{slug}/seed_{N}.json`）
     - 随机种子控制（多 seed 运行）
     - Checkpoint 保存/恢复（`checkpoints/{slug}/`）
   - 其余所需的utils、tools 等代码文件夹或者文件（如 `utils.py`、`data_loader.py` 等）
   - `config.yaml`：所有超参数（learning_rate, batch_size, epochs, seeds 等）
   - `run.sh`：封装完整启动命令（含 CUDA_VISIBLE_DEVICES、logging、conda 激活）
   - `requirements.txt`：实验专属依赖（若与主项目 requirements 不同）

5. **可选 Review LLM code review**（`--review`）：
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
   根据 Review LLM 反馈修正代码。

6. **Sanity check（小规模验证）**：
   - 用极小规模运行（1 epoch / 100 steps / 小 subset）
   - 验证：代码无 crash、数据加载正确、GPU 可用、loss 下降
   - 若 sanity 失败 → 修复代码，重试一次；仍然失败则报告错误并停止


**Gate： 用户手动检查**

> **注意**：在准备好实验代码，准备部署运行前需向用户确认，申请用户手动检查代码、实验配置(数据集路径，接口参数选择，API 配置等)相关信息，确认无误后运行，否则需执行修改直到用户确认执行


**Phase 2: 部署（Deploy）**

#### Local 模式（`--env local` 或默认）

1. **检查 GPU**：`nvidia-smi` 确认 GPU 可用、显存足够。若 `setup.hardware` 为 `cpu`/`none`/空且生成代码无 CUDA/GPU 关键字，跳过 GPU 检查直接进入步骤 2。
2. **启动**：
   ```bash
   screen -dmS exp-{slug} bash -c \
     "cd $(pwd) && bash experiments/code/{slug}/run.sh 2>&1 | tee logs/exp-{slug}.log"
   ```
3. 更新 `wiki/experiments/{slug}.md`：
   - status: `running`
   - run_log: `logs/exp-{slug}.log`
4. **估算运行时长**，写入 frontmatter：
   根据 `setup.hardware`（GPU 型号/数量）、`setup.model`（参数量）、`setup.dataset`（规模）合理估算：

   | 典型场景 | 估算范围 |
   |----------|----------|
   | 单 GPU + 小数据集（CIFAR / 小 NLP benchmark） | 0.5 – 3h |
   | 单 A100 + 中等数据集（ImageNet / GLUE） | 4 – 12h |
   | 多 GPU 或大模型 fine-tuning（≥7B） | 8 – 48h |

   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md started "{YYYY-MM-DDTHH:MM}"
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md estimated_hours {N}
   ```
5. 追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | deployed {slug} | env: local | session: exp-{slug} | eta: {N}h"
   ```

#### Remote 模式（`--env remote`）

**前提**：用户已配置 `config/server.yaml`。

1. **确认连通**：`python3 tools/remote.py status`
   - 若不可达 → 报错并建议检查 config/server.yaml
2. **查找空闲 GPU**：`python3 tools/remote.py gpu-status`（若 `setup.hardware` 为 `cpu`/`none`/空且代码无 CUDA/GPU 关键字则跳过）
   - 若无空闲 GPU → 报告各 GPU 占用情况，建议等待
3. **同步代码**：`python3 tools/remote.py sync-code`
4. **安装依赖**（首次或 requirements 有变化）：`python3 tools/remote.py setup-env`
5. **启动远程实验**：
   ```bash
   python3 tools/remote.py launch \
     --name "exp-{slug}" \
     --cmd "bash experiments/code/{slug}/run.sh" \
     --gpu {gpu_index}
   ```
6. 更新 `wiki/experiments/{slug}.md` frontmatter —— 以下字段已由 /exp-design 写入完整 CLAUDE.md 模板,都是空值:
   ```bash
   # 顶层 scalar 字段 —— 用 set-meta
   python3 tools/research_wiki.py set-meta wiki/experiments/{slug}.md status running
   python3 tools/research_wiki.py set-meta wiki/experiments/{slug}.md run_log "logs/exp-{slug}.log"
   ```

   嵌套 `remote:` 块无法通过 `set-meta` 更新（set-meta 只处理顶层 scalar 字段）。直接用 `Edit` 工具就地替换这五个空的子字段值。文件里已有的 block 形如：
   ```yaml
   remote:
     server: ""
     gpu: ""
     session: ""
     started: ""
     completed: ""
   ```
   用 5 次 Edit 调用（每个子字段一次）设置 `server`、`gpu`、`session`、`started`。`completed: ""` 留空由 Phase 4 填写。如果发现文件里没有 `remote:` block,说明 /exp-design 没写完整的 CLAUDE.md 模板;停下来报 bug,不要在这里追加 block（追加会让字段顺序偏离 canonical 模板,破坏后续 edit 的匹配）。
7. **估算运行时长**，写入 frontmatter（同 local 模式估算逻辑）：
   ```bash
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md started "{YYYY-MM-DDTHH:MM}"
   python3 tools/research_wiki.py set-meta \
     wiki/experiments/{slug}.md estimated_hours {N}
   ```
8. 追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | deployed {slug} | env: remote | server: {host} | gpu: {gpu} | eta: {N}h"
   ```

**输出 DEPLOY_REPORT 到终端**：

```markdown
# Deploy Report: {experiment title}

### Status: DEPLOYED ✅

- Session: exp-{slug}
- Environment: local | remote ({host} GPU {gpu})
- Log file: logs/exp-{slug}.log
- Code: experiments/code/{slug}/
- Estimated: ~{N}h（预计完成于 {YYYY-MM-DD HH:MM}）

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

### Collect 模式（`--collect` 或 `--check`，status == running）

**Phase 3: 监控/检查运行状态（Monitor）**

1. **读取部署信息**：从 `wiki/experiments/{slug}.md` frontmatter 获取环境（local 或 remote）和 session 名。

2. **检查进程是否还活着**：
   - **Local**：`screen -ls | grep exp-{slug}`
   - **Remote**：`python3 tools/remote.py check --name "exp-{slug}"`，解析 `alive` 字段

3. **若实验仍在运行（alive == true）**：
   - 获取最近日志：
     - Local：`tail -30 logs/exp-{slug}.log`
     - Remote：`python3 tools/remote.py tail-log --name "exp-{slug}" --lines 30`
   - **异常检测**：
     - NaN loss：检测 `loss: nan`
     - OOM：`CUDA out of memory`
     - Traceback：Python 异常堆栈
     - Inf loss：`loss: inf`
   - **自动修复尝试**（若检测到异常，最多 1 次）：
     - NaN/爆炸 → 从最近 checkpoint 恢复，降低学习率
     - OOM → 减小 batch size，重启
   - **输出进度报告**（不修改 wiki，仅报告）：
     ```
     Experiment {slug}: RUNNING
     Progress: step {N} / epoch {E}
     Latest metric: {metric} = {value}
     Anomalies: {none | NaN detected | ...}
     Estimated remaining: ~{N} hours
     Run `/exp-status` to monitor all running experiments.
     ```
   - **返回**（不执行 Phase 4）

4. **若实验已完成（alive == false / session gone）**：
   - 继续执行 Phase 4

**Phase 4: 收集结果（Collect Results）**

1. **拉取远程结果**（仅 remote 模式）：
   ```bash
   python3 tools/remote.py pull-results \
     --remote-path "results/{slug}/" \
     --local-path "./results/{slug}/"

   python3 tools/remote.py pull-results \
     --remote-path "logs/exp-{slug}.log" \
     --local-path "./logs/"
   ```

2. **检查结果文件存在**：`results/{slug}/seed_*.json`

3. **解析结果**：
   - 读取结果文件（JSON）
   - 计算每个 metric 的 mean ± std（跨 seeds）
   - 与 baseline 对比，计算提升幅度

4. **更新实验页面** `wiki/experiments/{slug}.md`：
   - status: `completed`
   - outcome: `succeeded` / `failed` / `inconclusive`
     - succeeded：所有 success criteria 满足
     - failed：核心指标未达标
     - inconclusive：结果混合或方差过大
   - key_result: 一句话总结核心发现
   - date_completed: 今天日期
   - 填充 `## Results` section：完整结果表格
   - 填充 `## Analysis` section：初步分析
   - 若 remote 模式：更新 `remote.completed` 时间戳

5. **追加日志**：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-run | completed {slug} | outcome: {outcome} | key: {key_result}"
   ```

6. **输出 RUN_REPORT 到终端**：
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

### Full 模式（`--full`，status == planned）

依次执行全部 4 个 Phase（Phase 1 → Phase 2 → Phase 3 → Phase 4），中间不返回。

适用场景：本地 CPU/GPU 几分钟内可完成的快速实验（sanity check、toy dataset 验证等）。

Phase 3 中不需要先检查 "是否还在运行"，而是等待 screen session 真正结束后再执行 Phase 4：
```bash
# 等待 session 结束（轮询）
while screen -ls | grep -q "exp-{slug}"; do
  sleep 30
done
# session 消失，进入 Phase 4
```

---

## Constraints

- **deploy 模式只接受 planned 实验**：若 status 为 running，提示使用 --collect；若为 completed，拒绝执行
- **collect 模式只接受 running 实验**：若 status 为 planned，提示先 deploy；若为 completed，提示已完成
- **collect 模式：alive 时不写 wiki**：仅报告进度，不修改任何 wiki 文件
- **代码统一写入 experiments/code/{slug}/**：不写到项目根目录或其他位置
- **不修改 idea 状态**：实验结果只写入 experiments/ 页面；idea 的 status 由 /exp-eval 负责更新
- **sanity check 必须通过**：Phase 1 sanity 失败则不部署（除非用户明确 override）
- **结果文件必须保存**：所有实验结果以 JSON 格式保存在 `results/{slug}/seed_{N}.json`
- **多 seed 结果取均值**：报告 mean ± std，不报告单次运行
- **graph edges 不在此 skill 创建**：tested_by 边已在 /exp-design 中创建
- **自动修复最多尝试 1 次**：防止无限重启循环

## Error Handling

- **experiment 找不到**：提示用户检查 slug，列出 wiki/experiments/ 中的候选（status=planned 或 running）
- **deploy 模式但 status == running**：提示 "已在运行中，使用 `/exp-run {slug} --collect` 检查状态"
- **collect 模式但 status == completed**：提示 "已完成，直接运行 `/exp-eval {slug}`"
- **GPU 不可用**：报告错误，建议用 --env remote 或等待 GPU 释放
- **Review LLM 不可用**（--review 模式）：跳过 code review，在 DEPLOY_REPORT 中标注「unreviewed」
- **sanity check 失败**：详细报告错误信息，尝试自动修复一次，仍失败则停止并建议手动调试
- **远程连接失败**：报告 SSH 错误，建议检查连接配置和 config/server.yaml
- **结果文件缺失**（collect 模式）：报告哪些 seeds 缺失结果，对已有结果正常汇总；若成功 seeds < 2 则标记 inconclusive
- **实验 crash**（collect 模式检测到 traceback）：在报告中附上 crash 信息和建议修复方向
- **--full 模式等待超时**：若 screen session 超过预期时间的 2x 仍存在，警告用户但不强制终止

## Dependencies

### Skills（via Skill tool）
- 无直接调用子 skill

### Tools（via Bash）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志
- `python3 tools/remote.py <command>` — 远程操作（status, gpu-status, sync-code, setup-env, launch, check, tail-log, pull-results）
- `nvidia-smi` — 本地 GPU 状态
- `screen` — 本地后台运行管理

### Configuration
- `config/server.yaml` — 远程服务器配置（仅 `--env remote` 时需要）

### MCP Servers
- `mcp__llm-review__chat` — Phase 1 代码审查（可选，`--review` 时使用）

### Claude Code Native
- `Read` — 读取 wiki 页面和日志文件
- `Write` — 写入 `experiments/code/{slug}/` 下的实验代码
- `Bash` — 执行部署命令、监控进程

### Called by
- `/research` Stage 3a（deploy 模式）和 Stage 3c（collect 模式）
- `/exp-status --collect-ready`（collect 模式）
- 用户手动调用
