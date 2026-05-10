---
title: "Deep learning can predict protein structure at near-experimental atomic accuracy from sequence alone"
slug: "deep-learning-predicts-protein-structure-atomic"
status: validated
origin: "Migrated from claims/deep-learning-predicts-protein-structure-atomic on 2026-05-10 (was status: supported, confidence: 0.92); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [protein-structure-prediction, deep-learning, casp14, alphafold, atomic-accuracy]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

Given a protein's amino acid sequence, an MSA derived from large public sequence databases, and optional structural templates, a deep neural network with the right architectural and loss inductive biases can predict the full 3D structure of the protein at near-experimental atomic accuracy — competitive with X-ray crystallography for the majority of single-chain targets — without requiring a homologous structure to be solved.

**Scope and conditions.** The atomic-accuracy claim applies to:

- Single chains in the regime spanned by the PDB.
- Chains with sufficient MSA depth (median Neff per residue greater than ~30; diminishing returns past ~100).
- Targets where the fold is not predominantly shaped by interactions with other chains, ligands, ions, or cofactors that are not implied by the sequence.

Outside these conditions, accuracy degrades, and the appropriate weaker claim is that confidence-calibrated structure prediction is possible but not yet at experimental accuracy.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- AlphaFold2 reports its own failure modes (low-MSA-depth proteins, hetero-complex bridging domains, ligand-dependent folds) which are localised counter-evidence. These do not refute the claim under its stated conditions but bound its scope.
- Subsequent work on conformational ensembles and intrinsically disordered regions raises an open question about whether "near-experimental atomic accuracy" extends from the most-likely-PDB-conformation to the biologically relevant ensemble.

**Open questions.**

- How does the claim transfer to biomolecular complexes (protein-protein, protein-NA, protein-ligand)?
- For orphan sequences and de novo designs, can self-distillation or large language models on protein sequences close the MSA-depth gap?
- Are pLDDT/pTM still well-calibrated outside the PDB-spanned regime where the claim is established?

## Pilot results

- **CASP14 (blind test)**: AlphaFold2's median backbone Calpha r.m.s.d.95 of 0.96 angstrom is within the ~1.4 angstrom width of a carbon atom and beats the second-best method by a factor of ~3.
- **Recent PDB chains (post-cutoff)**: median full-chain Calpha r.m.s.d.95 of 1.46 angstrom on a redundancy-filtered set of 3,144 chains.
- **Confidence calibration**: the network's pLDDT and pTM heads correlate strongly with realised accuracy (Pearson r = 0.76 and 0.85 respectively on n=10,795 chains), so the claim of atomic accuracy is paired with a usable per-prediction reliability estimate.
- **Ablations**: removing key inductive biases (IPA, triangle updates, end-to-end structure gradients, recycling) materially degrades accuracy, indicating that the result is not generic-deep-learning but tied to specific design choices.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
