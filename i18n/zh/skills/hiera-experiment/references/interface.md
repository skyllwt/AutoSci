# Hiera 旁路接口

在 AutoSci 项目根目录运行 CLI：

```text
python -m tools.hiera.cli --project . init <experiment-slug> --run-id <run-id> \
  --contract path/to/contract-overrides.json
```

远程客户端中断后，使用同一个已预留 attempt 恢复：

```text
python -m tools.hiera.cli --project . recover <experiment-slug> --run-id <run-id> \
  --attempt <attempt-id>
```

要对一个 Hiera run 中的所有待处理 attempt 做一次快速、非阻塞的远程检查，可执行：

```text
python -m tools.hiera.cli --project . status <experiment-slug> --run-id <run-id>
```

该命令会对每个待处理的远程 handle 轮询一次，发现终态时自动回收 receipt，绝不会提交新的 attempt。`recover` 仍然是恢复单个中断 attempt 的阻塞式路径；它会把已完成的 deep attempt 按 attempt ID 幂等地补记为 tuning bout。

`init` 创建隔离目录：

```text
runs/hiera/<experiment-slug>/<run-id>/
├── manifest.json
├── semantic_space.json
├── task_contract.yaml       # JSON 语法，同时符合 YAML 1.2
├── ledger.jsonl              # 只追加事件源
├── drafts/<candidate-id>/    # admission 前经过检查的模块化源码
├── candidates/<candidate-id>/
├── attempts/<attempt-id>/
└── FINAL_REPORT.json         # finalize 创建
```

契约 override 是合并到生成契约的 JSON 对象。可执行的最小内容是：

```json
{
  "candidate": {"entrypoint": "run.py", "editable_files": ["run.py"]},
  "evaluation": {
    "evaluate_command": ["python", "-c", "..."],
    "result_file": "results/result.json",
    "score_path": "score",
    "metric": "validation_loss",
    "direction": "minimize"
  },
  "resources": {"environment": "local", "timeout_seconds": 3600, "max_evaluations": 20}
}
```

命令必须是 argv 数组，只能使用 `{candidate_dir}`、`{run_dir}`、`{attempt_dir}`、`{result_file}`、`{config_file}` 和 `{entrypoint}`。执行使用 `shell=False`。结果文件在新的 attempt 目录内创建，必须是 JSON，且 `score_path` 对应有限数值。

两种适配器都支持 `preflight_command`。`prepare_command` 和 `collect_command` 必须为空：本地适配器不需要传输阶段，Hiera 远程适配器会自行部署候选快照并回收声明的产物。

## 远程执行

只有在 `approve` 前已经检查远程边界的契约中，才能把 `resources.environment` 设为 `remote`。远程资源字段如下：

| 字段 | 默认值 | 含义 |
|---|---|---|
| `remote_config` | `config/server.yaml` | 项目内的相对服务器配置路径；通过 `tools.remote` 读取，提供 `host`、`user`、`work_dir`、SSH 选项和已检查的运行环境设置。 |
| `remote_python` | `python3` | 远程 worker RPC 使用的单个 Python 可执行文件；也会替换候选 argv 开头的 `python` 或 `python3`。它是可执行文件路径或名称，不是 shell 命令。 |
| `remote_poll_seconds` | `5` | 状态检查之间的正数间隔。 |
| `remote_gpu` | 空 | 显式的逗号分隔 GPU 编号。为空且 `accelerator` 不是空、`cpu` 或 `none` 时，适配器选择一个当前空闲 GPU；CPU 运行不选择 GPU。 |

`config/server.yaml` 必须符合既有远程 helper 契约，并提供 `conda.path` 与 `conda.env`，或提供 `env_setup`。使用 `conda` 时，worker 通过 `conda run` 包装候选 argv；没有 `conda` 时，已检查的 `env_setup` 会由 `bash -lc` 先执行，随后执行经过 shell quoting 的候选 argv。这是自动激活远程环境；Hiera 不会调用项目级 `sync-code` 或 `setup-env`，不会安装候选 requirements，也不会传输数据集。因此候选依赖和数据需要预先存在于经过检查的远程环境中，或由经过检查的候选命令显式处理。服务器配置变化应视为已检查执行环境发生变化。凭据不会写入 Hiera 产物。

对于 `<attempt-id>`，适配器只把 admission 后的候选文件映射传到：

