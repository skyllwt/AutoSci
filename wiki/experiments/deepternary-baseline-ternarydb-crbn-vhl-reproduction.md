---
title: "DeepTernary baseline reproduction on TernaryDB CRBN+VHL test split"
slug: "deepternary-baseline-ternarydb-crbn-vhl-reproduction"
status: planned
target_claim: "ptm-protein-isoforms-enable-selective-drug"
hypothesis: "DeepTernary (Nat. Commun. 2025) reproduces its published per-tuple pTernary scores on the TernaryDB CRBN+VHL test split with mean absolute deviation < 5% from the values reported in the source manuscript and supplementary tables."
tags: [baseline, deepternary, ternarydb, crbn, vhl, reproduction]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "DeepTernary (released checkpoint, Nat. Commun. 2025)"
  dataset: "TernaryDB CRBN+VHL test split (the same split used in the DeepTernary paper)"
  hardware: "1 × A100 80GB (or equivalent)"
  framework: "PyTorch + the public DeepTernary inference repo"
metrics: ["pTernary mean absolute deviation vs paper", "per-tuple Pearson r", "wall-clock per tuple"]
baseline: "DeepTernary published values on the same split"
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

Confirm we can reproduce the baseline ternary-complex predictor we will perturb downstream. Without a reproduced baseline, every ΔpTernary number computed in later stages is suspect — we cannot tell whether a deviation is the PTM signal or a code/data plumbing bug.

## Setup

- **Model**: DeepTernary released checkpoint, Nat. Commun. 2025.
- **Data**: TernaryDB CRBN+VHL subset, exact test split per the source paper. Pulled from the published S3 mirror.
- **Hardware**: 1 × A100 80GB; expected wall-clock < 4 h end-to-end.
- **Software**: PyTorch + the public DeepTernary repo at the tagged release used in the paper.
- **Determinism**: single deterministic run (seed=0); no statistical replication needed for a baseline reproduction.

## Procedure

1. Clone the public DeepTernary repo at the paper-tagged commit; pin dependencies.
2. Download TernaryDB CRBN+VHL test split; verify checksums against the paper's published manifest.
3. Run inference on every (POI, E3, PROTAC) tuple in the test split.
4. Compute per-tuple pTernary; compare against the values reported in Supplementary Table S2 (and any per-tuple table the paper exposes).
5. Compute mean absolute deviation, per-tuple Pearson r, and per-tuple wall-clock.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **Success (mean abs deviation < 5%)** → proceed to Stage 2a, [[phase0-noise-floor-calibration-deepternary-ptm-perturbations]].
- **Failure (deviation >= 5%)** → STOP the pipeline. Investigate (in order): (a) checkpoint mismatch, (b) data preprocessing diff, (c) inference-time settings (batch / temperature / sampling). Do not start Phase-0 until baseline reproduces; the entire ΔpTernary calculation is meaningless against an un-reproduced baseline.
