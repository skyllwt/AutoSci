---
name: hiera-experiment
description: 为已有 AutoSci 实验运行可选的 Hiera 风格迭代候选搜索，同时保持 wiki 知识库和默认实验 workflow 不变
argument-hint: <experiment-slug> [--run-id <id>] [--init|--propose|--admit|--approve|--run|--recover|--tune|--loop|--status|--finalize]
---

# $hiera-experiment

## 作用和启用边界

仅当用户明确选择已有 AutoSci 实验的 Hiera 可选路径时使用本 skill。Hiera 是隔离的搜索旁路：

- 只读读取关联的 wiki 实验/design 和 runtime contract。
- 将全部搜索状态放在 runs/hiera/<experiment>/<run-id>/ 下。
- 搜索不可变 candidate 快照，并把证据写入旁路 ledger。
- 不创建 wiki entity，不修改 wiki schema 或实验状态，不重写 wiki/log.md，也不把搜索结果写回 wiki。
- 不替代 $exp-design、$exp-run、$exp-eval 或 $research。要形成确认性结论，必须回到正常且带用户门控的 workflow。

创建或改变 run 前必须阅读：

1. README.md：面向用户的流程和命令示例。
2. references/interface.md：契约字段、源码目录和远程 receipt。
3. 字段或权限不明确时，阅读对应 runtime contract 文件。

不得从含糊请求中自行推断方法、指标方向、资源边界、seed 策略或远程环境。缺少决定时必须询问用户，或请用户提供文字约束。

## 状态模型和命令职责

把整个生命周期当作状态机，不要把它当成一个自动完成的命令：

~~~text
init
  -> 检查/补全 semantic_space 和 task_contract
  -> 提出 semantic points
  -> 编写 drafts 和 candidate specs
  -> admit 不可变 candidate
  -> 人工检查源码和 contract
  -> approve 冻结 contract
  -> preflight
  -> run(screen)
  -> 选择一个迭代分支：
       propose 新语义方向
       tune 已审查 config_schema 的子候选
       loop 对已有 candidate 做 deep
       status/recover 处理远程 pending attempt
  -> finalize 旁路报告
  -> 可选地回到 $exp-run 和 $exp-eval 做正式确认
~~~

CLI 子命令和 agent 动作不是一回事：

| 阶段 | CLI 命令 | agent 负责的动作 |
|---|---|---|
| 初始化 | init | 创建旁路并展示 readiness errors。 |
| 补全输入 | 无 | 只编辑用户确认的语义或契约输入并校验。 |
| 提出 | propose | 展示 point ID 和元数据，不生成源码。 |
| 编写 | 无 | 在本 run 的 drafts 下写经过检查的源码/spec，不再次调用 propose。 |
| 准入 | admit | 将精确的 draft 导入不可变快照。 |
| 批准 | approve | 仅在用户明确批准执行边界后执行。 |
| 预检 | preflight | 检查 candidate，不预留评估预算。 |
| 评估 | run | 以 screen 或 deep 执行一个不可变快照。 |
| 调优 | tune | 生成并评估有界的不可变 config 子候选。 |
| 循环 | loop | 只在已有 eligible candidate 中调度 deep bout。 |
| 观察/恢复 | status / recover | 轮询或协调已有远程 attempt，不重新提交。 |
| 收尾 | finalize | 只写探索性旁路报告。 |

--propose skill flag 可能同时用于“提出 semantic point”和“编写 draft”。在编写阶段，必须以补充文字覆盖默认意图：不要调用 Python propose 子命令，而是编写选定 point 的 draft。

## 用户交互规则

skill 参数只选择阶段。补充文字用于传递参数无法表达的上下文：

- point、candidate、parent 和 attempt ID；
- round、limit、depth、指标、方向、seed 或资源限制；
- local/remote 选择及目标服务器/环境；
- 允许写入的具体路径和文件；
- 仅展示或禁止执行的边界；
- 用户已经检查并批准 contract 的事实；
- 要恢复的已有远程 attempt。

遵循以下规则：

- 默认的只读动作可以只使用 skill 指令。
- 缺少参数时询问，不要猜测。
- 生成 draft、admit、approve、部署、运行、调优、恢复或 finalize 前，先说明精确范围；需要用户决定时必须停下。
- 补充文字只收窄操作范围，不等于审批；approve 仍需要用户明确确认。

每次命令或 agent 文件操作后都要报告：

1. 读取或改变了什么。
2. 结果状态、ID、score、receipt 或 readiness error。
3. 还剩什么门控或缺少什么输入。
4. 下一步安全且无阻塞时的一条准确命令。

