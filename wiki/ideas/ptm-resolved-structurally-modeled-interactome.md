---
title: "PTM-resolved structurally-modeled human interactome via ΔpDockQ-per-PTM"
slug: "ptm-resolved-structurally-modeled-interactome"
status: proposed
origin: "ideate: gap G5 (PTM-resolved structurally-modeled interactome) + weakly_supported claim/ptm-protein-isoforms-enable-selective-drug"
origin_gaps: []
tags: [alphafold-multimer, protein-protein-interaction, ptm, interactome, drug-target]
domain: "ml-for-science"
priority: 5
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: ""
---

## Motivation

[[towards-structurally-resolved-human-protein-interaction]] used [[folddock-pipeline]] to AF2-Multimer-fold ≈65k high-confidence binary edges from HuRI / hu.MAP, scoring with [[pdockq-score]]. The recent kinase-TF iLIS atlas (bioRxiv 2025-10) extends this to allosteric hotspot mapping. Predictomes (Mol Cell 2025) is a classifier-curated AF-Multimer interactome at ≈16k high-confidence PPIs. **None of these stratify interfaces by PTM dependence.** Yet the literature documents many PTM-driven binary interactions (14-3-3 sigma–Cdc25C phospho, HIF1α–pVHL hydroxyl-proline, PCNA-K164-ubi, FOXO–14-3-3 phospho, …). A PTM-conditional interactome — where the operator is `ΔpDockQ(WT-WT, PTM-isoform-WT)` — would (a) systematize these one-off observations, (b) nominate druggable PPI hotspots that PTM-blind methods miss, and (c) provide the structural substrate for [[posttranslational-modification-inspired-drug-design]].

## Hypothesis

For binary edges in HuRI ∪ hu.MAP whose participants carry annotated PTM sites near the predicted interface, AF2-Multimer (FoldDock pipeline) predicts a `ΔpDockQ ≥ 0.3` shift between {WT-WT, PTM-isoform-WT} dimers in the literature-validated PTM-driven cases (14-3-3/Cdc25C, HIF1α/pVHL, PCNA/Pol-η-K164, FOXO/14-3-3) — and the proteome-scale top of the ΔpDockQ ranking enriches for known disease-associated PTM-dependent PPIs.

## Approach sketch

Restrict to binary edges where at least one partner has a UniProtKB / dbPTM-annotated PTM site within 12 Å of the predicted interface (after a single AF2-Multimer pass on WT-WT). For each surviving edge compute three folds: {WT-WT, PTM-isoform-A-WT, WT-PTM-isoform-B}. The **ΔpDockQ-per-PTM operator** is the headline contribution — defined per-edge with a noise floor estimated from random size-matched non-PTM substitutions on the same surface (mirroring the ΔpTernary discipline in [[ptm-aware-degrader-target-nomination]]). Pre-register the validation holdout: 14-3-3 sigma–Cdc25C (phospho), HIF1α–pVHL (hydroxyl-proline), PCNA–Pol-η-K164 (ubi), FOXO3a–14-3-3 (phospho); these are computed but **not used in any tuning step**. Project surviving high-ΔpDockQ edges onto the disease-associated PPI subset (Mendelian + cancer driver) for druggable hotspot nomination. Acknowledge the AF3-phospho-collapse risk (Bouvier 2025): for PTM-driven *conformational* changes, AF2/AF3 may underestimate ΔpDockQ; report the observed ΔpDockQ distribution against the noise floor and flag suspected false negatives explicitly.

## Expected outcome

- **Primary metric**: ΔpDockQ ≥ 0.3 + above-noise on the pre-registered holdout (4 cases) on at least 3 of 4; top-1% of proteome-scale ΔpDockQ enriches for disease-associated PTM-dependent PPIs (Fisher exact p < 10⁻³ vs random PPIs).
- **Claim status change**: lift [[ptm-protein-isoforms-enable-selective-drug]] confidence on the PPI-hotspot half (interface-targeting drugs) if proteome-scale enrichment holds.
- **Artifact**: a PTM-conditional interactome browser stratified by ΔpDockQ-per-PTM, complementing [[alphafold-db]] and Predictomes.
- Phase-4 deep validation:
  - Novelty score: 4/5 — exact ΔpDockQ-per-PTM operator across binary-interactome scaffolds appears unoccupied; closest competitors (Predictomes, kinase-TF iLIS atlas) are PTM-blind.
  - Review score: not run (rank-3 idea; only top-2 reviewed in this round).

## Risks

Feasibility: high. Top risks (review skipped per Phase-4 budget):

1. **AF2/AF3 may not respond to PTM-driven conformational changes at the interface.** Bouvier 2025 finds AF3-phospho only modestly improves on AF2; if the underlying predictor cannot resolve the PTM effect at the interface, ΔpDockQ collapses to zero across most edges and the operator is uninformative. Mitigation: noise floor calibration from non-PTM substitutions; explicit flag of suspected false negatives.
2. **Compute scope.** ≈65k edges × 3 folds × ≈10-min/fold ≈ 30k GPU-h on FoldDock. Mitigation: PTM-near-interface pre-filter cuts the candidate set to the subset where ΔpDockQ-per-PTM is mechanistically plausible (likely < 10k edges).
3. **PTM site annotation noise.** dbPTM mixes high- and low-confidence sites; restrict to UniProtKB experimentally validated annotations; report sensitivity analysis at multiple confidence thresholds.

## Pilot results

(empty — filled by /exp-eval)

## Lessons learned

(empty — filled by /exp-eval)
