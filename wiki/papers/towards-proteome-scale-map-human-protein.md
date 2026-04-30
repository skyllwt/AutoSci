---
title: "Towards a proteome-scale map of the human protein-protein interaction network"
slug: towards-proteome-scale-map-human-protein
arxiv: ""
venue: "Nature"
year: 2005
tags: [protein-protein-interaction, interactome, yeast-two-hybrid, human-proteome, systems-biology, network-biology, disease-genetics]
importance: 5
date_added: 2026-04-30
source_type: pdf
s2_id: "fe32bfbfb24b967bb606aa9b00cf46f17a3936c6"
keywords: [Y2H, CCSB-HI1, ORFeome, interactome map, binary PPI, co-affinity purification, OMIM disease genes]
domain: "Computational Biology"
code_url: ""
cited_by: []
---

## Problem

Prior to 2005 the human protein-protein interaction (PPI) network was known only through (1) literature-curated (LC) interactions biased by community attention, and (2) "interologs" inferred by orthology from model-organism interactome data. Both sources are inspection-biased, incomplete, and weakly supported by direct experiment in human cells. A systematic, proteome-scale, experimentally measured human binary PPI map did not exist, blocking systems-level inquiries into development, disease, and network evolution.

## Key idea

Build the first proteome-scale human binary PPI map by running a stringent high-throughput yeast two-hybrid (Y2H) screen over Gateway-cloned ORFs from the human ORFeome v1.1 (~8,100 ORFs / ~7,200 genes), then independently verify a representative sample by co-affinity purification (co-AP) GST pull-down in human 293T cells. Releasing the resulting CCSB-HI1 dataset — 2,754 binary interactions among 1,549 proteins — provides a low-bias scaffold for downstream systems and disease analyses.

## Method

- **Search space (Space-I)**: 7,200 x 7,200 gene matrix from human ORFeome v1.1 (~10% of the genome's protein-coding gene complement).
- **High-throughput Y2H pipeline**: each of ~8,100 DB-X bait constructs was mated to 45 mini-pools of 188 AD-Y prey (AD-188Ys) in 96-well format. Three Y2H reporter genes plus plasmid-shuffling counter selection eliminated de novo auto-activators.
- **Stringent phenotype testing**: only colonies positive on at least two reporter assays were retained. Both DB and AD inserts were PCR-amplified and Sanger-sequenced, generating 10,597 interaction sequence tags (ISTs). Collapsing to gene pairs and removing low-confidence calls yielded 2,754 interactions = CCSB-HI1.
- **Verification**: co-AP GST pull-downs on representative samples in 293T cells. ~78% verification rate for Y2H-only interactions, ~62% for LCI-only, ~81% for both — comparable in reliability to LC interactions.
- **Biological correlation analyses**: shared GO terms (component / function / process), shared upstream regulatory motif, mouse phenotype overlap, expression correlation across four expression datasets, and OMIM-disease overlap.
- **Network analyses**: power-law degree distribution check, hub-edge structure, MCODE clustering for module discovery, FuncAssociate for GO enrichment, evolutionary-class assortativity (eukaryotic / metazoan / mammalian / human).

## Results

- 2,754 binary interactions covering 1,549 proteins (~21% of proteins tested in Space-I).
- Increases the available binary-PPI count within Space-I by ~70%.
- Co-AP verification: ~78% (Y2H-only), ~81% (Y2H ∩ LCI), ~62% (LCI-only), suggesting CCSB-HI1 is comparable in technical reliability to LC interactions while LC quality is itself heterogeneous.
- Recovers 2.3% / 4.6% / 8.4% of LCI / LCI-core / LCI-hypercore interactions respectively — overlap rises with curator confidence.
- 424 interactions involve at least one OMIM disease-associated protein; 352 of these are not previously co-mentioned in PubMed/Google Scholar — over 300 new disease-associated PPIs surfaced.
- CCSB-HI1 pairs are enriched (vs. random within Space-I) for shared GO annotation in all three branches (P < 6e-20), for shared mouse phenotypes, for shared upstream regulatory motifs, and for correlated expression in 3 of 4 expression studies.
- Network has approximately power-law degree distribution and hierarchical organization with hubs, but does not show strong clustering — contradicting the "small world with high clustering" claim made for sparser model-organism interactome maps.
- Interactome appears to grow preferentially through additions among proteins of the same evolutionary class.
- Highlighted example: novel RTN4 - SPG21 interaction with two shared conserved upstream motifs, suggesting a candidate mechanism for Mast syndrome.

## Limitations

- Coverage: Space-I is only ~10% of the eventual full search space; the authors estimate CCSB-HI1 captures only ~1% of the total human interactome.
- Y2H is a binary assay run in a heterologous host (yeast); it under-represents membrane proteins and obligate complex components, and cannot recover cooperative or transient cellular contexts.
- Reproducibility within the screen was ~55%, comparable to AP-MS but below ideal — many true interactions are missed each pass.
- Static snapshot: the map records existence of detectable interactions, not when, where, or under what condition they occur in vivo.
- Biological false positive rate is hard to quantify directly; only partially addressed via correlative biological-attribute enrichment.

## Open questions

- How does interactome topology change with cell type, developmental stage, and disease state?
- What fraction of detected binary interactions are genuinely physiologically relevant in vivo?
- How can systematic Y2H be extended toward the full human ORFeome and integrated with AP-MS to recover non-binary complexes?
- Can integrating PPI maps with structural prediction (later realized by AlphaFold-driven structurally resolved PPI networks) close the gap between binary-detection and complex-architecture knowledge?

## My take

The pivotal value of CCSB-HI1 is methodological and sociological: it demonstrates that a single laboratory pipeline can produce a low-inspection-bias scaffold for the human interactome at a meaningful scale, and that such scaffolds correlate with independent biological attributes well enough to be trusted as prior. Even though the map is sparse by today's standards, every later systems-biology analysis, drug-target interaction predictor, and structurally resolved PPI network owes a measured debt to this dataset and its successors.

## Related

- Concepts: [[yeast-two-hybrid-system]], [[binary-protein-protein-interaction]], [[ccsb-hi1-human-interactome-v1]]
- Claims: [[high-throughput-y2h-recovers-novel-disease-associated-ppis]]
- People: [[marc-vidal]], [[jean-francois-rual]], [[frederick-roth]]
- Topics: [[medpredict]]
