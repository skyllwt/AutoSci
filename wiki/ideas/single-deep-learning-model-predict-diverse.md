---
title: "A single deep-learning model can predict diverse biomolecular complexes at high accuracy"
slug: "single-deep-learning-model-predict-diverse"
status: validated
origin: "Migrated from claims/single-deep-learning-model-predict-diverse on 2026-05-10 (was status: supported, confidence: 0.8); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [structure-prediction, biomolecular-complexes, alphafold, generalist-model]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

A single deep-learning model can predict the joint atomic structure of biomolecular complexes containing proteins, nucleic acids, small-molecule ligands, ions, and covalent modifications at higher accuracy than the best specialised predictor for each interaction class, when given only sequence and SMILES inputs.

**Scope and conditions.** - PDB-like complex inputs within the 5,120-token inference budget.
- Protein chains with sufficient MSA depth — accuracy degrades on shallow-MSA targets, similar to AF2 and AF-Multimer 2.3.
- Evaluation respects the AF3 homology filters (max 40% sequence identity to the training set) and the standard PoseBusters / CASP15 benchmark configurations; results outside these regimes are not directly tested.
- Does not extend to dynamical or multi-state behaviour: AF3 returns one static structure per seed.
- Does not extend to assemblies that exceed the inference token budget (membrane channels, full ribosomes, viral capsids).

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- AF3 underperforms the human-aided AIchemy_RNA2 on CASP15 RNA targets, suggesting that for RNA tertiary structure a specialist with human input still wins.
- Conformational coverage failures — e.g. cereblon predicted in the closed state for both apo and holo inputs — show that the "high accuracy" claim is class-aggregated and breaks for targets where a specialist exploiting MSA-resampling or ensemble methods could do better.
- 4.4% chirality-violation rate on PoseBusters means a non-trivial fraction of "successful" predictions are stereochemically invalid; specialised docking tools with explicit chirality constraints do not have this failure mode.
- AF3 weights and full training data were not released at publication, limiting independent verification of the headline benchmark numbers.

**Open questions.**

- Does the lift come from joint training across classes, from the diffusion head, or from training-set scale? Per-component ablations are not reported.
- How thin can the per-class training set become before a specialist beats AF3 on that class?
- Does the result transfer to under-represented PDB classes (membrane proteins, ribozyme intermediates, large RNA-RNA contacts) without class-specific fine-tuning?

## Pilot results

AlphaFold 3 reports head-to-head benchmark wins against specialised baselines in every interaction class it covers (Fig. 1c and Extended Data Table 1 of the paper), with significance levels at or below 10⁻³ in every comparison and below 10⁻¹⁸ for the largest cohorts. Wins are consistent across orthogonal metrics: pocket-aligned r.m.s.d. (ligands), interface LDDT (nucleic-acid interfaces), DockQ (protein-protein and antibody-antigen), and per-chain LDDT (monomers). The same trained weights handle all classes — there is no per-class fine-tuned variant in the headline numbers. A concurrent generalist (RoseTTAFold All-Atom) is included as a baseline and is beaten by AF3 on PoseBusters, suggesting the result is not specific to AF3's particular architecture but is at least achievable by the unified-prediction stance with current architectures and data.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
