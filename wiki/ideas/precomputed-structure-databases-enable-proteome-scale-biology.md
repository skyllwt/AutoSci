---
title: "Pre-computed AlphaFold-predicted structure databases enable proteome-scale structural biology that on-demand prediction cannot"
slug: "precomputed-structure-databases-enable-proteome-scale-biology"
status: validated
origin: "Migrated from claims/precomputed-structure-databases-enable-proteome-scale-biology on 2026-05-10 (was status: supported, confidence: 0.85); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [structural-biology, databases, alphafold, infrastructure]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

Centralized, pre-computed databases of AlphaFold-predicted structures (specifically, AlphaFold DB) unlock classes of analysis — proteome-scale comparative structure work, structurally-resolved interactome construction, cross-database integration with primary biological resources — that running AlphaFold2 on demand cannot practically support, because of the gap between seconds-per-lookup and hours-per-prediction inference cost, redundant compute carbon footprint, and the need for stable cross-references for primary biological databases (UniProt, Ensembl, InterPro, etc.).

**Scope and conditions.** - Coverage cutoffs limit applicability to viral sequences, very short / very long proteins, isoforms, multimers, and ligand complexes.
- AlphaFold2-only as of 2024; AlphaFold3 predictions are not yet integrated.
- Confidence-blind use of AFDB is unsafe; consumers must respect pLDDT and PAE.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- For specialized sequence spaces (metagenomic, designed proteins, viral), running on-demand prediction (or using ESM Atlas / dedicated runs) remains necessary.
- For applications needing the full 5-seed ensemble or model-internal uncertainty, AFDB's bulk-UniProt single-seed predictions are insufficient.

**Open questions.**

- How much of the proteome-scale work attributed to AFDB would have happened anyway via on-demand prediction at major HPC centres?
- What is the right governance model for keeping AFDB current as AlphaFold3 / multimer / isoform-aware predictors mature?

## Pilot results

The AlphaFold DB 2024 update reports (a) >214M predictions covering essentially all of UniProt, (b) integration into 7+ primary biological databases that cite stable AFDB URLs, (c) integration of structure-similarity clusters from Foldseek at proteome scale (only feasible because all structures are pre-computed and stored), and (d) explicit cost arguments — the carbon footprint of redundant inference and the lookup-vs-inference latency gap. Downstream papers (e.g. structurally-resolved human PPI networks, cross-organism comparative structural biology) have only become feasible after AFDB scaled.

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
