---
title: "Robustness: mutant-isoform PROTAC track (p53-Y220C, p53-R175H) reported separately from PTM track"
slug: "robustness-mutant-isoform-track-y220c-r175h"
status: planned
target_claim: "ptm-protein-isoforms-enable-selective-drug"
hypothesis: "On a held-out mutant-isoform PROTAC track (p53-Y220C bifunctional recruiters, p53-R175H bifunctional recruiters, ≈6-10 entries), the calibrated ΔpTernary pipeline shows AUC lift over PTM-blind baseline whose magnitude is DIFFERENT from the phospho-PROTAC AUC lift in [[calibrated-deltapternary-phospho-protac-ranking]] by >= 0.05 in EITHER direction. The two tracks must NOT be conflated in the headline number for [[ptm-protein-isoforms-enable-selective-drug]]: PTM and mutation are mechanistically distinct (covalent chemistry vs sequence change) even though both produce 'isoform-selective' drugs."
tags: [robustness, mutant-isoform, p53-y220c, p53-r175h, deltapternary, separation-of-tracks]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "Same as Stage 2b — DeepTernary + Boltz-2 (no CCD-PTM tokens needed; the 'PTM' here is a residue substitution, handled natively by Boltz-2 from a mutant sequence)"
  dataset: "Held-out mutant-isoform PROTAC track: ≈6-10 entries covering p53-Y220C bifunctional recruiters and p53-R175H bifunctional recruiters (PROTAC-DB + literature curation); matched negatives from PROTAC-DB CRBN+VHL"
  hardware: "1 × A100 80GB"
  framework: "Same as Stage 2b; per-POI noise-floor table extended to cover mutant POI variants (random size-matched residue substitutions, not chemical modifications)"
metrics: ["top-K=20 AUC on mutant-isoform track", "AUC lift over PTM-blind baseline on mutant-isoform track", "absolute difference vs phospho-PROTAC AUC lift", "per-POI breakdown of the two tracks side by side"]
baseline: "PTM-blind DeepTernary ranking (WT POI = wild-type p53 in this case) on the mutant-isoform held-out set"
outcome: ""
key_result: ""
linked_idea: "ptm-aware-degrader-target-nomination"
date_planned: 2026-05-02
date_completed: ""
run_log: ""
started: ""
estimated_hours: 12
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective

Run the calibrated ΔpTernary pipeline on a parallel mutant-isoform PROTAC track and report the result SEPARATELY from the phospho-PROTAC track. The source idea explicitly calls out that conflating mutant and PTM tracks would inflate the headline number; this experiment guards against that conflation by computing the two AUCs on independent held-out sets and contrasting them.

## Setup

- **Mutant-isoform set**: ≈6-10 entries: p53-Y220C bifunctional recruiters (the AOH1996 series and follow-ons) + p53-R175H bifunctional recruiters where structurally annotated.
- **POI structures**: predicted directly by Boltz-2 from mutant sequence (no CCD-PTM tokens; Boltz-2 handles residue substitutions natively).
- **Calibration**: per-POI noise-floor table extended via random size-matched residue substitutions (not chemical modifications). For Y220C: random ≈0.1-Å volume-change substitutions at non-interface positions. For R175H: random charge-change substitutions matched in volume.
- **Statistical replication**: 3 seeds.

## Procedure

1. Compile and curate the mutant-isoform held-out set; verify zero leakage with Boltz-2 training data (mutant p53 structures may already be present — flag and exclude any leaked entries).
2. For each tuple: predict {WT p53 POI structure, mutant POI structure} via Boltz-2; score both with DeepTernary; compute calibrated ΔpTernary per the mutant-noise-floor table.
3. Compute top-K=20 AUC and AUC lift over PTM-blind baseline.
4. Side-by-side comparison: tabulate phospho-PROTAC AUC lift (from Stage 2b) and mutant-isoform AUC lift; compute the absolute difference and analyse per-POI residuals.
5. Explicitly DO NOT pool the two tracks into a combined AUC for headline reporting.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **Mutant lift differs from phospho lift by >= 0.05** (in either direction) → confirms the two tracks are mechanistically distinct in the ΔpTernary regime; record this as a `conditions` constraint on [[ptm-protein-isoforms-enable-selective-drug]] that the support is stratified by PTM-vs-mutation mechanism.
- **Mutant lift within ±0.05 of phospho lift** → the two tracks behave similarly under this pipeline; this is a NEGATIVE result for the separation hypothesis but does NOT necessarily justify pooling — record the similarity and flag for further mechanistic investigation (the apparent comparability may be a degeneracy of the noise-floor protocol rather than real biology).
- **Mutant lift is sharply negative while phospho lift is positive** → the calibration table built from mutation-magnitude perturbations is mis-calibrated for the actual mutational effect; redesign the per-POI noise-floor protocol for mutants before drawing any cross-track conclusions.
