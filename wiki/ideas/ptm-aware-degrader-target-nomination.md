---
title: "PTM-aware degrader target nomination with ΔpTernary noise-floor calibration"
slug: "ptm-aware-degrader-target-nomination"
status: in_progress
origin: "ideate: weakly_supported claim/ptm-protein-isoforms-enable-selective-drug + Phase-1 finding that all current PROTAC ternary predictors are PTM-blind on the POI side"
origin_gaps: []
tags: [drug-design, ptm-isoforms, protac, ternary-complex, e3-ligase]
domain: "ml-for-science"
priority: 5
pilot_result: ""
failure_reason: ""
linked_experiments: [deepternary-baseline-ternarydb-crbn-vhl-reproduction, phase0-noise-floor-calibration-deepternary-ptm-perturbations, calibrated-deltapternary-phospho-protac-ranking, ablation-uncalibrated-vs-calibrated-deltapternary, ablation-boltz2-ptm-vs-md-relaxed-route, ablation-deepternary-vs-protac-stan-scorer, robustness-cross-ptm-type-ubiq-methyl, robustness-mutant-isoform-track-y220c-r175h]
date_proposed: 2026-04-30
date_resolved: ""
# bio-A7 (pilot 2026-05-11): GRADE = low — load-bearing premise (phospho-perturbation > noise floor)
# is empirically unverified. Anchor claim ptm-protein-isoforms-enable-selective-drug confidence
# is 0.6 (weakly_supported). Mechanistic basis exists (PTM-blind ternaries can't distinguish
# isoforms structurally), but thin positive set (< 10 truly PTM-selective experimental degraders)
# bounds the empirical evidence to "low" per GRADE conventions.
grade: low
---

## Motivation

[[posttranslational-modification-inspired-drug-design]] argues PTM-isoforms are druggable beyond wild-type, but [[ptm-protein-isoforms-enable-selective-drug]] is only `weakly_supported` (conf 0.6). Phase-1 landscape scan confirms all current ternary-complex predictors — DeepTernary (Nat. Commun. 2025), PROTAC-STAN (Adv. Sci. 2025), ET-PROTACs (Brief. Bioinform. 2024) — are PTM-blind on the POI side: they consume canonical-sequence POI structures and score ligand placement / E3 geometry. None ingests phosphorylation, ubiquitylation, acetylation, or methylation state of the POI when ranking degrader candidates. PTM-isoform-selective experimental degraders do exist (phospho-BCL-XL family; multiple kinase-substrate phospho-degron PROTACs; mutant-but-PTM-adjacent p53-Y220C bifunctional recruiters) but no compute pipeline systematically nominates them. [[ubiquitin-ligase-e3]] flags that current PROTAC E3 use is anchored on CRBN/VHL/MDM2/IAP — extending the recruitable E3 pool requires PTM-aware POI-side ranking.

## Hypothesis

Conditioning existing ternary-complex predictors on the POI's PTM state and computing a noise-floor-calibrated **ΔpTernary** score (PTM-isoform vs wild-type) ranks PTM-isoform-selective degrader candidates better than PTM-blind ranking, *provided* a null-perturbation baseline (random size-matched surface mutations) bounds the noise floor first.

## Approach sketch

Phase-0 (calibration): on a CRBN+VHL training subset of TernaryDB, perturb each POI surface with random size-matched modifications (≈80 Da, ≈3 Å radius, mimicking a phospho-group). Recompute DeepTernary / PROTAC-STAN scores. Fit a null distribution of ΔpTernary; report mean + 95% interval as the **noise floor**. Modifications cleared as informative only when |ΔpTernary| > 1.5 × noise floor.

Phase-1 (cascaded predictions): for each (POI, E3, PROTAC) tuple in PROTAC-DB, predict {wild-type, PTM-occupied} POI structures using two routes — (a) Boltz-2 with native CCD-PTM tokens at known sites, and (b) MD-relaxed phospho-structure as a fallback that **decouples this idea from [[ptm-conditioned-ensemble-prediction]]**. Feed both POI variants into ternary predictors. Compute ΔpTernary against the calibrated noise floor.

Phase-2 (split validation): two **mechanistically distinct** held-out tracks — (i) phospho-PROTACs (true PTM, e.g. phospho-BCL-XL, kinase-phospho-degron pairs from DegronMD); (ii) mutant-isoform PROTACs (Y220C, R175H — mutation, not PTM). Report retrospective vs prospective separately. Initial scope restricted to CRBN + VHL where ternary scorers were trained; exotic E3s deferred to v2.

## Expected outcome

- **Primary metric**: top-K PTM-isoform-selective ranking AUC > PTM-blind baseline by ≥ 0.05 on the phospho-PROTAC track, with noise-floor bound.
- **Claim status change**: lift [[ptm-protein-isoforms-enable-selective-drug]] from `weakly_supported` (0.6) to `supported` (≥ 0.75) if AUC lift survives noise-floor calibration on phospho-PROTAC track.
- Phase-4 deep validation:
  - Novelty score: 4/5 — ΔpTernary-as-PTM-selectivity-gap fed through DeepTernary/PROTAC-STAN/ET-PROTACs is unoccupied; experimentally grounded by a small set of true PTM-selective degraders.
  - Review score: 6/10 — hypothesis is testable but the pipeline rests on out-of-distribution score functions and a thin held-out positive set.

## Risks

Feasibility: medium-high. Top method weaknesses surfaced by /review:

1. **Out-of-distribution score function.** TernaryDB / PDB ternaries are essentially PTM-blind; asking DeepTernary or PROTAC-STAN to discriminate WT vs PTM-isoform via a ≈80 Da, ≈3 Å phospho perturbation is asking for signal *inside* their noise floor. Phase-0 noise-floor calibration is the load-bearing mitigation; if Phase-0 shows the noise floor swallows the signal, the idea fails fast and cheaply.
2. **Cascaded error.** Three error-propagating stages (POI structure → ternary score → ranking). AF3/Boltz-2 already underperform on small PROTAC interfaces (sub-Ångström features near the resolution limit). Mitigated by an MD-relaxed phospho-structure fallback that does not depend on a working PTM-Cfold ensemble.
3. **Thin positive set.** Truly-PTM-selective experimental degraders number < 10 across the literature. k-fold validation is statistically weak. Mitigation: synthetic positives from kinase-substrate phospho-degron pairs (DegronMD); strict retrospective vs prospective separation.

Additional concerns: PROTAC-DB is ≈80% CRBN/VHL-biased, so claims about "extended-canon E3 set" do not generalize without v2 work; mutant POIs (Y220C) and PTM POIs are mechanistically different and must not be conflated in the headline number.

## Pilot results

(empty — filled by /exp-eval)

## Lessons learned

(empty — filled by /exp-eval)
