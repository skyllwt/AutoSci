---
title: "Geometric deep learning on molecular representations"
slug: "geometric-deep-learning-molecular-representations"
arxiv: ""
venue: "Nature Machine Intelligence"
year: 2021
tags: [geometric-deep-learning, molecular-modelling, graph-neural-networks, drug-discovery, quantum-chemistry, casp, equivariance, smiles, review]
importance: 4
date_added: 2026-04-30
source_type: tex
s2_id: ""
keywords: [geometric deep learning, molecular graphs, equivariant neural networks, message passing, SMILES, 3D CNN, molecular surfaces, drug discovery, quantum chemistry, CASP]
domain: "ML for Molecules"
code_url: ""
cited_by: []
---

## Problem

Deep learning is increasingly applied to the molecular sciences (drug discovery, quantum chemistry, computer-aided synthesis planning), but molecules can be represented in many distinct ways — graphs, 3D point clouds, grids, surfaces, strings — each with different symmetry properties. Standard deep learning operates on Euclidean tensors and ignores the rotational, translational, reflective, and permutation symmetries that govern molecular reality. Without geometric priors, models waste capacity learning these symmetries from data, struggle on small datasets, and fail to distinguish chemically meaningful cases such as enantiomers from diastereomers. A unifying treatment that connects molecular representation choice, neural-network architecture, and the symmetry group that should be respected has been missing.

## Key idea

Geometric deep learning (GDL) is the umbrella for neural-network architectures that incorporate and process symmetry information about their inputs. For molecules, this means designing networks whose layers transform equivariantly (or invariantly) under the symmetry group of interest — typically the Euclidean group E(3) or the special Euclidean group SE(3), plus permutation of atom orderings. The choice of molecular representation (graph, 3D graph, point cloud, grid, surface, SMILES string) determines which symmetries are natural to enforce, and the architecture (GNN, equivariant message-passing GNN, 3D CNN, geodesic CNN, RNN, transformer) determines how those priors are realized. The review organizes molecular GDL by representation, lays out the trade-offs between expressivity, computational cost, and which chiral / stereochemical distinctions a given equivariance class can capture.

## Method

The article is a structured review rather than a new system. Its organization is the contribution:

- **Foundations.** Defines invariance, equivariance, and non-equivariance with respect to symmetry group transformations, recasts the standard E(3)/SE(3) operations (rotation, translation, reflection) in the molecular setting, and explains why incorporating geometric priors is a core design principle for modern neural networks.
- **Learning on graphs and point clouds.** GNNs and message-passing neural networks (MPNNs) for 2D / 3D molecular graphs and 3D point clouds; SchNet- and PaiNN-style architectures that include radial / angular edge features; SE(3)- and E(3)-equivariant GNNs (tensor field networks, EGNN, Cormorant, SE(3)-Transformers, NequIP) that exploit Euclidean symmetries via spherical harmonics or scalarized message passing. Discussion of graph-isomorphism limits of plain MPNNs and why angular features broaden the distinguishable graph class.
- **Learning on grids.** 3D CNNs over voxel grids of molecular conformers, used heavily for protein-ligand binding affinity (KDEEP), pose scoring, and active-site recognition. Trade-off: efficient on large macromolecules but not rotation-equivariant.
- **Learning on surfaces.** Geodesic / mesh CNNs and 3D GNNs for molecular surfaces (MaSIF-style), used for protein-protein interaction prediction and ligand-pocket fingerprinting; voxelized surface variants feeding 3D CNNs.
- **Learning on strings.** SMILES (and InChI / DeepSMILES / SELFIES) processed by RNNs and transformers as 1D or graph-structured sequences; transfer learning, reinforcement learning, and bidirectional training for de novo molecular design; molecular transformers for retrosynthesis and reaction prediction; equivariant transformers for protein structure prediction (AlphaFold).

Three target application areas — drug discovery, quantum chemistry, and computer-aided synthesis planning (CASP) — are tracked across all representation classes.

## Results

The review synthesizes empirical findings from the cited literature rather than presenting new experiments. Key takeaways:

- Equivariant message-passing GNNs achieve state-of-the-art on quantum-chemical energy, force, and wavefunction prediction for small molecules; SE(3)-equivariant variants distinguish enantiomers, E(3)-equivariant variants do not but are computationally cheaper and competitive on rotation-invariant targets.
- For drug-discovery property prediction, adding 3D geometric information often does not clearly outweigh the modeling cost of equivariant architectures over plain 2D-graph MPNNs.
- 3D CNNs remain practical for macromolecule-scale tasks (binding affinity, pocket recognition) where equivariant GNNs hit memory limits.
- SMILES-based RNNs and transformers dominate generative molecular design and retrosynthesis, with the Frechet ChemNet Distance as the de facto similarity benchmark.
- Equivariant transformers hybrid with E(3) / SE(3) layers achieve state-of-the-art on protein structure prediction.
- Box 3 demonstrates an E(3)-equivariant GNN trained on estrogen-receptor binding data, showing that intermediate-layer features capture both bioactivity and atom scaffolds — a concrete example of GDL feature interpretability.

## Limitations

- Equivariant message-passing networks (especially SE(3) variants using spherical harmonics and Wigner D-matrices) scale poorly to large molecular systems; quantum-mechanical wavefunction predictors are limited by quadratic scaling in electron count.
- For drug-relevant property prediction, the empirical benefit of 3D / equivariant architectures over 2D-graph baselines is inconsistent, and the added complexity is hard to justify case by case.
- Plain 2D-graph MPNNs cannot distinguish certain non-isomorphic graphs (Weisfeiler-Lehman bound).
- SMILES is non-univocal: the same molecule yields many strings, complicating property-prediction settings.
- Contemporary GDL studies routinely lack applicability-domain analysis, making it hard to know when predictions are trustworthy.
- No standard benchmark exists for evaluating the *quality of learned features* (as opposed to property-prediction or generation metrics).
- Mesh GNNs with rotational equivariance for molecular surfaces remain mostly unexplored experimentally.

## Open questions

- What is the optimal trade-off between equivariance, expressivity, and computational cost for drug-discovery scale problems?
- How can applicability-domain assessment ("where is this GDL model reliable?") be made geometry-aware and standard practice?
- Can quantum / electronic-structure features from fast quantum-ML models become a routine input representation for downstream GDL?
- What benchmarks would systematically evaluate learned molecular features rather than only end-task performance?
- How can interpretability tools (explainable AI for graphs) be integrated into GDL pipelines so domain experts can audit predictions?

## My take

This review is the canonical entry point into molecular GDL: it organizes a fragmented, fast-moving literature by molecular representation and symmetry group, gives a clean mental model of equivariance / invariance for chemists, and is honest about where 3D geometric priors do not yet pay off (drug-discovery property prediction). The taxonomy is the most reusable contribution — papers that follow it tend to slot cleanly into one of the (representation, architecture, symmetry) cells, which makes the literature navigable. The headline open question — when does the cost of equivariance buy you measurable downstream improvement — remains live and is exactly the empirical question that subsequent equivariant-architecture papers (NequIP, MACE, Allegro, GemNet, etc.) keep retesting.

## Related

- [[geometric-deep-learning]]
- [[equivariant-message-passing-neural-network]]
- [[smiles-chemical-language-modelling]]
- [[geometric-priors-improve-molecular-modelling]]
- [[equivariant-3d-models-improve-quantum-chemistry-not-uniformly-drug-discovery]]
- [[medpredict]]
