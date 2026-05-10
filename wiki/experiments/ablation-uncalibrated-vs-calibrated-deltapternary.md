---
title: "Ablation: uncalibrated raw ΔpTernary vs noise-floor-calibrated ΔpTernary on the same phospho-PROTAC track"
slug: "ablation-uncalibrated-vs-calibrated-deltapternary"
status: planned
target_claim: "noise-floor-calibrated-deltapternary-improves-ranking"
hypothesis: "On the same held-out phospho-PROTAC ranking set used in [[calibrated-deltapternary-phospho-protac-ranking]], replacing the per-POI noise-floor calibration with raw |ΔpTernary| (no calibration) reduces top-K=20 ranking AUC by >= 0.03 with >= 5 seeds. If the AUC drop is < 0.01 the calibration step contributes nothing and should be dropped from the pipeline."
tags: [ablation, calibration, deepternary, deltapternary, ptm-isoforms, phospho-protac]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "Same as [[calibrated-deltapternary-phospho-protac-ranking]] — DeepTernary + Boltz-2 PTM-conditioned POI"
  dataset: "Same held-out phospho-PROTAC track and the same negatives as [[calibrated-deltapternary-phospho-protac-ranking]]"
  hardware: "Re-uses the cached scores from Stage 2b; no new GPU inference, only re-ranking"
  framework: "Custom ranking pipeline with the calibration step toggled off"
metrics: ["top-K=20 AUC (uncalibrated)", "AUC delta vs calibrated", "per-seed mean and std"]
baseline: "Calibrated ΔpTernary AUC from [[calibrated-deltapternary-phospho-protac-ranking]]"
outcome: ""
key_result: ""
linked_idea: "ptm-aware-degrader-target-nomination"
date_planned: 2026-05-02
date_completed: ""
run_log: ""
started: ""
estimated_hours: 4
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective

Isolate the contribution of the per-POI noise-floor calibration step to the headline AUC lift. Determines whether calibration is a load-bearing component of the ΔpTernary pipeline or merely cosmetic.

## Setup

- **Inputs**: cached pTernary scores from Stage 2b on the held-out phospho-PROTAC track (no re-inference needed).
- **Pipeline modification**: skip the per-POI noise-floor table; rank tuples directly by raw |ΔpTernary|.
- **Statistical replication**: 5 seeds (matched seed-by-seed to Stage 2b for paired comparison).

## Procedure

1. Load cached pTernary scores from Stage 2b (per tuple, per seed).
2. For each seed: compute raw |ΔpTernary|; rank tuples; compute top-K=20 AUC.
3. Compare paired (seed-by-seed) against the calibrated AUC from Stage 2b; report mean AUC drop and std.
4. Report per-POI breakdown: which POIs benefit most from calibration, which are unaffected.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **AUC drop >= 0.03** → confirms [[noise-floor-calibrated-deltapternary-improves-ranking]]; lift that claim from `proposed` (0.3) toward `supported` (>= 0.75).
- **AUC drop 0.01-0.03** → calibration is helpful but not dominant; document the per-POI breakdown so downstream users can decide whether the extra Phase-0 cost is justified for their target set.
- **AUC drop < 0.01** → calibration adds no value on this track; mark [[noise-floor-calibrated-deltapternary-improves-ranking]] as `challenged`. Re-evaluate the entire Phase-0 noise-floor protocol — perhaps the threshold multiplier (1.5×) is wrong, or per-POI calibration should be replaced with global calibration.
