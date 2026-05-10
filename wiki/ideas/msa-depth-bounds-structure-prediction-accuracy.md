---
title: "MSA depth bounds the achievable accuracy of MSA-conditioned protein structure predictors"
slug: "msa-depth-bounds-structure-prediction-accuracy"
status: validated
origin: "Migrated from claims/msa-depth-bounds-structure-prediction-accuracy on 2026-05-10 (was status: supported, confidence: 0.85); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [msa, protein-structure-prediction, evolutionary-information, scaling, alphafold]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

For protein structure predictors that take a multiple sequence alignment (MSA) as their primary evolutionary input, prediction accuracy is monotonically bounded by MSA depth: below a critical depth (median per-residue effective sequence count Neff of approximately 30), accuracy collapses; above an upper plateau (Neff ~ 100), additional MSA depth yields diminishing returns. This depth-dependence implies that orphan and metagenomic sequences with shallow MSAs are intrinsically harder for the family of methods, independent of architecture refinements within that family.

**Scope and conditions.** - Holds for predictors whose inference pipeline consumes an MSA. Single-sequence predictors built on protein language models may exhibit a different scaling law (open question).
- Holds within the regime spanned by current public sequence databases (UniRef, MGnify, BFD, Uniclust30); whether radically deeper sequencing changes the plateau is unknown.
- Does not specify what alternative signals (templates, language-model embeddings, structural priors) can substitute when MSAs are shallow; the claim only bounds what MSA-conditioned methods can extract from MSA alone.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- Single-sequence / protein-LM-based predictors (post-AlphaFold2) report accuracy on orphan sequences that approaches MSA-based methods, suggesting the bound is specific to the MSA-conditioned family. This is consistent with the stated conditions rather than a refutation.
- Engineering tricks (paired MSAs from cross-species orthology, deeper metagenomic search) shift the operating point along the curve but have not been shown to remove the plateau.

**Open questions.**

- Does the same Neff threshold apply to protein-LM-augmented MSA predictors, or do LM features extend the low-MSA regime?
- How does the threshold scale for biomolecular complexes where pairing across chains adds another MSA-depth dimension?
- Can self-distillation be iterated to push the low-Neff curve further up without overfitting to the predictor's own biases?

## Pilot results

- **AlphaFold2, Fig. 5a**: lDDT-Calpha versus median per-residue Neff on the redundancy-reduced post-cutoff PDB set, restricted to chains in which less than 25% of long-range contacts are heteromeric. Both the high-coverage (>60% template coverage) and low-coverage (<30% template coverage) subgroups show the same threshold and plateau pattern, with the low-coverage subgroup more strongly Neff-dependent.
- **Self-distillation**: AlphaFold2's self-distillation training step specifically aims to attenuate this dependence by manufacturing additional supervised data from predicted structures of low-MSA-depth Uniclust30 sequences, and it improves accuracy on hard MSA-poor targets — indirectly confirming that MSA depth is the binding constraint and that mitigations work.
- **Discussion in the paper**: the authors hypothesise that MSA information is most needed in early Evoformer blocks to coarsely localise the structure, while later refinement is less MSA-dependent — consistent with a saturating dependence past a critical depth.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
