---
title: "MusiteDeep: a deep-learning based webserver for protein post-translational modification site prediction and visualization"
slug: "musitedeep-deep-learning-based-webserver-protein"
arxiv: ""
venue: "Nucleic Acids Research"
year: 2020
tags: [deep-learning, ptm, post-translational-modification, bioinformatics, webserver, protein-sequence, ensemble, attention, capsule-network]
importance: 3
date_added: 2026-04-30
source_type: tex
s2_id: ""
keywords: [PTM site prediction, MultiCNN, CapsNet, 2D attention, bootstrapping, transfer learning, weight averaging, FASTA, UniProtKB/Swiss-Prot, homology search, 3D structure visualization]
domain: "Bioinformatics"
code_url: "https://github.com/duolinwang/MusiteDeep_web"
cited_by: []
---

## Problem

Protein post-translational modifications (PTMs) — phosphorylation, glycosylation, acetylation, methylation, palmitoylation, ubiquitination, SUMOylation, hydroxylation, and others — are central to proteomic diversity and protein-function regulation. Experimentally annotating PTM sites is expensive, so dozens of computational predictors have been built, but most existing tools (i) target a single PTM type, (ii) require expensive features (PSSM, secondary structure, surface accessibility) that prevent batch-scale prediction, and (iii) limit submissions to a handful of sequences. There is no fast, sequence-only, general-purpose webserver that predicts multiple PTM types simultaneously for downstream cross-talk analysis.

## Key idea

Combine two complementary deep-learning architectures — a MultiCNN with a 2D attention mechanism, and a Capsule Network — into an ensemble that takes only raw protein sequences as input, with bootstrapping to handle class imbalance, weight averaging across iterations to widen the loss-surface optimum, and transfer learning from data-rich PTM types to data-poor ones. Wrap the resulting predictor in a webserver that supports batch FASTA upload, simultaneous prediction of multiple PTM types, homology-based UniProtKB/Swiss-Prot annotation overlay, and 3D-structure visualization through G2S + NGL viewer integration.

## Method

- **Input**: 33-residue fragments centered on the candidate site, one-of-K coded over 20 amino acids plus a hyphen pad token (21D vector per position); uncommon amino acids set to 0.05.
- **Architecture**: per-PTM binary classifier whose final score averages two networks:
  - **MultiCNN**: three 1D CNN layers, a 2D attention layer, two fully connected layers (introduced in the original MusiteDeep, ref. 21).
  - **CapsNet**: two 1D CNN layers, a PrimaryCaps layer, a PTMCaps layer (ref. 29).
- **Bootstrapping**: split training fragments into N balanced subsets (N = floor(neg/pos), capped at 30); train iteratively with Adam + early stopping; after N iterations save weights `W_i` and validation loss `L_i`, then take the weighted average `W = sum_i exp(1/L_i) W_i / sum_i exp(1/L_i)`.
- **Nested cross-validation ensemble**: 10-fold split of training data; for each split repeat the bootstrap procedure `N_C` times (N_C = 2 in the paper); final score is the mean over the 10 x N_C classifiers.
- **Transfer learning**: pre-train on a large related PTM (phosphoserine / phosphothreonine), then fine-tune on a small target PTM (phosphotyrosine) to reuse shared low-level sequence features, especially the disorder-region signal.
- **Webserver stack**: React + jQuery front end, KOA (Node.js) back end, Python deep-learning service in the business-logic layer, MongoDB persistence, REST API, stand-alone GitHub release.
- **Visualization**: predicted PTMs overlaid on the sequence with colour-coded confidence; homology-based BLAST against UniProtKB/Swiss-Prot to surface known annotations on aligned positions; G2S maps query sequence to PDB structures so predictions can be inspected in 3D via the NGL viewer.

## Results

Timestamp-based benchmark — train on UniProtKB/Swiss-Prot < 2010, test on >= 2010 annotations — reported as AUC / area-under-PR (Table 1 of the paper):

