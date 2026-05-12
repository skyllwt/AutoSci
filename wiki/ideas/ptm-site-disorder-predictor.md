---
title: "AlphaFold-derived PTM-site disorder predictor (eliminated)"
slug: "ptm-site-disorder-predictor"
status: failed
origin: "ideate: gap pLDDT-as-IDR-predictor + PTM site prediction in IDRs"
origin_gaps: []
tags: [ptm, alphafold, plddt, idr, eliminated]
domain: "Computational Biology / ML for Science"
priority: 1
pilot_result: ""
failure_reason: "[filter] saturated by SAPP (2025), PhosAF (2024), GraphPhos (2025), AstraPTM2 (2025), DeepPCT (2024), MTPrompt-PTM (2025) — 'AlphaFold structural features as input to PTM site predictor' is a published axis with at least five 2024-2025 entries. Adding pLDDT/IDR conditioning is incremental and unlikely to outperform any of these."
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
# bio-C3 (pilot merged 2026-05-12): scope of the banlist hit. The saturated subspace cited in
# failure_reason — SAPP, PhosAF, GraphPhos, AstraPTM2, DeepPCT, MTPrompt-PTM — is specifically
# human-mouse phospho-PTM site prediction trained on dbPTM / PhosphoSitePlus-class corpora
# (high-data regime). Plant phospho proteomes, microbial PTM, cross-species low-data transfer,
# and non-phospho PTMs (ubiquitin / methyl / acetyl) are NOT covered by these saturated tools
# — a future /ideate run targeting those scopes should NOT match this banlist entry.
scope:
  species: [human, mouse]
  disease_area: []
  data_regime: high_data
---

## Motivation

[[plddt]]-as-IDR-predictor is well-known but uncalibrated specifically for PTM sites in disordered regions, where most PTM sites live. The intent was a fine-tuned predictor combining pLDDT pattern + flanking sequence around PTM sites for use as a drop-in feature.

## Hypothesis

A PTM-site classifier conditioned on pLDDT + flanking sequence improves PTM-site precision in IDRs over the [[musitedeep-deep-learning-based-webserver-protein]] baseline.

## Approach sketch

Train a sequence-context model on pLDDT pattern + flanking sequence at PTM sites in low-pLDDT (< 50) regions. Release as a drop-in feature for existing PTM-site predictors.

## Expected outcome

Eliminated — see `failure_reason`.

## Risks

Saturated direction. Five published 2024-2025 entries already use AlphaFold structural features (pLDDT, PAE, residue-pair attention) as inputs to PTM-site predictors: SAPP, PhosAF, GraphPhos, AstraPTM2, DeepPCT, MTPrompt-PTM. Any incremental "pLDDT + flanking sequence" variant lands inside their ablation tables.

## Pilot results

(none — eliminated at Phase-3 filter, before any experiment)

## Lessons learned

The general "AF features → PTM site classifier" axis is closed. Future PTM-site work in this wiki should target *unaddressed* sub-problems: PTM-conditioned ensembles ([[ptm-conditioned-ensemble-prediction]]), PTM-aware degrader nomination ([[ptm-aware-degrader-target-nomination]]), or PTM-resolved interactomes ([[ptm-resolved-structurally-modeled-interactome]]).
