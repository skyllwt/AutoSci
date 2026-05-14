---
title: "Towards Automated Kernel Generation in the Era of LLMs"
slug: towards-automated-kernel-generation-era-llms
arxiv: ""
venue: IJCAI
year: 2026
tags: [survey, kernel-generation, llm, agent, gpu, code-generation, reinforcement-learning, supervised-fine-tuning]
importance: 4
date_added: 2026-05-14
source_type: tex
contribution_type: [survey]
datasets: []
code_url: https://github.com/flagos-ai/awesome-LLM-driven-kernel-generation
---

## TLDR

A comprehensive survey of LLM-based and agentic approaches for automating GPU kernel generation, covering supervised fine-tuning, reinforcement learning, multi-agent orchestration, datasets, benchmarks, and open challenges.

## Abstract

The performance of modern AI systems is fundamentally constrained by the quality of their underlying kernels, which translate high-level algorithmic semantics into low-level hardware operations. Achieving near-optimal kernels requires expert-level understanding of hardware architectures and programming models, making kernel engineering a critical but notoriously time-consuming and non-scalable process. Recent advances in large language models (LLMs) and LLM-based agents have opened new possibilities for automating kernel generation and optimization. LLMs are well-suited to compress expert-level kernel knowledge that is difficult to formalize, while agentic systems further enable scalable optimization by casting kernel development as an iterative, feedback-driven loop. Rapid progress has been made in this area. However, the field remains fragmented, lacking a systematic perspective for LLM-driven kernel generation. This survey addresses this gap by providing a structured overview of existing approaches, spanning LLM-based approaches and agentic optimization workflows, and systematically compiling the datasets and benchmarks that underpin learning and evaluation in this domain.

## Key Contributions

- Unified taxonomy of LLM-driven kernel generation: supervised fine-tuning and reinforcement learning approaches
- Systematic categorization of agent-based kernel generation: learning mechanisms, external memory, hardware profiling, multi-agent orchestration
- Comprehensive compilation of training datasets and knowledge bases for kernel generation
- Structured overview of benchmarks and evaluation metrics
- Identification of open challenges: data scarcity, agentic reasoning, scalable infrastructure, evaluation robustness, human-AI collaboration

## Method Summary

### LLM-based Approaches
- **Supervised Fine-Tuning**: ConCuR/KernelCoder uses curated datasets selected by reasoning conciseness and speedup; KernelLLM uses compiler-aligned PyTorch-Triton pairs with instruction tuning
- **Reinforcement Learning**: Kevin models kernel generation as multi-turn optimization with cross-turn reward attribution; QiMeng-Kernel applies hierarchical RL to macro-thinking strategies; AutoTriton combines structural assessments with runtime rewards; TritonRL uses hierarchical reward decomposition; CUDA-L1/L2 use contrastive RL with LLM-as-a-judge; AscendKernelGen extends to Ascend NPUs

### Agent-based Approaches
- **Learning Mechanisms**: Iterative refinement (Caesar, PEAK, DiffAgent, TritonX, KernelGen), population-based evolution (Lange et al., FM Agent, EvoEngineer, GPU Kernel Scientist, cuPilot)
- **External Memory Management**: Vector databases (AI CUDA Engineer), hardware-specific knowledge bases (KernelEvolve), structured reasoning graphs (ReGraphT)
- **Hardware Profiling Integration**: Static specification injection (QiMeng-TensorOp, QiMeng-GEMM, SwizzlePerf), dynamic feedback loops (CUDA-LLM, TritonForge, PRAGMA, KERNELBAND)
- **Multi-Agent Orchestration**: Plan-Code-Debug workflows (STARK, AKG), Coder-Judge loops (CudaForge, KForge), hierarchical task decomposition (KernelFalcon), platform-specific workflows (GEAK, Astra)

## Results

As a survey, the paper synthesizes findings across the field. Key observations:
- SFT approaches show that dataset quality (reasoning conciseness, task diversity) matters more than quantity
- RL approaches increasingly use hierarchical reward decomposition and verification-based feedback
- Agent frameworks are evolving from simple feedback loops to population-based evolution with external memory
- Benchmarks are expanding from single-platform NVIDIA to multi-platform (AMD, Ascend, Google TPU)

## Related

- [[gpu-kernel]]
- [[kernel-benchmark]]
- [[triton-language]]
- [[kernel-generation-sft]]
- [[kernel-generation-rl]]
- [[llm-agent-kernel-generation]]
