# Hiera 实验流程指南

本指南说明 AutoSci 中可选的 Hiera 搜索路径。它要求实验已经存在，并把搜索状态放在 `runs/hiera/` 旁路目录中；wiki 和正常实验设计只作为输入读取。Hiera 不改变 wiki schema、wiki 页面、`$exp-design`、`$exp-run`、`$exp-eval` 或 `$research`。

## 开始前

- 在 AutoSci 项目根目录执行命令。
- `<slug>` 必须已经有可供 run 读取的 experiment/design 记录。
- 先决定批准的执行环境是 `local` 还是 `remote`。远程执行要在 approve 前检查 `config/server.yaml` 以及 conda/环境字段。
- 将示例中的 `<slug>`、`<run-id>`、`<candidate-id>`、`<point-id>`、`<attempt-id>` 替换成当前值。
- skill 参数只选择流程阶段。补充文字用于提供参数本身无法表达的上下文：候选和父候选 ID、round/limit/depth、local/remote 边界、文件路径、仅展示限制，以及明确的审批或恢复决定。默认只读动作可以省略；只要 agent 需要猜参数，或将要写文件、审批、部署、运行、恢复 attempt，就必须补充。补充文字是操作边界，不等于人工审批；approve 和执行仍需要用户明确确认。

## run 目录

```text
runs/hiera/<slug>/<run-id>/
├── manifest.json              # 指向 wiki/design 的只读链接
├── semantic_space.json        # 机制假设和已探索关系
├── task_contract.yaml         # 执行、资源、命令、指标边界；approve 后冻结
├── ledger.jsonl               # append-only 的候选、attempt、结果记录
├── drafts/<candidate-id>/     # 等待审查/准入的源码
├── candidates/<candidate-id>/ # 不可变的 admitted 源码和 config.json
├── attempts/<attempt-id>/     # receipt、日志、远程句柄、结果
└── FINAL_REPORT.json          # finalize 生成的旁路总结
```

复杂 draft 通常使用很薄的 `run.py`，再把职责拆到 `experiment/data.py`、`models.py`、`training.py`、`evaluation.py` 等模块。candidate spec 与源码目录并列，明确 semantic point、config、entrypoint、editable files、评估命令、指标和优化方向。

## 命令总览

| 阶段 | 触发原因 | 用户 skill 指令 | Agent Python 指令 | 门控 |
|---|---|---|---|---|
| 初始化 | 创建新的隔离 Hiera run | `$hiera-experiment <slug> --run-id <id> --init` | `python -m tools.hiera.cli --project . init <slug> --run-id <id> [--contract FILE]` | 停下审查 semantic space |
| 补全输入 | 保守默认值不能表达已确认的机制/指标/远程边界 | 继续 init 对话并提供文字指令 | 无独立子命令；agent 编辑并校验 `semantic_space.json` / `task_contract.yaml` | 用户确认假设 |
| 提出 | 为一轮生成确定性的 semantic points | `$hiera-experiment <slug> --run-id <id> --propose` | `... propose <slug> --run-id <id> --round N --limit K` | 审查 points |
| 编写 draft | 把选中的 point 变成可审查源码和 spec | `$hiera-experiment <slug> --run-id <id> --propose`，并附编写文字 | 无独立子命令；agent 写入 `drafts/` | 审查完整源码/spec |
| 准入 | 将审查后的 draft 固化为不可变快照 | `$hiera-experiment <slug> --run-id <id> --admit` | `... admit ... --spec SPEC --source-dir SOURCE` | candidate 仍未批准 |
| 批准 | 冻结 execution contract digest | `$hiera-experiment <slug> --run-id <id> --approve` | `... approve <slug> --run-id <id>` | 明确人工批准 |
| 预检 | 不消耗评估预算地检查 candidate | `$hiera-experiment <slug> --run-id <id> --preflight` | `... preflight ... --candidate C` | 通过后才能运行 |
| Screen | 第一次有界的候选比较 | `$hiera-experiment <slug> --run-id <id> --run` | `... run ... --candidate C --depth screen` | 消耗一次 reservation |
| 迭代 | 新机制、参数子候选或 deep bout | 下文的 `--propose`、`--tune`、`--loop` | `propose`、`tune` 或 `loop` | 继续遵守 approval/budget |
| 观察/恢复 | 远程 attempt 等待中或客户端中断 | `--status` 或 `--recover` | `status` 或 `recover --attempt A` | 不自动重提 |
| Finalize | 没有待处理任务，需要旁路报告 | `$hiera-experiment <slug> --run-id <id> --finalize` | `... finalize <slug> --run-id <id>` | 只产生探索报告 |

