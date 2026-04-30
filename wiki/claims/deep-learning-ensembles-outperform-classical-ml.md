---
title: "Deep-learning ensembles with sequence-only input outperform feature-engineered classical ML for PTM site prediction across most PTM types"
slug: "deep-learning-ensembles-outperform-classical-ml"
status: weakly_supported
confidence: 0.6
tags: [deep-learning, ptm, bioinformatics, ensembles, benchmarking]
domain: "Bioinformatics"
source_papers: [musitedeep-deep-learning-based-webserver-protein]
evidence:
  - source: musitedeep-deep-learning-based-webserver-protein
    type: supports
    strength: moderate
    detail: "Timestamp-based benchmark (train < 2010, test >= 2010) on 13 PTM types: MusiteDeep (sequence-only, MultiCNN+CapsNet ensemble with bootstrap weight averaging) achieves higher AUC and area-under-PR than ModPred (logistic regression) and the strongest representative classical tool per PTM type (DeepPhos, GlycoEP, GPS-PAIL, MePred-RF, CSS-Palm4.0, UbiProber, GPS-SUMO, RF-Hydroxysite) on 12 of 13 PTM types under both metrics. Self-reported, single-paper evidence."
conditions: "Holds when training data is large enough to leverage deep ensembles (transfer learning compensates only partially for very small PTM datasets); benchmark uses UniProtKB/Swiss-Prot annotations, where negatives may be unobserved positives."
date_proposed: 2026-04-30
date_updated: 2026-04-30
---

## Statement

For protein post-translational modification site prediction, deep-learning ensembles that take only the raw amino-acid sequence as input — combining complementary architectures (e.g., CNN + capsule network), bootstrap subset training with weight averaging across iterations, and nested-cross-validation ensembling — outperform feature-engineered classical machine-learning predictors (logistic regression, SVM, random forest) on the majority of common PTM types under both AUC and area-under-PR.

## Evidence summary

The MusiteDeep webserver paper benchmarks its sequence-only ensemble against ModPred (logistic regression, covers all 13 PTM types) plus a representative classical tool per PTM type. MusiteDeep wins on AUC and PR-area for 12 of 13 PTM types; on hydroxyproline it still beats both baselines, but the gap is smaller. The evidence is:

- self-reported benchmarking by the proposing authors,
- on a single timestamp-based dataset (train < 2010, test >= 2010) drawn from UniProtKB/Swiss-Prot,
- with comparisons to baselines as published, not retrained under matched conditions.

This is suggestive but not conclusive — it warrants `weakly_supported` until at least one independent benchmark (a third-party blinded evaluation, or a cross-dataset replication) is folded in.

## Conditions and scope

- **Sequence-only inputs**: claim is about predictors that operate on raw sequence windows; structure-aware classical or deep models are not covered.
- **Per-PTM binary classification**: claim is restricted to the standard task formulation. It does not cover cross-talk modelling.
- **Sufficient data**: holds for PTM types with enough positive samples; transfer learning helps the smallest data regimes but does not eliminate the issue.
- **Threshold-free metrics**: the comparison uses AUC and area-under-PR; the claim does not assert superiority at any specific operating threshold.

## Counter-evidence

None recorded yet. Hydroxyproline (the lowest-margin case in MusiteDeep's own benchmark) and the unusually low PR-area for ubiquitination (0.279) signal that the claim is not uniform across PTM types.

## Linked ideas

None yet.

## Open questions

- Does the advantage hold under independent third-party benchmarks rather than self-reported comparisons?
- Does it persist when classical baselines are retrained on the same timestamp-based split with comparable hyperparameter tuning?
- Is the advantage maintained on PTM types whose positive sets are dominated by a single enzyme family (where motif specificity is high and feature engineering may already saturate)?
- How does the comparison change when AlphaFold-derived structural features are added to the classical baselines?
