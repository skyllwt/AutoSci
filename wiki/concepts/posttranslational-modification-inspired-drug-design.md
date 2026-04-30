---
title: "Posttranslational Modification Inspired Drug Design (PTMI-DD)"
aliases: ["PTMI-DD", "PTM-inspired drug design", "PTM-isoform-targeted drug design"]
tags: [drug-design, posttranslational-modification, ptm-isoforms, allosteric-inhibitor, covalent-inhibitor, protac, protein-protein-interaction, precision-medicine]
maturity: emerging
key_papers: ["[[drug-design-targeting-active-posttranslational-modification]]"]
first_introduced: "2020-12 (Meng, Liang, Zhao, Luo — Med Res Rev 2021;41:1701)"
date_updated: 2026-04-30
related_concepts: []
---

## Definition

**Posttranslational Modification Inspired Drug Design (PTMI-DD)** is a drug-design paradigm in which the target is the disease-relevant *PTM-modified isoform* of a protein rather than the wild-type protein itself. By exploiting the chemistry, conformation, PPI behaviour, or degradation pathway that the PTM creates, PTMI-DD aims to extend the intersection of chemical space and biological space and to deliver inhibitors with higher selectivity than conventional active-site competitors.

## Intuition

Biological space is small — only ~667 unique human protein efficacy targets are exploited by approved drugs, against ~20,000 candidates in the druggable genome. PTMs act as a multiplier on that biological space: a single gene can give rise to many functionally and structurally distinct isoforms (phospho-, methyl-, acetyl-, ubiquityl-, palmitoyl-, glycosyl-, myristoyl-, ...). Many of these isoforms are disease-specific. Aiming a drug at the disease-specific isoform — rather than the housekeeping wild-type — both expands the addressable target list and naturally improves selectivity by leaving the unmodified protein unperturbed.

## Formal notation

PTMI-DD is a strategic framework rather than a formal model. Loosely, given a wild-type target T and a PTM-modified isoform T*_m (where m denotes the modification, e.g. p-Tyr705-STAT3, K27me3-EZH2, myr-ABL1, palm-PD-L1), PTMI-DD seeks a ligand L such that

- affinity(L, T*_m) >> affinity(L, T), achieved via:
  - covalent ligation at a non-conserved residue exposed by the PTM,
  - binding to a pocket induced/stabilised by the PTM (e.g. ABL1 myristoyl pocket),
  - disruption or stabilisation of a PTM-dependent PPI interface,
  - recruitment of an E3 ligase to T*_m for proteasomal degradation (PROTAC mode).

## Variants

The paper enumerates four operational variants:

- **Covalent PTMI-DD** — small-molecule electrophile reacts with a residue made accessible or distinctive by the PTM context (e.g. cysteine-targeted kinase inhibitors such as ibrutinib).
- **Allosteric / induced-pocket PTMI-DD** — the PTM creates or stabilises a pocket absent on the unmodified protein; the canonical example is asciminib (ABL001) at the myristoyl pocket of Bcr-Abl.
- **PTM-PPI PTMI-DD** — the PTM is the recognition mark for a partner protein (e.g. methyl-K9 on H3 read by HP1γ; phospho-Tyr read by SH2 domains); inhibitors disrupt the PTM-driven interaction.
- **PTM-degrader PTMI-DD** — bifunctional degraders (PROTACs) recruit an E3 ligase (CRBN/VHL/MDM2/IAP) specifically to the PTM-isoform, hijacking the ubiquitin–proteasome system to degrade an otherwise undruggable target.

## Comparison

- vs. **conventional structure-based drug design (SBDD)** — SBDD targets the static wild-type pocket; PTMI-DD additionally conditions on the post-translational chemistry and resulting conformational ensemble, so it can target proteins SBDD considers undruggable (e.g. small GTPases like RhoA).
- vs. **fragment-based drug design (FBDD)** — orthogonal: FBDD asks how to grow a ligand into a pocket; PTMI-DD asks which pocket (the PTM-isoform's) to grow into.
- vs. **allosteric drug design** — PTMI-DD is a strict superset when the allosteric pocket is created or gated by a PTM; otherwise allosteric design is PTM-agnostic.

## When to use

- Disease biology implicates a specific PTM-isoform of a protein (e.g. Y705-phospho-STAT3, K27-methylated H3 by EZH2, palmitoylated PD-L1).
- Structural or dynamics evidence shows the PTM creates a distinct pocket, surface, or PPI interface.
- Selectivity over the wild-type (and over close paralogs) is mandatory for safety — common in oncology, autoimmunity, and neurodegeneration.

## Known limitations

- Many PTMs are transient and labile; experimental characterisation of the modified-state structure is hard.
- ML predictors of PTM sites do not (yet) predict the resulting conformational ensemble, which is what determines druggability.
- Some PTM-isoforms are present at low stoichiometry; cellular target engagement assays are difficult to design.
- Outside the CRBN/VHL/MDM2/IAP set, the catalogue of E3 ligases practically usable for PROTAC-style PTM degraders is small.

## Open problems

- Prospective nomination of druggable PTM-isoforms from sequence + PTM-site predictions, without expensive HTS.
- Generalising AlphaFold-class structural predictors to PTM-conditioned states.
- Building benchmark sets that score PTM-isoform vs. wild-type selectivity in cells, not just in biochemical assays.
- Expanding the usable E3 ligase set for PTM-targeted degradation.

## Key papers

- [[drug-design-targeting-active-posttranslational-modification]] — Meng et al., 2021. Coins PTMI-DD and lays out the four-strategy framework.

## My understanding

PTMI-DD is currently more useful as a vocabulary than as a generative algorithm: it labels a class of mechanism-of-action stories (asciminib, EZH2 inhibitors, PROTACs targeting CRBN-recruitable PTM-isoforms) that already exist, and gives medicinal chemists a checklist for where selectivity can come from. The interesting open frontier is making it prospective — predicting which PTM-isoform of a given disease driver will yield a tractable pocket — which puts PTM-site predictors and PTM-conditioned structure predictors squarely on the critical path.