表格中的 `...` 代表公共前缀 `python -m tools.hiera.cli --project .`。

## 有序流程

### 1. 初始化隔离 run

**何时使用。** 新建一个 `<run-id>` 时使用一次，在 propose 或生成候选源码之前执行。

**作用。** `init` 创建旁路目录，把 run 与现有 wiki/design 以只读方式关联，并生成初始 semantic space 和 task contract。它建立 Hiera 边界，不改 wiki，也不运行代码。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --init
```

**需要补充的文字及目的。** 当默认 contract 不足，或需要明确禁止副作用时补充。文字告诉 agent 已确认的资源、指标、命令、环境和文件；skill flag 本身无法携带这些内容。
```text
使用 contract-overrides.json 和 config/server.yaml 进行远程 CPU 运行。
只做初始化，展示 manifest.json、semantic_space.json 和
task_contract.yaml；不要 propose、生成源码、admit、approve、部署或运行。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . init <slug> --run-id <run-id> --contract contract-overrides.json
```
如果生成的 contract 已足够，则省略 `--contract`。

**产物和停点。** 生成 `manifest.json`、`semantic_space.json`、`task_contract.yaml`。如果机制假设、关系、指标方向或执行字段仍缺失，agent 必须停下等待补充。

### 2. 补全 semantic space 和 contract

**何时使用。** 仅当初始化后的保守默认值不能表示已经确认的设计决策时使用。

**作用。** 把已批准的实验设计写成机器可读的假设和关系，避免 Hiera 自行猜测方法、指标方向、seed 策略或 remote 边界。

**用户 skill/文字指令。** 这一步没有独立 Python 子命令或 skill flag。可以这样明确：
```text
只更新 runs/hiera/<slug>/<run-id>/semantic_space.json，写入已确认的
A、B 机制假设、必要关系和指标方向。不要生成候选、写 draft、
admit、approve、preflight、部署或运行。
```
“只更新”是必要边界：这一步是规划动作，不是继续生命周期的授权。

**Agent 动作。** agent 编辑并校验 JSON/YAML 文件；没有固定 CLI 子命令。

**产物和停点。** 审查假设和关系是否与 design 一致；确认后再进入 `propose`。

### 3. 提出 semantic points

**何时使用。** semantic space 确认后使用；后续需要新的机制方向时也回到这里。

**作用。** `propose` 只确定性生成 semantic points，不生成可执行源码。候选图根据 round 和 ledger 选择 fresh、局部 improve 或 crossover，并记录 coverage/父关系。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --propose
```

**需要补充的文字及目的。** 补充 round、limit 和仅展示限制，因为 skill flag 没有这些参数；这样不会意外生成过多 points 或直接进入源码生成。
```text
生成 round 0，最多 4 个 semantic proposal。展示每个 point 的
operation、parents、changes 和 coverage。不要编写源码、admit、approve、
preflight、部署或运行。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . propose <slug> --run-id <run-id> --round 0 --limit 4
```

**产物和停点。** 输出 point ID 和元数据。选择要实现的 point；它们还不是 admitted candidate。

### 4. 编写模块化 draft 和 candidate spec

**何时使用。** 用户选定一个或多个 point ID 后使用；后续新 proposal 需要实现时也使用。

**作用。** 把 semantic point 转成可审查源码和 metadata，同时把未审查代码留在 `drafts/`，不进入 `candidates/`。这是唯一生成实验源码的阶段。

**用户 skill 指令。** 入口仍使用 `--propose`，但必须用文字把 agent 从“提出 point”切换到“编写源码”：
```text
针对 point <point-id>（parents: <parent-ids>）生成模块化 candidate 和
spec。源码只写入
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>/，使用已审查的目录结构。
展示完整源码、config、命令、指标、方向和 remote CPU contract。
不要再次调用 propose CLI，不要写 candidates/、admit、approve、preflight、
部署或运行。
```
明确“不要再次调用 propose CLI”是为了消除同一个 skill flag 的歧义。

**Agent 动作。** 没有独立 Python 子命令。agent 写 draft 树和 spec，并校验 editable-file 白名单及命令 placeholder。

**产物和停点。** 审查每个源码文件、candidate spec、config、评估命令、指标/方向及 local/remote 边界；确认后才能 `admit`。

