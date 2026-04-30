---
title: "Geometric priors (equivariance / invariance) systematically improve neural-network modelling of molecular systems"
slug: "geometric-priors-improve-molecular-modelling"
status: supported
confidence: 0.75
tags: [geometric-deep-learning, equivariance, molecular-modelling]
domain: "ML for Molecules"
source_papers: [geometric-deep-learning-molecular-representations]
evidence:
  - source: geometric-deep-learning-molecular-representations
    type: supports
    strength: moderate
    detail: "Atz et al. (2021) review the molecular GDL literature and document strong gains for equivariant message-passing GNNs in quantum chemistry (energy, force, wavefunction prediction) and for equivariant transformers in protein structure prediction. They also document that the gain is inconsistent for drug-discovery property prediction, so support is moderate rather than strong."
conditions: "Holds clearly for quantum-chemistry tasks (small-to-medium molecules; targets that are physically invariant or equivariant under E(3)/SE(3)) and for macromolecular structure prediction. Holds weakly or inconsistently for drug-discovery property prediction, where the cost of equivariant architectures often does not pay off over plain 2D-graph MPNNs."
date_proposed: 2026-04-30
date_updated: 2026-04-30
---

## Statement

Incorporating geometric priors — invariance or equivariance under the symmetry group acting on a molecular representation (typically E(3) or SE(3) plus permutation) — produces neural-network models that match or outperform symmetry-naive baselines on molecular modelling tasks, because the prior eliminates the need to learn the symmetry from data and forces predictions to respect physical structure.

## Evidence summary

The Atz et al. (2021) review synthesizes a wide literature showing:

- Equivariant message-passing GNNs (SchNet, PaiNN, NequIP, EGNN, Cormorant, SE(3)-Transformer) achieve state-of-the-art on quantum-chemical energy, force, and wavefunction prediction for small molecules.
- Equivariant transformers (combined with E(3)/SE(3) layers) achieve state-of-the-art on protein structure prediction (AlphaFold-class models).
- Adding angular / radial features to plain MPNNs (DimeNet) materially broadens the class of non-isomorphic molecular graphs that can be distinguished.

Counter-evidence within the same review:

- For drug-discovery property prediction, several studies find that 3D / equivariant architectures do *not* clearly outweigh the modeling cost over 2D-graph MPNNs.
- Conformer ensembling does not consistently help over single-conformer training.

Net assessment: the prior is robustly useful where the target has a physical reason to be invariant / equivariant under the chosen group, and only weakly useful where it does not.

## Conditions and scope

- Strongly supported: molecular energies, atomic forces, dipole moments, wavefunctions; protein structure prediction; tasks on small-to-medium molecules where SE(3)/E(3)-equivariant message passing is computationally feasible.
- Weakly supported: drug-discovery property prediction (bioactivity, ADMET) where 2D-graph baselines are competitive.
- Out of scope: macromolecule-scale tasks where current SE(3)-equivariant networks cannot scale; in those cases 3D CNNs or non-equivariant GNNs may still be preferable.

## Counter-evidence

The same review explicitly notes that the empirical gain of 3D / equivariant priors over plain 2D-graph MPNNs is inconsistent for drug-discovery property prediction. This is the main reason confidence is set at 0.75 rather than higher.

## Linked ideas

Pending — populated when ideas are linked via origin_gaps.

## Open questions

- Under what conditions on dataset size, target type, and molecule scale does the cost of equivariance pay off downstream?
- Can hybrid architectures (language-model pretraining + equivariant fine-tuning) capture both data scale and geometric structure?
