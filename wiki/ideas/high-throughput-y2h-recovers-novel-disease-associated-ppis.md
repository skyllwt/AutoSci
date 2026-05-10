---
title: "Stringent high-throughput Y2H recovers many novel disease-associated human PPIs at low inspection bias"
slug: "high-throughput-y2h-recovers-novel-disease-associated-ppis"
status: validated
origin: "Migrated from claims/high-throughput-y2h-recovers-novel-disease-associated-ppis on 2026-05-10 (was status: supported, confidence: 0.8); see Pilot results for original paper-level evidence."
origin_gaps: []
tags: [protein-protein-interaction, interactome, yeast-two-hybrid, disease-genetics]
priority: 3
pilot_result: ""
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
---

## Motivation

*Migrated from former claim. The original assertion is preserved as the Hypothesis below; the paper-level evidence that supported it is preserved under Pilot results.*

## Hypothesis

A stringent high-throughput yeast two-hybrid screen of cloned human ORFs, when verified by an orthogonal binary-binding assay (co-AP) on a representative sample, can produce a binary-PPI dataset that (a) is comparable in technical reliability to literature-curated interactions, (b) carries substantially less inspection bias, and (c) surfaces a large fraction of novel candidate disease-associated PPIs not previously co-mentioned in the literature.

**Scope and conditions.** - Requires multi-reporter Y2H phenotype selection plus plasmid-shuffling auto-activator counter-selection; weaker pipelines (single reporter, no auto-activator filter) do not necessarily inherit the same false-positive properties.
- Requires orthogonal binary verification on a representative sample to estimate the technical false-positive rate before claims about novelty are credible.
- Applies to soluble proteins detectable in the yeast nucleus; integral membrane proteins and assemblies needing native PTM context remain underrepresented.
- "Novelty" was estimated via co-occurrence search in PubMed and Google Scholar at 2005 publication time and may decay as later annotations import these very edges back into the literature.

## Approach sketch

*Empirical finding migrated from a former claim — supporting evidence is paper-level / review-level rather than experiment-level. See Pilot results.*

## Expected outcome

*N/A — this idea was migrated as a validated empirical finding, not as a new prospective hypothesis.*

## Risks

- The CCSB-HI1 network does not exhibit the high clustering coefficient predicted by "small world" claims for sparser model-organism interactome maps; this leaves open the possibility that biological-attribute enrichment is driven by hubs and degree, not by the full network being uniformly biologically meaningful.
- ~55% within-screen reproducibility means a single run misses many true edges and randomly recovers some near-noise edges; novelty estimates conditioned on a single screen are noisier than conditioned on a multi-pass union.

**Open questions.**

- Does the same novelty / reliability profile hold when the protocol is extended toward the full human ORFeome (subsequent HI-II / HuRI releases)?
- What is the in-vivo physiological-relevance rate of "novel disease-associated PPIs" surfaced by this protocol (i.e., do they map onto genuine disease biology when followed up in cells / animal models)?
- Can structurally resolved PPI prediction (AlphaFold-driven) further filter Y2H-derived disease candidates by predicted interface plausibility?

## Pilot results

- CCSB-HI1 (Rual et al. 2005, [[towards-proteome-scale-map-human-protein]]): 2,754 binary edges, 1,549 proteins, 424 OMIM-associated edges of which 352 (~83%) are novel by literature search.
- Co-AP verification rates: ~78% (Y2H-only), ~81% (Y2H ∩ LCI), ~62% (LCI-only) — Y2H-only edges are at least as reliable as LCI-only edges.
- CCSB-HI1 edges are enriched for shared GO annotation, shared upstream regulatory motifs, shared mouse phenotypes, and correlated mRNA expression vs. random Space-I pairs (P < 6e-20 for GO terms).

## Lessons learned

*To be filled in as downstream experiments reference this finding.*
