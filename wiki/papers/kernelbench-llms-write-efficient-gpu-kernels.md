---
title: "KernelBench: Can LLMs Write Efficient GPU Kernels?"
slug: kernelbench-llms-write-efficient-gpu-kernels
arxiv: "2502.10517"
year: 2025
tags: [benchmark, gpu-kernel, llm, code-generation, evaluation]
importance: 5
date_added: 2026-05-14
source_type: tex
tldr: "Introduces KernelBench, a benchmark of 250 PyTorch ML workloads evaluating LLMs' ability to write correct and fast GPU kernels. Shows frontier reasoning models achieve <20% success rate, with iterative refinement and feedback improving results."
contribution_type: [benchmark, evaluation-metric, analysis]
datasets: [kernelbench-250]
code_url: https://github.com/Scaling-Intelligence/KernelBench
---

## Problem & Context

Efficient GPU kernels are crucial for ML performance, but writing them is time-consuming and requires significant expertise. Despite a Cambrian explosion of ML architectures, available implementations routinely underperform their peak potential. A key example is FlashAttention — the initial kernel was released in 2022, five years after the Transformer was proposed, and it took two more years to port to NVIDIA Hopper GPUs. The proliferation of AI hardware (NVIDIA, TPU, Groq, Cerebras, Graphcore) with different specs and instruction sets makes cross-platform porting a significant pain point.

## Key idea

Can language models help write correct and optimized kernels? KernelBench evaluates this by providing LMs with PyTorch reference code and asking them to generate optimized CUDA implementations. The benchmark covers 250 tasks across three levels of complexity: individual operations (100 tasks), operator sequences (100 tasks), and full ML architectures (50 tasks). A new metric fast_p measures the percentage of generated kernels that are both functionally correct and offer speedup greater than threshold p over baseline.

## Method

### Task format

Each task provides:
- **Input**: PyTorch `Model` class with `__init__` and `forward()` methods, plus `get_inputs()` and `get_init_input()` functions specifying tensor shapes and data types
- **Output**: LM generates `ModelNew` class with custom optimizations (e.g., inline CUDA kernel calls)

### Three difficulty levels

1. **Level 1 (100 tasks)**: Single primitive operations (matmul, convolution, activations, norms, losses). PyTorch uses well-optimized closed-source kernels, making this challenging.
2. **Level 2 (100 tasks)**: Operator sequences (3-6 operations) that can be fused for performance (e.g., convolution + ReLU + bias).
3. **Level 3 (50 tasks)**: Full ML architectures from popular GitHub repositories (pytorch, huggingface/transformers, huggingface/pytorch-image-models).

### Evaluation

- **Correctness**: Compare output of LM-generated `ModelNew` against reference `Model` on 5 random inputs
- **Performance**: Wall-clock execution time comparison using repeated trials
- **fast_p metric**: Fraction of tasks where kernel is both correct AND has speedup > p over PyTorch Eager baseline. fast_0 = correctness rate; fast_1 = fraction achieving >1x speedup.

### Baselines evaluated

Models tested: GPT-4o, OpenAI o1, DeepSeek V3, DeepSeek R1, Claude 3.5 Sonnet, Llama 3.1-70B Instruct, Llama 3.1-405B Instruct. All evaluated with one-shot prompting on NVIDIA L40S.

## Experiment & Results

### One-shot baseline

Frontier reasoning models perform best but still fall short:
- DeepSeek R1: 36% fast_1 on Level 2 (PyTorch Eager), 37% on torch.compile
- OpenAI o1: 24% fast_1 on Level 2
- Other models: <10% fast_1 on most levels
- All models: <20% fast_1 on average over PyTorch Eager

### Error analysis

- Reasoning models (o1, R1) produce fewer execution failures (<55% incorrect) vs. other models (>70%)
- All models struggle similarly with functional correctness
- Trade-off observed: models attempting complex optimizations (tensor core wmma instructions) produce more errors

### Performance analysis

- Fewer than 15% of LM-generated kernels outperform PyTorch across all levels
- Reasoning-based LMs generally outperform others in providing speedups
- CUDA is a low-resource language: only 0.073% of The Stack v1.2 corpus

### Cross-hardware variation

- Level 1 kernels generalize well across GPUs
- Level 2 shows larger variation: DeepSeek R1 achieves 36% fast_1 on L40S but 47% on A10G
- One-shot kernels may not generalize well across hardware as optimization complexity increases

### Interesting kernel patterns discovered

- **Operator fusion**: GELU (2.9x), Softsign (1.3x), matmul+division+summation+scaling (2.6x)
- **Memory hierarchy**: Cosine similarity (2.8x), triplet margin loss (2.0x) using shared memory
- **Algorithmic optimizations**: Dense-diagonal matrix multiplication exploiting sparsity (13x speedup)

### Iterative refinement

Providing execution results and profiler feedback in context improves kernel quality:
- o1: 12% to 43% fast_1
- R1: 36% to 72% fast_1
- Claude 3.5 Sonnet: 12% to 18% fast_1

## Limitations

- All evaluation on NVIDIA GPUs only (L40S primary, with A10G/H100 cross-hardware studies)
- No ground-truth kernels provided (evaluation-only benchmark)
- torch.compile baseline has runtime overhead for small kernels in Level 1
- Current models cannot effectively use tensor core instructions
- Limited to PyTorch ecosystem; other frameworks (JAX, TensorFlow) not covered
- Hardware-specific optimizations in generated kernels may not transfer across GPU types

## Open questions

- How to improve LM performance in low-resource data regimes (CUDA as 0.073% of training data)?
- Can alternative programming abstractions (ThunderKittens, CUTLASS, Triton) simplify generation?
- How to expand evaluation to non-NVIDIA hardware accelerators?
- Can agentic workflows with iterative refinement close the gap to human-written kernels?
- How to systematically provide hardware-specific information to LMs for target-specific optimization?

## My take

KernelBench establishes the first comprehensive benchmark for LLM kernel generation, directly mapping to real production value. The fast_p metric is well-designed — adjustable threshold captures both correctness and performance in a single number. The key insight is that frontier reasoning models show nascent capability (some 2.9x-13x speedups on specific tasks) but remain far from reliable (<20% overall). The iterative refinement results (up to 72% fast_1 with R1 + feedback) suggest the path forward involves better feedback mechanisms rather than purely scaling model size. The cross-hardware generalization gap at Level 2 is particularly concerning for practical deployment.

## Related

- [[kernel-benchmark]]
- [[gpu-kernel]]
- [[triton-language]]
