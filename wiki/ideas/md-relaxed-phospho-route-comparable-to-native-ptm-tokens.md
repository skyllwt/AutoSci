---
title: "MD-relaxed phospho-structure fallback yields ΔpTernary signal comparable to native CCD-PTM-token Boltz-2 prediction"
slug: "md-relaxed-phospho-route-comparable-to-native-ptm-tokens"
status: proposed
origin: "Migrated from claims/md-relaxed-phospho-route-comparable-to-native-ptm-tokens on 2026-05-10 (was status: proposed, confidence: 0.3); evidence captured as edges and below."
origin_gaps: []
tags: [protac, ternary-complex, ptm-isoforms, boltz-2, molecular-dynamics, ptm-conditioning]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-05-02
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; supporting evidence and tested_by experiment links are captured in graph edges and Pilot results.*

## Hypothesis

For the purpose of computing per-POI ΔpTernary in the [[ptm-aware-degrader-target-nomination]] pipeline, an MD-relaxed phospho-structure of the POI (built by force-field minimisation + short MD on the wild-type structure with the PTM modification chemically attached) yields ΔpTernary scores that are not significantly different from those obtained when the PTM-occupied POI is predicted natively by Boltz-2 with CCD-PTM tokens at the known sites. Practically: if Boltz-2 PTM tokens turn out to be unreliable or inaccessible for a given target, the MD route is a usable substitute that does not gate the ΔpTernary pipeline on a working PTM-conditioned structure predictor.

**Scope and conditions.** - **PTM types in scope**: phosphorylation, ubiquitylation (mono-Ub on a single Lys), methylation. Lipidation and glycosylation excluded because they require specialised force-field parameters and frequently larger conformational sampling.
- **MD protocol**: >= 50 ns explicit solvent, ff14SB + phosaa14SB (or equivalent), with the modification chemically attached at t=0 to the equilibrated wild-type structure.
- **POI starting structure**: PDB if available; AlphaFold-DB v4 structure with pLDDT > 70 in the modification region otherwise.

## Approach sketch

*Empirical claim migrated from a former claim — supporting evidence is paper-level / experiment-design-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a proposed hypothesis with experiments planned (see edges).*

## Risks

- For PTMs that cause large-scale conformational rearrangement (e.g., 14-3-3-binding-induced disorder-to-order in some phospho-substrates), 50 ns MD will not sample the post-modification ensemble; the routes will diverge and the claim fails for that subset.
- Boltz-2 native CCD-PTM tokens may exploit training-time correlations that an MD-only structure misses; in that case the routes are NOT comparable and the headline idea is gated on Boltz-2 PTM-token quality (a partial dependency on [[ptm-conditioned-ensemble-prediction]] re-emerges).

## Pilot results

No direct evidence yet. The mechanistic argument rests on:

1. PTM-induced local conformational changes that are druggable (per the PTMI-DD framework in [[drug-design-targeting-active-posttranslational-modification]]) are typically dominated by side-chain repacking and short-range backbone adjustments within ≈8 Å of the modified residue. Both Boltz-2 native CCD-PTM and MD relaxation should capture local repacking; both will fail at PTM-induced large-scale allostery.
2. AF3 / Boltz-2 already underperform on small PROTAC interfaces near the resolution limit (per [[accurate-structure-prediction-biomolecular-interactions-alphafold]] limitations); the marginal gain of native PTM tokens over a force-field-relaxed structure may be small in this regime.
3. If the route choice is a major confound, it would be a methodological bug for the headline idea — independent verification matters.

## Lessons learned

*To be filled in as the planned experiments produce results.*
