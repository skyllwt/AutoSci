---
title: Triton
aliases: [triton-compiler, openai-triton]
tags: [triton, gpu, compiler, kernel-language, code-generation]
maturity: active
definition: "Triton is a Python-like language and compiler for writing GPU kernels, developed by OpenAI. It provides a higher-level abstraction than CUDA while maintaining competitive performance, making it particularly amenable to LLM-based code generation."
key_papers: [tritonbench-benchmarking-large-language-model-capabilities]
first_introduced: 2021
date_updated: 2026-05-14
related_concepts: [gpu-kernel, kernel-benchmark]
linked_ideas: [llm-agent-gpu-kernel-optimization]
---

## Definition

Triton is an open-source language and compiler that enables writing GPU kernels in a Python-like syntax. It abstracts low-level details like shared memory management and thread scheduling while exposing enough control for performance-critical decisions like block sizes and memory access patterns.

## Intuition

Triton sits between the high-level abstractions of PyTorch and the low-level control of CUDA. It lets programmers think in terms of blocks of data rather than individual threads, while the compiler handles the hardware-specific details.

## Variants

- **Triton (OpenAI)**: Original implementation targeting NVIDIA GPUs
- **Triton (AMD)**: Extended support for AMD GPUs via ROCm
- **Triton IR**: The intermediate representation used by the Triton compiler

## Comparison

| Aspect | CUDA | Triton | PyTorch |
|--------|------|--------|---------|
| Abstraction | Low | Medium | High |
| Performance ceiling | Highest | High | Medium |
| LLM codegen ease | Medium | High | Highest |
| Portability | NVIDIA | NVIDIA+AMD | All |

## Known limitations

- Not all CUDA kernel patterns are expressible in Triton
- Compiler optimizations may not match hand-tuned CUDA
- Limited support for complex synchronization patterns

## Open problems

- Extending Triton to more hardware targets
- Improving compiler optimization for diverse kernel patterns
- Better integration with LLM-based code generation pipelines

## Relationship to foundations

Triton builds on decades of compiler research (polyhedral optimization, GPU programming models) while enabling a new wave of AI-assisted kernel development.

## My understanding