```text
<work_dir>/runs/hiera/<experiment-slug>/<run-id>/<attempt-id>/
├── candidate/               # admission 后的不可变文件映射
├── job.json                 # 绑定 token 的部署 receipt
├── worker.py
├── worker.pid
├── execution.json           # 持久化 running/terminal 状态
├── preflight_stdout.log
├── preflight_stderr.log
├── stdout.log
├── stderr.log
└── <evaluation.result_file>
```

该路径不会同步整个项目、push 分支或传输 wiki。worker 以 candidate 目录为 `cwd` 执行 `preflight_command` 和 `evaluate_command`。命令应通过绝对 `{result_file}` 占位符写入 JSON 结果。回收范围仅包括四个日志和声明的结果文件；只有远程 execution receipt 表示 evaluation 成功且返回码为零，并且 `score_path` 解析为有限数值时，才能接受成功分数。

远程部署前会先在 `ledger.jsonl` 中预留预算。本地 attempt 目录持久化 `remote.json`，绑定 attempt ID、候选、token、主机、服务器配置摘要和远程路径。同一个 token 的重复部署是幂等操作，绝不会启动第二个 worker。`status` 会对待处理 handle 执行一次非阻塞轮询，并在终态时回收结果；客户端断线后，`recover --attempt <attempt-id>` 会检查冻结契约和候选快照，再轮询并回收同一个 attempt，不会再次预留预算或提交部署。两条路径都会按 attempt ID 将完成的 deep evaluation 幂等补记为 tuning bout。`running` 保持 pending；远程终态失败只作为失败评估回收；`missing` 或 `unknown` 只有在显式恢复操作中才会作为失败收尾，绝不能报告为成功完成，也不得自动重新启动。

## 模块化候选源码

复杂实验应让 metadata spec 保持简短，把源码放入经过检查的目录树：

```text
runs/hiera/<experiment-slug>/<run-id>/drafts/method-variant-a/
├── run.py                    # 薄的 CLI/训练入口
└── experiment/
    ├── __init__.py
    ├── data.py               # 数据加载和划分策略
    ├── models/
    │   ├── __init__.py
    │   └── method.py          # 方法特有的模型变体
    ├── training.py           # 优化循环
    └── evaluation.py         # 指标和结果序列化
```

实际目录按实验需要组织，不要为了套用示例而创建空模块。把每个源码文件列入 `candidate.editable_files`，metadata spec 中不再塞入大段源码，然后执行：

```text
python -m tools.hiera.cli --project . admit <experiment-slug> --run-id <run-id> \
  --spec path/to/method-variant-a.json \
  --source-dir runs/hiera/<experiment-slug>/<run-id>/drafts/method-variant-a
```

`--source-dir` 与 `spec.files` 互斥。源码目录必须位于本次运行的 `drafts/` 内，只能包含 `candidate.editable_files` 列出的 UTF-8 文件，不能包含 `config.json`；工具会根据 spec 的 `config` 生成该文件。嵌套目录会原样保留在不可变 candidate 快照中。小型单文件候选仍可使用下面的内联 `files` 形式。

每个内联 `admit --spec` 文件格式如下：

```json
{
  "candidate_id": "method-variant-a",
  "operation": "fresh",
  "parents": [],
  "semantic_point": {"dim-method": "hyp-baseline-method"},
  "config": {"learning_rate": 0.001},
  "files": {"run.py": "# 完整候选源码\n"}
}
```

工具会加入 `config.json` 并记录每个文件摘要；任何已 admission 的文件发生变化都会被拒绝执行。`parents` 必须指向较早的候选。源码或配置改变时必须使用新候选 ID 和新快照。命令应使用经过检查的入口和配置占位符，例如 `{"evaluate_command": ["python", "{entrypoint}", "--config", "{config_file}", "--output", "{result_file}"]}`。

`propose` 只提出语义点，由 Claude Code 或用户编写、检查并 admission 候选文件。`approve` 冻结契约摘要；`preflight`、`run`、`recover`、`tune` 和 `loop` 都要求该冻结摘要。契约含有经检查的 `candidate.config_schema` 时，`tune --candidate ID --limit N` 会复制不可变源码快照、生成边界内的配置变体、执行评估，并将每个变体记录为子候选。`loop` 反复选择符合条件的 deep 候选并记录 tuning bout，直到轮数或契约预算耗尽。
