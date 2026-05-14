---
title: "The New Compiler Stack: A Survey on the Synergy of LLMs and Compilers"
slug: new-compiler-stack-survey-synergy-llms
tags: [survey, llm, compiler, code-translation, code-optimization, compilation]
importance: 4
date_added: 2026-05-14
source_type: tex
tldr: "A systematic survey of 159 studies on LLM-enabled compilation, proposing a multi-dimensional taxonomy based on Design Philosophy (Selector/Translator/Generator), LLM Methodology (Training-Required/Training-Free), Level of Code Abstraction, and Task Type."
contribution_type: [survey, taxonomy]
---

## Problem & Context

The compiler has traditionally relied on handcrafted heuristics for optimization. While early ML approaches introduced data-driven methods, they required intensive feature engineering. The emergence of LLMs represents a fundamental shift: pre-trained on vast code corpora, LLMs can understand, generate, and transform programming languages without explicit feature engineering. However, the rapid proliferation of LLM-enabled compiler research lacked a systematic organization.

## Key idea

This survey proposes a comprehensive multi-dimensional taxonomy to categorize LLM-enabled compiler research along four axes:
1. **Design Philosophy**: How the LLM is architecturally integrated (Selector, Translator, Generator)
2. **LLM Methodology**: How the model is technically developed (Training-Required vs Training-Free)
3. **Level of Code Abstraction**: The representational level being processed (NL, PL, IR/ASM)
4. **Task Type**: The specific compiler-related goal (transpilation, optimization, repair, synthesis)

## Method

The authors conducted a systematic literature review following SLR protocol:
- Searched across arXiv, Google Scholar, ACM DL, and IEEE Xplore
- Applied three-phase filtering: initial search, deduplication/screening, full-text review
- Final corpus: 159 primary studies

Three Design Philosophies identified:
- **LLM as Selector**: LLM chooses from predefined compiler actions (flags, passes). Safest but limited to existing options.
- **LLM as Translator**: LLM directly performs code transformation as sequence-to-sequence task. Most powerful but verification is critical.
- **LLM as Generator**: LLM generates compiler tools/scripts that perform transformations. Hybrid approach balancing flexibility and determinism.

Two LLM Methodologies:
- **Training-Required**: Domain pre-training, SFT, RL/feedback tuning. High specialized performance but task-locked.
- **Training-Free**: Prompt engineering, RAG, agentic workflows. High flexibility but depends on base model capability.

## Experiment & Results

As a survey paper, the contributions are analytical rather than experimental:
- Systematic categorization of 159 studies across the four-dimensional taxonomy
- Identification of three primary benefits: democratization of compiler development, discovery of novel optimization strategies, broadening of compiler's scope
- Key challenges identified: ensuring correctness, achieving scalability, interpretability
- Most promising direction: hybrid systems combining training-required and training-free approaches

## Limitations

- Excludes traditional ML techniques (SVM, decision trees) that don't use language models
- Focuses on Transformer-based LLMs, may miss other emerging architectures
- Rapid evolution of the field means some recent work may not be captured

## Open questions

- How to ensure correctness guarantees when LLMs generate compiler transformations?
- Can hybrid systems (SFT + agentic workflows) achieve both specialization and flexibility?
- How to scale LLM-based approaches to entire codebases beyond function-level?
- What are effective verification methods for LLM-generated compiler outputs?

## My take

This survey provides a much-needed organizational framework for the rapidly growing field of LLM-enabled compilation. The multi-dimensional taxonomy (Design Philosophy x LLM Methodology x Code Abstraction x Task Type) is particularly useful for researchers entering the field. The key insight that Selector/Translator/Generator represent a spectrum of control vs. creative potential is valuable for system design decisions.

## Related

- [[llm-enabled-compilation]]
- [[llm-as-selector]]
- [[llm-as-translator]]
- [[llm-as-generator]]
