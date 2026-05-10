---
title: "Deep-learning ensembles with sequence-only input outperform feature-engineered classical ML for PTM site prediction across most PTM types"
slug: "deep-learning-ensembles-outperform-classical-ml"
status: tested
origin: "Migrated from claims/deep-learning-ensembles-outperform-classical-ml on 2026-05-10 (was status: weakly_supported, confidence: 0.6); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [deep-learning, ptm, bioinformatics, ensembles, benchmarking]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

For protein post-translational modification site prediction, deep-learning ensembles that take only the raw amino-acid sequence as input — combining complementary architectures (e.g., CNN + capsule network), bootstrap subset training with weight averaging across iterations, and nested-cross-validation ensembling — outperform feature-engineered classical machine-learning predictors (logistic regression, SVM, random forest) on the majority of common PTM types under both AUC and area-under-PR.

**Scope and conditions.** - **Sequence-only inputs**: claim is about predictors that operate on raw sequence windows; structure-aware classical or deep models are not covered.
- **Per-PTM binary classification**: claim is restricted to the standard task formulation. It does not cover cross-talk modelling.
- **Sufficient data**: holds for PTM types with enough positive samples; transfer learning helps the smallest data regimes but does not eliminate the issue.
- **Threshold-free metrics**: the comparison uses AUC and area-under-PR; the claim does not assert superiority at any specific operating threshold.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a tested empirical finding, not as a new prospective hypothesis.*

## Risks

None recorded yet. Hydroxyproline (the lowest-margin case in MusiteDeep's own benchmark) and the unusually low PR-area for ubiquitination (0.279) signal that the claim is not uniform across PTM types.

**Open questions.**

- Does the advantage hold under independent third-party benchmarks rather than self-reported comparisons?
- Does it persist when classical baselines are retrained on the same timestamp-based split with comparable hyperparameter tuning?
- Is the advantage maintained on PTM types whose positive sets are dominated by a single enzyme family (where motif specificity is high and feature engineering may already saturate)?
- How does the comparison change when AlphaFold-derived structural features are added to the classical baselines?

## Pilot results

The MusiteDeep webserver paper benchmarks its sequence-only ensemble against ModPred (logistic regression, covers all 13 PTM types) plus a representative classical tool per PTM type. MusiteDeep wins on AUC and PR-area for 12 of 13 PTM types; on hydroxyproline it still beats both baselines, but the gap is smaller. The evidence is:

- self-reported benchmarking by the proposing authors,
- on a single timestamp-based dataset (train < 2010, test >= 2010) drawn from UniProtKB/Swiss-Prot,
- with comparisons to baselines as published, not retrained under matched conditions.

This is suggestive but not conclusive — it warrants `weakly_supported` until at least one independent benchmark (a third-party blinded evaluation, or a cross-dataset replication) is folded in.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
