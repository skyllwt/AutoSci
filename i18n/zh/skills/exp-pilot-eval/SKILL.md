---
description: 预实验结果评估 — 读取预实验结果，应用成功标准，更新 idea 页面（pilot_result，失败时更新 failure_reason），生成 PILOT_VERDICT_REPORT。由 /ideate Phase 5 在 /exp-pilot-run 之后调用。
argument-hint: <idea-slug> [--auto]
---

# /exp-pilot-eval

> 评估预实验结果并更新关联的 idea 页面。
> 从 `experiments/pilot/code/{slug}/results/` 读取预实验结果，应用判定逻辑（pass/fail/inconclusive），更新 idea 的 `pilot_result`、`failure_reason` 和 `status` 字段。
> 由 `/ideate` Phase 5 在 `/exp-pilot-run` 完成后调用。

## Inputs

- `idea-slug`：刚完成预实验的 idea 的 slug
- `--auto`（可选）：自动模式，不暂停等待用户确认（由 `/research` 调用时使用）

## Outputs

- `wiki/ideas/{slug}.md` — 更新 `pilot_result`（始终）、`failure_reason`（失败时）、`status`（失败时 → `failed`）
- `wiki/log.md` — 追加日志
- **PILOT_VERDICT_REPORT**（输出到终端）— 判定结果、wiki 变更摘要、下一步建议
- `experiments/pilot/{slug}/report.md` — PILOT_VERDICT_REPORT 文件副本（持久记录）

## Wiki Interaction

### Reads
- `wiki/ideas/{slug}.md` — 关联 idea 当前状态：`status`、`pilot_result`、`failure_reason`
- `experiments/pilot/code/{slug}/results/seed_*.json` — 预实验结果
- `experiments/pilot/code/{slug}/pilot.log` — 预实验运行日志（用于失败诊断：错误、警告、运行时行为）
- `experiments/pilot/{slug}.yaml` — Pilot Spec（用于 success_criterion 和 baseline 参考）

### Writes
- `wiki/ideas/{slug}.md` — 更新 `pilot_result`、`failure_reason`（失败时）、`status`（失败时）
- `wiki/log.md` — 追加操作日志
- `experiments/pilot/{slug}/report.md` — PILOT_VERDICT_REPORT 文件副本

### Graph edges created
- 无。预实验评估不创建 graph edges（正式实验的 edges 由 `/exp-eval` 创建）。

## Workflow

**Step 1: 加载上下文**

1. 读取 idea 页面 `wiki/ideas/{slug}.md`：
   - 当前 `status` 和 `pilot_result`
   - 当前 `failure_reason`（对 proposed idea 应为空）

2. 读取预实验结果 `experiments/pilot/code/{slug}/results/seed_*.json`：
   - 解析结果文件（JSON）
   - 计算每个 metric 的 mean ± std（跨 seeds）

3. 读取预实验日志 `experiments/pilot/code/{slug}/pilot.log`：
   - 扫描错误、警告、OOM、发散信号
   - 提取运行时行为上下文，用于失败诊断和判定报告

4. 读取 Pilot Spec `experiments/pilot/{slug}.yaml`：
   - 提取 `success_criterion`（pass、fail、inconclusive 条件）
   - 提取 `baseline.expected_value` 用于对比

**Step 2: 应用判定逻辑**

根据 Pilot Spec 的 success_criterion 评估预实验结果。判定阈值故意宽松 — 预实验的目的是检测明显失败，而非衡量最终性能。

- **Pass**：预实验未显示明确失败。由于预实验使用缩减的 batch size（论文的 1/4–1/8）和缩短的训练（完整步数的 10–30%），结果天然带有噪声且偏向下限。因此：比 baseline 有改进、与 baseline 基本持平、甚至略差于 baseline 都算 pass。路径 C 下，若现有方法在新设定下确实失败（gap 被确认），也算 pass。
- **Fail**：预实验显示明确、无歧义的失败（发散、相比 baseline 严重退化、根本性不兼容）。阈值较高 — 只有明显不可行的 idea 才应在此阶段被淘汰。
- **Inconclusive**：预实验有噪声或不确定 — 结果无法明确判定为 pass 或 fail。

**Step 3: 更新 Idea 页面**

