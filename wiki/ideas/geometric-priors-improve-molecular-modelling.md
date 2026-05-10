---
title: "Geometric priors (equivariance / invariance) systematically improve neural-network modelling of molecular systems"
slug: "geometric-priors-improve-molecular-modelling"
status: validated
origin: "Migrated from claims/geometric-priors-improve-molecular-modelling on 2026-05-10 (was status: supported, confidence: 0.75); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [geometric-deep-learning, equivariance, molecular-modelling]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

Incorporating geometric priors — invariance or equivariance under the symmetry group acting on a molecular representation (typically E(3) or SE(3) plus permutation) — produces neural-network models that match or outperform symmetry-naive baselines on molecular modelling tasks, because the prior eliminates the need to learn the symmetry from data and forces predictions to respect physical structure.

**Scope and conditions.** - Strongly supported: molecular energies, atomic forces, dipole moments, wavefunctions; protein structure prediction; tasks on small-to-medium molecules where SE(3)/E(3)-equivariant message passing is computationally feasible.
- Weakly supported: drug-discovery property prediction (bioactivity, ADMET) where 2D-graph baselines are competitive.
- Out of scope: macromolecule-scale tasks where current SE(3)-equivariant networks cannot scale; in those cases 3D CNNs or non-equivariant GNNs may still be preferable.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

The same review explicitly notes that the empirical gain of 3D / equivariant priors over plain 2D-graph MPNNs is inconsistent for drug-discovery property prediction. This is the main reason confidence is set at 0.75 rather than higher.

**Open questions.**

- Under what conditions on dataset size, target type, and molecule scale does the cost of equivariance pay off downstream?
- Can hybrid architectures (language-model pretraining + equivariant fine-tuning) capture both data scale and geometric structure?

## Pilot results

The Atz et al. (2021) review synthesizes a wide literature showing:

- Equivariant message-passing GNNs (SchNet, PaiNN, NequIP, EGNN, Cormorant, SE(3)-Transformer) achieve state-of-the-art on quantum-chemical energy, force, and wavefunction prediction for small molecules.
- Equivariant transformers (combined with E(3)/SE(3) layers) achieve state-of-the-art on protein structure prediction (AlphaFold-class models).
- Adding angular / radial features to plain MPNNs (DimeNet) materially broadens the class of non-isomorphic molecular graphs that can be distinguished.

Counter-evidence within the same review:

- For drug-discovery property prediction, several studies find that 3D / equivariant architectures do *not* clearly outweigh the modeling cost over 2D-graph MPNNs.
- Conformer ensembling does not consistently help over single-conformer training.

Net assessment: the prior is robustly useful where the target has a physical reason to be invariant / equivariant under the chosen group, and only weakly useful where it does not.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
