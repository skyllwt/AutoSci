---
title: "KernelBenchX: A Comprehensive Benchmark for Evaluating LLM-Generated GPU Kernels"
slug: kernelbench-comprehensive-benchmark-evaluating-llm-generated
arxiv: ""
venue: ""
year: 2026
tags: [benchmark, triton, gpu-kernel, llm-code-generation, evaluation]
importance: 4
date_added: 2026-05-14
source_type: tex
s2_id: ""
tldr: "KernelBenchX is a benchmark for evaluating LLM-based Triton kernel generation with 176 tasks across 15 categories, revealing that task structure (not method design) determines correctness, iterative refinement repairs but doesn't optimize, and correctness doesn't imply efficiency."
contribution_type: [benchmark, empirical-study]
datasets: []
code_url: "https://github.com/BonnieW05/KernelBenchX"
cited_by: []
---

## Problem & Context

LLM-based Triton kernel generation has attracted significant interest, yet fundamental empirical questions remain unanswered: where does this capability break down, and why? Existing benchmarks like KernelBench, TritonBench, and MultiKernelBench provide evaluation frameworks but suffer from unresolved task categories, insufficient correctness verification, and limited efficiency evaluation. Two key questions are unresolved:

1. **Capability boundary**: We don't know which types of tasks current methods handle reliably, which consistently fail, and why.
2. **Iterative refinement role**: It's unclear whether different strategies improve compilation, correctness, or performance, and to what extent.

## Key idea

KernelBenchX addresses these limitations through category-aware evaluation with three key extensions:
1. **Robust two-stage correctness protocol** that rejects implementations passing output comparison by chance
2. **Unified 15-category taxonomy** with quantization and multi-precision task extensions for fine-grained structural analysis
3. **Hardware-efficiency metrics beyond runtime** (IOU for memory bandwidth, MFU for compute utilization)

## Method

### Benchmark Design
- **176 tasks** across 15 categories: Activation, Convolution, Fusion, Index, LinearAlgebra, Loss, Math, MatrixMultiply, Normalization, Optimizer, Pooling, Quantization, Random, Reduce, and SpatialOps
- Categories based on computational structure rather than operator type
- Extensions: fp16/bf16/int8 multi-precision variants, W8A8/W4A16 quantization tasks

### Correctness Protocol
- **Call Accuracy**: Import/compile/call verification + task constraints (static checker for quantization)
- **Execution Accuracy**: Multi-distribution testing (standard + outlier mode with 0.1% probability, 50x scale factor)
- Dtype-aware numerical tolerances; quantization requires cosine similarity ≥ 0.90-0.95, L1 relative error ≤ 0.05-0.10, RMSE ≤ 0.10-0.15

### Compared Methods
Five representative methods spanning key design axes:
- **AutoTriton**: Trained via SFT + RL, single-pass generation
- **GEAK**: Agentic framework (generator, evaluator, reflector, optimizer), 3 iterations
- **KernelAgent**: Multi-agent generate-verify-refine workflow, up to 5 refinement rounds
- **Claude**: General-purpose model, single-pass
- **DeepSeek-Coder**: Zero-specialization baseline

## Experiment & Results

### Overall Results (176 tasks)
| Method | Compile (%) | Correct (%) | Correct/Compile (%) | Speedup |
|--------|-------------|-------------|---------------------|---------|
| AutoTriton | 36.4 | 17.0 | 46.9 | 1.35× |
| GEAK | 68.8 | 30.7 | 44.6 | 1.15× |
| KernelAgent | 64.2 | 10.8 | 16.8 | 1.41× |
| Claude | 45.5 | 22.7 | 50.0 | 1.26× |

### Three Key Findings

**Finding 1: Task structure determines correctness more than method design**
- Category explains 9.4% variance in semantic correctness vs. 3.3% for method (nearly 3× difference)
- 72% of Fusion tasks fail across all methods; Math tasks solved consistently
- Quantization remains completely unsolved (0/30 successes) despite non-trivial compilation rates

**Finding 2: Iterative refinement improves correctness, but not performance**
- GEAK iterations: compile rate rises 52.3% → 68.8%, but speedup declines 1.58× → 1.44×
- Newly rescued kernels consistently underperform: 1.16× vs. 1.58× speedup in round 0→1
- Dominant edit types are repairs (mask fixes, dtype/casting), not optimization rewrites

**Finding 3: Correctness does not imply efficiency**
- 46.6% of correct kernels slower than PyTorch eager baseline
- Pooled median speedup only 1.0008×
- Cross-hardware speedup variance reaches 21.4× (worst case)

### Hardware Evaluation
Six NVIDIA GPUs: RTX 5090, RTX 4090, A100-PCIE-40GB, H20, H800 PCIe, L20
- Fraction of correct kernels slower than PyTorch: 18% (A100) to 76% (L20)

## Limitations

- Quantization tasks remain completely unsolved, revealing systematic misunderstanding of numerical computation contracts
- Cross-hardware portability is weak (max/min speedup ratio median 2.15×)
- Iterative refinement converges to correct but often slow implementations
- Static complexity proxies correlate only weakly with failure (r ≤ 0.21)
- Current feedback mechanisms insufficient for performance optimization

## Open questions

1. How to handle global coordination and non-local semantic contracts in kernel generation?
2. How to explicitly model numerical precision requirements (quantization, mixed-precision)?
3. How to incorporate hardware efficiency into generation rather than post-hoc optimization?
4. What feedback mechanisms would enable iterative refinement to improve performance, not just correctness?
5. How to achieve cross-architecture kernel generation (NVIDIA, AMD, Ascend)?

## My take

This paper provides valuable empirical grounding for the LLM kernel synthesis field. The three findings—category-structured correctness, repair-biased refinement, and correctness-efficiency gap—reveal fundamental limitations of current approaches. The insight that task structure matters more than method design is particularly important for future research directions.

## Related

- [[kernelbench-llms-write-efficient-gpu-kernels]]
- [[tritonbench-benchmarking-large-language-model-capabilities]]
- [[gpu-kernel]]
- [[kernel-benchmark]]
- [[triton-language]]
- [[llm-kernel-synthesis]]
