---
title: "Supervised Fine-Tuning for Kernel Generation"
aliases: [sft-kernel-generation, kernel-sft]
tags: [supervised-fine-tuning, kernel-generation, llm, code-generation, training]
maturity: active
definition: "Supervised fine-tuning for kernel generation is the process of adapting pre-trained LLMs to generate GPU kernels using paired datasets that map high-level computational intent to optimized low-level kernel implementations."
key_papers: [towards-automated-kernel-generation-era-llms]
first_introduced: "2025"
date_updated: 2026-05-14
related_concepts: [gpu-kernel, kernel-generation-rl]
linked_ideas: []
---

## Definition

Supervised fine-tuning (SFT) for kernel generation specializes pre-trained LLMs to produce high-performance GPU kernels by training on curated datasets that pair algorithmic descriptions or high-level operator specifications with corresponding optimized kernel implementations.

## Intuition

General-purpose LLMs can write code but lack the specialized knowledge needed for high-performance kernel development. SFT bridges this gap by exposing the model to expert-quality kernel examples, effectively distilling hardware-specific optimization knowledge into the model's parameters.

## Key Approaches

- **Reasoning-quality curation**: ConCuR selects training samples based on reasoning conciseness, speedup achieved, and task diversity, producing KernelCoder
- **Compiler alignment**: KernelLLM uses the Triton compiler to produce aligned PyTorch-Triton pairs with structured prompts encoding computation-to-kernel mappings
- **Chain-of-thought supervision**: AscendKernelGen incorporates CoT reasoning into SFT datasets for Ascend NPU kernel generation

## Known Limitations

- Dataset quality is critical and expensive to achieve at scale
- High-performance kernels exhibit long-tail distribution, making comprehensive coverage difficult
- SFT alone may not discover novel optimization strategies beyond training data

## Open Problems

- Scaling SFT datasets with hardware-aware domain knowledge
- Collecting optimization trajectories (not just final kernels) for training
- Cross-architecture transfer learning for kernel generation

## Relationship to Foundations

SFT for kernel generation builds on general LLM fine-tuning techniques but requires domain-specific data curation that captures hardware-level optimization patterns.
