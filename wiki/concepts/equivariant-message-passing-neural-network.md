---
title: "Equivariant message-passing neural network"
aliases: ["E(3)-equivariant GNN", "SE(3)-equivariant GNN", "equivariant MPNN", "equivariant GNN"]
tags: [graph-neural-networks, equivariance, message-passing, 3d-molecular-graphs, quantum-chemistry, geometric-deep-learning]
maturity: active
key_papers: [geometric-deep-learning-molecular-representations]
first_introduced: "Thomas et al., 2018 (Tensor Field Networks); generalized in subsequent E(3)/SE(3)-equivariant GNN literature (EGNN, Cormorant, SE(3)-Transformer, NequIP, PaiNN)"
date_updated: 2026-04-30
related_concepts: [geometric-deep-learning]
---

## Definition

An equivariant message-passing neural network is a graph neural network whose message-passing layers commute with rotations, translations (and optionally reflections) of input 3D atom coordinates. Concretely, if the input 3D graph G3D = (V, E, R) is rotated by R in SO(3) (or transformed by an element of E(3) / SE(3)), all geometric internal features (vectors, tensors) of the network rotate accordingly while scalar features stay invariant. Aggregations are still permutation-invariant over neighbors, as in standard MPNNs.

## Intuition

Plain message-passing networks on 3D molecular graphs have to learn rotational symmetry from data — the loss of this prior wastes parameters and data. Equivariant MPNNs build the symmetry into the layer algebra: messages between atoms are constructed from geometrically-meaningful primitives (relative vectors, distances, angles, spherical harmonics) that transform predictably under rotation. The network can then output invariant scalars (energies) or equivariant vectors / tensors (forces, dipole moments) by construction.

## Formal notation

A message-passing layer updates node features v_i^l to v_i^{l+1} via:

v_i^{l+1} = phi(v_i^l, AGG_{j in N(i)} psi(v_i^l, v_j^l, r_ij))

In an equivariant variant, psi and phi are restricted to operate on geometric tensors that transform under the chosen symmetry group — e.g., via tensor products of irreducible representations and spherical harmonics (tensor field networks, NequIP), or via scalar / vector channels with carefully designed mixing (EGNN, PaiNN). The key invariant is: F(T(X)) = T'F(X) for every T in the symmetry group.

## Variants

- **SE(3)-equivariant**: equivariant to rotations + translations only; can distinguish enantiomers (chirality preserved). Examples: tensor field networks, SE(3)-Transformer, Cormorant. Computationally heavy due to spherical-harmonic / Wigner-D-matrix machinery.
- **E(3)-equivariant**: equivariant to rotations + translations + reflections; cannot distinguish enantiomers but distinguishes diastereomers. Examples: EGNN, NequIP. Cheaper; competitive on rotation-invariant targets.
- **Direction- / angle-aware non-equivariant**: includes radial and angular edge features (DimeNet, SchNet variants) without enforcing strict rotation equivariance — captures geometric shape better than pure 2D-graph MPNNs but does not give layer-level equivariance guarantees.

## Comparison

vs. plain (2D-graph) MPNNs: equivariant MPNNs can distinguish stereochemistry and geometric shape that flat graphs collapse. vs. 3D CNNs over voxels: equivariant MPNNs are mesh-free and naturally handle variable-size molecules but scale poorly to macromolecule-sized systems.

## When to use

- Quantum-chemistry tasks (energies, forces, wavefunctions, dipole moments) on small-to-medium molecules where rotation invariance / equivariance is physically required.
- Tasks that depend on stereochemistry or 3D geometric shape.
- Data-efficient settings where the symmetry prior buys generalization.

## Known limitations

- SE(3)-equivariant variants using spherical harmonics scale poorly with model width, harmonic order, and molecule size.
- Quantum-mechanical wavefunction predictions scale quadratically with electron count.
- For drug-discovery property prediction, empirical gains over 2D-graph baselines are inconsistent.
- Implementation correctness is subtle; many "equivariant" architectures differ in which symmetry group and which tensor types they actually preserve.

## Open problems

- Reducing the cost of high-order tensor message passing to scale to macromolecular systems.
- Reconciling equivariance with the practical benchmarks of drug discovery, where 3D priors do not consistently help.
- Choosing between SE(3) and E(3) variants in a principled way given the chiral / non-chiral nature of the target.

## Key papers

- [[geometric-deep-learning-molecular-representations]] — the review categorizes equivariant MPNN variants and surveys their performance across quantum chemistry, drug discovery, and CASP.

## My understanding

The interesting question is no longer "can we build equivariant GNNs" but "when does the cost of equivariance pay off downstream?" For quantum chemistry the answer is consistently yes; for drug discovery the answer is "often not enough to justify the model complexity." The Atz et al. review is honest about this gap.