若 verdict == `pass`：
- 设置 `pilot_result`：`"pass — <关键指标 vs baseline 的一句话总结>"`
- Status 不变（保持 `proposed` 或当前状态）
- 示例：`"pass — accuracy 0.82 vs baseline 0.80, loss converges"`

若 verdict == `fail`：
- 设置 `pilot_result`：`"fail — <具体失败>"`
- 设置 `failure_reason`：`"[pilot] <具体失败描述>"`
  - `[pilot]` 前缀区分于 Phase 3 的 `[filter]` 淘汰和 `/exp-eval` 的实验后失败
- 将 status 转为 `failed`：
  ```bash
  python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md pilot_result "fail — <具体失败>"
  python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to failed --reason "[pilot] <具体失败描述>"
  ```
  - `transition` 会校验生命周期规则（如拒绝从 `validated` 降级到 `failed`）并自动设置 `failure_reason` 和 `date_resolved`。
- failure_reason 示例：`"[pilot] loss diverged after 50 steps (reached 1e5 vs baseline 0.3)"`

若 verdict == `inconclusive`：
- 设置 `pilot_result`：`"inconclusive — needs full experiment"`
- Status 不变

**Step 4: 报告**

1. 若 `--auto` 未设置：在终端展示判定结果和 wiki 变更，对边界情况等待用户确认

2. 追加日志：
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "exp-pilot-eval | {slug} | verdict: {verdict} | pilot_result: {result}"
   ```

3. 输出 **PILOT_VERDICT_REPORT** 到终端并写入 `experiments/pilot/{slug}/report.md`：
   ```markdown
   # Pilot Verdict Report: {slug}

   ## Verdict: {pass / fail / inconclusive}

   ## Results Summary
   | Metric | Baseline | Pilot (mean±std) | Δ |
   |--------|----------|------------------|---|
   | {metric} | {baseline-value} | {mean}±{std} | {delta} |

   ## Pilot Log
   - 日志：experiments/pilot/code/{slug}/pilot.log
   - 关键信号：{日志中观察到的错误/警告/OOM/发散，或"运行正常"}

   ## Wiki Changes
   | Page | Field | Old | New |
   |------|-------|-----|-----|
   | ideas/{slug} | pilot_result | {old} | {new} |
   | ideas/{slug} | status | {old} | {new} | (only if changed) |
   | ideas/{slug} | failure_reason | — | {new} | (only if failed) |

   ## Next Steps
   - {if pass: proceed to /exp-design for full experiments}
   - {if fail: idea eliminated; review pilot log for details}
   - {if inconclusive: proceed to full experiment with caution}
   ```

## Constraints

- **只处理已预实验的 ideas**：结果必须存在于 `experiments/pilot/code/{slug}/results/`
- **failure_reason 必须具体**：不能是模糊的 "pilot failed" — 需包含什么失败了以及为什么
- **Idea 生命周期只向前**：`proposed → failed`（不能从 validated 退回 failed）
- **不创建 graph edges**：正式实验的 edges 由 `/exp-eval` 创建
- **Pass 阈值故意宽松**：检测明显失败，而非衡量最终性能
- **`[pilot]` 前缀在 failure_reason 中必须存在**：区分于 `[filter]` 和实验后失败

## Error Handling

- **Idea 页面找不到**：报告错误，建议先运行 `/ideate`
- **预实验结果找不到**：报告错误，建议先运行 `/exp-pilot-run`
- **Idea 已经 failed**：报告当前状态，不覆盖
- **Idea 已经 validated**：拒绝降级 status，报告警告
- **Pilot Spec 找不到**：报告错误，建议先运行 `/ideate` 生成 spec

## Dependencies

### Skills (via Skill tool)
- 无

### Tools (via Bash)
- `python3 tools/research_wiki.py set-meta wiki/ideas/{slug}.md <field> "<value>"` — 更新 idea 字段（如 pilot_result）
- `python3 tools/research_wiki.py transition wiki/ideas/{slug}.md --to <status> [--reason "..."]` — 转换 idea 生命周期状态
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### Claude Code Native
- `Read` — 读取 idea 页面、预实验结果、预实验日志、Pilot Spec
- `Edit` — 更新 idea 页面字段
- `Bash` — 执行 research_wiki.py 命令

### Called by
- `/ideate` Phase 5
- 用户手动调用
