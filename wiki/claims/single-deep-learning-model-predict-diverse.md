---
title: "A single deep-learning model can predict diverse biomolecular complexes at high accuracy"
slug: "single-deep-learning-model-predict-diverse"
status: supported
confidence: 0.8
tags: [structure-prediction, biomolecular-complexes, alphafold, generalist-model]
domain: "Computational Biology / ML for Science"
source_papers: [accurate-structure-prediction-biomolecular-interactions-alphafold]
evidence:
  - source: accurate-structure-prediction-biomolecular-interactions-alphafold
    type: supports
    strength: strong
    detail: "AlphaFold 3, a single trained model, achieves significantly higher accuracy than specialised baselines across protein-ligand (PoseBusters v.1, n=428, vs. AutoDock Vina P = 2.27 × 10⁻¹³ and vs. RoseTTAFold All-Atom P = 4.45 × 10⁻²⁵), protein-RNA (n=25, P = 2.57 × 10⁻³), protein-dsDNA (n=38, P = 2.78 × 10⁻³), protein-protein (n=1,064, P = 1.81 × 10⁻¹⁸), and antibody-antigen (n=65, P = 6.54 × 10⁻⁵, with 1,000 seeds) tasks, plus a highly significant protein-monomer LDDT improvement over AF-Multimer 2.3 (P = 1.74 × 10⁻³⁴)."
conditions: "PDB-like complexes within the 5,120-token inference budget; sufficient MSA depth for protein chains; structures within the homology and quality filters used for evaluation. Does not extend to dynamical / multi-state prediction or to assemblies beyond the inference token budget."
date_proposed: 2026-04-30
date_updated: 2026-04-30
---

## Statement

A single deep-learning model can predict the joint atomic structure of biomolecular complexes containing proteins, nucleic acids, small-molecule ligands, ions, and covalent modifications at higher accuracy than the best specialised predictor for each interaction class, when given only sequence and SMILES inputs.

## Evidence summary

AlphaFold 3 reports head-to-head benchmark wins against specialised baselines in every interaction class it covers (Fig. 1c and Extended Data Table 1 of the paper), with significance levels at or below 10⁻³ in every comparison and below 10⁻¹⁸ for the largest cohorts. Wins are consistent across orthogonal metrics: pocket-aligned r.m.s.d. (ligands), interface LDDT (nucleic-acid interfaces), DockQ (protein-protein and antibody-antigen), and per-chain LDDT (monomers). The same trained weights handle all classes — there is no per-class fine-tuned variant in the headline numbers. A concurrent generalist (RoseTTAFold All-Atom) is included as a baseline and is beaten by AF3 on PoseBusters, suggesting the result is not specific to AF3's particular architecture but is at least achievable by the unified-prediction stance with current architectures and data.

## Conditions and scope

- PDB-like complex inputs within the 5,120-token inference budget.
- Protein chains with sufficient MSA depth — accuracy degrades on shallow-MSA targets, similar to AF2 and AF-Multimer 2.3.
- Evaluation respects the AF3 homology filters (max 40% sequence identity to the training set) and the standard PoseBusters / CASP15 benchmark configurations; results outside these regimes are not directly tested.
- Does not extend to dynamical or multi-state behaviour: AF3 returns one static structure per seed.
- Does not extend to assemblies that exceed the inference token budget (membrane channels, full ribosomes, viral capsids).

## Counter-evidence

- AF3 underperforms the human-aided AIchemy_RNA2 on CASP15 RNA targets, suggesting that for RNA tertiary structure a specialist with human input still wins.
- Conformational coverage failures — e.g. cereblon predicted in the closed state for both apo and holo inputs — show that the "high accuracy" claim is class-aggregated and breaks for targets where a specialist exploiting MSA-resampling or ensemble methods could do better.
- 4.4% chirality-violation rate on PoseBusters means a non-trivial fraction of "successful" predictions are stereochemically invalid; specialised docking tools with explicit chirality constraints do not have this failure mode.
- AF3 weights and full training data were not released at publication, limiting independent verification of the headline benchmark numbers.

## Linked ideas

(none yet)

## Open questions

- Does the lift come from joint training across classes, from the diffusion head, or from training-set scale? Per-component ablations are not reported.
- How thin can the per-class training set become before a specialist beats AF3 on that class?
- Does the result transfer to under-represented PDB classes (membrane proteins, ribozyme intermediates, large RNA-RNA contacts) without class-specific fine-tuning?
