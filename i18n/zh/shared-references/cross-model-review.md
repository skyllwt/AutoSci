# 评审独立性原则

> 引用方: `/review`, `/novelty`, `/ideate`, `/exp-eval`, `/exp-design`, `/paper-plan`, `/paper-draft`, `/rebuttal`, `/refine`

---

## Core Rule

When using a Review LLM (any external model) as a reviewer or cross-verifier, **never share the primary model's own judgment, scores, or conclusions** with the reviewer before they form their independent assessment.

The reviewer must receive:
- The **artifact** being reviewed (idea, method, paper draft, experiment results)
- The **relevant context** (wiki pages, prior work, constraints)
- The **review criteria** (what to evaluate, at what difficulty level)

The reviewer must **NOT** receive:
- Claude's own score or rating of the artifact
- Claude's assessment of strengths/weaknesses
- Claude's recommendation (proceed/modify/abandon)
- Any framing that anchors the reviewer toward a particular conclusion

---

## Why This Matters

1. **Anchoring bias**: If the Review LLM sees "Claude rated this 7/10", its review will cluster around 7. Independent assessment catches blind spots that anchored assessment misses.
2. **Confirmation bias**: If Claude says "the main weakness is X", the Review LLM will focus on X and miss weakness Y. Unprimed reviewers explore the full space.
3. **Diversity of perspective**: The entire value of cross-model review is that different models have different biases. Sharing judgments before review collapses this diversity.

---

## How to Apply

### In `/review` (adversarial critique)
- Step 2: Send artifact + context + review prompt to the Review LLM. Do NOT include any pre-assessment.
- Step 3 (multi-turn): Claude may respond to the Review LLM's critique with rebuttals, but these are responses to its points, not pre-formed judgments.

### In `/novelty` (cross-verification)
- Step 3: Send method signature + existing similar works to the Review LLM. Do NOT include Claude's novelty score from Step 2.

### In `/ideate` (dual-model brainstorm)
- Phase 2: The Review LLM generates ideas from the same landscape context as Claude, but does NOT see Claude's idea list. Merge happens after both complete independently.

### In `/exp-eval` (impartial verdict)
- Step 2: Send experiment results + the linked idea's hypothesis + context to the Review LLM. Do NOT include Claude's interpretation of the results.

---

## Composing Independent Assessments

After both models have independently assessed:

1. **If scores agree** (within 1 point): Use the average. High confidence.
2. **If scores disagree** (2+ points apart): Flag the disagreement explicitly. Investigate which model missed what. Report both scores with reasoning.
3. **Conservative default**: When combining novelty or quality scores, take the **lower** score. Better to underestimate than to overcommit to a flawed idea.
4. **不得用平均值掩盖关键发现**：若其中一个模型发现致命缺陷（如该方法已被发表），该发现无论另一模型评分如何均成立。

---

## Review LLM 可用性检查

调用 `mcp__llm-review__chat` 之前，每个 skill 必须检查可用性并优雅处理。

### 检测

`mcp__llm-review__chat` 调用会失败的情况：
- MCP server 未配置（缺少 `.mcp.json` 或 `enableAllProjectMcpServers` 未启用）
- `.env` 中未设置 `LLM_API_KEY` 或 `LLM_BASE_URL`
- API 端点不可达

### 降级协议

当 review MCP server **不可用**时：

1. **不要静默跳过**。告知用户：
   > "跨模型 review 尚未配置。此 skill 在独立 review LLM 辅助下效果更好。你想现在配置，还是仅用 Claude 继续？"

2. **若用户选择配置**，交互引导：
   - 询问用户使用哪个 OpenAI 兼容 API（DeepSeek、OpenAI、Qwen、OpenRouter 等）
   - 帮助用户编辑 `.env`，设置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`
   - 提示用户重启 Claude Code 以使 MCP server 加载新配置
   - 引导参考 `.env.example` 中的 provider 列表

3. **若用户选择继续（不配置 review）**，进入 Claude-only 模式：
   - 跳过 `mcp__llm-review__chat` 调用
   - 由 Claude 自身执行 review/critique 步骤（自评模式）
   - 明确标注输出为 `[Claude 自评 — 无独立第二意见]`
   - 其余 skill 流程正常执行

### 当 Review LLM 可用时

按上述标准跨模型 review 协议执行。`mcp__llm-review__chat` 工具由 `llm-review` MCP server 提供（在 `.mcp.json` 中配置），兼容任何 OpenAI-compatible API。