### 5. Admit 不可变 candidate

**何时使用。** draft 和 spec 通过源码审查后使用。

**作用。** `admit` 把精确的 UTF-8 源码复制为不可变快照，生成 `config.json`，记录 digest，并在 ledger 中关联 parent/semantic point。它不批准也不执行。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --admit
```

**需要补充的文字及目的。** 提供精确 spec/source 路径，防止准入错误 draft；同时声明不执行，因为 admit 不是 approve。
```text
只准入
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json
和
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>。
不要 approve、preflight、部署或运行。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . admit <slug> --run-id <run-id> --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
```

**产物和停点。** 检查 `candidates/<candidate-id>/`、生成的 `config.json` 和 ledger。代码或 config 改动必须使用新的 candidate ID；随后进入批准门控。

### 6. Approve 执行 contract

**何时使用。** 所有 admitted candidate 文件和 contract 都审查完后使用。这是人工门控。

**作用。** `approve` 冻结后续 preflight、run、tune、loop、status、finalize 使用的 `task_contract` digest。它是 contract 批准，不替代源码审查，也不会自行部署或运行。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --approve
```

**必须补充的批准文字及目的。** agent 必须收到用户已经审查可执行边界的明确声明；skill flag 本身不能证明这个事实。
```text
我已审查 admitted 源码、entrypoint、config、评估命令、指标、方向、
资源限制、数据假设及 local/remote 环境。我明确批准冻结的 Hiera
execution contract。只执行 approve，不要 preflight 或运行。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
```

**产物和停点。** 记录冻结的 contract digest。远程运行还要检查 `resources.remote_config`、`remote_python`、`remote_gpu`、host/work directory 以及 conda/`env_setup`。

### 7. Preflight：不消耗评估

**何时使用。** approve 后、candidate 第一次 screen 前，每个 admitted candidate 使用一次。

**作用。** 检查冻结 contract、源码 digest、entrypoint、placeholder 和 adapter 边界；不预留预算，也不运行完整实验。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --preflight
```

**需要补充的文字及目的。** 指明 candidate，并再次说明不执行；skill flag 没有 candidate 参数。
```text
只预检 candidate <candidate-id>。检查冻结 contract、源码 digest、
entrypoint、placeholder 及 local/remote 边界。不要预留评估或运行实验。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . preflight <slug> --run-id <run-id> --candidate <candidate-id>
```

**产物和停点。** 失败时先修复 contract/source 检查；通过后才能 screen。

### 8. 运行有界 screen

**何时使用。** 每个 admitted candidate 第一次比较时使用。只有批准的 contract 是 remote 时才选择 remote。

**作用。** `screen` 预留一次评估，执行不可变快照，校验声明的 JSON score 并写入 receipt，为选择 deep 候选提供证据。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --run
```

**需要补充的文字及目的。** 写明 candidate、depth、adapter 和收集边界，决定代码在哪里运行以及允许传输什么。
```text
使用批准的 <local|remote> contract，以 screen 深度运行 candidate
<candidate-id>。只部署不可变 candidate 快照，收集声明的 JSON 结果和
有界日志；不要修改 wiki 或同步 AutoSci 源码。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth screen
```

**产物和停点。** 检查 attempt receipt、score、失败状态和 ledger。失败 attempt 仍是证据并消耗 reservation，不会静默重试。随后可比较其他 candidate、回到 `propose` 或进入 deep 迭代。

### 9. 选择迭代分支

查看 screen 证据后只选择一个分支。

#### 9a. 新机制：回到 propose

当现有语义方向不足时，回到第 3 步。新 point 必须再次经过 author → admit → approve → preflight → screen。

#### 9b. 参数子候选：tune

**触发原因。** 只有批准的 candidate 有已审查且非空的 `candidate.config_schema` 时使用。

**作用。** `tune` 在 schema 内生成不可变子 candidate，跳过已尝试配置，按指定深度评估，并记录 parent 关系；不会修改 parent。

**用户 skill 指令和补充文字。**
```text
$hiera-experiment <slug> --run-id <run-id> --tune
使用 <candidate-id> 作为 parent。在已审查的 config_schema 内生成最多
3 个未尝试配置，展示子配置和 parent 关系，然后运行 deep 评估。
不要修改 parent 或 contract。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . tune <slug> --run-id <run-id> --candidate <candidate-id> --limit 3 --depth deep
```
tune 会校验冻结 contract 并执行有界子候选评估，不是只预览。

