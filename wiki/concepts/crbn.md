---
title: "CRBN (Cereblon)"
aliases: ["Cereblon", "CRL4-CRBN substrate receptor"]
tags: [e3-ligase, protac, ubiquitin-ligase, drug-discovery]
maturity: active
definition: "Substrate receptor of the CUL4-DDB1-CRBN (CRL4-CRBN) E3 ubiquitin ligase complex. Hijacked by PROTACs, IMiDs (thalidomide, lenalidomide, pomalidomide), and molecular glue degraders to recruit neo-substrates for proteasomal degradation."
key_papers: [ubiquitin-ligases-oncogenic-transformation-cancer-therapy]
first_introduced: "thalidomide tragedy (1957) — molecular target identified 2010 (Ito et al., Science)"
date_updated: 2026-05-11
related_concepts: [ubiquitin-ligase-e3, ubiquitylation, posttranslational-modification-inspired-drug-design]
linked_ideas: [ptm-aware-degrader-target-nomination]
# bio-A2 (light pilot 2026-05-11): protein-anchor fields filled because this concept IS a
# specific gene product (vs the class concept ubiquitin-ligase-e3 which keeps these empty).
gene_symbol: "CRBN"
uniprot_id: "Q96SW2"
pdb_ids: ["4CI1", "4CI2", "5HXB", "5FQD"]   # CRBN + IMiD / PROTAC ligand structures
species: ["human"]
---

## Definition

CRBN (Cereblon) is the substrate-recognition subunit of the **CRL4-CRBN E3 ubiquitin ligase complex** (Cullin-4A–DDB1–CRBN). Together with VHL, MDM2, and the IAP family, CRBN is one of the four "canonical" recruitable E3 ligases that current PROTAC and molecular-glue drug-discovery campaigns target.

The relevance to this wiki: every PROTAC ternary-complex predictor benchmarked in [[ptm-aware-degrader-target-nomination]] (DeepTernary, PROTAC-STAN, ET-PROTACs) is trained on the [[ternarydb]] CRBN+VHL subset, and CRBN-anchored degraders dominate that subset (≈80% bias per the idea's risk analysis).

## Intuition

CRBN's natural function is to mark damaged or short-lived substrate proteins with K48-linked polyubiquitin chains, flagging them for proteasomal degradation. Drug discovery hijacks this by tethering a small molecule that **binds CRBN's tri-tryptophan pocket** (IMiD-like glutarimide handle) to a second small molecule that **binds a target of interest (POI)** — induced proximity drags the POI into CRBN's substrate position, causing its ubiquitylation and degradation.

This is the same mechanism the **`binds` edge from [[posttranslational-modification-inspired-drug-design]] → [[ubiquitin-ligase-e3]]** captures at the class level; CRBN is the specific instance of that class.

## Variants

- **Wild-type CRBN** — canonical sequence used by all current ternary-complex scorers.
- **CRBN^Y384A** — clinical-resistance mutation that disrupts IMiD binding; bypasses many CRBN-based degraders.
- **CRBN domain truncations** (TBD, LON, CULT) — research tools; not currently in TernaryDB.

## Comparison

| Feature | CRBN | VHL | MDM2 |
|---|---|---|---|
| Ligand class | IMiD (thalidomide-like glutarimide) | VH032 / VHL-1 / VHL-2 | Nutlin-like / Idasanutlin |
| Recruitment pocket | Tri-tryptophan pocket | HIF-1α hydroxylysine surface | p53 transactivation domain |
| Substrate-receptor scaffold | CUL4-DDB1 | CUL2-Elongin-B/C | RING domain |
| Coverage in [[ternarydb]] | ~50% of CRBN+VHL subset | ~50% | absent |

## When to use

CRBN should be **the recruited E3** in degrader design when:
- The POI lacks a tractable VHL-recruitment surface
- The desired half-life is short (CRBN-mediated degradation is typically faster than VHL-mediated for matched ligands)
- A clinically-validated IMiD ligand (lenalidomide, pomalidomide) is acceptable as the E3-binding handle

## Known limitations

1. **CRBN^Y384A clinical resistance** — emerges in multiple myeloma after IMiD therapy; degraders sharing the same E3-recruitment ligand class share this vulnerability.
2. **CRBN expression heterogeneity** — varies across cell lines and tissues, so cellular degradation potency does not always track ternary-complex affinity.
3. **Coverage bias in training data** — [[ternarydb]] inherits the ~80% CRBN/VHL bias from PROTAC-DB; extending degrader design to non-canonical E3 ligases requires going outside the current ternary-complex scorer training distribution.

## Open problems

- **PTM-isoform-selective CRBN-PROTAC ranking** — the load-bearing premise of [[ptm-aware-degrader-target-nomination]]. CRBN-trained ternary scorers do not see POI PTM state, so they cannot distinguish wild-type vs phospho-occupied substrate surfaces. Phase-0 noise-floor calibration ([[phase0-noise-floor-calibration-deepternary-ptm-perturbations]]) is the gating experiment.

## Key papers

This concept page's `key_papers` list is currently anchored on [[ubiquitin-ligases-oncogenic-transformation-cancer-therapy]] (the only paper in this wiki that explicitly discusses E3 ligases as oncogenic targets and PROTAC substrates). Future ingest of dedicated CRBN structural / mechanistic papers — Ito et al. 2010 (thalidomide-CRBN identification, Science), Fischer et al. 2014 (CRBN-IMiD crystal structure, Nature), the DeepTernary paper (Nat. Commun. 2025) — will extend this list.

## My understanding

CRBN is the most clinically-validated recruitable E3 in the PROTAC universe (lenalidomide / pomalidomide as anchors), but its substrate selectivity is **PTM-blind** in current compute pipelines. Closing that gap is the central wager of the PTM-aware degrader pipeline. The CRBN-Y384A resistance pattern is a useful sanity check: any degrader campaign that does not survive a CRBN^Y384A robustness experiment is gating its claim on the wild-type CRBN pocket and risks the same clinical-resistance escape as legacy IMiDs.
