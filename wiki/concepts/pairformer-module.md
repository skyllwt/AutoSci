---
title: "Pairformer module"
aliases: ["pairformer", "AF3 pairformer", "pairformer block"]
tags: [structure-prediction, attention, alphafold, architecture]
maturity: emerging
key_papers: [accurate-structure-prediction-biomolecular-interactions-alphafold]
first_introduced: "AlphaFold 3 (2024)"
date_updated: 2026-04-30
related_concepts: [diffusion-based-structure-prediction]
---

## Definition

The pairformer is the dominant trunk block of AlphaFold 3, replacing AlphaFold 2's evoformer. It is a stack of 48 blocks operating only on the pair representation (n × n × 128) and the single representation (n × 384); the MSA representation is processed once by a thin embedding block and then dropped. All later information flow happens through the pair representation.

## Intuition

AF2's evoformer treated MSA rows as a first-class tensor, exchanging information between MSA rows and pair-edge geometry through expensive row/column attention. AF3 observed that, once the pair representation is rich enough, almost all the geometric signal AF2 extracted from the MSA can be funnelled through the pair tensor up front. The pairformer keeps the geometrically meaningful operations — triangle multiplicative updates and triangle self-attention around starting and ending nodes — and drops the MSA-row track entirely. This makes the trunk simpler, cheaper, and friendlier to non-protein chemistry where MSAs are unavailable or meaningless (ligands, modified residues, ions).

## Formal notation

Each pairformer block applies, in order: triangle update with outgoing edges, triangle update with incoming edges, triangle self-attention around the starting node, triangle self-attention around the ending node, transition (MLP) on the pair representation, single attention with pair bias, and a transition on the single representation. The 48 blocks have independent parameters. Pair channels c = 128, single channels c = 384.

## Variants

- **AF3 pairformer (canonical)**: 48 blocks, MSA module reduced to 4 blocks of pair-weighted averaging that feeds the pair representation only.
- The diffusion module reuses many of the same triangle-update primitives over a different conditioning signal but is architecturally separate.

## Comparison

- **vs. evoformer (AF2)**: same triangle primitives, same block count (48 vs. 48), but the MSA-row track is removed; pair-axis attention replaces row/column attention; MSA influence is funnelled through a 4-block pair-weighted-averaging embedding rather than 48 blocks of joint MSA-pair processing.
- **vs. plain self-attention**: keeps geometry-aware triangle updates that explicitly enforce the triangle inequality at the representation level.

## When to use

- When predicting structures for inputs where MSAs are unreliable or absent (general chemistry, modified residues, designed sequences).
- When MSA-track compute is the bottleneck and most of the signal already lives in the pair representation.

## Known limitations

- Inherits AF2's MSA-depth dependence for protein chains: shallow-MSA targets still suffer despite the simpler MSA module.
- Triangle self-attention is the dominant compute cost and scales unfavourably with sequence length, limiting the maximum token count (5,120 in AF3 inference).
- Without the MSA-row track, signal from co-evolution must be recovered by the pair-weighted-averaging embedder; whether this is lossless versus AF2's evoformer for very-shallow-MSA proteins is not separately ablated in the paper.

## Open problems

- Can the triangle-attention quadratic-in-n cost be replaced by a linearised or sparse variant without losing accuracy on long complexes?
- Is the 4-block MSA module a generic-enough route for evolutionary information, or does it leave headroom for shallow-MSA improvements?
- Does the pairformer transfer to non-structure tasks (binding-affinity prediction, mutation-effect scoring) that consume pair representations?

## Key papers

- [[accurate-structure-prediction-biomolecular-interactions-alphafold]] — introduces the pairformer and uses it as the structure-prediction trunk.

## My understanding

The pairformer's contribution is more architectural minimalism than novel mechanism: every primitive it uses already existed in the evoformer. The interesting empirical claim is that almost all of the evoformer's MSA-side processing was redundant once you commit to a strong pair representation and a generative diffusion head. The result simplifies the trunk and broadens it to non-protein chemistry; it does not, on its own, explain AF3's accuracy gains, which come from the trunk-plus-diffusion combination.
