---
title: "Accurate structure prediction of biomolecular interactions with AlphaFold 3"
slug: "accurate-structure-prediction-biomolecular-interactions-alphafold"
arxiv: ""
venue: "Nature"
year: 2024
tags: [structure-prediction, alphafold, diffusion, protein-ligand, protein-nucleic-acid, biomolecular-complexes]
importance: 5
date_added: 2026-04-30
source_type: pdf
s2_id: ""
keywords: [AlphaFold 3, pairformer, diffusion module, protein-ligand docking, PoseBusters, protein-nucleic acid, antibody-antigen, biomolecular complex]
domain: "Computational Biology / ML for Science"
code_url: ""
cited_by: []
---

## Problem

Modelling biomolecular complexes — proteins together with nucleic acids, small-molecule ligands, ions, and modified residues — is central to understanding cellular function and to rational drug design, but the field had been fragmented. AlphaFold 2 transformed protein-only structure prediction, and AlphaFold-Multimer extended it to protein-protein complexes, but a wide zoo of specialised tools handled each remaining interaction class (docking, RNA folding, glycosylation, etc.) and most deep-learning attempts at general biomolecular prediction trailed physics-inspired methods. A unified, high-accuracy predictor for arbitrary complexes from sequence and SMILES inputs alone did not yet exist.

## Key idea

Build a single deep-learning system that ingests any biomolecular complex (polymer sequences plus ligand SMILES plus covalent-bond annotations) and predicts the joint atomic structure. Two architectural shifts make this practical: (1) replace the AlphaFold 2 evoformer with the simpler **pairformer**, which de-emphasises MSA processing and routes information almost entirely through the pair representation, and (2) replace the structure module — built around amino-acid-specific frames and torsion angles — with a **diffusion module** that directly denoises raw atomic coordinates without any equivariant machinery, eliminating stereochemical-violation losses and special handling of bonded chemistry.

## Method

- **Inputs.** Polymer sequences (protein, DNA, RNA), ligand SMILES, residue modifications, and covalent-bond annotations are passed through an input embedder, conformer generation, template search, and a small MSA module (4 blocks).
- **Trunk.** 48 pairformer blocks operate on a pair representation (n × n × 128) and a single representation (n × 384). The pairformer keeps triangle updates and triangle self-attention from AF2 but drops MSA-row attention; the MSA module is a thin pair-weighted-averaging block, not a row-column transformer.
- **Diffusion module.** Replaces the AF2 structure module. A 3 + 24 + 3-block stack with per-atom and per-token conditioning denoises noised atomic coordinates back to the true coordinates, following the EDM diffusion formulation. No rotational frames, no torsion parameterisation, no equivariance constraints. The multiscale denoising trains the network to handle local stereochemistry at low noise and global geometry at high noise.
- **Confidence head.** Because diffusion training only sees a single denoising step, AF3 introduces a "mini-rollout" during training (larger step size, full structure generated) so a separate confidence module can be trained to predict pLDDT, PAE, and a new PDE matrix.
- **Anti-hallucination.** Cross-distillation from AlphaFold-Multimer v2.3 predictions, plus a ranking term that rewards solvent-accessible surface area, suppresses spurious compact structure in disordered regions.
- **Training.** Three stages — initial training (crop 384), fine-tune 1 (crop 640), fine-tune 2 (crop 768). PDB cut-off 30 September 2021 (or 2019 for PoseBusters runs). Mini-batch 256 inputs × 32-48 diffusion samples per step.
- **Inference.** 5 model seeds × 5 diffusion samples = 25 candidates per target, ranked by a global score combining pTM/ipTM with chirality and clash penalties. For antibody-antigen, ranking quality keeps improving up to 1,000 seeds.

## Results