#### 9c. 现有 candidate：loop deep bout

**触发原因。** admitted、approved candidate 仍适合获得 deep 证据，且不需要新源码时使用。

**作用。** `loop` 在现有 candidate 中调度 deep bout，记录 anchor/challenger 和 tuning 决策，并在轮数、bout 上限或预算耗尽时停止。它不 propose、不生成源码、不 tune。

**用户 skill 指令和补充文字。**
```text
$hiera-experiment <slug> --run-id <run-id> --loop
最多运行 2 个 deep bout，每个 candidate 最多 1 个 bout。只使用已
admitted candidate；不要 propose、生成源码或 tune。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . loop <slug> --run-id <run-id> --rounds 2 --max-bouts 1
```

#### 9d. 远程等待或中断：status/recover

**触发原因。** 远程 attempt 等待中或可能已完成时用 `status`；客户端断开且已有 attempt ID 时才用 `recover`。

**作用。** `status` 轮询并收集 terminal receipt，不提交替代任务；`recover` 恢复同一个远程句柄，不重新预留或启动第二个 attempt。

**用户 skill 指令和补充文字。**
```text
$hiera-experiment <slug> --run-id <run-id> --status
轮询一次所有 pending remote attempt 并收集 terminal receipt。不要重提
worker，也不要预留替代 attempt。
```
```text
$hiera-experiment <slug> --run-id <run-id> --recover
恢复已有 remote attempt <attempt-id>。不要预留新的预算或重提 worker。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
python -m tools.hiera.cli --project . recover <slug> --run-id <run-id> --attempt <attempt-id>
```

**产物和停点。** status/recover 可能补写 ledger 和 receipt，但不能把 missing/unknown attempt 当作成功。收到 terminal receipt 后回到迭代分支或 finalize。

### 10. Finalize 探索性搜索

**何时使用。** 用户确认没有 pending attempt，且需要旁路搜索报告时使用。finalize 本身不会等待或替你收集 pending 任务。

**作用。** `finalize` 汇总 candidate、评估覆盖、最佳已记录 score、experience revision 和隔离状态；不写 wiki，也不把探索证据变成正式结论。

**用户 skill 指令。**
```text
$hiera-experiment <slug> --run-id <run-id> --finalize
```

**需要补充的文字及目的。** 明确已完成收集，并禁止误写 wiki 或声明科学结论。
```text
所有 remote attempt 都已收集或明确恢复。只在 Hiera 旁路中写入
FINAL_REPORT.json；不要写回 wiki，也不要声明正式结论。
```

**Agent Python 指令。**
```powershell
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
```

**下一步。** 如果要做正式确认，把选定方法放入正常实验路径，使用现有的用户门控 `$exp-run` 和 `$exp-eval`。

## 本地和远程执行

在批准的 contract 中把 `resources.environment` 设为 `local` 或 `remote`。远程运行时，Hiera adapter 读取项目相对路径 `config/server.yaml`，只把不可变 candidate 快照上传到每个 attempt 的旁路目录，激活审查过的 `conda.path` + `conda.env` 或 `env_setup`，执行审查过的 preflight/evaluation argv，并收集有界日志和声明的 JSON 结果。它保存 `remote.json`，让 `status` 和 `recover` 能继续同一个 attempt。

adapter 不调用项目级 `sync-code`、`setup-env`、`launch` 或 `pull-results`，不传输 AutoSci 源码/wiki，也不安装任意 candidate 依赖。依赖和数据必须已经在审查过的远程环境中，或由审查过的 candidate 命令显式处理。

评估命令使用 argv 列表，例如：
```json
["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]
```
只允许 `{candidate_dir}`、`{run_dir}`、`{attempt_dir}`、`{result_file}`、`{config_file}`、`{entrypoint}`。结果文件必须是 JSON，且 `score_path` 必须解析为有限数字。

## 人工门控和安全停点

出现以下情况必须停下等待用户：semantic space 需要机制假设/关系，源码/spec 尚未审查，contract 或远程环境尚未批准，或结果需要在 Hiera 之外做正式确认。每一步完成后，agent 应报告改变的文件/状态，并在安全且无阻塞时给出一个准确的下一步命令。不得静默跳过 approve、部署、执行、恢复或结果接收。

Hiera 不创建 wiki entity、不修改 wiki schema/status、不重写 `wiki/log.md`，也不把搜索结果写回 wiki。ledger 和报告只是旁路证据；正式确认仍使用 AutoSci 的正常 workflow。
