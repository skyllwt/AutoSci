---
description: 交互式 API key 配置引导 — 检测当前 .env 状态，逐步引导配置 Semantic Scholar、DeepXiv 和 Review LLM
---

# /setup

> 引导你完成 ΩmegaWiki 的可选 API key 配置。
> 读取当前 `.env`，展示已配置和未配置的内容，并帮助你逐步设置每个 key，
> 包括清晰解释每个 key 的作用和获取方式。
> 可随时重新运行，只更新你选择配置的 key。

## Inputs

- 不需要任何参数
- 读取：`.env`（当前配置状态）
- 读取：`config/setup-guide.md`（每个 key 的参考说明）

## Outputs

- 更新后的 `.env`（包含新配置的 key）
- 当前配置状态总结

## Wiki Interaction

### Reads
- 无（setup 在 wiki 创建之前运行）

### Writes
- 无（不修改 wiki）

## Workflow

### Step 1：读取配置参考文档

读取 `config/setup-guide.md`，加载所有可配置 key 的完整参考信息，
包括每个 key 的作用、使用它的 skill、获取方式以及未配置时的降级行为。

### Step 2：检测当前环境

运行以下命令检查已配置的内容：

```bash
python3 -c "
import sys, os
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
keys = {
    'SEMANTIC_SCHOLAR_API_KEY': 'Semantic Scholar',
    'DEEPXIV_TOKEN':            'DeepXiv',
    'LLM_API_KEY':              'Review LLM（API key）',
    'LLM_BASE_URL':             'Review LLM（base URL）',
    'LLM_MODEL':                'Review LLM（模型名）',
}
for k, label in keys.items():
    v = os.environ.get(k, '').strip()
    print(f'SET:{k}' if v else f'UNSET:{k}')
"
```

同时检测 Python 环境和 `.venv` 状态：
```bash
ls .venv/ 2>/dev/null && echo "venv:present" || echo "venv:absent"
python3 --version
```

### Step 3：展示配置状态

向用户展示清晰的状态总结，按状态分组：

```
ΩmegaWiki 配置状态
================================
✓  ANTHROPIC_API_KEY      — 由 Claude Code 管理（claude login）

推荐配置：
✗  Semantic Scholar        — 未配置（引用链扩展速度慢 3 倍，建议配置免费 key）

可选：
✗  DeepXiv                 — 未配置（语义搜索不可用）
✗  Review LLM              — 未配置（跨模型 review 不可用）
```

询问用户："您想配置哪些？（可以跳过任意一个或全部）"

### Step 4：配置各 Key（用户决定）

对用户想要配置的每个 key，按以下子流程处理。
写入 `.env` 前必须向用户确认。

---

#### 4a：Semantic Scholar API Key

**解释**："Semantic Scholar 提供论文引用数据和检索功能。
被 /ingest、/init、/novelty、/ideate 使用。免费获取。
**推荐配置** — 不配置的话，/init 速度慢 3 倍，引用链扩展效率大幅下降。"

**引导获取**："访问 https://www.semanticscholar.org/product/api，
点击 'Get API Key'，免费申请。"

**询问**："您是否有 Semantic Scholar API key？（粘贴，或输入 'skip' 跳过）"

**如果提供了 key**，写入 `.env`：
使用 Edit 工具更新 `.env`：
- 若已有 `SEMANTIC_SCHOLAR_API_KEY=`（即使为空），替换该行
- 否则追加 `SEMANTIC_SCHOLAR_API_KEY=<值>`

---

#### 4b：DeepXiv Token

**解释**："DeepXiv 提供语义论文检索、AI 论文摘要（TLDR）和热门论文检测。
被 /daily-arxiv、/novelty、/ideate、/ingest、/init 使用。
不配置时，这些 skill 回退到 arXiv RSS + Semantic Scholar，功能全部可用，
只是缺少语义搜索和 TLDR 功能。"

**提供三种选项**：
1. **自动注册**（推荐，免费，秒完成）：运行注册请求
2. **粘贴已有 token**：用户提供自己的 token
3. **跳过**：稍后配置

**选项 1 — 自动注册**，运行：
```bash
python3 -c "
import sys, json
from uuid import uuid4
try:
    import requests
except ImportError:
    print('ERROR: requests 未安装', file=sys.stderr)
    sys.exit(1)

suffix = uuid4().hex[:10]
payload = {
    'sdk_secret': 'UuZp0i83svQU7_naUEexczc-X3NWv7lvNkD8e3sPyng',
    'name': f'deepxiv_{suffix}',
    'email': f'{suffix}@example.com',
}
try:
    resp = requests.post('https://data.rag.ac.cn/api/register/sdk', json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)

if not result.get('success'):
    print(f'ERROR: {result.get(\"message\", \"unknown\")}', file=sys.stderr)
    sys.exit(1)

token = result.get('data', {}).get('token', '')
daily_limit = result.get('data', {}).get('daily_limit', 1000)
if not token:
    print('ERROR: 响应中没有 token', file=sys.stderr)
    sys.exit(1)

print(token)
print(f'daily_limit:{daily_limit}', file=sys.stderr)
"
```
stdout → token 值；stderr → 人类可读状态（直接透传，不要抑制）。

