# Hiera 实验流程指南

这份文档面向使用 AutoSci 可选 Hiera 路径的用户。Hiera 是已有 wiki 实验旁路搜索流程：它保持 wiki、知识图谱以及 `exp-design` / `exp-run` / `exp-eval` 正常 workflow 不变。

## Hiera 做什么

Hiera 在反复迭代中探索不可变的实验候选：提出语义点，等待用户检查候选源码，执行已批准的快照，调优有界配置，并把证据写入只追加 ledger。搜索结果是探索性证据；如果要形成确认性结论，仍需走正常实验 workflow 及其用户门控。

Hiera 不会把候选写成 wiki 实体，也不会自动写回 wiki。所有状态都在下面的旁路目录中：

```text
runs/hiera/<experiment-slug>/<run-id>/
├── manifest.json              # 关联只读 wiki/design 输入
├── semantic_space.json        # propose 探索的假设和关系
├── task_contract.yaml         # 已批准的执行和评分边界
├── ledger.jsonl               # 只追加的候选、attempt、结果事件
├── drafts/<candidate-id>/     # admission 前检查过的源码
├── candidates/<candidate-id>/ # admission 后不可变快照
├── attempts/<attempt-id>/     # receipt、日志和回收结果
└── FINAL_REPORT.json          # finalize 生成的旁路搜索报告
```

skill 本身的组织方式：

```text
.opencode/skills/hiera-experiment/      # OpenCode 当前激活的 skill
├── SKILL.md                          # agent 规则和安全边界
├── README.md                         # 本用户指南
└── references/interface.md           # JSON 字段、远程契约和目录布局

i18n/en/skills/hiera-experiment/      # 英文源文件
i18n/zh/skills/hiera-experiment/      # 中文源文件
```

## 完整生命周期

通常按以下顺序进行：

```text
init → 检查并补充 semantic space → propose
     → 编写 drafts 和 candidate spec → admit
     → 人工检查 → approve
     → preflight → run(screen)
     → 反复 loop/tune/run(deep)
     → 必要时 status 或 recover → finalize
     → 如需确认，再走 exp-run 和 exp-eval
```

所有命令都从 AutoSci 项目根目录执行。把 `<slug>`、`<run-id>` 和 `<candidate-id>` 替换为当前运行的值。

### 1. 初始化隔离 run

```text
python -m tools.hiera.cli --project . init <slug> --run-id <run-id>
```

如果实验需要明确的资源、命令、指标或远程环境，使用 `--contract path/to/contract-overrides.json`。`init` 只读读取关联 wiki 实验和 design，创建旁路目录；它不会生成候选源码，也不会执行实验。

初始化后检查：

```text
runs/hiera/<slug>/<run-id>/semantic_space.json
runs/hiera/<slug>/<run-id>/task_contract.yaml
```

初始 semantic space 只有保守 baseline。如果 baseline 不足，用户必须补充已经确认的机制假设和必要关系。不要替用户猜测方法、指标方向或命令。

下一步：检查这两个文件，只写入已经确认的语义假设，然后执行 `propose`。

### 2. 提出语义点

```text
python -m tools.hiera.cli --project . propose <slug> \
  --run-id <run-id> --round 1 --limit 4
```

`propose` 根据当前 semantic space 和 ledger 确定性地提出 fresh、improve 或 crossover 语义点。它不会写源码、admit 候选、approve 契约或运行实验。检查提出的点，选择需要实现的候选。

下一步：为选中的点编写源码树和 spec，然后执行 `admit`。

### 3. 编写模块化 draft 和 candidate spec

经过检查的源码只能放在当前 run 的 `drafts/` 目录。复杂候选通常按下面组织：

```text
drafts/<candidate-id>/
├── run.py                 # 薄的 CLI 入口
└── experiment/
    ├── __init__.py
    ├── data.py            # 数据加载和划分策略
    ├── models.py          # 模型定义或变体
    ├── training.py        # 优化/训练循环
    └── evaluation.py      # 指标和 JSON 结果序列化
```

candidate spec 与源码目录分开，例如 `drafts/<candidate-id>.spec.json`。它必须明确候选 ID、semantic point、config、entrypoint、源码文件、评估命令、指标和方向。源码树只能包含 `candidate.editable_files` 列出的 UTF-8 文件，不能自行放入 `config.json`。

这个阶段只是生成源码并准备检查。不要自行把源码写入 `candidates/`。

下一步：向用户展示完整 draft、spec、契约边界和评估命令；检查通过后执行 `admit`。

### 4. Admission：生成不可变候选

```text
python -m tools.hiera.cli --project . admit <slug> \
  --run-id <run-id> \
  --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json \
  --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
```

`admit` 校验 spec，把经过检查的源码树复制到 `candidates/<candidate-id>/`，根据 spec 的 `config` 生成 `config.json`，并把文件摘要写入 `ledger.jsonl`。源码或 config 改变时必须使用新的候选 ID。Admission 仍不会批准契约，也不会执行候选。

下一步：检查不可变候选快照，并准备审批门。

### 5. Approve 执行契约（人工门控）

```text
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
```

只有在用户明确检查并批准候选、源码、入口、config、资源限制、评估命令、指标、方向以及本地/远程边界后，才执行 `approve`。它会冻结契约摘要。之后的 `preflight`、`run`、`tune`、`loop`、`status` 和 `finalize` 都必须使用该冻结契约；契约变化后必须重新检查并批准。

