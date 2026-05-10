---
title: "Ablation: Boltz-2 native CCD-PTM-token route vs MD-relaxed phospho-structure route for ΔpTernary"
slug: "ablation-boltz2-ptm-vs-md-relaxed-route"
status: planned
target_claim: "md-relaxed-phospho-route-comparable-to-native-ptm-tokens"
hypothesis: "On a matched subset of held-out phospho-PROTAC tuples (where both Boltz-2 native CCD-PTM tokens and MD-relaxed phospho-structures can be built), feeding the two POI variants into DeepTernary yields ΔpTernary scores whose Pearson correlation across the matched set is r >= 0.7 with mean absolute disagreement < 0.10 in normalised score units. If the two routes diverge (r < 0.5 or |disagreement| > 0.20), the headline ΔpTernary pipeline is gated on Boltz-2 PTM-token quality and partially re-couples to [[ptm-conditioned-ensemble-prediction]]."
tags: [ablation, boltz-2, molecular-dynamics, ptm-conditioning, deepternary, route-comparison]
domain: "Computational Drug Design / Chemical Biology"
setup:
  model: "Boltz-2 (Jan 2026, native CCD-PTM tokens) vs MD-relaxed phospho-structure (AMBER ff14SB + phosaa14SB, 50 ns explicit-solvent) — both fed into the same DeepTernary scorer"
  dataset: "≈25 matched phospho-PROTAC tuples from the held-out track in [[calibrated-deltapternary-phospho-protac-ranking]] where (a) the PTM site has a CCD-PTM token in Boltz-2 AND (b) the wild-type POI has a PDB or AlphaFold-DB v4 structure with pLDDT > 70 in the modification region (to seed MD)"
  hardware: "2 × A100 80GB (Boltz-2 inference) + 1 × A100 80GB MD node, MD wall-clock dominates"
  framework: "Boltz-2 + GROMACS or OpenMM for MD relaxation + DeepTernary + the same calibration table from Phase-0"
metrics: ["per-tuple ΔpTernary Pearson r between routes", "mean absolute disagreement (normalised score units)", "per-tuple per-route confidence intervals", "MD wall-clock per tuple vs Boltz-2 wall-clock per tuple"]
baseline: "Boltz-2 native CCD-PTM-token route (the headline route used in Stage 2b)"
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

Test whether the headline pipeline can decouple from native PTM-conditioned structure prediction. If MD-relaxed phospho-structures yield ΔpTernary signal comparable to Boltz-2 native PTM tokens, the idea has an independent fallback and is not gated on the parallel idea [[ptm-conditioned-ensemble-prediction]].

## Setup

- **Matched tuple selection**: ≈25 tuples from the Stage 2b held-out track for which both routes are buildable.
- **Boltz-2 route**: Jan 2026 weights, native CCD-PTM token at the experimentally annotated site, default sampling settings (no Boltz-sample modifications).
- **MD route**: start from PDB or AlphaFold-DB v4 WT structure (pLDDT > 70 at the modification region); chemically attach the PTM at t=0; minimise; equilibrate (NPT, 1 ns); production MD (NPT, 50 ns) with AMBER ff14SB + phosaa14SB; take the last-frame structure as the PTM-occupied input to DeepTernary.
- **Scorer**: DeepTernary with the per-POI noise-floor calibration from Phase-0.
- **Statistical replication**: 5 seeds for the MD route (different MD initial velocities); Boltz-2 route uses 5 sampling seeds. Paired seed-by-seed.

## Procedure

1. For each matched tuple, build the WT POI structure (PDB or AlphaFold-DB).
2. Generate PTM-occupied structure via Boltz-2 (5 seeds) and via MD (5 seeds).
3. Score each PTM-occupied structure + WT structure with DeepTernary; compute calibrated ΔpTernary per route per seed.
4. For each tuple, compute the Pearson correlation of ΔpTernary across routes (paired by seed); report mean Pearson r across the 25 tuples and mean absolute disagreement.
5. Plot the per-tuple ΔpTernary Boltz-2 vs MD scatter; flag outlier tuples for case-by-case inspection.

## Results

(to be filled after /exp-run)

## Analysis

(to be filled after /exp-run)

## Claim updates

(to be filled after /exp-eval)

## Follow-up

- **r >= 0.7 and |disagreement| < 0.10** → routes are interchangeable; lift [[md-relaxed-phospho-route-comparable-to-native-ptm-tokens]] from `proposed` (0.3) toward `supported` (>= 0.75); update [[calibrated-deltapternary-phospho-protac-ranking]] follow-up to officially permit the MD fallback for tuples where Boltz-2 PTM tokens are missing.
- **0.5 <= r < 0.7 or 0.10 <= |disagreement| < 0.20** → routes are partially comparable; record per-tuple disagreement profiles so that future Stage 2b runs can pick the route per-tuple based on the structural class (small-PTM phosphorylation OK with MD; large-rearrangement phospho-binding-site cases use Boltz-2).
- **r < 0.5 or |disagreement| > 0.20** → routes diverge; mark [[md-relaxed-phospho-route-comparable-to-native-ptm-tokens]] as `challenged` and record that the headline pipeline is gated on Boltz-2 PTM-token quality. This is bad news for risk-distribution: re-evaluate dependency on [[ptm-conditioned-ensemble-prediction]] before any further investment.
