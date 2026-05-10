---
title: "Noise-floor-calibrated ΔpTernary improves PTM-isoform degrader ranking precision over uncalibrated raw ΔpTernary"
slug: "noise-floor-calibrated-deltapternary-improves-ranking"
status: proposed
origin: "Migrated from claims/noise-floor-calibrated-deltapternary-improves-ranking on 2026-05-10 (was status: proposed, confidence: 0.3); evidence captured as edges and below."
origin_gaps: []
tags: [protac, ternary-complex, ptm-isoforms, calibration, deepternary, protac-stan]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-05-02
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; supporting evidence and tested_by experiment links are captured in graph edges and Pilot results.*

## Hypothesis

Calibrating the per-POI ΔpTernary score against a noise floor estimated from random size-matched POI surface perturbations (≈80 Da, ≈3 Å radius — chosen to mimic the chemical footprint of a phospho-group), and only counting |ΔpTernary| > 1.5 × noise floor as informative, materially improves the precision of PTM-isoform-selective degrader ranking compared with using raw ΔpTernary directly.

The mechanism: PTM-blind ternary scorers (DeepTernary, PROTAC-STAN, ET-PROTACs) were trained on PDB ternaries that contain almost no PTM diversity on the POI side. Asking them to discriminate WT vs PTM-isoform via a ≈80 Da surface change is asking for signal *inside* their score-function noise. A per-POI noise floor estimated from random surface perturbations of the same chemical magnitude separates "real PTM-induced ternary geometry change" from "random surface jitter the scorer happens to be sensitive to".

**Scope and conditions.** - **Scorers in scope**: DeepTernary (Nat. Commun. 2025), PROTAC-STAN (Adv. Sci. 2025), ET-PROTACs (Brief. Bioinform. 2024). All trained on essentially PTM-blind PDB ternaries.
- **POI universe**: CRBN+VHL subset of TernaryDB, ≈80 Da-magnitude PTM perturbations only. Bulkier modifications (lipidation, glycosylation > 200 Da) are out of scope for this claim.
- **Threshold rule**: per-POI noise floor, not global. A global threshold would conflate POI-specific scorer sensitivity with PTM signal.

## Approach sketch

*Empirical claim migrated from a former claim — supporting evidence is paper-level / experiment-design-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a proposed hypothesis with experiments planned (see edges).*

## Risks

None yet. Possible failure modes:
- If the noise floor is so wide that |ΔpTernary| > 1.5 × noise floor never fires on real PTM-PROTACs, the calibration kills both noise and signal — the idea fails fast.
- If raw ΔpTernary is *already* near-perfect on the held-out set (unlikely given Risk #1 in the source idea), calibration provides no additional precision.

## Pilot results

No direct evidence yet. The mechanistic argument rests on:

1. The surface-area / mass scale of a phospho-group (≈80 Da, ≈3 Å) is small compared with typical interface contact areas; PTM-blind scorers are unlikely to be calibrated for perturbations at this scale.
2. Phase-0 noise-floor calibration is standard practice in any score-function differential analysis where the score function was not trained for the differential task.
3. The contrast experiment ([[ablation-uncalibrated-vs-calibrated-deltapternary]]) directly isolates whether the calibration step contributes to ranking precision over raw ΔpTernary.

## Lessons learned

*To be filled in as the planned experiments produce results.*
