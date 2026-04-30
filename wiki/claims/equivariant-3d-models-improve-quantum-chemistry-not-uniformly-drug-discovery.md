---
title: "Equivariant 3D neural networks reliably outperform 2D-graph baselines for quantum-chemistry targets but not consistently for drug-discovery property prediction"
slug: "equivariant-3d-models-improve-quantum-chemistry-not-uniformly-drug-discovery"
status: supported
confidence: 0.7
tags: [equivariant-message-passing, quantum-chemistry, drug-discovery, molecular-property-prediction, ablation]
domain: "ML for Molecules"
source_papers: [geometric-deep-learning-molecular-representations]
evidence:
  - source: geometric-deep-learning-molecular-representations
    type: supports
    strength: moderate
    detail: "Atz et al. (2021) report consistent state-of-the-art quantum-chemistry results from SE(3)/E(3)-equivariant GNNs (energies, forces, interatomic potentials, wavefunctions) but explicitly note that, for drug-discovery property prediction, 3D / equivariant architectures often fail to clearly outweigh the increased model complexity relative to 2D-graph MPNN baselines."
conditions: "Holds when comparing 3D / equivariant message-passing GNNs against 2D-graph MPNN baselines under matched data and compute budgets. The drug-discovery side of the gap is sensitive to dataset size, target type (physicochemical vs. bioactivity), and conformer-generation quality."
date_proposed: 2026-04-30
date_updated: 2026-04-30
---

## Statement

Equivariant 3D neural networks (SE(3)/E(3)-equivariant message-passing GNNs) deliver reliable gains over symmetry-naive or 2D-graph baselines on quantum-chemistry prediction tasks (energies, forces, wavefunctions, interatomic potentials), but the same architectural choice does not deliver consistent gains on drug-discovery property prediction; the added model complexity is often not justified by downstream performance.

## Evidence summary

From the Atz et al. (2021) review:

- SE(3)- and E(3)-equivariant GNNs (SchNet, PaiNN, Cormorant, NequIP, SE(3)-Transformer, EGNN) achieve SOTA on quantum-mechanical targets where invariance / equivariance is physically required.
- Including 3D information in molecular graphs generally improves drug-relevant property prediction, but there is no marked difference between using single or multiple molecular conformations for training (Axelrod & Gomez-Bombarelli, 2020).
- The review explicitly states that for drug discovery applications, 3D-aware message passing "has often failed to clearly outbalance the increased complexity of the model."

This is a structural difference, not a methodological artifact: quantum-chemistry targets are tied to physical symmetries the equivariant prior captures; drug-discovery targets often depend more on data scale, conformer quality, and human-engineered features.

## Conditions and scope

- Strongly supported for quantum-chemistry property prediction at small-molecule scale.
- Supported but with significant variance for drug-discovery property prediction.
- Out of scope: macromolecule-scale targets, where 3D CNNs and protein-structure-prediction architectures (AlphaFold-class) are the current benchmark rather than equivariant GNNs.

## Counter-evidence

Some drug-discovery studies cited in the review do report gains from 3D-aware GNNs, particularly when 3D conformer generation is high quality and the task depends on geometry (binding pose, pharmacophore matching). The claim is therefore "not uniformly" rather than "no improvement at all."

## Linked ideas

Pending — populated when ideas are linked via origin_gaps.

## Open questions

- What dataset / target features predict whether an equivariant 3D architecture will beat 2D-graph baselines on a given drug-discovery task?
- Can data-augmentation or pretraining strategies close the gap without paying full equivariant-architecture cost?
- How important is conformer-generation quality vs. architectural equivariance for downstream drug-discovery accuracy?