- Phosphoserine/threonine: 0.896 / 0.329 (vs ModPred 0.753 / 0.134; DeepPhos 0.809 / 0.190)
- Phosphotyrosine: 0.958 / 0.864 (vs ModPred 0.695 / 0.151; DeepPhos 0.681 / 0.163)
- N-linked glycosylation: 0.993 / 0.937 (vs ModPred 0.774 / 0.264; GlycoEP 0.928 / 0.210)
- O-linked glycosylation: 0.943 / 0.539 (vs ModPred 0.783 / 0.128; GlycoEP 0.808 / 0.043)
- N6-acetyllysine: 0.978 / 0.858 (vs ModPred 0.702 / 0.127; GPS-PAIL 0.629 / 0.229)
- Methylarginine: 0.941 / 0.844 (vs ModPred 0.770 / 0.130; MePred-RF 0.681 / 0.152)
- Methyllysine: 0.951 / 0.850 (vs ModPred 0.670 / 0.108; MePred-RF 0.782 / 0.514)
- S-palmitoylation-cysteine: 0.961 / 0.922 (vs ModPred 0.824 / 0.478; CSS-Palm4.0 0.735 / 0.465)
- Pyrrolidone-carboxylic-acid: 0.979 / 0.947 (vs ModPred 0.860 / 0.578)
- Ubiquitination: 0.804 / 0.279 (vs ModPred 0.584 / 0.091; UbiProber 0.651 / 0.107)
- SUMOylation: 0.990 / 0.881 (vs ModPred 0.740 / 0.213; GPS-SUMO 0.706 / 0.357)
- Hydroxylysine: 0.982 / 0.930 (vs ModPred 0.974 / 0.891; RF-Hydroxysite 0.919 / 0.300)
- Hydroxyproline: 0.732 / 0.627 (vs ModPred 0.694 / 0.437; RF-Hydroxysite 0.514 / 0.075)

MusiteDeep is best or tied-best on 12 of 13 PTM types under both metrics. Throughput: less than three minutes for 1000 sequences per PTM on CPU only. Performance held under low train/test sequence-similarity bins (Supplementary Figure S2). The webserver supports up to 10 MB FASTA uploads, five concurrent jobs per user, 72-hour result retention, and a REST API with a Python client template. A locally maintained UniProtKB/Swiss-Prot PTM-annotation database refreshes every three months.

## Limitations

- Hydroxyproline AUC of 0.732 with PR area 0.627 is the weakest of the 13 PTM types; the gap to the second-strongest tool is small.
- Ubiquitination PR area is 0.279 even though AUC is 0.804, signalling that the strongly imbalanced positive class still hurts precision at the operating point most users care about.
- Performance numbers come from the paper's own timestamp-based benchmark; no third-party blinded comparison is reported in the manuscript itself.
- The approach predicts each PTM type independently. Cross-talk visualization is supported in the UI, but the model does not jointly model coupled modifications, so observed co-localizations may reflect confounded sequence motifs rather than a learned interaction.
- Sequence-only design ignores cellular context (kinase availability, expression, localization), which limits generalization to condition-specific PTM events.
- Homology-based annotation overlay inherits the coverage and bias of UniProtKB/Swiss-Prot.

## Open questions

- How well does MusiteDeep transfer to organisms or PTM types absent from the UniProtKB/Swiss-Prot training distribution?
- Does jointly modelling multiple PTM types (rather than averaging per-type predictors) materially improve cross-talk inference?
- Can structural context from AlphaFold-predicted proteomes be folded back into the predictor as a feature, given the visualization layer already consumes 3D structures?
- What is the calibration of the confidence score across PTM types and across imbalance regimes — i.e., is a 0.7 score on ubiquitination comparable to a 0.7 score on N-linked glycosylation?

## My take

The contribution is mostly an engineering integration win — combining MultiCNN and CapsNet with bootstrapping, weight averaging, and transfer learning, then wrapping it in a usable webserver — rather than a new architectural insight. The benchmark numbers are compelling and the speed claim (real-time, batch, CPU-only) is the right target for biologists who actually use this kind of tool. The most useful re-usable idea here is the weight-averaging-on-bootstrapped-subsets trick for class-imbalanced sequence prediction; the most fragile part is treating per-PTM predictors as independent when the whole motivation for the visualization layer is cross-talk. A follow-up that ingests AlphaFold structural context and jointly models PTM types would be a natural next step.

## Related

- [[post-translational-modification-site-prediction]]
- [[deep-learning-ensembles-outperform-classical-ml]]