不得静默连续跨过 admit、approve、preflight、部署、执行、结果接收或正式确认。

## 各阶段规则

### 1. 初始化

执行：

~~~text
python -m tools.hiera.cli --project . init <experiment-slug> --run-id <run-id> [--contract FILE] [--space FILE]
~~~

只有在用户已经检查过 JSON 对象并希望把它合并进生成契约时才使用 --contract。只有在用户已经检查过 semantic-space JSON 时才使用 --space。这些输入只是覆盖或补全默认值，不是执行批准。

初始化会：

- 只读读取关联 wiki/design；
- 创建 manifest.json、semantic_space.json、task_contract.yaml、drafts/、candidates/、attempts/ 和 preflight/；
- 记录绑定本 run 的 source snapshot；
- 报告 readiness_errors，不替用户猜测缺失字段。

如果 semantic space 仍只有保守 baseline、关系缺失或 contract 未就绪，init 后必须停下，请用户确认机制假设、关系、指标/方向、命令、资源和环境。除非用户明确要求下一阶段，不得在同一轮 propose 或生成源码。

### 2. 补全 semantic space 或 contract

这一步没有独立 Python 子命令。agent 只能编辑用户明确指定的文件，通常是：

- runs/hiera/<slug>/<run-id>/semantic_space.json；或
- 在重新执行 init 前由用户提供的 contract override 文件。

编辑 semantic space 时必须保留 schema、dimension/hypothesis 归属以及 requires、activates、excludes 关系，校验 point closure，不得加入未经确认的方法。编辑 contract 时必须保留生成的 source/state 字段，不得伪造凭据或服务器设置。

编辑后展示变更的 JSON/YAML 并停下等待确认。这一步只是规划，不会 propose、写 candidate 源码、admit、approve、preflight、部署或运行。

### 3. 提出 semantic points

执行：

~~~text
python -m tools.hiera.cli --project . propose <slug> --run-id <run-id> --round N --limit K
~~~

operation 是确定性的：

- 没有 admitted candidate：fresh；
- 已有带 score 的 candidate 且不是 crossover 轮：improve；
- round % 3 == 2 且至少有两个带 score 的 candidate：crossover。

命令会把 proposal decision 写入 ledger.jsonl，并输出 point ID、semantic point、change、可用的 parent 和 coverage。它不写源码，也不创建 candidate snapshot。让用户选择要实现的 point ID；point ID 还不是 admitted candidate。

### 4. 编写模块化 draft

这是 agent 负责的文件生成阶段，没有 Python 子命令。用户可以用 --propose 进入 skill，但补充文字必须明确这是编写源码，而不是继续提出 point。

只允许写入：

~~~text
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>/
runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json
~~~

复杂源码优先使用薄的 run.py，并将职责拆到 experiment/data.py、experiment/models.py、experiment/training.py 和 experiment/evaluation.py 等模块。不要为了匹配示例而添加空模块。

draft/spec 展示必须包含：

- candidate_id、operation、parents 和精确 semantic_point；
- 完整源码树及 candidate.editable_files 白名单；
- config 和经过审查的 candidate.config_schema；
- contract entrypoint 和 argv 评估命令；
- result 文件路径、score_path、metric、direction、timeout、budget、accelerator 以及 local/remote 环境；
- 远程运行的 remote_config、远程 Python、GPU 策略、work directory 来源和 conda/env_setup 边界。

本阶段禁止写 candidates/、把 config.json 放进 draft 源码、调用 admit 或运行代码。

### 5. Admit 不可变 candidate

用户必须先检查完整 draft 和 spec，然后执行：

~~~text
python -m tools.hiera.cli --project . admit <slug> --run-id <run-id> --spec runs/hiera/<slug>/<run-id>/drafts/<candidate-id>.spec.json --source-dir runs/hiera/<slug>/<run-id>/drafts/<candidate-id>
~~~

admit 会强制检查：

- source-dir 位于本 run 的 drafts/ 内；
- 源码是 UTF-8、非 symlink，并且与 candidate.editable_files 完全一致；
- entrypoint 存在，源码中没有 config.json；
- candidate_id、semantic point、operation、parents、config 和 schema 有效；
- parents 已经是 ledger 中存在的 candidate。

它把源码复制到 candidates/<candidate-id>/，生成 config.json，计算文件/code digest，并追加 candidate 记录。它不会批准 contract、运行 preflight、预留预算或执行代码。源码或 config 发生变化时必须使用新的 candidate ID 并重新 admit。

### 6. 批准冻结的 execution contract

approve 是人工门控。执行前：

