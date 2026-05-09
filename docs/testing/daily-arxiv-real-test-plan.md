# OmegaWiki `/daily-arxiv` 真实测试计划

> **测试性质**：行为验证 / 集成验证 / 回归验证  
> **非单元测试**：所有测试均通过真实 API、真实文件系统、真实 GitHub Actions 或真实 Claude Code Skill 交互完成。  
> **测试环境**：`OmegaWiki/` 仓库；`wiki/` 当前为空（仅含 `.gitkeep`），`config/daily-arxiv.yml` 暂不存在。  
> **执行前提**：已配置 `SEMANTIC_SCHOLAR_API_KEY`（可选但建议），DeepXiv / SMTP 可选。

---

## 1. 测试目标与范围

### 1.1 目标
- 验证 `/daily-arxiv` 在 **inform** 与 **auto-ingest** 两种模式下的完整链路。
- 验证 GitHub Actions Workflow 在 `schedule` 与 `workflow_dispatch` 触发下的行为。
- 验证 `/daily-arxiv` 与 `/discover`、 `/ingest` 的边界与联动。
- 验证**空 wiki**、**无 config**、**外部 API 降级**等边界场景。
- 确保 **inform 模式绝不修改 `wiki/` 或 `raw/discovered/`**（核心回归项）。

### 1.2 范围
- **在范围内**：`tools/daily_arxiv.py`（config / prepare / finalize / recommend-llm / digest）、`.github/workflows/daily-arxiv.yml`、Skill `/daily-arxiv` 的交互命令（setup / status / disable / bare run）、`tools/send_email.py`、与 `/ingest` 的联动行为。
- **不在范围内**：`/discover` 内部 ranking 算法的正确性（已由工具层保证）、并行 ingest、非 arXiv 来源的 ingest。

---

## 2. 环境准备（Pre-flight Checklist）

执行以下命令确认基线状态：

```bash
cd /home/woden/Workspace/OmegaWiki

# 2.1 确认工具链可导入
python3 -c "import tools.fetch_arxiv, tools.fetch_s2, tools.fetch_deepxiv, tools.daily_arxiv; print('OK')"

# 2.2 确认 wiki 基线为空（或记录当前论文列表）
ls wiki/papers/ | grep -v .gitkeep | wc -l   # 预期：0

# 2.3 确认 config 不存在（用于测试默认推断路径）
test ! -f config/daily-arxiv.yml && echo "config missing as expected"

# 2.4 确认外部 API key 可用性（可选）
python3 -c "import os; print('S2:', bool(os.getenv('SEMANTIC_SCHOLAR_API_KEY')))"
python3 -c "import os; print('DeepXiv:', bool(os.getenv('DEEPXIV_TOKEN')))"

# 2.5 确认 workflow 文件存在
ls -la .github/workflows/daily-arxiv.yml

# 2.6 创建测试隔离目录
mkdir -p .daily-arxiv/test-runs
```

---

## 3. 测试场景矩阵

| 编号 | 场景 | 模式 | 触发方式 | 核心验证点 |
|------|------|------|----------|------------|
| T1 | 本地 bare inform，无 config，空 wiki | inform | 本地 CLI | 默认推断、无 wiki 突变 |
| T2 | 本地 inform，带 config，空 wiki | inform | 本地 CLI | config 解析、外部 enrich |
| T3 | 本地 tool-ranked fallback digest | inform | 本地 CLI | 无 decisions 时 fallback |
| T4 | 本地 OpenAI-compatible LLM recommend | inform | 本地 CLI | recommend-llm 子命令 |
| T5 | 本地 finalize 含人工 decisions | inform | 本地 CLI | decisions 合并、排序、digest 格式 |
| T6 | Skill `/daily-arxiv` 交互命令 | — | Claude Code | setup / status / disable UX |
| T7 | GitHub Actions workflow_dispatch inform | inform | CI | 完整 CI 链路、Artifact、Job Summary |
| T8 | GitHub Actions workflow_dispatch auto-ingest | auto-ingest | CI | auto-ingest 守卫、commit 行为 |
| T9 | 外部 API 降级与空 feed 边界 | inform | 本地 CLI | graceful degradation |
| T10 | inform → 用户手动 `/ingest` → `/discover` 联动 | inform+manual | Skill | 跨 skill 边界 |
| T11 | schedule 触发且 schedule.enabled=false | — | CI | 早退行为 |
| T12 | 邮件发送验证（可选） | inform | 本地/CI | SMTP 配置检查与真实投递 |

