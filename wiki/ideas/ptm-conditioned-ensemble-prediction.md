---
title: "PTM-conditioned pair-representation scaling for calibrated conformational ensembles"
slug: "ptm-conditioned-ensemble-prediction"
status: proposed
origin: "ideate: weakly_supported claim/diffusion-based-generation-eliminates-need-equivariant + documented gap that AF3-phospho collapses to a single dominant state (Bouvier 2025; Ramasamy Protein Sci. 2026)"
origin_gaps: []
tags: [alphafold, conformational-ensemble, ptm, structure-prediction, pair-representation]
domain: "ml-for-science"
priority: 4
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: ""
---

## Motivation

[[accurate-structure-prediction-biomolecular-interactions-alphafold]] (AF3) and [[diffusion-based-structure-prediction]] both collapse to a single dominant structure even when supplied with PTM-modified residues — Bouvier et al. (bioRxiv 2025-04) and Ramasamy (Protein Sci. 2026) document that AF3-phospho only modestly improves on AF2/AF3-non-phospho. The sampling axis itself is now crowded (AFsample2/3, ConforFold, AFEX, Boltz-sample / pair-representation scaling — bioRxiv Jan 2026). What no method has done is **couple PTM conditioning to ensemble sampling** and **calibrate against PTM-driven conformational switch benchmarks**: kinase activation loops, 14-3-3-binding tail-tagged transcription factors, ubiquitin chain topologies. This sits at the intersection of [[evoformer]], [[plddt]], [[predicted-aligned-error]] (calibration in unfamiliar regions) and [[diffusion-based-generation-eliminates-need-equivariant]] (currently `weakly_supported`, conf 0.55).

## Hypothesis

A PTM-conditioned **pair-representation scaling adapter** on top of a frozen Boltz-2 backbone, trained on a small PTM-switch dataset with quantitative ensemble ground truth (NMR order parameters, EPR distance distributions, MD-derived populations), recovers calibrated populations of PTM-induced alternative conformations on a held-out switch benchmark — outperforming both vanilla Boltz-2 with native CCD-PTM tokens and Boltz-sample (pair-rep scaling, PTM-blind) head-to-head.

## Approach sketch

The architectural delta is the load-bearing contribution: a **PTM adapter** that (a) reads PTM annotations at modified residues, (b) emits a learned bias on the pair-representation block of a frozen Boltz-2 backbone, and (c) is trained against population labels (not single-structure RMSD). Training scope is deliberately narrow: 2-3 PTM classes with quantitative ensemble ground truth — kinase activation loops (active vs inactive populations from MD + cryo-EM), 14-3-3-binding tail-tagged TFs (binding-competent fraction from NMR / FP), and one IDR-tail PTM case with NMR cross-validation. Vanilla Boltz-2 with native CCD-PTM tokens is the lower bound; Boltz-sample (PTM-blind pair-rep scaling) is the upper bound the adapter must beat. ConforFold and AFsample3 also enter the comparison table. Scope explicitly excludes proteome-scale ensemble decoding — that is deferred until the adapter beats the named baselines on the narrow benchmark.

## Expected outcome

- **Primary metric**: switch-population calibration error (KL divergence from MD/NMR-derived populations) lower than vanilla Boltz-2-PTM and Boltz-sample on held-out kinase + 14-3-3 + IDR-tail cases.
- **Claim status change**: lift [[diffusion-based-generation-eliminates-need-equivariant]] toward `supported` if PTM-conditioned ensemble calibration succeeds *without* re-introducing equivariant machinery; or contradict it if the win requires equivariance.
- Phase-4 deep validation:
  - Novelty score: 3/5 — PTM tokens themselves are not novel (Boltz-2 already accepts them via CCD); novelty rests on the adapter + calibration framing, which fills a gap documented in Bouvier 2025 and Ramasamy 2026 but is incremental relative to the crowded sampling literature.
  - Review score: 5/10 — testable but at risk of being scooped if a competitor lands PTM-conditioning + sampling first.

## Risks

Feasibility: medium. Top method weaknesses surfaced by /review:

1. **PTM tokens alone are not architectural novelty.** Boltz-1/2 already accept PTM-modified residues via CCD codes; AF3-phospho exists. The contribution must be the PTM-conditioned pair-representation adapter, with a clean ablation table separating (a) vanilla Boltz-2-PTM, (b) Boltz-2-PTM + Boltz-sample, (c) Boltz-2-PTM + adapter (this work). Without that ablation, the paper reduces to "we ran existing tools."
2. **Calibration ground truth is sparse and biased.** Quantitative ensemble references exist for ≈10 kinase activation loops and a handful of 14-3-3 complexes; ubiquitin chain topology preferences and IDR-tail PTM switches have anecdotal references. Phospho-bias risk is high. Mitigation: pre-register the held-out set; report per-PTM-class breakdown; do not summarize across PTM classes in the headline number.
3. **MSA subsampling is orthogonal to PTM-driven conformational change.** PTM switches are local-chemistry effects; MSA depth perturbation samples evolutionarily-encoded alternative states. Boltz-sample (Jan 2026) already showed pair-rep scaling beats MSA subsampling for general multi-state recovery — confirming that MSA subsampling is the wrong primitive, hence the move to pair-rep scaling here.

Additional concerns: AF3 weights are non-commercial, so the adapter must target Boltz-2 (open weights) and any AF3 results are demonstrative rather than load-bearing.

## Pilot results

(empty — filled by /exp-eval)

## Lessons learned

(empty — filled by /exp-eval)