~~~text
python -m tools.hiera.cli --project . approve <slug> --run-id <run-id>
~~~

用户必须已经检查 admitted 源码和完整 contract，包括：

- entrypoint、editable/readonly files、config 和 config schema；
- evaluation/preflight argv、result 文件、score_path、metric 和 direction；
- timeout、最大评估次数、accelerator 和数据假设；
- local/remote 环境以及全部远程 server/conda 字段。

approve 会检查 readiness，计算不可变 contract 字段的 digest，设置 state.approved 并更新 manifest。它不代表跳过了源码审查，也不部署或执行。approve 是 run 级别的：后续 candidate 可以在同一个冻结 contract 下 admit。contract 变化后必须停下，展示变化字段，重新获得人工审查并再次执行 approve；关联的 wiki/design source snapshot 变化时才建立新的 run。digest 不匹配时后续执行必须 fail closed。

### 7. Preflight

approve 后、candidate 第一次评估前，每个 candidate 执行一次：

~~~text
python -m tools.hiera.cli --project . preflight <slug> --run-id <run-id> --candidate <candidate-id>
~~~

preflight 检查冻结 contract、manifest source snapshot、candidate 文件 digest、entrypoint 和 placeholder。本地环境若有审查过的 preflight_command 会执行，但不会预留预算；远程环境只做本地结构检查，真正的远程 preflight 在提交远程任务时由 worker 执行。失败时必须先修复；如果 contract 发生变化，还要重新 approve。

### 8. 运行一次评估

执行：

~~~text
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth screen
python -m tools.hiera.cli --project . run <slug> --run-id <run-id> --candidate <candidate-id> --depth deep
~~~

screen 用于第一次有界比较；deep 只表示用户需要更深证据。depth 是调度标签，不会自动增加 seed、step 或改变模型参数；这些策略必须在已审查的 candidate config/code 中实现。

每次 run 都会：

1. 检查冻结 contract 和不可变 snapshot；
2. 在启动前把一次评估预留写入 ledger.jsonl；
3. 本地用 shell=False 执行审查过的 argv，或通过 Hiera remote adapter 执行；
4. 要求返回码为 0、存在声明的 JSON 结果，并且 score_path 是有限数值；
5. 写入 receipt、日志、score 和结果 digest。

失败、超时、格式错误或缺失结果的 attempt 仍是证据并消耗 reservation。不得静默重试，也不得把它解释为成功。

### 9. 选择一个迭代分支

检查 receipt 和 coverage 后只选择一个分支。

新语义方向：回到 propose，再经过 author → admit → preflight → screen。不得修改 admitted snapshot。除非 contract 字段需要变化，否则 run 级 contract 可复用。

参数调优：

~~~text
python -m tools.hiera.cli --project . tune <slug> --run-id <run-id> --candidate <candidate-id> --limit K --depth deep
~~~

只有批准的 contract 存在非空且已审查的 candidate.config_schema 时才可使用 tune。调优器会校验边界和类型，确定性生成未尝试配置，复制 parent 的不可变源码，写入每个 child 的 config.json，执行 child，并记录 parent 关系。它不会修改 parent，也不是只预览命令。失败 child 仍消耗预算并保留为证据。

Deep loop：

~~~text
python -m tools.hiera.cli --project . loop <slug> --run-id <run-id> --rounds R --max-bouts B
~~~

loop 只选择 best score 为有限数且已有 tuning bout 少于 B 的 candidate。它记录 scheduler decision，执行 deep，记录 bout，并在 round、bout 或 budget 上限达到时停止。它不会调用 propose、生成源码或创建 config 子候选。

选择分支前，先协调那些已经写入 deep evaluation、但尚未写入 tuning-bout 事件的终态 attempt。scheduler 和恢复逻辑通过 attempt ID 避免重复 deep bout。

### 10. 观察或恢复远程 attempt

执行：

~~~text
python -m tools.hiera.cli --project . status <slug> --run-id <run-id>
python -m tools.hiera.cli --project . recover <slug> --run-id <run-id> --attempt <attempt-id>
~~~

status 是对 pending remote handle 的非阻塞轮询。它可能收集终态 receipt，并更新 ledger、coverage、experience revision 和 reconciliation 记录；绝不会提交替代 attempt。本地 run 使用 status 时只报告/协调本地 ledger，不会轮询远程主机。

recover 只用于已有远程 attempt，例如客户端中断后或需要明确检查时。它会校验 attempt token、candidate digest、contract digest、worker digest、host 和规范远程路径，然后轮询并回收同一个 handle。它不会再次预留评估或启动第二个 worker；recover 只支持 remote。