---

## 4. 测试详案

### T1：本地 bare inform，无 config，空 wiki

**目的**：验证工具在最小依赖下的自愈能力（missing config → inferred defaults）。

**步骤**：

```bash
cd /home/woden/Workspace/OmegaWiki
run_dir=".daily-arxiv/test-runs/t1"
mkdir -p "$run_dir"

# Step 1: config 子命令默认推断
python3 tools/daily_arxiv.py config --out "$run_dir/resolved-config.json"
cat "$run_dir/resolved-config.json"

# Step 2: prepare（不使用外部 API，避免网络波动影响基线测试）
python3 tools/daily_arxiv.py prepare \
  --wiki-root wiki \
  --out "$run_dir/recommendation-context.json" \
  --out-feed "$run_dir/feed.json" \
  --no-external

# Step 3: finalize（无 decisions，验证 fallback）
python3 tools/daily_arxiv.py finalize \
  --context "$run_dir/recommendation-context.json" \
  --out-md "$run_dir/digest.md" \
  --out-json "$run_dir/digest.json"

# Step 4: 输出检查
cat "$run_dir/digest.md" | head -30
cat "$run_dir/digest.json" | python3 -m json.tool | head -40
```

**预期结果**：
- `resolved-config.json` 中 `mode` = `inform`，`categories` 包含默认 5 个 CS/ML 类别。
- `recommendation-context.json` 中 `profile.is_sparse` = `true`；`candidates` 列表非空（arXiv RSS 有数据）。
- `digest.md` 包含标题 "Daily arXiv Recommendations"、Summary 统计、候选列表。
- `digest.json` 中 `llm_decision_available` = `false`，`notes` 包含 fallback 提示。
- `wiki/` 与 `raw/discovered/` 无任何新增或修改（关键回归项）。

**验证命令**：

```bash
git diff --name-only | grep -E "^(wiki|raw)/" | wc -l   # 预期：0
git status --short | grep -E "^(wiki|raw)/" | wc -l      # 预期：0
```

---

### T2：本地 inform，带 config，启用外部 enrich

**目的**：验证 config 解析、Semantic Scholar / DeepXiv 富化、profile 提取。

**步骤**：

```bash
run_dir=".daily-arxiv/test-runs/t2"
mkdir -p "$run_dir"

# Step 0: 创建临时 config
cat > "$run_dir/daily-arxiv.yml" <<'EOF'
mode: inform
hours: 48
categories: [cs.LG, cs.AI]
max_recommendations: 5
max_auto_ingest: 1
profile:
  derive_from_wiki: true
  positive_topics: ["transformer", "diffusion model"]
  negative_topics: ["quantum computing"]
enrichment:
  semantic_scholar: true
  deepxiv: true
  s2_anchor_limit: 3
  s2_candidate_limit: 6
  deepxiv_brief_limit: 4
EOF

# Step 1: config 解析
python3 tools/daily_arxiv.py config \
  --config "$run_dir/daily-arxiv.yml" \
  --out "$run_dir/resolved-config.json"

# Step 2: prepare（启用外部 enrich）
python3 tools/daily_arxiv.py prepare \
  --config "$run_dir/daily-arxiv.yml" \
  --wiki-root wiki \
  --out "$run_dir/recommendation-context.json" \
  --out-feed "$run_dir/feed.json"

# Step 3: 检查 enrich 信号
python3 - <<'PY'
import json
ctx = json.load(open(".daily-arxiv/test-runs/t2/recommendation-context.json"))
for c in ctx.get("candidates", [])[:3]:
    print(c["arxiv_id"],
          "S2:", bool(c.get("signals",{}).get("semantic_scholar")),
          "DeepXiv:", bool(c.get("signals",{}).get("deepxiv")))
print("notes:", ctx.get("notes", []))
PY
```

