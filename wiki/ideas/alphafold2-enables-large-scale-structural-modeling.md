---
title: "AlphaFold2 enables large-scale structural modeling of human PPI network"
slug: "alphafold2-enables-large-scale-structural-modeling"
status: validated
origin: "Migrated from claims/alphafold2-enables-large-scale-structural-modeling on 2026-05-10 (was status: supported, confidence: 0.75); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [alphafold2, protein-protein-interaction, interactome, structural-biology]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

AlphaFold2, applied via the FoldDock pipeline and ranked by pDockQ confidence, can produce high-confidence structural models for thousands of human protein-protein interactions at interactome scale, with calibration good enough to support downstream mechanistic analyses (disease mutations at interfaces, phosphorylation co-regulation, partial higher-order assembly).

**Scope and conditions.** - Interactions need a reasonably deep paired MSA. HuRI's Y2H set is enriched in transient, MSA-poor, disorder-rich pairs and is systematically harder to model.
- The claim is about **binary complexes**. Higher-order assembly via iterative dimer alignment works for some systems (TFIIH, RFC) and partially fails for others (20S proteasome chain identity, eIF2B without trimer scaffolds).
- "High confidence" means pDockQ > 0.5 with the validation above; lower-confidence models (0.23-0.5) should be treated as hypothesis generators only.
- Paralogous-subunit complexes can have correct overall geometry but swapped chain identities.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- ~20% of pDockQ > 0.5 predictions are still incorrect (DockQ < 0.23) — not negligible at interactome scale.
- Indirect-contact pairs in large complexes occasionally produce high pDockQ scores (e.g. RFC3-RFC5), so high pDockQ does not guarantee a real direct interaction.
- For transient interactions (much of HuRI), the method's recall is low and unmeasured: the framework cannot tell "no interaction" from "real but unmodelable interaction".

**Open questions.**

- What is the true precision-recall tradeoff at lower pDockQ cutoffs once orthogonal experimental constraints are folded in?
- Does AF-Multimer materially improve over FoldDock + pDockQ on the same 65,484 pairs, especially for the HuRI subset?
- How well do follow-up assembly methods (e.g. Bryant et al. sequential assembly, Nat Commun 2022) extend the binary-complex result to native multi-subunit stoichiometries?

## Pilot results

The supporting paper applies AF2 + FoldDock to all 65,484 nonredundant human PPI pairs from HuRI and hu.MAP 2.0. Three independent validation channels back the claim:

1. **Solved structures (1,465 complexes)**: 80% of pDockQ > 0.5 predictions match the experimental complex (DockQ > 0.23); 70% at pDockQ > 0.23.
2. **Orthogonal crosslink mass spectrometry**: 75% of pDockQ > 0.5 models have at least one experimental crosslink within the linker's maximal feasible distance.
3. **Disease-mutation enrichment**: pathogenic ClinVar variants are 2.3× enriched at predicted interface residues vs. non-interface (P = 2.7e-31), consistent with the predicted interfaces being structurally meaningful rather than random.

The 3,137 high-confidence models include 1,371 with no homology to any known structure, demonstrating net new structural coverage rather than mere recapitulation.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
