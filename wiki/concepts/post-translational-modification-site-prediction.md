---
title: "Post-translational modification site prediction"
aliases: [PTM site prediction, PTM prediction, protein PTM prediction]
tags: [bioinformatics, deep-learning, protein-sequence, ptm, classification]
maturity: active
key_papers: [musitedeep-deep-learning-based-webserver-protein]
first_introduced: ""
date_updated: 2026-04-30
related_concepts: []
---

## Definition

Post-translational modification (PTM) site prediction is the computational task of identifying, from a protein's amino-acid sequence (and optionally structural or evolutionary context), which residues carry a specific covalent modification — phosphorylation, glycosylation, acetylation, methylation, palmitoylation, ubiquitination, SUMOylation, hydroxylation, and related additions. It is typically formulated as per-residue binary classification, with one model trained per PTM type, using a fixed-length sequence window centred on the candidate site as input.

## Intuition

Each PTM type is catalysed by a family of enzymes (kinases, glycosyltransferases, methyltransferases, ligases, etc.) whose recognition motifs are encoded — at least partially — in local sequence context. A predictor that can capture both short motifs (the immediate neighbours of the target residue) and longer-range patterns (disorder propensity, secondary-structure tendency) can rank candidate residues by modification likelihood. Prediction is useful where experimental annotation is sparse: at proteome scale, on non-model organisms, and as a hypothesis generator for biologists studying signalling cascades and cross-talk between modifications.

## Formal notation

Given a protein sequence `s = s_1 s_2 ... s_L` over a 20-letter alphabet and a PTM type `t` with eligible residue subset `A_t`, the task is to learn `f_t : window(s, i) -> [0, 1]` predicting the probability that residue `i in A_t` carries modification `t`. The window is usually `(2k+1)` residues centred on `i` (commonly k=16, so a 33-residue window) with a pad token for positions outside the sequence. Training data are positive sites annotated in databases such as UniProtKB/Swiss-Prot, dbPTM, and PhosphoSitePlus, with negatives sampled from the same eligible residue type that lacks an annotation. Evaluation uses AUC and area-under-PR because the negative-to-positive ratio is large and threshold-free metrics are fairer than accuracy.

## Variants

- **Per-PTM independent models** — one binary classifier per PTM type (MusiteDeep's default).
- **Multi-task models** — a shared backbone with per-PTM heads, trained jointly so low-data PTMs benefit from data-rich ones.
- **Sequence-only vs feature-engineered** — classical pipelines (Musite, GlycoEP, GPS-PAIL, MePred-RF) rely on PSSM, secondary structure, surface accessibility, BLOSUM-derived features. Modern deep models (MusiteDeep, DeepPhos) take raw sequences and learn features directly.
- **Structure-aware** — emerging variants that consume AlphaFold-predicted structures or surface-accessibility annotations alongside the sequence window.
- **Profile-based** — tools such as PTM-ssMP score candidate sites against known modification profiles; cannot predict de novo.

## Comparison

- vs. **kinase-substrate prediction**: kinase-substrate models explicitly target the substrate-kinase pairing; PTM site prediction collapses across kinases within a PTM type.
- vs. **PTM cross-talk modelling**: PTM site prediction asks whether residue `i` is modified; cross-talk modelling asks whether modification at residue `i` depends on or co-occurs with modification at residue `j`. Most current site predictors are per-PTM-type and do not model coupling.
- vs. **structure-based reactivity prediction**: alternative approaches predict modifiability from atomic-level features (solvent accessibility, electrostatics) rather than sequence motifs; complementary signal but expensive to compute proteome-wide.

## When to use

- Rapid screening of candidate PTM sites in proteins lacking experimental annotation.
- Generating hypotheses about regulatory residues for downstream mutagenesis or mass-spectrometry validation.
- Annotating non-model organism proteomes where homology transfer is weak.
- Comparing relative modification likelihood across paralogs or disease-mutant variants.

## Known limitations

- Negative-set construction is biased: any "unannotated" residue is treated as negative even though many will eventually be reclassified as positive once experimentally probed.
- Most predictors do not model cellular context (expression level, sub-cellular localization, kinase abundance), so a confidently predicted site may simply be unreachable in vivo.
- Independent per-PTM training prevents the model from learning genuine cross-talk between modifications.
- Performance is uneven across PTM types; rare modifications (hydroxyproline, methylarginine) remain difficult.
- Calibration across PTM types is rarely audited: a confidence of 0.7 may mean different things for phosphorylation versus ubiquitination.

## Open problems

- Joint modelling of multiple PTM types to capture cross-talk explicitly.
- Incorporating AlphaFold-quality structures as a routine input feature.
- Domain adaptation across organisms and tissue contexts.
- Better-calibrated, threshold-free outputs that downstream tools can compose.

## Key papers

- [[musitedeep-deep-learning-based-webserver-protein]] — ensemble MultiCNN + CapsNet + bootstrap weight averaging + transfer learning, sequence-only webserver covering 13 PTM types.

## My understanding

The field has moved from feature-engineered SVMs / random forests (Musite, GlycoEP, GPS-PAIL, MePred-RF) towards sequence-only deep models (MusiteDeep, DeepPhos) and is now poised to absorb structural context from AlphaFold and to generalize toward joint multi-PTM modelling. The core unsolved issue is not motif extraction — deep nets handle that — but the fact that "negative" labels are mostly unobserved positives, which caps the achievable PR-area especially for rare modifications.
