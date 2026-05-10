---
title: "E3 ligase deregulation in cancer alters substrate stability and is therapeutically exploitable in a context-dependent manner"
slug: "e3-ligase-deregulation-cancer-alters-substrate"
status: validated
origin: "Migrated from claims/e3-ligase-deregulation-cancer-alters-substrate on 2026-05-10 (was status: supported, confidence: 0.85); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [ubiquitin-ligase, cancer, drug-target, oncogene, tumour-suppressor]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

Deregulation of ubiquitin ligases (E3s) — through mutation, copy-number change, transcriptional or post-translational alteration — is a pervasive driver of cancer phenotypes that operates by shifting the stability, localization, or complex assembly of E3 substrates. Because the same E3 can act as oncogene or tumour suppressor depending on lineage and signalling context, therapeutic intervention targeting E3-substrate axes is both feasible and necessarily context-specific. Concrete clinical translations include MDM2–p53 disruptors (Nutlins, RG7112), SCF–SKP2 inhibitors that trigger p53-independent senescence, PARP inhibitors that exploit BRCA1/HR deficiency, and PROTAC-style targeted degraders that recruit healthy E3s (VHL, cereblon, MDM2, IAP) to remove undruggable oncoproteins.

**Scope and conditions.** The claim applies most strongly to the well-studied E3s catalogued in the source review and in cancer-genomics consortia datasets. It is weaker for the long tail of less-characterized E3s (~600 in the human genome) where mechanistic and clinical evidence is sparse. The therapeutic-tractability arm is most strongly supported for MDM2, the proteasome, BRCA1/HR exploitation by PARP inhibition, and PROTACs recruiting a small set of E3s with available ligands (VHL, cereblon, MDM2, IAP).

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- BRCA1's E3 activity may not be strictly required for its tumour-suppressor function: a Brca1I26A mouse retaining BARD1 binding but lacking ligase activity has reduced tumour development relative to WT, while Brca1C61G (which disrupts BARD1 binding) phenocopies Brca1−/−. This suggests scaffolding contributions independent of ligase activity for at least one major tumour-suppressor E3.
- Many E3-targeted agents have shown preclinical efficacy that does not translate to durable clinical responses, indicating that E3 inhibition alone is often insufficient and that compensatory ligase rerouting may limit single-agent activity.
- The substrate networks of cullin–RING ligases overlap (multiple F-box proteins compete for SCF), so inhibiting one substrate receptor may reroute cullin activity rather than stabilize the intended substrate.

**Open questions.**

- What predictive variables (lineage, signalling state, chain topology, subcellular localization) most reliably forecast whether perturbing a given E3 is pro- or anti-tumour?
- Can substrate-selective E3 inhibitors be engineered (for example, FBXW7-cyclin E selective vs FBXW7-MYC selective) without globally disrupting the host E3 complex?
- For PROTACs, which E3s beyond the current handful (VHL, cereblon, MDM2, IAP) yield productive ternary complexes with arbitrary targets, and what governs ternary-complex formation?
- How much of the clinical efficacy gap between preclinical E3-targeted agents and clinical outcomes is attributable to ligase-rerouting compensation vs pharmacology vs trial design?

## Pilot results

- Mouse models with E3 knockouts or missense alleles (FBXW7, BRCA1, parkin, VHL, MDM2 transgenics, SPOP) reproducibly alter tumour incidence and spectrum, establishing causal contribution rather than correlation.
- Genomic studies have mapped recurrent cancer mutations and copy-number changes onto E3 genes (MDM2 amplification, FBXW7 loss-of-function, VHL loss in clear-cell RCC, SPOP mutations in prostate cancer, BRCA1/2 in breast/ovarian, PARK2 deletions in colorectal and other tumours).
- Biochemical and structural studies have validated specific E3-substrate axes (MDM2-p53, SCF-FBXW7-cyclin E/MYC/c-Jun/mTOR, VHL-HIF-α, BRCA1-BARD1, CRL3-SPOP-AR/SRC-3, NEDD4-RAS/PTEN).
- Clinical evidence to date includes proteasome inhibitors (bortezomib, carfilzomib) approved for multiple myeloma, MDM2-p53 antagonists in trials for haematological malignancies, PARP inhibitors approved for BRCA-mutant breast/ovarian cancer, and the rapidly maturing PROTAC pipeline (ARV-110, ARV-471 and follow-ons).
- Context-dependent dual roles are well established: NEDD4 acts as tumour suppressor in normal cells but oncogenic in RAS-mutant cells via PTEN degradation; SPOP is tumour suppressor in nucleus but oncogene in cytoplasm; CDH1 has dual-suppressor effect on BRAF.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
