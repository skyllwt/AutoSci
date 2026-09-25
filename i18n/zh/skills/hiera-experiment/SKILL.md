---
name: hiera-experiment
description: 为已有 AutoSci 实验运行可选的 Hiera 风格迭代候选搜索，同时保持 wiki 知识库和默认实验 workflow 不变
argument-hint: <experiment-slug> [--run-id <id>] [--init|--propose|--admit|--approve|--run|--recover|--tune|--loop|--status|--finalize]
---

# $hiera-experiment

仅当用户明确选择已有实验的 Hiera 可选路径时使用。它是旁路 workflow：状态全部写入 `runs/hiera/<experiment>/<run-id>/`，不会新增 wiki 实体、修改 wiki schema、改变 wiki 实验状态，也不会替代 `$exp-design`、`$exp-run`、`$exp-eval` 或 `$research`。

创建运行前请阅读 [references/interface.md](references/interface.md)，其中定义了精确 JSON 字段和运行目录契约。

## 每一步都给出清晰的后续建议

每次执行 Hiera 命令后，都要说明实际结果和被改变的状态。只要下一步已经具备条件，就给出一条填好 run 和 candidate ID 的确切命令（或简短命令模板），并说明它的作用。如果仍需要人工门控、补充语义假设、检查源码或决定契约，就明确告诉用户需要检查或提供什么，并在门控完成前停止。不得静默越过 `approve`、部署、运行或结果接收等门控。

搜索包含真实的反复迭代：

1. **初始化并检查。** 只读读取关联的 wiki 实验、idea 和 design，执行 `python -m tools.hiera.cli init <slug> --run-id <id>`。检查 `semantic_space.json` 和 `task_contract.yaml`。默认语义空间只有保守的 baseline，用户必须提供机制假设和关系；不得猜测方法、指标方向或命令。
2. **编写候选。** 执行 `propose --round N` 获取确定性的 fresh、improve 或 crossover 点。复杂候选应组织成小型源码树：让 `run.py` 只负责入口，把数据加载放在 `experiment/data.py`，模型变体放在 `experiment/models/`，训练放在 `experiment/training.py`，指标和结果处理放在 `experiment/evaluation.py`；只添加实验实际需要的模块。将候选元数据 spec 与源码树分开，把经过检查的源码树放入当前运行的 `drafts/<candidate-id>/`，再执行 `admit --spec ... --source-dir runs/hiera/<experiment>/<run-id>/drafts/<candidate-id>`。小型候选仍可使用原来的内联 `files` 映射。候选 ID、父候选、语义点、代码摘要和配置写入 ledger。代码或配置改变时必须生成新的快照。
3. **批准门。** 向用户展示候选文件、契约、命令、资源上限、指标、方向和评估边界。用户明确批准后才能执行 `approve`；批准会冻结契约摘要。未批准或已变化的契约不得执行。
4. **筛选并迭代。** 执行 `preflight --candidate ID`，再执行 `run --candidate ID --depth screen`。检查 receipt 和 ledger。重复 proposal → admission → preflight → screen；候选仍符合条件时，`loop` 可对同一候选进行多次 deep tuning。调度器记录 anchor/challenger 决策，并在预算或 bout 上限到达时停止。失败评估保留为证据并计入预算，不得无记录重试。
   如果已检查的契约包含非空 `candidate.config_schema`，使用 `tune --candidate ID --limit N --depth deep` 创建不可变参数变体。调优器校验边界、跳过已试配置、评估每个变体，并将每个变体记录为子候选。下一轮可选择最佳子候选作为新父候选。
   `resources.environment` 选择已经批准的执行适配器。`local` 保持原有本地行为；`remote` 使用 [references/interface.md](references/interface.md) 中定义的 Hiera 专用远程适配器：它只把不可变候选快照部署到单次 attempt 的旁路目录，在那里执行 preflight 和 evaluation，再回收有界日志和声明的 JSON 结果；它不会调用项目级远程实验 workflow。
   `status` 会对每个待处理 attempt 执行一次非阻塞远程轮询，并对已终态的 attempt 自动回收 receipt；它是 Hiera 旁路中对应 `$exp-status` 检查/回收部分的入口。如果远程客户端在预留 attempt 后断线，对同一个运行执行 `recover --attempt ID`。恢复会检查冻结契约和候选快照，然后轮询并回收已有 handle，不会重新部署或再次预留 attempt；同时会修复 deep tuning ledger 记录，避免恢复后 loop 重复消耗同一个 bout。
5. **谨慎收尾。** `status` 和 `finalize` 只生成旁路 JSON 报告。搜索最佳结果只是探索证据；若要形成确认性结论，应把选定方法复制到正常实验代码路径，再调用已有、带用户审批的 `$exp-run` 和 `$exp-eval` workflow。不得自动把搜索结果写入 wiki。

## 契约规则

- 使用 argv 列表，禁止 shell 字符串。命令占位符只能是 `{candidate_dir}`、`{run_dir}`、`{attempt_dir}`、`{result_file}`、`{config_file}` 和 `{entrypoint}`。
- `result_file` 必须在新的 attempt 目录内创建 JSON；`score_path` 必须解析为有限数值；必须明确设为 `minimize` 或 `maximize`。
- `resources.max_evaluations` 在执行前预留，因此崩溃也不会消耗未记录的预算。日志和 receipt 保存在 attempt 目录。
- 两种适配器都要求 `evaluation.prepare_command` 和 `evaluation.collect_command` 为空；非空值会被拒绝。本地适配器直接执行已审核的 argv，远程适配器自行部署快照并回收结果。
- 保持候选源码模块化且显式。`candidate.editable_files` 是经过检查的文件白名单，支持嵌套相对路径。优先使用薄入口和职责明确的模块，避免把所有逻辑写进一个很大的 `run.py` 或重复的源码字符串。`admit --source-dir` 只从当前运行的 `drafts/` 导入白名单内的 UTF-8 源码；生成的 `config.json` 来自 candidate 的 `config` 对象，不应写入源码树。
- 批准远程契约前，还要检查 `resources.remote_config`、`remote_python`、`remote_gpu`、所选服务器配置，以及配置提供的 `conda` 或 `env_setup`。适配器会自动为 worker 和候选命令激活这个经过检查的环境，但不会运行项目级 `sync-code`/`setup-env`、安装候选依赖或传输数据集；这些依赖和数据必须已经存在于经检查的远程环境中，或由经过检查的候选命令显式处理。`env_setup` 是经过检查的服务器配置中的 shell 环境设置，不是候选在契约中提供的文本。
- 每次本地或远程执行都先在只追加 ledger 中预留 attempt，再启动进程。远程 attempt 同时保留持久化本地 handle 和远程执行 receipt。客户端中断后应恢复同一个 attempt；不得另占预算，也不得启动第二个 worker。`missing` 或 `unknown` 必须人工检查，远程失败绝不能当作成功完成。
- proposal 输出 coverage 优先级，status/finalize 输出派生的 experience revision。

## 边界

`wiki/`、`raw/` 和 runtime 契约只读。不得直接修改 `wiki/graph/`，不得重写 `wiki/log.md`，不得把 Hiera 候选作为 wiki 实体。不得向远程 push。每个实现批次都要向 `revise.md` 追加记录。