- **Protein-ligand (PoseBusters v.1, n = 428).** AF3 achieves substantially higher pocket-aligned-r.m.s.d. < 2 Å success than AutoDock Vina (P = 2.27 × 10⁻¹³) and RoseTTAFold All-Atom (P = 4.45 × 10⁻²⁵), despite using only sequence and SMILES inputs while Vina is given the holo pocket.
- **Protein-nucleic acid.** Higher interface LDDT than RoseTTAFold2NA on protein-RNA (n = 25, P = 2.57 × 10⁻³) and protein-dsDNA (n = 38, P = 2.78 × 10⁻³); higher CASP15 RNA accuracy than RoseTTAFold2NA and AIchemy_RNA (the best automated CASP15 entry), though still below the human-aided AIchemy_RNA2.
- **Covalent modifications.** Bonded ligands (n = 66) and glycosylation (n = 28) predicted at high success rates; modified residues handled without specialised heads.
- **Protein complexes.** All protein-protein DockQ > 0.23 success up significantly versus AlphaFold-Multimer v2.3 (n = 1,064, P = 1.81 × 10⁻¹⁸); antibody-antigen interfaces show a particularly large improvement (n = 65, P = 6.54 × 10⁻⁵, with 1,000 seeds).
- **Monomers.** Protein-monomer LDDT improvement over AF-M 2.3 is highly significant (P = 1.74 × 10⁻³⁴).
- **Confidence calibration.** Chain-pair ipTM tracks DockQ and interface LDDT across complex types; per-chain pLDDT tracks LDDT-to-polymer for proteins, nucleic acids, and ligands.

## Limitations

- **Stereochemistry.** 4.4% chirality-violation rate on PoseBusters even with a chirality penalty in the ranker. Atom clashes still occur, especially in protein-nucleic complexes with > 100 nucleotides and > 2,000 residues total; some homomers produce overlapping chains.
- **Hallucination in disordered regions.** Diffusion can synthesise plausible-looking but spurious compact structure in IDRs; cross-distillation from AF2 plus an SASA ranking term reduces but does not eliminate the failure mode.
- **Single-state predictor.** AF3 returns one static structure per seed; multiple seeds do not approximate the solution ensemble. Conformational coverage is limited — e.g. cereblon is predicted in the closed (holo) state even when given as apo.
- **Antibody-antigen sampling cost.** High accuracy requires ranking over up to 1,000 model seeds, increasing inference cost relative to the standard 5-seed protocol.
- **MSA-depth dependence.** Like AF-Multimer 2.3, AF3 degrades on shallow-MSA targets.
- **No public model weights at release** (covered in the original paper text only as "data availability" — limits independent replication and benchmarking compared with AF2's open release).

## Open questions

- Can a generative structure predictor be coupled to an MSA-resampling or ensemble-sampling scheme to recover dynamical / multi-state behaviour rather than collapsing to a single PDB-like snapshot?
- How much of AF3's lift over specialised docking tools comes from joint training versus the diffusion formulation versus dataset scale? Ablations isolating each are not reported.
- What is the smallest training set (or which data slices) sufficient to match AF3 quality on a given complex class — i.e. how data-efficient is the unified framework relative to specialised predictors per class?
- Can the diffusion module's lack of equivariance be exploited (or replaced) to add cheap symmetry-aware prior, narrowing the chirality-violation gap?
- Does the same recipe transfer to membrane proteins, glycan-only structures, RNA-RNA tertiary contacts, or ribozyme catalysis intermediates that are under-represented in the PDB?

## My take

AF3 is the clearest demonstration so far that biomolecular structure prediction is a single problem rather than a federation of specialised problems — and that a generative diffusion head, with all its messiness, beats hand-engineered equivariant heads once the data and pair representation are good enough. The most surprising design choice is the unconditional drop of equivariance in the structure-generation step: AF2's invariant point attention was treated as load-bearing, and AF3 simply removes it. The price is paid in occasional chirality and clash failures, papered over by ranking heuristics. The paper is also notable for what it does **not** include: open weights, full training data, and ablation tables that would let outside groups reproduce the architectural claims. For a model of this importance, the gap between "we ran the experiment" and "you can run it too" is unusually wide; most of the open questions above will be answered by community reimplementations rather than by the original paper.

## Related

- [[pairformer-module]]
- [[diffusion-based-structure-prediction]]
- [[biomolecular-complex-prediction-unified-deep-learning]]
- [[unified-deep-learning-handles-biomolecular-complexes]]
- [[diffusion-replaces-equivariant-structure-modules]]
- [[demis-hassabis]]
- [[john-jumper]]
- [[max-jaderberg]]
- [[josh-abramson]]
- [[highly-accurate-protein-structure-prediction-alphafold]]
