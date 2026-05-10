---
title: "PTM protein isoforms enable selective drug design beyond wild-type targets"
slug: "ptm-protein-isoforms-enable-selective-drug"
status: tested
origin: "Migrated from claims/ptm-protein-isoforms-enable-selective-drug on 2026-05-10 (was status: weakly_supported, confidence: 0.6); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [drug-design, posttranslational-modification, ptm-isoforms, selectivity, allosteric-inhibitor, covalent-inhibitor, protac]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

Designing drugs against the disease-relevant post-translationally modified isoform of a protein — rather than its wild-type counterpart — yields better selectivity and expands the druggable target space relative to conventional structure-based drug design. This is the central empirical claim of the PTMI-DD framework.

**Scope and conditions.** - Restricted to small-molecule and PROTAC modalities; antibody and biologics evidence is mentioned but not central.
- The PTM in question must be (i) disease-relevant, (ii) experimentally characterizable on the target, and (iii) yield an isoform-specific binding mode (covalent reactivity, induced pocket, PPI interface, or E3-recruitable surface).
- Cellular selectivity over the wild-type counterpart must be demonstrable; biochemical-only selectivity is insufficient.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a tested empirical finding, not as a new prospective hypothesis.*

## Risks

- The review does not quantify how often a candidate PTM-isoform yields a tractable drug; the catalogue is biased toward successes and is likely a low base rate when applied prospectively.
- Many PTMs are transient and substoichiometric, which complicates target engagement at the isoform level and may erode the apparent selectivity advantage in vivo.
- Selectivity wins from non-conserved-cysteine targeting are not unique to PTMI-DD logic; some are explainable by conventional covalent-inhibitor design without invoking PTM-isoform specificity.
- Outside the CRBN/VHL/MDM2/IAP set, PTM-isoform-specific PROTAC recruitment remains mostly aspirational.

**Open questions.**

- What is the prospective hit-rate of PTMI-DD when the PTM-isoform is nominated by ML predictors rather than known disease biology?
- Can PTM-conditioned structure predictors (AlphaFold-class) reliably reveal PTM-induced pockets before any HTS?
- How well does cellular isoform-selectivity translate to in-vivo selectivity, especially under PTM-cycling conditions?

## Pilot results

The supporting evidence is review-level and case-based rather than benchmark-level:

- **Allosteric isoform inhibition (strong case).** Asciminib (ABL001) binds the myristoyl pocket of ABL1, exploiting the N-myristoylated isoform of Bcr-Abl. It produced positive Phase III results in CML and Ph+ ALL where ATP-site competitors had hit resistance ceilings.
- **Epigenetic isoform inhibition (moderate case).** EZH2 K510/K514/K515 automethylation and SMYD2-driven K307 methylation increase PRC2 activity in tumours; tazemetostat (FDA-approved 2020) targets EZH2 in epithelioid sarcoma. HDAC inhibitors (vorinostat, romidepsin, belinostat, panobinostat) are approved for cutaneous and peripheral T-cell lymphomas.
- **Covalent isoform inhibition (moderate case).** Ibrutinib targets a non-conserved cysteine of BTK; the authors report a covalent RhoA inhibitor identified via PTMI-DD reasoning.
- **Degrader-mode isoform targeting (moderate case).** Thalidomide-class CRBN binders, bortezomib, and carfilzomib treat multiple myeloma; PROTACs extend this mode to PTM-specific recruitment.
- **Structural-dynamics support (weak/moderate).** Statistical PDB analysis shows phosphorylation and N-glycosylation induce significant non-extreme structural changes; PTMs can drive disorder-to-order transitions, creating new ordered surfaces.

Confidence is set at 0.6 (weakly_supported) because: the claim is supported by clinical wins but no quantified prospective hit-rate exists; the wins are concentrated in kinases / epigenetics / CRBN-amenable degraders rather than spread across the proteome; and there is selection bias toward success stories in the reviewed literature.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
