---
name: "fast_p Metric"
slug: fast-p-metric
type: evaluation
tags: [evaluation, metric, kernel, speedup, correctness]
source_papers: [kernelbench-llms-write-efficient-gpu-kernels]
parent_methods: []
child_methods: []
date_updated: 2026-05-14
---

## Definition

The fast_p metric measures the percentage of generated GPU kernels that are both functionally correct and offer a speedup greater than adjustable threshold p over a baseline implementation. Formally:

fast_p = (1/N) * sum(1(correct_i AND speedup_i > p))

where speedup is the ratio of baseline wall-clock time to generated kernel time.

## How it works

1. Generate input tensors of prescribed shape and precision
2. Run reference Model and LM-generated ModelNew on the inputs
3. Compare outputs for functional correctness (5 random inputs per task)
4. Measure wall-clock execution time with repeated trials
5. Compute speedup ratio: baseline_time / generated_kernel_time
6. Count tasks where BOTH correct AND speedup > p

## Key properties

- **fast_0**: Equivalent to correctness rate (speedup threshold = 0, so any correct kernel passes)
- **fast_1**: Fraction of correct kernels achieving >1x speedup over baseline
- **Adjustable difficulty**: Increasing p progressively raises the bar
- **Unified metric**: Captures both correctness and performance in a single number

## When to use

- Evaluating LLM-generated or compiler-generated GPU kernels
- Comparing kernel generation methods across different models or approaches
- Measuring progress on kernel optimization benchmarks
- Any scenario requiring joint correctness + performance evaluation

## Limitations

- Performance baselines are hardware-specific
- Correctness checks based on numerical comparison may miss subtle issues
- Does not capture compilation time or memory usage
