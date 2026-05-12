---
description: 实验执行全流程：准备代码 → 部署运行 → 监控状态 → 收集结果，支持三种运行模式
argument-hint: <experiment-slug> [--review] [--collect] [--full] [--env local|remote]
---

# /exp-run

> 执行 wiki/experiments/ 中已规划的实验。
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
- `experiments/code/{slug}/` — 实验代码目录（Phase 1 生成，deploy / full 模式）。布局按实验 A5-full setup 字段决定（bio-C7 minimal pilot 2026-05-12 合并），路由规则与每种布局的文件清单见 Phase 1 Step 3：
  - **ML 布局**（默认）：`train.py`、`config.yaml`、`run.sh`、`requirements.txt`
  - **MD 布局**（`setup.assay_type` 匹配 `\bMD\b|molecular dynamics`）：`mdrun.sh`、`system.{gro,pdb}`、`system.top`、`mdp/{em,nvt,npt,md}.mdp`、`analyze.py`、`requirements.txt`
  - **Docking 布局**（`setup.assay_type` 含 `docking`）：`dock.sh`、`receptor.pdb`、`ligands.sdf`、`config.yaml`、`analyze.py`、`requirements.txt`
  - **Wet-lab 布局**（`setup.in_silico_or_wet == "wet_lab"`）：`protocol.md`、`analysis.ipynb`、`data/`、`figures/`、`requirements.txt`
- `wiki/experiments/{slug}.md` — 更新 status、outcome、key_result、date_completed、run_log、remote 块
- `wiki/log.md` — 追加操作日志

### Graph edges created
- **无**。实验与 idea 之间的 tested_by 边已在 /exp-design 中创建。

## Workflow

**前置**：确认工作目录为 wiki 项目根（包含 `wiki/`、`raw/`、`tools/` 的目录）。

---

### Deploy 模式（默认，status == planned）

**Phase 1: 准备（Prepare）**

1. **读取实验页面**：
   - `wiki/experiments/{slug}.md`：提取 setup（model, dataset, hardware, framework）、metrics、baseline、hypothesis。存在时一并读取 A5-full bio 字段：`setup.in_silico_or_wet`、`setup.assay_type`、`setup.force_field`、`setup.solvent_model`、`setup.simulation_length`、`setup.species`、`setup.cell_line`、`setup.weight_version`、`setup.random_seed_protocol` —— 这些驱动 Step 3 的 setup-type 路由（bio-C7 minimal pilot）。
   - 验证 status == `planned`
   - 若 status 为 `running`，提示用户使用 `--collect` 模式
   - 若 status 为 `completed`/`abandoned`，拒绝执行

2. **加载实现上下文**：
   - 读取关联 idea 的 approach sketch（实现指南）
   - 读取相关论文的方法描述（算法细节）
   - 读取同一 idea 的其他实验（参考代码结构）

