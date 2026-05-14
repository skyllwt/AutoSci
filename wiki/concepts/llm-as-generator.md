---
title: "LLM as Generator"
aliases: [llm-generator, generator-philosophy]
tags: [llm, compiler, design-philosophy, code-generation, compiler-development]
maturity: active
definition: "A design philosophy where the LLM generates source code of programs that perform code transformations, rather than directly transforming code itself. The generated artifacts (scripts, compiler passes) can be inspected, verified, and reused."
key_papers: [new-compiler-stack-survey-synergy-llms]
first_introduced: "2023"
date_updated: 2026-05-14
related_concepts: [llm-enabled-compilation, llm-as-selector, llm-as-translator]
---

## Definition

LLM as Generator is an indirect, meta-level design philosophy where the LLM's role is to generate the source code of a program that performs the desired code transformation. The workflow is typically two-step: (1) the LLM writes a script or program implementing the transformation logic, (2) this generated program is compiled and executed to apply changes to target code. This combines LLM pattern-recognition with deterministic program execution.

## Intuition

Rather than having the LLM directly transform code (which risks hallucinations), this approach has the LLM write deterministic programs that perform transformations. The generated artifact can be inspected, verified, and reused, offering higher trust than direct generative models. It's like having an LLM write a compiler pass rather than act as the compiler itself.

## Variants

- **Compiler Pass Generation**: LLM generates new optimization passes for existing compilers
- **Backend Generation**: LLM generates compiler backends for new architectures
- **Script Generation**: LLM generates transformation scripts for specific tasks
- **Tool Development**: LLM generates compiler development tools

## Comparison

| Aspect | Selector | Translator | Generator |
|--------|----------|------------|-----------|
| Safety | Highest | Lowest | Medium |
| Creative potential | Lowest | Highest | Medium |
| Verification need | Low | High | Medium |
| Trust/Transparency | Medium | Low | Highest |

## Known limitations

- Increased workflow complexity (two-step process)
- Requires LLM to understand specific compiler APIs and frameworks
- Currently scarce for core compiler tasks due to complexity
- Generated code still needs verification

## Open problems

- Improving LLM understanding of compiler internals and APIs
- Scaling to complex compiler components beyond simple passes
- Creating standardized interfaces for compiler code generation
- Combining with formal verification of generated code

## Relationship to foundations

LLM as Generator bridges software engineering (code generation) with compiler engineering. It applies LLM code generation capabilities to the meta-task of creating compiler tools, rather than using LLMs as the tools themselves.

## My understanding

