---
title: "Binary protein-protein interaction"
aliases: [binary PPI, direct protein-protein interaction, pairwise PPI]
tags: [protein-protein-interaction, network-biology, interactome]
maturity: stable
key_papers: [towards-proteome-scale-map-human-protein]
first_introduced: ""
date_updated: 2026-04-30
related_concepts: [yeast-two-hybrid-system, ccsb-hi1-human-interactome-v1]
---

## Definition

A binary protein-protein interaction is a direct physical contact between exactly two proteins, A and B, detectable in at least one experimental assay. The interactome under this definition is the set of all such (A, B) pairs in a given organism / cell context. The definition explicitly excludes (1) higher-order complex membership without direct A-B contact, (2) functional or genetic interactions, and (3) the dynamics or stoichiometry of the interaction.

## Intuition

A binary edge is the smallest unit of interactome topology — two proteins that touch each other directly, without a shared scaffold. Treating PPIs as binary lets us model the cell as an undirected graph whose nodes are proteins and edges are detectable direct contacts.

## Formal notation

- Interactome graph G = (V, E), V = proteins, E ⊆ V × V binary contacts
- Binary edge (A, B) ∈ E iff A and B are detected to interact directly in ≥1 assay
- Note: the edge definition is *assay-conditioned*; different assays give different E with different biases.

## Variants

- **Stable binary contact**: high-affinity, long-lived interaction (e.g., obligate heterodimer).
- **Transient binary contact**: short-lived signaling or enzyme-substrate contact.
- **Conditional binary contact**: interaction that occurs only under specific cell state, PTM, or localization.
- **Y2H-detectable binary contact**: detectable when both proteins fold and meet in the yeast nucleus — a strict subset of true binary contacts.

## Comparison

- vs. **complex membership (co-complex association)**: two proteins co-purified in a complex via AP-MS may not be in direct binary contact; binary PPI is the strictly more granular relation.
- vs. **functional / genetic interaction**: genetic-interaction edges (synthetic lethality, suppression) reflect pathway relations, not necessarily physical contact.
- vs. **interolog**: a binary PPI inferred for an organism by orthology from a known PPI in a model organism, without direct experimental verification.

## When to use

- Reasoning about direct physical signaling paths, allosteric regulation, and compound binding-pocket competition.
- Building ground-truth scaffolds for graph algorithms (community detection, centrality, hub analysis).
- Generating disease-associated candidate PPIs for follow-up validation.

## Known limitations

- Each binary-PPI assay (Y2H, co-AP, MAPPIT, LUMIER, etc.) has its own bias profile; "binary PPI" is operationally defined by which assay confirmed the edge.
- A single positive call is not a guarantee of physiological relevance — co-affinity purification or orthogonal validation typically applies.
- The boundary between "transient" and "non-existent" binary contact is fuzzy and assay-dependent.

## Open problems

- A generally accepted gold-standard human binary-PPI set still does not exist; literature-curated sets are inspection-biased and high-throughput sets are noisy.
- Linking binary-PPI maps to higher-order complex architecture and to context (cell type, PTM, localization) remains open.

## Key papers

- [[towards-proteome-scale-map-human-protein]] — operationalized "binary PPI" via stringent high-throughput Y2H + co-AP verification at the human proteome scale.

## My understanding

"Binary PPI" is best treated as an *assay-conditioned* edge label rather than a single biological truth. Combining Y2H, AP-MS, and proximity labeling via consensus produces a more robust working interactome than any single assay, because each assay's bias profile is partially complementary.