注册成功后写入 `.env`。失败时显示错误信息，并提供让用户手动粘贴 token 的选项。

---

#### 4c：Review LLM

**解释**："Review LLM 将 ΩmegaWiki 连接到第二个 AI 模型，进行独立的对抗性评审。
被 /review、/novelty、/ideate、/paper-plan、/paper-draft、/rebuttal、/refine、
/exp-eval、/exp-design，以及 /daily-arxiv 的 inform 推荐使用。支持任何 OpenAI-compatible API。
不配置时，这些 skill 跳过跨模型 review 步骤（功能全部保留）。"

**展示 provider 对照表**（来自 `config/setup-guide.md` Key 3 部分）。

**如果用户问 'OpenAI-compatible 是什么意思'**：解释为任何接受
`POST /chat/completions`、请求体格式为 `{"model": "...", "messages": [...]}` 的 API。

**依次询问**：
1. `LLM_BASE_URL` — 例如 `https://api.deepseek.com/v1`
2. `LLM_API_KEY` — 对应 provider 的 API key
3. `LLM_MODEL` — 模型名称，例如 `deepseek-chat`

**格式校验**：Base URL 应以 `http://` 或 `https://` 开头，通常以 `/v1` 结尾。
格式看起来有问题时，写入前询问用户确认。

**用户确认后写入** `.env` 中的三个变量。

**写入后提醒**：Review LLM MCP server 在 Claude Code 启动时读取 `.env`，
变更在重启 Claude Code 后生效。

---

#### 4d：arXiv Categories（仅用户主动询问时）

此 key 有合理默认值（`cs.LG,cs.CV,cs.CL,cs.AI,stat.ML`）。
仅当用户明确要求，或其研究领域明显不在 ML/AI 范围内时才配置。

---

### Step 5：验证配置

用户完成配置后，运行验证检查：

```bash
python3 -c "
import sys, os
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
keys = ['SEMANTIC_SCHOLAR_API_KEY', 'DEEPXIV_TOKEN', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for k in keys:
    v = os.environ.get(k, '').strip()
    print(f'已配置  {k}' if v else f'未配置  {k}')
"
```

展示最终总结。对仍未配置的 key，简要说明其解锁的功能，
并告知用户可以随时重新运行 `/setup` 来补充配置。

### Step 6：下一步

如果是全新安装（`wiki/` 目录不存在）：
```
配置完成。接下来：
  • 将你自己的论文放入 raw/papers/（.tex 或 .pdf）
  • 可选：把意图笔记放入 raw/notes/，网页存档放入 raw/web/
  • /init 与直接本地 /ingest 会自动管理 raw/discovered/ 与 raw/tmp/ 下的生成内容
  • 运行：/init [你的研究主题]
```

如果 `wiki/` 已存在：
```
配置已更新。重启 Claude Code 后 Review LLM 变更生效。
```

## Constraints

- **不覆盖已有非空值**，除非先征得用户同意
- **不在输出中展示完整 key 值**，只显示前 8 个字符 + `...`
- **只写入 `.env`**，不写入 `~/.env` 或其他位置
- **不读写 wiki**，此 skill 可在 wiki 创建之前运行
- **优雅跳过**：若用户说"全部跳过"，展示状态总结后直接退出

## Error Handling

- **`.env` 不存在**：提示用户 `setup.sh` 可能未运行，提供创建命令：
  ```bash
  cp config/.env.example .env
  ```
  然后继续配置流程。

- **`config/setup-guide.md` 不存在**：直接使用本 SKILL.md 中的信息继续。

- **DeepXiv 注册失败**（网络错误、服务器错误）：清晰展示错误信息，
  提供让用户手动粘贴 token 的选项，或跳过。

- **Python 环境问题**（`tools/_env.py` 找不到）：提示 `.venv` 可能未激活，
  但仍通过 shell 或 Python 文件读取检查 `.env` 当前状态。

## Dependencies

### Tools（via Bash）
- `python3 -c "import _env; ..."` — 读取当前 `.env` 状态
- `python3 -c "import requests; ..."` — DeepXiv 自动注册 HTTP 请求

### Files Read
- `config/setup-guide.md` — 所有可配置 key 的完整参考
- `.env` — 当前配置（读 + 写）

### Files Written
- `.env` — 通过 Edit 工具写入新配置的 key

### 不调用 MCP server、不访问 wiki、不调用其他 skill
