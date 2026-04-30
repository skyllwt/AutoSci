---
title: "An integrated bioinformatics platform for investigating the human E3 ubiquitin ligase-substrate interaction network"
slug: integrated-bioinformatics-platform-investigating-human-e3
arxiv: ""
venue: "Nature Communications"
year: 2017
tags: [bioinformatics, ubiquitination, e3-ligase, naive-bayes, protein-interaction-network, web-platform]
importance: 3
date_added: 2026-04-30
source_type: tex
s2_id: ""
keywords: [E3-substrate interaction, UbiBrowser, naive Bayesian classifier, likelihood ratio, ubiquitin ligase, E3 recognition motif, domain enrichment, GO term enrichment]
domain: "computational biology"
code_url: "http://ubibrowser.ncpsb.org"
cited_by: []
---

## Problem

The high specificity of the ubiquitination cascade (E1 → E2 → E3) is governed by the interaction between an E3 ubiquitin ligase and its substrate, but only ~15% of known ubiquitinated proteins (less than 900 out of >5,700 substrates with >30,000 sites in mUbiSiDa) had a confirmed E3 partner at the time of writing. Existing experimental strategies to identify E3-substrate interactions (ESIs) — GPS profiling, protein microarrays, live phage display, mass spectrometry — are slow, expensive, and low-throughput because of E3s' weak interactions and low substrate levels. A high-throughput computational strategy that systematically maps the human E3-substrate interaction network at proteome scale was missing.

## Key idea

Combine multiple heterogeneous biological evidence types — homologous mouse-to-human ortholog ESIs, enriched domain pairs, enriched GO term pairs, protein-protein interaction (PPI) network loop motifs, and inferred E3 recognition consensus sequence motifs — into a single naive Bayesian classifier whose composite likelihood ratio (LRcomp) gives a calibrated confidence score for any candidate E3-substrate pair. Deliver the resulting proteome-wide ESI predictions through an interactive web platform (UbiBrowser) with per-edge evidence breakdowns.

## Method

- **Golden standards.** Manually curated 913 E3-substrate pairs (GSP) from PubMed abstracts before 2010-01-01 using a text-mining tool ("E3miner") and pattern filtering. The negative set (GSN, 2734 pairs) was built from physical PPIs (HPRD + IntAct + iRefIndex) that were not in any known ESI list.
- **Five evidence channels.** For each, a likelihood ratio LR(f) = P(f | positive) / P(f | negative) was estimated from GSP/GSN:
  1. Ortholog-ESI: map 366 mouse pairs from E3Net to human via Inparanoid 8.0.
  2. Domain enrichment ratio (DER) over Pfam 27 domain assignments.
  3. GO term enrichment ratio (GER) for molecular function, biological process, and cellular component.
  4. Network topology: counts of 3- and 4-interaction loops in HPRD-derived integrated network including the candidate ESI.
  5. E3 recognition consensus motif inferred per E3 with a motif-x-style procedure using the E3's GSP substrates as foreground and HPRD interactors as background.
- **Bayesian integration.** Conditional independence assumed across evidence types, so LRcomp = product of individual LRs (with the maximum LR retained when multiple sources exist for the same evidence type). Score normalized to a (0,1) UbiBrowser Score via logistic transform.
- **Evaluation.** Five-fold cross-validation on GSP/GSN. Independent evaluation on a 402-ESI test set drawn from post-2010 literature. Pair-input split protocol of Park & Marcotte (C1/C2/C3) to avoid overfitting.
- **Validation experiment.** Co-immunoprecipitation, in vivo ubiquitination, and dose-dependent destabilization assays in MDA-MB-231 cells confirm a predicted Smurf1-Smad3 interaction (LR = 29.87): wild-type Smurf1 reduces Smad3 protein levels and increases its poly-ubiquitination, while the C699A ligase-dead mutant does not.
- **Deployment.** UbiBrowser web service (MySQL + Apache 2 + PHP/Perl/JavaScript) with network-view (confidence and evidence modes) and sequence-view rendering predicted ubiquitination sites, recognized domains, and E3 recognition motifs.

## Results

- Scored 14,459,214 E3-protein pairs across 714 E3s and 20,251 human proteins; 14,419 high-confidence predicted ESIs are surfaced.
- Five-fold cross-validation AUROC = 0.827 (95% CI 0.811-0.842) for the integrated Bayesian model, substantially above any single-evidence model (best single channel: GO term pair, AUROC 0.696).
- Independent post-2010 test set AUROC = 0.73 (95% CI 0.697-0.769).
- Pair-input split AUROCs: C1 = 0.855, C2 = 0.816, C3 = 0.629 — non-trivial generalization even when neither member of the test pair is seen during training, because the model relies on transferable domain/motif/GO features.
- Compared to Huang et al. 2016, UbiBrowser yields markedly fewer non-substrate regulators among predictions (2% vs 21%, P = 1.25 × 10⁻⁵).
- Anecdotal validations recovered from later literature: ITCH-TAB1, CHIP-EGFR (in pancreatic cancer), NEDD4-HER3, all top-ranked predictions later confirmed experimentally.
- Wet-lab validation: Smurf1 destabilizes and ubiquitinates Smad3 in a ligase-activity-dependent manner; co-IP confirms Smurf1-Smad3 association in vivo with MG132.

## Limitations

- Conditional independence across evidence types is a simplification: domain, GO, and network features are correlated in practice, so LRcomp can over-credit redundant evidence.
- Performance collapses sharply when neither test E3 nor substrate appears in training (C3 AUROC 0.629), bounding generalization to truly novel proteins.
- GSN is constructed from physical PPIs that are not annotated as ESIs — a "non-substrate" label that may include unknown true substrates and inflate apparent specificity.
- Evidence channels are static snapshots of 2013-2014 era databases (HPRD 2009, Pfam 27, IntAct 2013, GO 2014), so coverage decays as new ESIs and domain annotations accumulate.
- The 913-ESI GSP is small relative to the 14M scored pairs; class imbalance and curation bias may inflate calibration of UbiBrowser Score.
- Smurf1-Smad3 wet-lab validation is performed under overexpression in a single cell line (MDA-MB-231) — endogenous-level relevance is not established.

## Open questions

- How would deep representation learning over sequence/structure (e.g. AlphaFold-derived structural features) compare to the current motif-and-domain features in the same Bayesian framework?
- Can the model be retrained with structurally-resolved interaction surfaces to fix C3-regime generalization?
- Does the framework transfer to other E1/E2/E3 cascades (SUMOylation, NEDDylation, ISGylation), where golden-standard sets are even smaller?
- Can the UbiBrowser score be calibrated into an absolute interaction probability rather than a relative ranking?

## My take

A clean, 2017-vintage example of disciplined feature engineering plus naive-Bayes integration in computational biology: it works because each of the five LRs is individually informative and cheap to compute, and the integrated AUROC sits well above each component. The wet-lab Smurf1-Smad3 confirmation gives the predictions empirical credibility beyond cross-validation numbers. The most interesting modern angle is that domain/motif/GO pair features are exactly the kind of priors that a structure-aware predictor (AlphaFold-Multimer, RoseTTAFold-2tracks, ESMFold + interaction heads) could replace or augment — so UbiBrowser is a natural baseline against which to measure whether structural prediction has actually moved the needle for E3-substrate identification.

## Related

- [[e3-ubiquitin-ligase-substrate-interaction-prediction]]
- [[e3-ubiquitin-ligase-substrate-network-predicted]]
