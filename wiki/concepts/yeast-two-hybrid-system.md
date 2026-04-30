---
title: "Yeast two-hybrid system"
aliases: [Y2H, yeast two-hybrid, Gal4 two-hybrid assay]
tags: [protein-protein-interaction, molecular-biology, screening-assay, interactome]
maturity: stable
key_papers: [towards-proteome-scale-map-human-protein]
first_introduced: "Fields & Song, 1989"
date_updated: 2026-04-30
related_concepts: [binary-protein-protein-interaction, ccsb-hi1-human-interactome-v1]
---

## Definition

The yeast two-hybrid (Y2H) system is a genetic assay that detects pairwise physical interactions between two proteins (a "bait" X and a "prey" Y) by reconstituting the function of a transcription factor — classically Gal4 — in *Saccharomyces cerevisiae*. The bait is fused to the Gal4 DNA-binding domain (DB-X) and the prey to the Gal4 activation domain (AD-Y). Physical contact between X and Y reassembles a functional transcription factor and turns on selectable reporter genes (e.g., GAL1::HIS3, GAL1::lacZ).

## Intuition

Two halves of a transcription factor that cannot meet on their own can be brought together only if the proteins they hang from physically interact. The yeast cell becomes a programmable detector: growth on selective media or color change reports binding.

## Formal notation

- DB-X = Gal4 DNA-binding-domain - bait fusion
- AD-Y = Gal4 activation-domain - prey fusion
- Reporter R(X, Y) = ON iff X and Y physically interact within the yeast nucleus

## Variants

- **High-throughput Y2H** (e.g., Rual et al. 2005): Gateway-cloned ORFeome libraries, mated in 96-well plates against pools of 188 AD-Y preys, with multiple reporter genes and plasmid-shuffling counter-selection against auto-activators.
- **Cytoplasmic / split-ubiquitin Y2H**: variants for membrane and cytoplasm-localized proteins where Gal4-based nuclear assays fail.
- **One-vs-all matrix Y2H**: each bait individually screened against every prey.
- **Mating-based pooled Y2H**: bait haploid cells mated with prey-pool haploids to combinatorially generate diploid test populations.

## Comparison

- vs. **co-affinity purification / co-IP**: Y2H detects binary contacts in vivo in a heterologous host; co-AP detects associations from the native cell lysate but cannot distinguish direct from indirect binding.
- vs. **AP-MS (affinity purification - mass spectrometry)**: AP-MS recovers complexes at proteome scale but is biased toward stable, abundant interactors; Y2H captures more transient binary contacts.
- vs. **proximity labeling (BioID, APEX)**: proximity labeling reports neighborhoods rather than direct contacts, with different biases on transient interactions.

## When to use

- Building proteome-scale binary interactome scaffolds where direct binary (not complex) contacts are the question.
- Discovering candidate disease-associated PPIs as hypotheses for downstream validation.
- Screening domain or mutant variants against curated prey libraries.

## Known limitations

- Heterologous host context: not the protein's native cellular environment; post-translational modifications and partner availability may differ.
- Under-representation of integral membrane proteins (Gal4-based nuclear readout cannot reach them without specialized variants).
- Auto-activator baits and "sticky" preys produce false positives without aggressive counter-selection.
- Reproducibility of any single Y2H pass is ~50-60%; multiple independent screens are needed for high recall.

## Open problems

- How to most efficiently combine Y2H, AP-MS, and proximity labeling to converge on a "ground-truth" human interactome?
- Can Y2H variants be engineered to recover transmembrane and lipid-bilayer-resident interactions at scale?

## Key papers

- [[towards-proteome-scale-map-human-protein]] — high-throughput Y2H over the human ORFeome v1.1, producing CCSB-HI1.

## My understanding

Y2H is best regarded as a high-throughput hypothesis generator, not a proof of physiological interaction. Its value as an interactome-mapping primitive is that, when run with stringent multi-reporter selection and orthogonal verification, the technical false-positive rate is low enough for population-level statistical analyses to surface biological signal even though any individual call is noisy.