**预期结果**：
- `resolved-config.json` 中 `hours` = 48，`categories` = `["cs.LG", "cs.AI"]`，`max_recommendations` = 5。
- `recommendation-context.json` 中 `profile.keywords` 包含 `transformer`、`diffusion` 等正向词；`negative_topics` 被过滤。
- 前几个 candidate 的 `signals.semantic_scholar` 和/或 `signals.deepxiv` 非空（若 API 正常）。
- `notes` 中若无 API 失败则不应出现 "degraded"；若有失败则应有具体原因。

---

### T3：本地 tool-ranked fallback digest（兼容旧路径）

**目的**：验证 `digest` 子命令在无 LLM、无 decisions 时的 backward-compatible 行为。

**步骤**：

```bash
run_dir=".daily-arxiv/test-runs/t3"
mkdir -p "$run_dir"

# 复用 T1 的 feed
python3 tools/daily_arxiv.py digest \
  --feed ".daily-arxiv/test-runs/t1/feed.json" \
  --wiki-root wiki \
  --out-md "$run_dir/digest.md" \
  --out-json "$run_dir/digest.json" \
  --max-items 10
```

**预期结果**：
- `digest.json` 中 `recommendation_enabled` = `false`，`llm_decision_available` = `false`。
- `notes` 明确提示这是 compatibility digest，不包含评分或下载。
- 不修改 wiki。

---

### T4：本地 OpenAI-compatible LLM recommend（inform 模式）

**目的**：验证 `recommend-llm` 子命令及 third-party LLM 决策生成。

**前置条件**：环境变量 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 至少有一个可用（或本地有兼容服务）。

**步骤**：

```bash
run_dir=".daily-arxiv/test-runs/t4"
mkdir -p "$run_dir"

# Step 1: 准备 context（可复用 T2 的 context，但限流 candidate 数量以节省 token）
python3 -c "
import json
ctx = json.load(open('.daily-arxiv/test-runs/t2/recommendation-context.json'))
ctx['candidates'] = ctx['candidates'][:8]   # 限制 LLM 输入量
json.dump(ctx, open('$run_dir/compact-context.json', 'w'), ensure_ascii=False, indent=2)
"

# Step 2: 调用 third-party LLM
python3 tools/daily_arxiv.py recommend-llm \
  --context "$run_dir/compact-context.json" \
  --out "$run_dir/llm-decisions.json" \
  --limit 8 \
  --timeout 120

# Step 3: 检查 decisions 格式
python3 - <<'PY'
import json
d = json.load(open(".daily-arxiv/test-runs/t4/llm-decisions.json"))
print("provider:", d.get("provider"))
print("model:", d.get("model"))
print("decisions count:", len(d.get("decisions", [])))
for dec in d.get("decisions", [])[:3]:
    print(dec.get("arxiv_id"), dec.get("decision"), dec.get("confidence"), dec.get("score"))
print("notes:", d.get("notes", []))
PY
```

**预期结果**：
- `llm-decisions.json` 中 `provider` = `openai-compatible`，`mode` = `inform`。
- 所有 `decision` ∈ {`strong_recommend`, `maybe`, `skip`}，**绝不应出现 `ingest`**（third-party LLM 禁止 ingest）。
- `confidence` ∈ {`high`, `medium`, `low`}，`score` 为 0-1 数字或 `null`。
- 若 LLM 不可用，命令应抛出清晰错误并 exit 1。

