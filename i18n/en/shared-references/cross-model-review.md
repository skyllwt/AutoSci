# Reviewer Independence Principle

> Referenced by: `/review`, `/novelty`, `/ideate`, `/exp-eval`, `/exp-design`, `/paper-plan`, `/paper-draft`, `/rebuttal`, `/refine`

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
4. **Never average away a critical finding**: If one model finds a fatal flaw (e.g., the method is already published), that finding stands regardless of the other model's score.

---

## Review LLM Availability Check

Before calling `mcp__llm-review__chat`, every skill must check availability and handle gracefully.

### Detection

A call to `mcp__llm-review__chat` will fail if:
- The MCP server is not configured (missing `.mcp.json` or `enableAllProjectMcpServers` not set)
- `LLM_API_KEY` or `LLM_BASE_URL` is not set in `.env`
- The API endpoint is unreachable

### Fallback Protocol

When the review MCP server is **unavailable**:

1. **Do NOT silently skip the review step.** Inform the user:
   > "Cross-model review is not configured. This skill works best with an independent review LLM. Would you like to set it up now, or proceed with Claude-only analysis?"

2. **If the user wants to configure**, guide them interactively:
   - Ask which OpenAI-compatible API provider they have (DeepSeek, OpenAI, Qwen, OpenRouter, etc.)
   - Help them edit `.env` to set `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
   - Tell them to restart Claude Code so the MCP server picks up the new config
   - Reference `.env.example` for the full provider table

3. **If the user wants to proceed without review**, continue with Claude-only mode:
   - Skip the `mcp__llm-review__chat` call
   - Perform the review/critique step using Claude itself (self-review)
   - Clearly mark the output as `[Claude self-review — no independent second opinion]`
   - The rest of the skill workflow proceeds normally

### When Review LLM IS Available

Proceed with the standard cross-model review protocol as defined above. The `mcp__llm-review__chat` tool is provided by the `llm-review` MCP server (configured in `.mcp.json`), which works with any OpenAI-compatible API.
