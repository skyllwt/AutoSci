---
title: "Ablation: DeepTernary vs PROTAC-STAN scorer substitution on the same calibrated ΔpTernary protocol"
slug: "ablation-deepternary-vs-protac-stan-scorer"
status: planned
target_claim: "ptm-protein-isoforms-enable-selective-drug"
hypothesis: "Replacing DeepTernary with PROTAC-STAN (Adv. Sci. 2025) inside the calibrated ΔpTernary pipeline yields top-K=20 ranking AUC on the held-out phospho-PROTAC track that is within 0.05 of the DeepTernary AUC, with both still showing >= 0.05 lift over their respective PTM-blind baselines. If only one scorer carries the lift, the headline result is scorer-specific and not a property of the calibrated ΔpTernary axis."
tags: [ablation, scorer-substitution, deepternary, protac-stan, deltapternary, ptm-isoforms, phospho-protac]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "PROTAC-STAN (Adv. Sci. 2025 released checkpoint) substituted for DeepTernary in the Stage 2b pipeline; same Boltz-2 PTM-conditioned POI structures, same held-out track"
  dataset: "Same held-out phospho-PROTAC track and negatives as [[calibrated-deltapternary-phospho-protac-ranking]]; per-POI noise-floor table re-computed on PROTAC-STAN (separate Phase-0 scope on the same training subset)"
  hardware: "1 × A100 80GB"
  framework: "PROTAC-STAN inference + reuse of Boltz-2 cached PTM-conditioned POI structures from Stage 2b"
metrics: ["top-K=20 AUC (PROTAC-STAN)", "AUC delta vs DeepTernary AUC", "AUC lift vs PROTAC-STAN PTM-blind baseline", "per-POI noise-floor stats for PROTAC-STAN"]
baseline: "DeepTernary calibrated AUC from [[calibrated-deltapternary-phospho-protac-ranking]] AND PROTAC-STAN PTM-blind ranking (WT-only) on the same set"
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

Verify that the headline AUC lift is a property of the calibrated ΔpTernary protocol rather than an artefact of one specific scorer's quirks. Robustness check across the two leading PTM-blind ternary predictors.

## Setup

- **Scorer-A**: DeepTernary (already validated by Stage 2b).
- **Scorer-B**: PROTAC-STAN (Adv. Sci. 2025 released checkpoint).
- **Data**: same Stage 2b held-out track (phospho-PROTAC positives + matched negatives); same Boltz-2 PTM-conditioned POI structures (cached, no re-prediction).
- **Calibration**: PROTAC-STAN requires its own per-POI noise-floor table — run a 100-perturbation-per-POI mini-Phase-0 on the CRBN+VHL training subset using PROTAC-STAN scores. Lighter than DeepTernary Phase-0 because the Phase-0 protocol is already validated; only the per-POI tables differ.
- **Statistical replication**: 5 seeds for the held-out evaluation; matched seed-by-seed to Stage 2b.

## Procedure

1. Generate PROTAC-STAN per-POI noise-floor table on the CRBN+VHL training subset (100 random size-matched perturbations per POI).
2. Score the cached Boltz-2 WT and PTM-occupied POI structures from Stage 2b with PROTAC-STAN; compute calibrated ΔpTernary per the new noise-floor table.
3. Rank held-out tuples by PROTAC-STAN calibrated ΔpTernary; compute top-K=20 AUC.
4. Also compute PTM-blind baseline AUC for PROTAC-STAN (WT-only ranking) for the per-scorer lift comparison.
5. Compare DeepTernary AUC vs PROTAC-STAN AUC; compute AUC delta and per-POI breakdown.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **|AUC delta| < 0.05 AND both scorers show >= 0.05 lift over their PTM-blind baselines** → headline result is scorer-robust; supports [[ptm-protein-isoforms-enable-selective-drug]] more strongly than Stage 2b alone.
- **|AUC delta| 0.05-0.10 OR only one scorer shows >= 0.05 lift** → result is scorer-sensitive but not scorer-specific; record which POI subsets account for the disagreement and recommend the better-performing scorer per-subset for downstream use.
- **|AUC delta| > 0.10 OR only DeepTernary shows the lift** → headline result is essentially a DeepTernary-specific finding; downgrade the support strength of [[ptm-protein-isoforms-enable-selective-drug]] from this experiment family. Do NOT claim scorer-agnostic ΔpTernary as a general method.
