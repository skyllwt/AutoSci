---
title: "SMILES chemical language modelling"
aliases: ["chemical language model", "SMILES RNN", "molecular transformer", "string-based molecular deep learning"]
tags: [smiles, chemical-language-model, generative-molecular-design, retrosynthesis, recurrent-neural-network, transformer]
maturity: active
key_papers: [geometric-deep-learning-molecular-representations]
first_introduced: "Segler et al., 2018 (ACS Central Science) — RNNs for de novo molecule generation; molecular transformers introduced shortly after for retrosynthesis"
date_updated: 2026-04-30
related_concepts: [geometric-deep-learning]
---

## Definition

Chemical language modelling is the family of deep-learning techniques that treat molecular string representations — most commonly SMILES, but also InChI, DeepSMILES, and SELFIES — as sequences with their own syntax and semantics, and apply sequence models (RNNs, transformers) to learn them. The "language" interpretation lets de novo design, retrosynthesis, reaction prediction, and property prediction reuse the architectural and training advances of natural-language processing.

## Intuition

A SMILES string is an alphanumeric encoding of a molecular graph: letters denote atoms, parentheses branches, digits ring closures, and symbols bond types and stereochemistry. Not every character combination is a valid molecule (the "language" has a syntax), and small string changes can correspond to large changes in physicochemical or biological properties (the "language" has semantics). Once you accept this framing, next-token prediction over SMILES is enough to learn to *generate* novel molecules, and sequence-to-sequence translation between reactants and products is enough to learn retrosynthesis.

## Formal notation

A molecule is encoded as a sequence s = {s_1, s_2, ..., s_T} of T tokens. An RNN-based language model parameterizes p(s_{t+1} | s_1, ..., s_t, h_t) for next-token prediction. A transformer-based model treats the sequence as a fully-connected (encoder) or causally-connected (decoder) graph and updates token embeddings via residual self-attention blocks; positional information is added through learned or sinusoidal positional encodings.

## Variants

- **RNN-based generative models** (Segler et al., 2018): vanilla RNNs, LSTMs, and GRUs trained autoregressively on SMILES; combined with transfer learning or reinforcement learning for property-targeted de novo design.
- **Molecular transformers**: encoder-decoder transformers for retrosynthesis (reactants <-> products), forward reaction prediction, multi-step synthesis, regio- and stereoselective reactions, reaction-yield prediction.
- **String alternatives**: DeepSMILES (parenthesis-free), SELFIES (string syntax guarantees chemical validity), one-letter amino-acid sequences for peptide / protein modelling.
- **Augmentation strategies**: SMILES enumeration (multiple non-canonical strings for the same molecule), bidirectional learning, canonicalization.

## Comparison

vs. graph-based molecular deep learning: chemical language models give up explicit graph structure but inherit the entire NLP toolkit (transformers, large-scale pretraining, transfer learning, RL). vs. 3D / equivariant approaches: chemical language models cannot directly express 3D geometry, but they handle generative design and reaction prediction more naturally.

## When to use

- Generative molecular design (de novo design, focused libraries).
- Retrosynthesis and forward reaction prediction (sequence-to-sequence).
- Reaction-yield, regio-, and stereoselectivity prediction.
- Settings where pretraining on large unlabeled molecule corpora is the main lever.

## Known limitations

- SMILES is non-univocal: the same molecule maps to many strings, complicating property-prediction baselines and requiring augmentation or canonicalization.
- Generated strings may be syntactically invalid SMILES; SELFIES addresses this by construction but has not displaced SMILES.
- Pure language models discard explicit 3D and stereochemical structure that equivariant graph models can encode directly.
- Property prediction from SMILES alone is sometimes outperformed by graph-based methods on certain benchmarks.

## Open problems

- When is string-based generation preferable to graph-based generation, given the validity guarantees of SELFIES and the 3D awareness of equivariant GNNs?
- Combining language-model pretraining with geometric / 3D priors at fine-tuning time.
- Evaluating chemical language models on prospective rather than retrospective benchmarks.

## Key papers

- [[geometric-deep-learning-molecular-representations]] — situates chemical language models within the broader GDL taxonomy and surveys their applications in generative design, CASP, reaction-yield prediction, and protein structure prediction.

## My understanding

SMILES-based modelling remains the dominant generative-design approach despite the ongoing rise of graph-based generators, mostly because the NLP transfer-learning playbook works very well on it. The interesting frontier is hybrid: pretrain a language model on enormous SMILES corpora, then fine-tune with a 3D / equivariant head for tasks that need geometry.