---

### T5：本地 finalize 含人工 decisions

**目的**：验证 `finalize` 正确合并 LLM decisions、排序、auto-ingest 选择逻辑。

**步骤**：

```bash
run_dir=".daily-arxiv/test-runs/t5"
mkdir -p "$run_dir"

# Step 1: 创建模拟 decisions（含一个 ingest decision 以测试守卫）
python3 - <<'PY'
import json
ctx = json.load(open(".daily-arxiv/test-runs/t2/recommendation-context.json"))
candidates = ctx.get("candidates", [])
decisions = []
for i, c in enumerate(candidates[:5]):
    decisions.append({
        "arxiv_id": c["arxiv_id"],
        "decision": "ingest" if i == 0 else ("strong_recommend" if i == 1 else "maybe"),
        "confidence": "high" if i < 2 else "medium",
        "score": 0.95 - i * 0.1,
        "rationale": f"Test rationale {i}",
        "wiki_connections": ["test-topic"],
        "signals_used": ["arxiv", "wiki_profile"]
    })
json.dump({"decisions": decisions}, open(".daily-arxiv/test-runs/t5/mock-decisions.json", "w"), ensure_ascii=False, indent=2)
PY

# Step 2: finalize（inform 模式）
python3 tools/daily_arxiv.py finalize \
  --context ".daily-arxiv/test-runs/t2/recommendation-context.json" \
  --decisions "$run_dir/mock-decisions.json" \
  --out-md "$run_dir/digest-inform.md" \
  --out-json "$run_dir/digest-inform.json"

# Step 3: 创建 auto-ingest 版本的 context 并 finalize
python3 -c "
import json
ctx = json.load(open('.daily-arxiv/test-runs/t2/recommendation-context.json'))
ctx['config']['mode'] = 'auto-ingest'
json.dump(ctx, open('$run_dir/auto-ingest-context.json', 'w'), ensure_ascii=False, indent=2)
"

python3 tools/daily_arxiv.py finalize \
  --context "$run_dir/auto-ingest-context.json" \
  --decisions "$run_dir/mock-decisions.json" \
  --out-md "$run_dir/digest-auto.md" \
  --out-json "$run_dir/digest-auto.json"
```

**预期结果**：
- **inform digest**：`auto_ingest.enabled` = `false`；ingest decision 被保留但不触发任何文件系统写入；`listed_candidates` 按 `ingest > strong_recommend > score` 排序。
- **auto-ingest digest**：`auto_ingest.enabled` = `true`，`auto_ingest.selected` 仅包含第一个 candidate（`ingest` + `high`），且受 `max_auto_ingest=1` 限制；其余 ingest decision 应带有 `auto_ingest_blocked` 原因。
- 两种情况下 `wiki/` 均未被修改。

**验证命令**：

```bash
python3 - <<'PY'
import json
for name in ["digest-inform", "digest-auto"]:
    d = json.load(open(f".daily-arxiv/test-runs/t5/{name}.json"))
    print(name, "mode:", d.get("mode"), "auto_ingest:", d.get("auto_ingest", {}).get("enabled"))
    print("  selected:", [x.get("arxiv_id") for x in d.get("auto_ingest", {}).get("selected", [])])
    blocked = [c for c in d.get("candidates", []) if c.get("auto_ingest_blocked")]
    print("  blocked:", len(blocked))
PY
```

---

### T6：Skill `/daily-arxiv` 交互命令

**目的**：验证 Skill 层面的 UX：setup、status、disable、bare run。

**执行方式**：在 Claude Code 对话中，逐条发送以下命令，记录返回行为。

