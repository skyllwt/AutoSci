---
title: "Heterogeneous biological evidence integrated by naive Bayes predicts human E3-substrate interactions at proteome scale"
slug: e3-ubiquitin-ligase-substrate-network-predicted
status: supported
confidence: 0.75
tags: [bioinformatics, ubiquitination, e3-ligase, naive-bayes, prediction]
domain: "computational biology"
source_papers: [integrated-bioinformatics-platform-investigating-human-e3]
evidence:
  - source: integrated-bioinformatics-platform-investigating-human-e3
    type: supports
    strength: strong
    detail: "Naive Bayesian integration of five evidence channels (ortholog ESI, domain enrichment, GO enrichment, PPI network loops, E3 recognition motif) achieves AUROC 0.827 (95% CI 0.811-0.842) on five-fold cross-validation against a 913-pair golden standard, AUROC 0.73 on a 402-pair independent post-2010 test set, and recovers known interactions (ITCH-TAB1, CHIP-EGFR, NEDD4-HER3) at top-rank positions. A predicted Smurf1-Smad3 interaction (LR=29.87) is wet-lab validated by co-IP, dose-dependent destabilization, and ligase-activity-dependent ubiquitination in MDA-MB-231 cells."
conditions: "Holds when at least one of E3 or substrate appears in the training golden-standard set (C1/C2 splits, AUROC 0.82-0.86). Generalization to fully novel pairs (C3 split, neither member seen in training) is much weaker (AUROC 0.629). Evidence channels reflect Pfam/GO/HPRD/IntAct/iRefIndex snapshots from 2009-2014; calibration may degrade as databases evolve."
date_proposed: 2026-04-30
date_updated: 2026-04-30
---

## Statement

Combining heterogeneous biological evidence — ortholog E3-substrate interactions, enriched domain pairs, enriched GO term pairs, PPI network loops, and inferred E3 recognition consensus motifs — through a naive Bayesian classifier yields a calibrated confidence score for human E3 ubiquitin ligase-substrate interactions that substantially outperforms any single-evidence baseline and recovers experimentally validated interactions at top ranks across multiple disease-relevant case studies.

## Evidence summary

The supporting paper [[integrated-bioinformatics-platform-investigating-human-e3]] reports a five-fold cross-validation AUROC of 0.827 (95% CI 0.811-0.842) on a 913-pair literature-curated golden standard, well above the best single-evidence channel (GO term pair, AUROC 0.696) and other channels (ortholog 0.644, domain 0.637, network loops 0.570-0.599, recognition motif 0.661). On an independent 402-pair test set built from post-2010 literature the model still achieves AUROC 0.73. Three published anecdotal validations (ITCH-TAB1 in skin inflammation, CHIP-EGFR in pancreatic cancer, NEDD4-HER3 across colon and gastric cancers) appeared at top ranks and were each later confirmed in follow-up wet-lab papers. The authors additionally validate a previously-unconfirmed top prediction — Smurf1-Smad3 (LR = 29.87) — in MDA-MB-231 cells via dose-dependent Smad3 destabilization, in vivo poly-ubiquitination assays, and reciprocal co-immunoprecipitation, with the C699A ligase-dead Smurf1 mutant abolishing the effect.

## Conditions and scope

- Performance is measured on human ESIs only; transfer to other species (or other ligation cascades like SUMOylation, NEDDylation) is not established by the cited evidence.
- AUROC drops to 0.629 in the strict pair-input C3 split (neither E3 nor substrate seen during training), so the claim is robust mainly when at least one partner has prior annotation.
- Wet-lab validation is overexpression-condition in MDA-MB-231 — endogenous-physiological relevance was acknowledged as harder to detect in Smurf1 knockouts because of compensation by Smurf2.
- Calibration depends on the evidence database snapshots used; as Pfam/GO/HPRD-class resources update, scores require retraining.

## Counter-evidence

- The C3 split AUROC (0.629) is close to the 0.5 random baseline and shows that the model relies heavily on one of the test partners being present in training.
- Yamashita et al. observed no Smad-protein-abundance change in Smurf1-/- mice, mildly weakening the in vivo strength of the Smurf1-Smad3 prediction; the authors attribute this to compensation by Smurf2.
- Conditional independence between evidence channels (assumed by naive Bayes) is at best an approximation; correlated evidence can inflate the composite LR.

## Linked ideas

(none yet)

## Open questions

- Does swapping hand-engineered Pfam/GO/motif features for AlphaFold-derived structural features lift the C3 AUROC?
- Does the framework retain performance when retrained on post-2014 ubiquitination databases (mUbiSiDa, PhosphoSitePlus)?
- Can a structure-aware reformulation give absolute (rather than relative) interaction probabilities?
