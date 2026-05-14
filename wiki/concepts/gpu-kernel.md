---
title: GPU Kernel
aliases: [cuda-kernel, triton-kernel, gpu-program]
tags: [gpu, kernel, parallel-computing, cuda]
maturity: stable
definition: "A GPU kernel is a function that executes on a GPU's massively parallel processors, typically launched with thousands of threads organized in a grid of thread blocks. Kernels are the fundamental unit of GPU computation."
key_papers: [kernelbench-llms-write-efficient-gpu-kernels]
first_introduced: ""
date_updated: 2026-05-14
related_concepts: [triton-language, kernel-benchmark]
linked_ideas: [llm-agent-gpu-kernel-optimization]
---

## Definition

A GPU kernel is a function designed to execute on Graphics Processing Units, launched with a grid of thread blocks where each thread runs the same code on different data (SIMT model). Kernels must manage memory hierarchy (global, shared, registers), thread synchronization, and hardware-specific constraints.

## Intuition

Think of a GPU kernel as a highly parallel loop where each iteration runs on a separate processor core. The challenge is organizing memory access and computation to maximize throughput on this massively parallel hardware.

## Variants

- **CUDA kernels**: Written in CUDA C/C++, compiled to NVIDIA GPU PTX/SASS
- **Triton kernels**: Written in Python-like Triton language, compiled via Triton compiler
- **OpenCL kernels**: Cross-platform parallel kernels
- **ROCm/HIP kernels**: AMD GPU kernel programming model

## Comparison

| Feature | CUDA | Triton | OpenCL |
|---------|------|--------|--------|
| Hardware target | NVIDIA | NVIDIA/AMD | Cross-platform |
| Language | C/C++ | Python | C |
| LLM-friendliness | Medium | High | Low |
| Abstraction level | Low | Medium | Low |

## Known limitations

- Memory management complexity (coalescing, bank conflicts)
- Thread divergence degrades performance
- Architecture-specific optimizations limit portability

## Open problems

- Automated memory access pattern optimization
- Cross-architecture kernel generation
- LLM-friendly kernel representations

## Relationship to foundations

GPU kernels are the computational substrate for modern ML training and inference, HPC simulations, and data-intensive applications.

## My understanding