| 步骤 | 用户输入 | 预期行为 |
|------|----------|----------|
| 6.1 | `/daily-arxiv status` | 报告 config 不存在、workflow 存在、schedule 默认启用、API key 可见性（若有）、最近本地 digest（若有）。 |
| 6.2 | `/daily-arxiv setup` | 复制 `config/daily-arxiv.yml.example` → `config/daily-arxiv.yml`；解释所需 secrets；不修改 wiki。 |
| 6.3 | `/daily-arxiv` | 在已存在 config 后，bare run 执行 inform 模式：调用 `prepare` → 请求 LLM judgment → `finalize`；输出 digest 摘要；不修改 wiki。 |
| 6.4 | `/daily-arxiv --mode auto-ingest` | 仅当具备 Claude Code 运行时才应被允许；否则应拒绝或降级为 inform。 |
| 6.5 | `/daily-arxiv disable` | 将 `config/daily-arxiv.yml` 中的 `schedule.enabled` 设为 `false`，或明确告诉用户手动修改。 |

**回归检查**：
- 每次 skill 调用后，运行 `git status --short` 确认 `wiki/` 与 `raw/discovered/` 无未跟踪/修改文件。

---

### T7：GitHub Actions workflow_dispatch inform

**目的**：验证 CI 中最常用的手动触发链路（inform 模式）。

**步骤**：

1. 在 GitHub 仓库页面 → Actions → Daily arXiv recommendation → Run workflow。
2. 参数保持默认（mode 留空，send_email 默认 true 但无 SMTP secrets 时会跳过）。
3. 等待运行完成。

**验证清单**：

| 检查项 | 验证方法 |
|--------|----------|
| Workflow 成功完成 | Actions 页面绿色对勾 |
| `config` 步骤输出 `resolved-config.json` | 展开 "Resolve run configuration" 日志 |
| `prepare` 步骤生成 `feed.json` + `recommendation-context.json` | 展开 "Prepare recommendation context" 日志 |
| 若配置了 Claude auth，则 "Run Claude recommendation" 步骤执行，且生成 `llm-decisions.json` | 展开对应步骤日志 |
| 若无 Claude auth 但有 Review LLM，则 "Run OpenAI-compatible LLM recommendation" 执行 | 展开对应步骤日志 |
| 若两者皆无，则 "Note skipped Claude recommendation" 出现，且 `finalize` 使用 tool-ranked fallback | 展开 "Finalize digest" 日志 |
| `finalize` 生成 `digest.md` + `digest.json` | 日志末尾应显示 "listed -> .daily-arxiv/run/digest.md" |
| Job Summary 包含 digest Markdown | 在 Actions 运行详情页查看 Summary |
| Artifacts 上传成功 | 在 Actions 运行详情页下载 `daily-arxiv-<run_id>` Artifact，内含 5-6 个 JSON/Markdown 文件 |
| **无 commit 发生** | inform 模式下不应出现 "Commit auto-ingest changes" 的实质提交；确认仓库无新 commit |

---

### T8：GitHub Actions workflow_dispatch auto-ingest

**目的**：验证 CI 中 auto-ingest 模式的守卫、ingest 调用、commit 行为。

> ⚠️ **风险**：此测试会真实修改 `wiki/` 和 `raw/discovered/` 并 push commit。建议在 feature branch 或测试仓库执行，或提前备份。

**前置条件**：
- `ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_OAUTH_TOKEN` 已配置（workflow 会校验）。
- `mode` 已设为 `auto-ingest`，或手动 dispatch 时传入 `mode=auto-ingest`。

**步骤**：

1. 在 GitHub Actions 页面手动触发 workflow，输入 `mode = auto-ingest`，`max_auto_ingest = 1`（保守值）。
2. 等待运行完成。

**验证清单**：

