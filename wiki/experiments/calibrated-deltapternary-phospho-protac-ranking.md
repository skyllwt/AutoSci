---
title: "Calibrated ΔpTernary ranking on the phospho-PROTAC held-out track"
status: planned
slug: "calibrated-deltapternary-phospho-protac-ranking"
target_claim: "ptm-protein-isoforms-enable-selective-drug"
hypothesis: "On a held-out phospho-PROTAC ranking task (true experimental phospho-PROTACs from the literature, augmented with synthetic positives from kinase-substrate phospho-degron pairs in DegronMD), feeding Boltz-2 PTM-conditioned POI structures into DeepTernary and computing the per-POI noise-floor-calibrated ΔpTernary lifts top-K (K=20) ranking AUC by >= 0.05 over the PTM-blind ranking baseline (DeepTernary on WT POI only), with >= 5 random seeds."
tags: [validation, deepternary, boltz-2, phospho-protac, ranking, deltapternary, ptm-isoforms]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "DeepTernary scorer + Boltz-2 (Jan 2026 weights) for PTM-conditioned POI structure prediction with native CCD-PTM tokens"
  dataset: "Held-out phospho-PROTAC track: true experimental phospho-PROTACs (phospho-BCL-XL family, ≈8-10 entries) + synthetic positives from kinase-substrate phospho-degron pairs in DegronMD (≈30-50 entries); negatives from PTM-blind PROTAC-DB CRBN+VHL entries with no known PTM-isoform selectivity"
  hardware: "2 × A100 80GB (Boltz-2 inference dominates wall-clock)"
  framework: "Boltz-2 + DeepTernary + custom ranking pipeline that consumes the Phase-0 per-POI noise-floor calibration table"
metrics: ["top-K (K=20) ranking AUC", "AUC lift over PTM-blind baseline", "per-seed mean and std", "noise-floor-bounded confidence band on the AUC lift"]
baseline: "DeepTernary on WT-only POI structure (PTM-blind ranking) on the same held-out set"
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

Validate the headline target claim [[ptm-protein-isoforms-enable-selective-drug]] in the prospective ranking setting: does PTM-conditioning of POI structure, combined with noise-floor-calibrated ΔpTernary, beat the PTM-blind baseline on a track where the positives are known PTM-isoform-selective experimental degraders?

## Setup

- **POI structure prediction**: Boltz-2 (Jan 2026 weights) with native CCD-PTM tokens at the experimentally annotated PTM sites; if the CCD-PTM token coverage is incomplete for a given PTM, fall back to the MD-relaxed route from [[ablation-boltz2-ptm-vs-md-relaxed-route]] (this fallback is gated by that ablation reporting comparability).
- **Scorer**: DeepTernary (the reproduced baseline checkpoint).
- **Calibration**: per-POI noise-floor table from [[phase0-noise-floor-calibration-deepternary-ptm-perturbations]]. Threshold: |ΔpTernary| > 1.5 × per-POI noise floor.
- **Held-out positive set**: experimental phospho-PROTACs (phospho-BCL-XL series, kinase-phospho-degron pairs from DegronMD where (POI, kinase, PROTAC) are co-annotated). Strict prospective hold: no entry in the positive set may have appeared in TernaryDB / PROTAC-DB training splits used by DeepTernary or Boltz-2.
- **Negative set**: PTM-blind PROTAC-DB CRBN+VHL entries with no known PTM-isoform selectivity, matched on POI molecular weight bracket and PROTAC linker length.
- **Statistical replication**: 5 random seeds for ranking-shuffle; report mean ± std AUC.

## Procedure

1. Assemble the held-out positive + negative sets per the setup; verify zero leakage with TernaryDB / PROTAC-DB training splits.
2. For each (POI, E3, PROTAC) tuple: predict {WT POI structure, PTM-occupied POI structure} via Boltz-2; score both with DeepTernary; compute raw and noise-floor-calibrated ΔpTernary.
3. Rank tuples by calibrated ΔpTernary; compute top-K=20 ranking AUC.
4. Repeat with PTM-blind ranking (DeepTernary on WT-only) for the same tuples — this is the baseline.
5. Repeat the full pipeline across 5 seeds; report mean ± std AUC and AUC lift; quote the noise-floor-bound confidence band.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **Success (AUC lift >= 0.05, exceeds noise-floor-bound confidence band)** → lift [[ptm-protein-isoforms-enable-selective-drug]] from `weakly_supported` (0.6) toward `supported` (≥ 0.75); proceed to Stage 3 ablations and Stage 4 robustness in parallel.
- **Marginal (AUC lift 0.02-0.05, or lift exists but does not clear noise-floor band)** → run the calibration ablation [[ablation-uncalibrated-vs-calibrated-deltapternary]] first; the calibration step may need re-tuning. Defer Stage 4 until the ablation reports.
- **Failure (no AUC lift)** → record a negative result against the source idea; do NOT immediately mark the idea as `failed`, because Phase-0 may have already shown the noise floor is wide. Instead: trigger [[ablation-deepternary-vs-protac-stan-scorer]] to check whether scorer choice was the gating factor; if both scorers fail, then mark idea as `failed` with `failure_reason` set accordingly.
