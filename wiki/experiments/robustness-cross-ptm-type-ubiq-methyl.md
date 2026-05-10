---
title: "Robustness: cross-PTM-type generalization of calibrated ΔpTernary (ubiquitylation + methylation tracks)"
slug: "robustness-cross-ptm-type-ubiq-methyl"
status: planned
target_claim: "ptm-protein-isoforms-enable-selective-drug"
hypothesis: "On held-out tracks of (a) mono-ubiquitylation-degron PROTACs and (b) methylation-degron PROTACs, the calibrated ΔpTernary pipeline (DeepTernary, Boltz-2 PTM tokens, per-POI noise-floor) maintains top-K ranking AUC lift >= 0.03 over the PTM-blind baseline. A drop below 0.03 indicates the AUC lift on phospho-PROTACs does not generalize across PTM types; a drop below zero (i.e., the pipeline ranks worse than baseline) indicates active harm and must be reported."
tags: [robustness, generalization, ubiquitylation, methylation, deepternary, deltapternary, ptm-isoforms]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "Same as [[calibrated-deltapternary-phospho-protac-ranking]] — DeepTernary + Boltz-2 PTM tokens"
  dataset: "Held-out tracks: (a) mono-ubiquitylation-degron PROTACs (≈10-15 entries from PROTAC-DB + literature mining), (b) methylation-degron PROTACs (≈8-12 entries from histone methylation degraders + EZH2-substrate degraders); matched negatives from PROTAC-DB CRBN+VHL with no annotated PTM-isoform selectivity"
  hardware: "2 × A100 80GB"
  framework: "Same as Stage 2b; only the held-out track changes; per-POI noise-floor table extended to cover the new POIs"
metrics: ["top-K=20 AUC per track", "AUC lift over PTM-blind baseline per track", "cross-track per-POI noise-floor comparison (phospho vs ubiq vs methyl-perturbation magnitudes)"]
baseline: "PTM-blind DeepTernary ranking (WT-only POI) on each respective track"
outcome: ""
key_result: ""
linked_idea: "ptm-aware-degrader-target-nomination"
date_planned: 2026-05-02
date_completed: ""
run_log: ""
started: ""
estimated_hours: 16
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective

Check whether the headline ΔpTernary AUC lift on phospho-PROTACs generalizes to mechanistically distinct PTM types (ubiquitylation, methylation). Generalization across PTM types is the headline-strength condition for [[ptm-protein-isoforms-enable-selective-drug]]; a phospho-only lift would be a much weaker (and narrower) result.

## Setup

- **Track A — ubiquitylation**: ≈10-15 mono-Ub-degron PROTACs from PROTAC-DB + literature; the perturbation magnitude is ≈ 8.5 kDa (mono-Ub is much larger than phospho — the noise-floor calibration table needs a separate Ub-mass perturbation arm in Phase-0 follow-up).
- **Track B — methylation**: ≈8-12 methylation-degron PROTACs (histone methyl-tail degraders, EZH2-substrate degraders); perturbation magnitude is ≈ 14-42 Da (smaller than phospho).
- **Boltz-2 PTM tokens**: native CCD-PTM tokens for ubiquitin attachment and mono/di/tri-methyl-Lys are all present in Jan 2026 weights.
- **Statistical replication**: 3 seeds per track (smaller positive sets justify fewer seeds; budget allocation).

## Procedure

1. Compile and curate the two held-out tracks; verify zero leakage with TernaryDB / PROTAC-DB training splits.
2. Extend the per-POI noise-floor calibration table to cover (a) ≈8.5 kDa Ub-mass perturbations and (b) ≈14-42 Da methyl-mass perturbations. Important: the perturbation mass must match the PTM-type-specific scale, NOT reuse the phospho ≈80 Da setting.
3. Score WT and PTM-occupied POI structures via Boltz-2 + DeepTernary; compute calibrated ΔpTernary per the new tables.
4. Compute top-K=20 AUC and AUC lift over PTM-blind baseline per track.
5. Cross-PTM comparison: report whether the noise-floor magnitudes scale with the perturbation size as expected (linear-ish for small perturbations, super-linear when perturbation is large enough to hit a discontinuity in the scorer's training distribution).

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **Both tracks lift >= 0.03** → cross-PTM generalization holds; strongly supports the headline claim's broad scope.
- **One track lifts >= 0.03, the other does not** → the headline applies to a subset of PTM types; record per-PTM-type breakdown in [[ptm-protein-isoforms-enable-selective-drug]] conditions field; do NOT generalize the headline across all PTMs.
- **Neither lifts >= 0.03 OR negative lift on either** → the phospho result was a special case; report as such and tighten the scope of [[ptm-protein-isoforms-enable-selective-drug]] to phospho-PROTACs only. A negative lift (worse than baseline) on either track requires immediate investigation: scorer training data for that PTM type is likely so sparse that the calibrated ΔpTernary pipeline is actively misled.