| 检查项 | 预期结果 |
|--------|----------|
| Workflow 成功 | 绿色对勾 |
| `Validate auto-ingest credentials` 通过 | 若未配置 Claude auth，此步骤应失败并给出清晰错误 |
| Claude Code Action 被调用 | 步骤 "Run Claude recommendation and optional ingest" 出现 |
| Claude 实际调用了 `/ingest` | 在 Claude 输出日志中搜索 "ingest" 或查看 `llm-decisions.json` 中的 `ingest_status` |
| 仅 `max_auto_ingest` 数量的论文被 ingest | `digest.json` 中 `auto_ingest.selected` 长度 ≤ 1 |
| Commit 发生 | 仓库出现 "daily-arxiv auto-ingest" commit，仅包含 `wiki/` 和 `raw/discovered/` 的变更 |
| Commit 不包含其他文件 | `git show --stat <commit>` 确认无 `.daily-arxiv/`、无 workflow 文件等 |
| `digest.json` 中未选中 ingest 的 candidate 带有 `auto_ingest_blocked` | 下载 artifact 后检查 |

**回滚**：

```bash
# 若需撤销测试带来的 wiki 变更
git revert <auto-ingest-commit-sha> --no-edit
git push
```

---

### T9：外部 API 降级与空 feed 边界

**目的**：验证所有外部依赖失败时，pipeline 不崩溃，且 digest 仍有效。

**子场景**：

#### 9a. arXiv RSS 在指定窗口内无新论文

```bash
run_dir=".daily-arxiv/test-runs/t9a"
mkdir -p "$run_dir"

# 使用极小的 hours（如 1）在冷门类别上
python3 tools/daily_arxiv.py prepare \
  --hours 1 --categories cs.CE \
  --wiki-root wiki --out "$run_dir/context.json" --out-feed "$run_dir/feed.json"

python3 tools/daily_arxiv.py finalize \
  --context "$run_dir/context.json" \
  --out-md "$run_dir/digest.md" --out-json "$run_dir/digest.json"
```

**预期**：`digest.json` 中 `counts.new_candidates` = 0；`digest.md` 仍有效；exit code = 0。

#### 9b. 外部 enrich 完全关闭

复用 T1（`--no-external`），确认 `notes` 中提示 "Skip S2 and DeepXiv enrichment"，`signals.semantic_scholar` / `deepxiv` 均为 `null`。

#### 9c. 模拟 S2 API 失败（若无网络）

临时断网或设置无效 API key：

```bash
SEMANTIC_SCHOLAR_API_KEY=invalid_key_12345 \
  python3 tools/daily_arxiv.py prepare \
  --wiki-root wiki --out "$run_dir/bad-s2-context.json" --out-feed "$run_dir/bad-s2-feed.json"
```

**预期**：prepare 仍成功完成；`notes` 中包含 S2 degraded 信息；exit code = 0。

---

### T10：inform → 用户手动 `/ingest` → `/discover` 联动

**目的**：验证跨 skill 边界：daily-arxiv 推荐某篇论文后，用户通过 `/ingest` 将其纳入 wiki，随后 `/discover` 能基于这篇新论文产生关联推荐。

**步骤**：

1. 执行 T1 或 T7 获取一篇 `strong_recommend` 的论文，记录其 arXiv URL（例如 `https://arxiv.org/abs/2501.01234`）。
2. 在 Claude Code 中执行：
   ```
   /ingest https://arxiv.org/abs/2501.01234
   ```
3. 确认 `wiki/papers/` 下新增对应 `.md` 文件，`raw/discovered/` 下新增源文件，`wiki/index.md` 和 `wiki/log.md` 被更新。
4. 执行：
   ```
   /discover --anchor 2501.01234
   ```
   或
   ```
   /discover --from-wiki
   ```
5. 确认 `/discover` 输出的 shortlist 不包含已 ingest 的论文（dedup 正常）。

**回归检查**：
- `/ingest` 创建的论文页面 frontmatter 包含 `arxiv_id`、`title`、`authors`、`date`。
- `wiki/graph/edges.jsonl` 和 `citations.jsonl` 被正确追加。

---

### T11：schedule 触发且 schedule.enabled=false