3. **编写实验代码**，写入 `experiments/code/{slug}/`。

   **Setup-type 路由**（bio-C7 minimal pilot 2026-05-12 合并）—— 按 A5-full setup 字段选布局：

   ```
   if setup.in_silico_or_wet == "wet_lab":                  → wet-lab 布局
   elif setup.assay_type 匹配 \bMD\b|molecular dynamics:    → MD 布局
   elif setup.assay_type 含 "docking":                       → docking 布局
   else（默认,含 in_silico/mixed 但非 MD/docking,或字段空）：→ ML 布局（current）
   ```

   `setup.in_silico_or_wet == "mixed"` 时,默认按 in-silico 路由;湿实验侧非平凡时再 scaffold 一个并列的 `wet-lab/` 子目录。

   **ML 布局**（默认 —— 向后兼容）：
   - `train.py`：训练/评估脚本（argparse;按 `setup.dataset` 加载数据;按 `setup.model` 与 baseline 初始化模型;训练/推理循环;指标计算;JSON 结果保存到 `results/{slug}/seed_{N}.json`;多 seed 控制;Checkpoint 在 `checkpoints/{slug}/`）
   - `config.yaml`：全部超参数（learning_rate、batch_size、epochs、seeds、……）
   - `run.sh`：启动封装（CUDA_VISIBLE_DEVICES、logging、conda 激活）
   - `requirements.txt`：实验专属依赖

   **MD 布局**（`setup.assay_type` 匹配 MD 时）：
   - `mdrun.sh`：启动封装 —— 按 `setup.framework` 选 GROMACS（`gmx grompp` + `gmx mdrun`）或 OpenMM Python runner;力场参数来自 `setup.force_field`;模拟时长来自 `setup.simulation_length`;seed 预算来自 `setup.random_seed_protocol`
   - `system.gro`（GROMACS）或 `system.pdb`（OpenMM / 通用）：初始结构;PROTAC 三元复合体应在内联注释中标出源 PDB / AlphaFold-DB 版本
   - `system.top`：与 `setup.force_field` 一致的 topology（如 phospho 残基 MD 用 AMBER ff14SB + phosaa14SB）
   - `mdp/em.mdp`、`mdp/nvt.mdp`、`mdp/npt.mdp`、`mdp/md.mdp`（GROMACS）：能量最小化 + 等温等容 + 等温等压 + 生产参数;production 长度与 `setup.simulation_length` 一致。OpenMM 时改为单一 `system_setup.py` 构造 System。
   - `analyze.py`：轨迹分析（RMSD / RMSF / 残基距离 / 界面 SASA,按 hypothesis 选）;JSON 结果写到 `results/{slug}/seed_{N}.json` 保持下游 `/exp-eval` consumer shape 一致
   - `requirements.txt`：GROMACS / OpenMM / MDAnalysis / mdtraj 任一

   **Docking 布局**（`setup.assay_type` 含 "docking" 时）：
   - `dock.sh`：启动封装 —— 按 `setup.framework` 选 AutoDock Vina / Glide / DiffDock;读 receptor + ligand,按 `setup.random_seed_protocol` 多 seed 运行,写 per-pose 分数
   - `receptor.pdb`：预处理 receptor（一般是 POI;PROTAC docking 时是 Boltz-2 / AlphaFold-3 给出的 POI + E3 复合体）
   - `ligands.sdf`：docking 化合物库（单或批）
   - `config.yaml`：docking 参数（搜索盒中心 + 大小、exhaustiveness、scoring function、输出数）
   - `analyze.py`：pose 排序 + 聚类;按 ML / MD route 一致的 shape 写 `results/{slug}/seed_{N}.json`
   - `requirements.txt`：docking 框架 + RDKit + 分析库

   **Wet-lab 布局**（`setup.in_silico_or_wet == "wet_lab"` 时）：
   - `protocol.md`：完整流程 —— 试剂（含 RRID / Cellosaurus / Addgene ID,来自未来 A8 reproducibility 块）、分步指令、控制、预期 readouts。直接引用 `setup.assay_type`（Y2H / AP-MS / cryo-EM / NMR / binding_assay / …）、`setup.cell_line`、`setup.species`。
   - `analysis.ipynb`：notebook 摄取 `data/` 下原始结果 CSV,按 C6 表的统计协议（bootstrap CI / stratified k-fold / bio×tech replicates,匹配 `setup.random_seed_protocol`）出汇总,写 `results/{slug}/run.json` 与 in-silico route 同 shape。
   - `data/`：空占位（湿实验执行时填入;按数据共享策略 gitignore 或 commit）
   - `figures/`：来自 `analysis.ipynb` 的图
   - `requirements.txt`：仅分析所需的 pandas / scipy / matplotlib / seaborn 等 —— 湿实验本身无 Python 依赖

   全部 4 种布局都把输出保持为 JSON shape,下游 `/exp-eval` verdict gate 与 `/paper-draft` consumer 不按 setup type 分支。完整 C7（`skills/exp-run/references/templates/{ml,md,wet-lab,docking}/` 下的具体模板文件）延后 —— 最小 pilot 由 agent 按上述文件清单 scaffold。

4. **可选 Review LLM code review**（`--review`）：
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

5. **Sanity check（小规模验证）**：
   - 用极小规模运行（1 epoch / 100 steps / 小 subset）
   - 验证：代码无 crash、数据加载正确、GPU 可用、loss 下降
   - 若 sanity 失败 → 修复代码，重试一次；仍然失败则报告错误并停止

**Phase 2: 部署（Deploy）**

#### Local 模式（`--env local` 或默认）

1. **检查 GPU**：`nvidia-smi` 确认 GPU 可用、显存足够
2. **启动** —— entry-point 名按 setup-type 布局选（bio-C7 minimal pilot）：`run.sh`（ML,默认）、`mdrun.sh`（MD）、`dock.sh`（docking）。Wet-lab 实验**不**自动启动 —— `/exp-run` 仅 scaffold `protocol.md` 并提示用户手动执行,`data/` 填好后再 `--collect` 进入。
   ```bash
   ENTRY=run.sh   # 按 Step 3 布局改 mdrun.sh / dock.sh
   screen -dmS exp-{slug} bash -c \
     "cd $(pwd) && bash experiments/code/{slug}/${ENTRY} 2>&1 | tee logs/exp-{slug}.log"
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
2. **查找空闲 GPU**：`python3 tools/remote.py gpu-status`
   - 若无空闲 GPU → 报告各 GPU 占用情况，建议等待
3. **同步代码**：`python3 tools/remote.py sync-code`
4. **安装依赖**（首次或 requirements 有变化）：`python3 tools/remote.py setup-env`
5. **启动远程实验** —— entry-point 名按 Step 3 布局（`run.sh`/`mdrun.sh`/`dock.sh`;wet-lab 仅本地,不远程）：
   ```bash
   ENTRY=run.sh   # 按 Step 3 布局
   python3 tools/remote.py launch \
     --name "exp-{slug}" \
     --cmd "bash experiments/code/{slug}/${ENTRY}" \
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
- **不修改 idea 状态**：实验结果只写入 experiments/ 页面；idea 的 status / pilot_result 由 /exp-eval 负责更新
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
