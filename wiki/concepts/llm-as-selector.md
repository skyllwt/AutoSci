---
title: "LLM as Selector"
aliases: [llm-selector, selector-philosophy]
tags: [llm, compiler, design-philosophy, optimization, pass-selection]
maturity: active
definition: "A design philosophy where the LLM functions as a policy engine, selecting the best course of action from a predefined set of compiler options (flags, passes, optimization strategies)."
key_papers: [new-compiler-stack-survey-synergy-llms]
first_introduced: "2023"
date_updated: 2026-05-14
related_concepts: [llm-enabled-compilation, llm-as-translator, llm-as-generator]
---

## Definition

LLM as Selector is a design philosophy in LLM-enabled compilation where the LLM's primary role is to select optimal compiler actions from a predefined, finite set of options. The LLM is prompted with source code context and valid choices, then uses its contextual understanding to make informed decisions. The compilation system performs the actual transformation based on the LLM's selection.

## Intuition

This approach treats the LLM as a "hyper-optimizer" that can reason about code to make better choices than traditional heuristics. Since the LLM only selects from valid, human-defined actions, the resulting transformation is guaranteed to be valid (assuming a valid selection). This provides the highest degree of safety among the three design philosophies.

## Variants

- **Flag/Pass Selection**: Choosing optimal compiler flags or optimization pass sequences
- **Heuristic Replacement**: Replacing handcrafted compiler heuristics with LLM decisions
- **Search Guidance**: Using LLM to make optimization space search more efficient
- **Agentic Selection**: LLM-based agents that perform series of selections

## Comparison

| Aspect | Selector | Translator | Generator |
|--------|----------|------------|-----------|
| Safety | Highest | Lowest | Medium |
| Creative potential | Lowest | Highest | Medium |
| Verification need | Low | High | Medium |
| Implementation complexity | Low | High | Medium |

## Known limitations

- Cannot discover novel optimizations not encoded in available options
- Limited by the predefined search space
- Performance depends on quality of available choices

## Open problems

- Expanding the action space while maintaining safety guarantees
- Combining selector with generator for hybrid approaches
- Scaling to complex multi-step optimization sequences

## Relationship to foundations

LLM as Selector is the most direct evolution from traditional ML-in-compiler techniques, replacing models trained on handcrafted features with LLMs that reason directly over source code.

## My understanding

