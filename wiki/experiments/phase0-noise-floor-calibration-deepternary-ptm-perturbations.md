---
title: "Phase-0 noise-floor calibration of ΔpTernary under random size-matched POI surface perturbations (DeepTernary)"
slug: "phase0-noise-floor-calibration-deepternary-ptm-perturbations"
status: planned
target_claim: "noise-floor-calibrated-deltapternary-improves-ranking"
hypothesis: "Under N=200 random size-matched (≈80 Da, ≈3 Å radius) POI surface perturbations per tuple on the TernaryDB CRBN+VHL training subset, the resulting null distribution of ΔpTernary has a 95% interval narrow enough that real PTM-induced ΔpTernary values can clear the threshold |ΔpTernary| > 1.5 × noise-floor mean on at least 30% of true PTM-PROTAC positives. If the null distribution swallows the entire signal range, the load-bearing premise of [[ptm-aware-degrader-target-nomination]] fails fast."
tags: [calibration, noise-floor, deepternary, ternarydb, ptm-perturbation, phase-0]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "DeepTernary (the same checkpoint validated by [[deepternary-baseline-ternarydb-crbn-vhl-reproduction]])"
  dataset: "TernaryDB CRBN+VHL training subset (≈100 tuples) + a small probe set of 5-10 known phospho-PROTAC POI structures"
  hardware: "1 × A100 80GB"
  framework: "PyTorch + DeepTernary inference + a custom random-perturbation script (mass / radius constrained surface point picker)"
metrics: ["per-POI noise-floor mean and 95% interval", "fraction of true PTM-PROTAC positives clearing |ΔpTernary| > 1.5 × noise floor", "per-POI scorer-sensitivity slope (ΔpTernary vs perturbation distance from interface)"]
baseline: "raw |ΔpTernary| with no calibration (from the same perturbations)"
outcome: ""
key_result: ""
linked_idea: "ptm-aware-degrader-target-nomination"
date_planned: 2026-05-02
date_completed: ""
run_log: ""
started: ""
estimated_hours: 24
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---

## Objective

Characterise the per-POI null distribution of ΔpTernary under random size-matched surface modifications that mimic the chemical footprint of a phospho-group, and decide whether the noise floor leaves headroom for real PTM signal. This is the **load-bearing fail-fast gate** for the entire [[ptm-aware-degrader-target-nomination]] idea: if the null distribution is wider than the PTM signal, the ΔpTernary axis is unusable and Stage 2b onwards is killed.

## Setup

- **Model**: same DeepTernary checkpoint as the reproduced baseline.
- **POI universe**: TernaryDB CRBN+VHL training subset (≈100 (POI, E3, PROTAC) tuples).
- **Perturbation protocol**: per POI, sample 200 random surface positions; at each, attach a chemically inert size-matched mock group (≈80 Da, ≈3 Å radius — neutral, no charge, no H-bond donors/acceptors) using a constrained side-chain remodel + 100-step minimisation.
- **Probe set**: 5-10 known phospho-PROTAC POI structures (phospho-BCL-XL family, kinase-substrate phospho-degron pairs from DegronMD where structures are available) for the headline "fraction of positives clearing threshold" metric.
- **Hardware**: 1 × A100 80GB; total ≈100 POI × 200 perturbations × DeepTernary inference + minimisation.

## Procedure

1. For each tuple in the training subset, sample 200 random surface positions; build size-matched perturbed POI structures.
2. Score each perturbed structure with DeepTernary; record ΔpTernary = score(perturbed) - score(WT).
3. For each POI, fit the null distribution: report mean and 95% interval; flag POIs where the noise floor exceeds the typical PTM-PROTAC signal magnitude (≈ score-shift seen on the probe set).
4. Score the probe set of true PTM-PROTAC POIs with both perturbed (PTM site) and WT structures; compute the fraction whose ΔpTernary clears the per-POI threshold |ΔpTernary| > 1.5 × noise-floor mean.
5. Plot ΔpTernary vs perturbation distance from the known interface; check whether scorer sensitivity is concentrated at the interface (signal-favoring) or diffuse (noise-favoring).

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **Success (>= 30% of probe-set positives clear the per-POI threshold)** → proceed to Stage 2b, [[calibrated-deltapternary-phospho-protac-ranking]]. Record the per-POI noise floors as a calibration table for downstream stages to consume.
- **Marginal (10-30% clear)** → reduce the threshold multiplier from 1.5× to 1.2× and re-evaluate; document the precision tradeoff. If marginal even at 1.0× (i.e., raw differential), proceed only to Stage 3 ablation [[ablation-uncalibrated-vs-calibrated-deltapternary]] — skip Stage 2b until the route ablation [[ablation-boltz2-ptm-vs-md-relaxed-route]] reports.
- **Failure (< 10% clear)** → STOP. The DeepTernary score function does not resolve PTM-scale perturbations on CRBN+VHL targets. Update the source idea [[ptm-aware-degrader-target-nomination]] with `failure_reason` = "Phase-0 noise floor swallowed signal on DeepTernary CRBN+VHL"; consider whether a different scorer (PROTAC-STAN, future PTM-aware scorer) survives — this becomes a much smaller follow-up exp.