**目的**：验证用户可通过 config 关闭定时任务，而 schedule 触发时应优雅跳过。

**步骤**：

1. 本地创建 config 并关闭 schedule：
   ```bash
   cp config/daily-arxiv.yml.example config/daily-arxiv.yml
   # 编辑 config/daily-arxiv.yml，设置 schedule.enabled: false
   ```
2. 在 GitHub Actions 中无法真正模拟 cron schedule，但可验证 workflow 逻辑：
   - 查看 workflow 中 "Note disabled schedule" 步骤：若 `schedule_enabled != 'true'`，则向 `GITHUB_STEP_SUMMARY` 写入提示并跳过后续核心步骤。
3. 或者，本地模拟 config 解析：
   ```bash
   python3 tools/daily_arxiv.py config --out /tmp/resolved.json
   python3 -c "import json; print(json.load(open('/tmp/resolved.json'))['config']['schedule']['enabled'])"
   ```

**预期**：`schedule.enabled: false` 时，workflow 的 `resolve` 步骤输出 `schedule_enabled=false`，后续 `prepare` / `finalize` 被 `if` 条件跳过。

---

### T12：邮件发送验证（可选，取决于 SMTP 配置）

**目的**：验证 `tools/send_email.py` 在真实 SMTP 下的行为。

**子场景**：

#### 12a. 配置检查（无 SMTP secrets）

```bash
unset SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_FROM DAILY_ARXIV_EMAIL_TO
python3 tools/send_email.py --check-config
```

**预期**：exit code ≠ 0， stderr 提示缺少哪些环境变量。

#### 12b. 配置检查（有 secrets）

若 secrets 已配置：

```bash
python3 tools/send_email.py --check-config
```

**预期**：exit code = 0，输出 "SMTP configuration OK"。

#### 12c. 真实发送（本地）

```bash
# 复用 T1 的 digest
python3 tools/send_email.py \
  --subject "[TEST] OmegaWiki daily arXiv" \
  --body-file ".daily-arxiv/test-runs/t1/digest.md" \
  --to "your-test-email@example.com"
```

**预期**：收件箱收到邮件，正文为 Markdown 纯文本，Subject 正确。

#### 12d. CI 邮件发送

在 T7/T8 中若 `send_email=true` 且 SMTP secrets 配置正确，应在 workflow 的 "Send digest e-mail" 步骤看到成功日志。若 secrets 缺失，该步骤应失败但**不阻断**整个 workflow（当前 workflow 中该步骤没有 `continue-on-error: true`，因此实际会失败并导致 workflow 失败——这是一个需要关注的实现细节）。

---

## 5. 数据与产物检查清单

每次测试运行后，以下产物应满足格式约束：

### 5.1 `resolved-config.json`

```json
{
  "config": {
    "mode": "inform|auto-ingest",
    "hours": <int>,
    "categories": [<str>],
    "max_recommendations": <int>,
    "max_auto_ingest": <int>,
    "email": {"enabled": <bool>},
    "schedule": {"enabled": <bool>, "cron": <str>},
    "profile": {...},
    "enrichment": {...}
  },
  "notes": [<str>]
}
```

### 5.2 `recommendation-context.json`

```json
{
  "generated_at": <ISO-8601>,
  "mode": "inform|auto-ingest",
  "config": {...},
  "profile": {
    "is_sparse": <bool>,
    "anchors": [...],
    "keywords": [...]
  },
  "counts": {
    "feed_total": <int>,
    "already_in_wiki": <int>,
    "new_candidates": <int>
  },
  "candidates": [
    {
      "arxiv_id": <str>,
      "title": <str>,
      "is_known": <bool>,
      "signals": {
        "arxiv_rss": true,
        "semantic_scholar": <dict|null>,
        "deepxiv": <dict|null>,
        "llm": <bool|null>
      }
    }
  ],
  "notes": [<str>]
}
```

### 5.3 `llm-decisions.json`