远程契约审批前，要明确检查 `resources.remote_config`、`remote_python`、`remote_gpu`、主机/工作目录以及 `conda` 环境或 `env_setup`。

审批成功后的下一步：对每个已 admission 候选执行 `preflight`。

### 6. Preflight：不消耗评估预算

```text
python -m tools.hiera.cli --project . preflight <slug> \
  --run-id <run-id> --candidate <candidate-id>
```

`preflight` 检查冻结契约、候选快照、命令占位符和执行边界，不会预留评估预算，也不会运行实验。远程契约会在部署前检查远程适配器边界。

通过后的下一步：执行一次有界 screen 评估。

### 7. Screen 候选

```text
python -m tools.hiera.cli --project . run <slug> \
  --run-id <run-id> --candidate <candidate-id> --depth screen
```

`screen` 预留一个预算名额，运行不可变快照，回收声明的 JSON 结果并记录 receipt。失败 attempt 仍是证据并消耗预留名额，不会被静默重试。检查 receipt 和分数后，再决定哪些候选进入深度迭代。

下一步：为比较提出/admit 新候选，或对符合条件的候选使用 `loop` / `tune`。

### 8. 使用 deep bout 迭代

用有界 loop 执行多轮深度评估和调优：

```text
python -m tools.hiera.cli --project . loop <slug> \
  --run-id <run-id> --rounds 2 --max-bouts 1
```

`loop` 选择符合条件的候选，执行 deep 评估并记录 tuning bout，直到达到指定轮数、bout 上限或契约预算。它不会绕过审批，也不会写入 wiki。

当 `candidate.config_schema` 存在时，可以执行有界参数搜索：

```text
python -m tools.hiera.cli --project . tune <slug> \
  --run-id <run-id> --candidate <candidate-id> \
  --limit 3 --depth deep
```

`tune` 为契约 schema 范围内的配置创建不可变子候选，跳过已经尝试的配置，评估每个子候选并记录父子关系。它不会修改父候选快照。

下一步：检查分数、seed/稳定性诊断和调优决策；如果需要新的语义方向，回到 `propose`，为新候选重复 admission 和审批流程。

### 9. 检查或恢复远程 attempt

对一个 Hiera run 的待处理远程 attempt 做一次非阻塞检查：

```text
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
```

`status` 对每个待处理 handle 轮询一次，发现终态时回收 receipt；不会提交替代 attempt。如果本地客户端在预留 attempt 后断开，恢复同一个 attempt：

```text
python -m tools.hiera.cli --project . recover <slug> \
  --run-id <run-id> --attempt <attempt-id>
```

`recover` 检查冻结契约和候选摘要，恢复已有远程 handle，并按 attempt ID 幂等地补记完成的 deep evaluation。`missing` 或 `unknown` 只有在显式恢复操作中才会作为失败收尾，绝不能报告为成功或自动重新启动。

下一步：拿到终态 receipt 后继续有界迭代，或结束探索并执行 `finalize`。

### 10. Finalize 探索性搜索

```text
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
```

`finalize` 生成 `FINAL_REPORT.json`，包含候选/评估覆盖、最佳记录分数、experience revision 和 wiki 隔离状态。它不会给出科学结论，也不会写入 wiki。

如果要做确认性结论，下一步是把选定方法复制到正常实验路径，并使用已有、带用户门控的 `exp-run` 和 `exp-eval`。

## 本地和远程执行

本地执行时将 `resources.environment` 设为 `local`；远程执行时只能在已批准契约中设为 `remote`。Hiera 远程适配器通过项目内相对路径 `config/server.yaml` 读取配置，并且会：

- 只把不可变候选快照上传到单次 attempt 的旁路目录；
- 在远程主机应用已检查的 `conda.path` + `conda.env`，或已检查的 `env_setup`；
- 执行已检查的 preflight/评估命令，回收有界日志和声明的 JSON 结果；
- 保留本地 `remote.json` handle，使 `status` 和 `recover` 能继续同一个 attempt。

它不会调用项目级 `sync-code`、`setup-env`、`launch` 或 `pull-results`，不会同步 AutoSci 源码树，不会安装任意候选依赖，也不会传输 wiki。依赖和数据必须已经存在于经过检查的远程环境中，或由经过检查的候选命令显式处理。

评估命令是 argv 数组，例如：

```json
["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]
```

只允许使用这些占位符：`{candidate_dir}`、`{run_dir}`、`{attempt_dir}`、`{result_file}`、`{config_file}` 和 `{entrypoint}`。结果文件必须是 JSON，且 `score_path` 必须解析为有限数值。

## 人工门控和安全停点

在已批准边界内，agent 可以检查、提出、生成 draft、admit、preflight、运行已批准评估、监控、recover、tune、loop 和 finalize。出现以下情况必须停下来请求用户输入：

- semantic space 需要机制假设或关系；
- 候选源码或 candidate spec 需要检查；
- 执行契约或远程环境需要审批；
- 结果需要在 Hiera 探索之外做确认性决定。

每条命令执行后，agent 都应说明发生了什么，并在下一步安全且条件满足时给出具体命令。这样用户能持续操作，同时不会跳过任何门控。