running 仍表示 pending；终态失败是失败证据；missing 或 unknown 必须显式检查/恢复，绝不能报告为成功。

### 11. 收尾探索性搜索

finalize 前，远程 run 必须先执行 status，并确认没有 pending attempt。然后执行：

~~~text
python -m tools.hiera.cli --project . finalize <slug> --run-id <run-id>
~~~

finalize 写入 FINAL_REPORT.json，其中包含 ledger summary、coverage、experience revision、contract digest、source isolation 检查和 wiki_writeback: none。它不会等待远程任务、检查 pending、选择正式 winner 或更新 wiki。存在 pending 时，必须先收集或恢复。

如果要形成确认性结论，把选定方法复制到正常实验路径，使用已有的用户门控 $exp-run 和 $exp-eval。不得自动把探索性 Hiera score 转成正式结果。

## Contract 和命令不变量

task contract 是 JSON-compatible YAML。生成的 source/state 字段是权威数据，不能被任意 override 替换。可执行 contract 必须包含：

- candidate.entrypoint 和非空相对路径 candidate.editable_files；
- evaluation.kind: command；
- 非空 evaluation.evaluate_command；
- 相对路径 evaluation.result_file；
- 非空 evaluation.score_path、metric，以及明确的 direction（minimize 或 maximize）；
- 正数 resources.timeout_seconds 和 max_evaluations；
- resources.environment 为 local 或 remote。

命令必须是 argv 列表，禁止 shell 字符串。只允许这些 placeholder：

~~~text
{candidate_dir} {run_dir} {attempt_dir} {result_file} {config_file} {entrypoint}
~~~

本地 evaluator 使用 shell=False。evaluation.prepare_command 和 evaluation.collect_command 必须为空；快照部署和结果收集由 adapter 负责。result 文件必须位于新的 attempt 目录内，是 UTF-8 JSON，且 score_path 对应有限数值。

## 本地和远程执行

本地执行时，evaluator 以 candidate snapshot 为工作目录运行审查过的命令，并把日志/receipt 写到本地 attempt 目录。

远程执行时，Hiera adapter 通过 tools.remote 读取项目相对的 resources.remote_config，默认是 config/server.yaml。它只把 admitted candidate 文件映射传到每个 attempt 的远程旁路目录，发送 worker，执行审查过的 preflight/evaluation 命令，并回收有界日志和声明的结果文件。它不调用项目级 sync-code、setup-env、launch 或 pull-results，不同步 AutoSci 源码或 wiki，也不安装任意 candidate 依赖。

approve 前必须检查：

- remote_config：相对项目路径，通常为 config/server.yaml；
- remote_python：一个可执行路径/名称，不是 shell 命令；
- remote_poll_seconds：正数轮询间隔；
- remote_gpu：空字符串或逗号分隔的 GPU 索引；
- server 的 host、user、work_dir、SSH 设置，以及且仅有一种已审查的运行时设置：conda.path + conda.env，或 env_setup。

adapter 会在远程 worker 上激活已审查的 conda/环境设置。数据和依赖必须已经存在于远程环境，或由已审查的 candidate 命令显式处理。凭据留在 server 配置中，不得复制到 Hiera artifact。server 配置变化意味着执行环境变化，下一次执行前必须重新审查 contract。

## 失败、幂等和安全

- 保持 candidate snapshot 不可变，禁止原地修改 candidates/<candidate-id>/。
- 源码/config 改动使用新的 candidate ID；关联的 wiki/design source snapshot 改变时使用新的 run ID。
- 客户端中断不得消耗替代预算，使用 recover 恢复同一个 attempt。
- 没有匹配 attempt、candidate、contract、worker、host 和 path digest 的远程 receipt 不得接受。
- 保持 ledger.jsonl append-only，不得重写历史来隐藏失败 attempt。
- raw/{papers,notes,web} 是用户所有，只读。
- 不得直接修改 wiki/graph/，不得重写 wiki/log.md。
- 不得向远程 push 或发布远程修改。
- 遵循当前仓库的变更记录规则。不要在 Hiera run 内创建 revise.md；在干净发行分支中，除非用户明确要求，不要添加测试/用户记录。

## 每次动作的固定报告格式

使用简洁具体的报告：

~~~text
Changed/read: <文件或命令>
State: <run/candidate/attempt 状态和 ID>
Gate: <用户需要检查什么，或 none>
Next: <一条安全的准确命令，或说明为何必须停下>
~~~

命令失败时保留其输出，并说明属于 contract/readiness、source-digest mismatch、budget exhausted、本地进程、远程传输还是结果校验问题。不得静默重试或改变 contract。