```json
{
  "provider": "claude|openai-compatible",
  "model": <str>,
  "mode": "inform|auto-ingest",
  "generated_at": <ISO-8601>,
  "decisions": [
    {
      "arxiv_id": <str>,
      "decision": "strong_recommend|maybe|skip|ingest",
      "confidence": "high|medium|low",
      "score": <float|null>,
      "rationale": <str>,
      "wiki_connections": [<str>],
      "signals_used": [<str>],
      "ingest_status": <str>,      // 可选，仅 auto-ingest 后
      "ingest_error": <str>        // 可选，仅失败时
    }
  ],
  "notes": [<str>]
}
```

### 5.4 `digest.json`

```json
{
  "generated_at": <ISO-8601>,
  "mode": "inform|auto-ingest",
  "llm_decision_available": <bool>,
  "counts": {...},
  "listed_candidates": [...],
  "auto_ingest": {
    "enabled": <bool>,
    "cap": <int>,
    "selected": [...],
    "requires_ingest_skill": true
  },
  "notes": [<str>]
}
```

---

## 6. 回归测试重点

| 回归项 | 检查方法 |
|--------|----------|
| **inform 模式零写入** | 每次 inform 测试后 `git status --short` 确认 `wiki/`、`raw/discovered/`、`.daily-arxiv/run/`（本地）无变更。 |
| **auto-ingest 只通过 `/ingest`** | 检查 auto-ingest 后的 commit diff，确认无手写的 paper page、无手写的 graph edge、无手写的 index 更新（所有变更应由 `/ingest` 工具产生）。 |
| **decisions 格式兼容** | `llm-decisions.json` 支持 `{"decisions": [...]}` 和裸 list 两种格式；支持以 arxiv_id 为 key 的 dict 格式。用 T5 的 mock 数据验证。 |
| **空 wiki profile 不自毁** | T1 中 `is_sparse=true` 时 prepare 仍成功，且 candidate 的 `tool_rank_score` 不为 `null`。 |
| ** digest 始终可生成** | 即使 feed 为空、decisions 缺失、所有 candidate 已存在，finalize 或 digest 子命令 exit code = 0，产物 JSON/Markdown 均有效。 |

---

## 7. 执行顺序建议

为避免污染 wiki 并最大化早期发现问题：

```
Day 1 — 本地安全测试（不改 wiki）
  T1 → T3 → T9a/b/c → T5 → T2 → T4

Day 2 — Skill 交互测试
  T6（setup / status / disable / bare run）

Day 3 — CI 测试（inform，无风险）
  T7 → T11

Day 4 — 联动与邮件测试
  T10 → T12

Day 5 — CI 测试（auto-ingest，有风险，最后执行）
  T8（在隔离分支或确认可回滚后执行）
```

---

## 8. 问题记录模板

测试过程中发现的问题使用以下格式记录：

```markdown
### Issue-编号
- **场景**：T?
- **现象**：...
- **复现步骤**：...
- **预期 vs 实际**：...
- **影响**：blocker / major / minor / cosmetic
- **根因假设**：...
- **修复状态**：open / fixed / wontfix
```

---

## 9. 附录：快速检查命令速查

```bash
# 检查 wiki 是否被修改
git diff --name-only | grep -E "^(wiki|raw)/"

# 检查 artifact 完整性
unzip -l daily-arxiv-<run_id>.zip

# 检查 digest JSON schema
python3 -c "import json; d=json.load(open('digest.json')); assert 'listed_candidates' in d"

# 检查 decisions 中无非法 decision 值
python3 -c "
import json
d=json.load(open('llm-decisions.json'))
valid = {'strong_recommend','maybe','skip','ingest'}
for x in d.get('decisions',[]):
    assert x['decision'] in valid, x
print('OK')
"

# 快速查看候选数
python3 -c "import json; c=json.load(open('recommendation-context.json'))['counts']; print(c)"
```
