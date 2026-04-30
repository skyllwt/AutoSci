---
title: "Geometric deep learning"
aliases: ["GDL", "geometric DL", "deep learning with geometric priors"]
tags: [deep-learning, equivariance, invariance, symmetry, neural-architectures]
maturity: active
key_papers: [geometric-deep-learning-molecular-representations]
first_introduced: "Bronstein et al., 2017 (IEEE Signal Processing Magazine)"
date_updated: 2026-04-30
related_concepts: [equivariant-message-passing-neural-network, smiles-chemical-language-modelling]
---

## Definition

Geometric deep learning (GDL) is the umbrella term for neural-network architectures that incorporate and exploit geometric priors — information about the structure and symmetry properties of the input domain. GDL generalizes classical (Euclidean, grid-based) deep learning to non-Euclidean domains such as graphs, manifolds, meshes, point clouds, and structured strings, and to architectures whose layers transform equivariantly or invariantly under a chosen symmetry group.

## Intuition

A standard convolutional network bakes in translation equivariance over a regular pixel grid. GDL asks: what is the right symmetry group for *your* data, and can we design layers that respect it natively? For molecules, the natural group is E(3) or SE(3) (rotations, translations, optionally reflections) plus permutation of atom orderings. Architectures that bake in these symmetries no longer have to learn them from data, which improves sample efficiency and generalization.

## Formal notation

Given an input X and a transformation T from a symmetry group G, a neural network F is:

- **Equivariant** if F(T(X)) = T'F(X) for some T' in the same group (the transformation commutes with the layer).
- **Invariant** if F(T(X)) = F(X) (T' is the identity action; a special case of equivariance).
- **Non-equivariant** if neither holds.

A network is equivariant under G when every layer transforms equivalently under every action of G.

## Variants

- **Graph neural networks (GNNs)** for graphs and 3D point clouds; message passing is permutation-equivariant by construction.
- **E(3)- and SE(3)-equivariant message-passing GNNs** for 3D molecular graphs (tensor field networks, EGNN, Cormorant, SE(3)-Transformer, NequIP, PaiNN); use spherical harmonics, irreducible representations, or scalarized geometric features to enforce rotation equivariance.
- **3D CNNs** over voxel grids — translation-equivariant but not rotation-equivariant; rely on data augmentation.
- **Geodesic / mesh CNNs** over molecular surfaces.
- **Equivariant transformers** combining attention with E(3) / SE(3) equivariant layers (used in protein structure prediction).

## Comparison

vs. classical deep learning on molecules (descriptors + MLP / CNN over Euclidean tensors): GDL replaces hand-engineered, symmetry-stripped descriptors with learned features over the natural geometric structure of the molecule. vs. plain GNNs without 3D awareness: equivariant-GDL variants additionally distinguish stereochemical configurations that 2D-graph models conflate.

## When to use

- Inputs have a clear, exploitable symmetry group (graphs, point clouds, meshes, sequences with chemical structure).
- Sample efficiency matters and the symmetry would otherwise be learned from data.
- Targets that should be invariant or equivariant under the chosen group (energies are invariant; forces and dipole moments are equivariant).

## Known limitations

- SE(3)-equivariant layers using spherical harmonics and Wigner-D matrices are computationally expensive and limit applicability to small / medium molecular systems.
- For drug-discovery property prediction, the empirical benefit of 3D / equivariant priors over 2D-graph baselines is inconsistent.
- Equivariance to a chosen group is double-edged: E(3)-equivariant networks cannot distinguish enantiomers (because they are equivariant to reflection); SE(3)-equivariant networks can.
- No standard benchmark for evaluating learned-feature quality (vs. end-task accuracy).

## Open problems

- Optimal trade-off between equivariance, expressivity, and compute for drug-discovery scale tasks.
- Geometry-aware applicability-domain assessment for GDL models.
- Benchmarks for the *quality of learned molecular features* rather than only end-task performance.
- Routine integration of explainable-AI tooling into GDL pipelines for domain-expert audit.

## Key papers

- [[geometric-deep-learning-molecular-representations]] (Atz, Grisoni, Schneider, 2021) — canonical review of GDL on molecular representations.

## My understanding

GDL is best understood as a design-principle layer above architecture choice: pick the symmetry group that matters for your data, then choose an architecture whose layers respect it. The Atz et al. review is the most readable introduction for chemists; the Bronstein et al. proto-book ("grids, groups, graphs, geodesics, and gauges") is the deeper mathematical reference.
