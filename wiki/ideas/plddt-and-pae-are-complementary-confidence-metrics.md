---
title: "pLDDT and PAE are complementary confidence metrics — pLDDT for per-residue local accuracy, PAE for pairwise relative-position accuracy"
slug: "plddt-and-pae-are-complementary-confidence-metrics"
status: validated
origin: "Migrated from claims/plddt-and-pae-are-complementary-confidence-metrics on 2026-05-10 (was status: supported, confidence: 0.9); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [confidence-metrics, alphafold, structural-biology]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

pLDDT and PAE are not redundant: pLDDT estimates per-residue local accuracy (in the lDDT-Cα sense), while PAE estimates the *pairwise* error in residue `i`'s position when the prediction is aligned at residue `j`. Multi-domain reasoning — including AlphaFold-Multimer interface scoring and AFDB Foldseek-cluster downstream interpretation — requires both: a region with high pLDDT but high outward PAE is locally well-modelled but globally orientationally uncertain, which pLDDT alone cannot reveal.

**Scope and conditions.** - Both metrics are *predicted*; calibration on out-of-distribution sequences (viral, designed, IDR-rich) is uncertain.
- For single-domain / short-sequence predictions, pLDDT alone may be adequate; PAE's added value is concentrated in multi-domain and complex reasoning.
- The 2022-07 numerical bug poisoned ~4% of pLDDT values until the 2022-11 fix; the v3-vs-v4 split must be respected when evaluating downstream pipelines that pre-date the fix.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- For users whose downstream task only needs binding-site / single-residue reasoning, PAE provides little marginal information beyond pLDDT.
- Aggregate PAE summaries (mean inter-domain PAE) and aggregate pLDDT correlate strongly on average, so for *coarse* confidence triage, either metric alone may suffice.

**Open questions.**

- What is the right principled fusion of pLDDT and PAE into a single downstream-task-aware confidence score?
- How calibrated is PAE on out-of-distribution sequences?
- Should pLDDT-low regions be treated as predicted IDRs by default?

## Pilot results

The AlphaFold DB 2024 paper documents both metrics as first-class outputs, codifies the operational pLDDT tier guidance (>90 / 70-90 / 50-70 / <50), and invests engineering effort specifically in coupling the PAE viewer to the 3D viewer for inter-domain interpretation. The investment makes sense only if the two metrics are non-redundant.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
