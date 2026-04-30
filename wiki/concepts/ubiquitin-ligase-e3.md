---
title: "Ubiquitin ligase (E3)"
aliases: ["E3 ubiquitin ligase", "E3 ligase", "E3", "ubiquitin protein ligase"]
tags: [ubiquitin, post-translational-modification, enzyme, cancer, drug-target]
maturity: stable
key_papers: [ubiquitin-ligases-oncogenic-transformation-cancer-therapy]
first_introduced: ""
date_updated: 2026-04-30
related_concepts: [ubiquitylation]
---

## Definition

An ubiquitin ligase (E3) is the third and substrate-selecting enzyme of the ubiquitylation cascade. After an E1 activates ubiquitin in an ATP-dependent manner and an E2 receives it as a thioester, an E3 brings substrate and E2~Ub together and catalyzes formation of an isopeptide bond between ubiquitin's C-terminal glycine and a substrate lysine (or, less commonly, an N-terminus, cysteine, serine or threonine). The human genome encodes roughly 600–700 E3s, providing the substrate specificity that the small E1/E2 pool lacks.

## Intuition

E1s and E2s are generic activation/transfer machinery; E3s are the addressing system that decides *which* protein gets the ubiquitin tag, *which lysine* on that protein, and *what kind of chain* gets built. By controlling tag identity (mono-, multi-mono-, K48, K63, K11, K6, K27, K29, K33, M1) E3s route the substrate to one of several fates: proteasomal degradation, lysosomal/autophagic clearance, altered subcellular localization, signalling complex assembly, transcriptional response. Most cellular regulation that passes through ubiquitylation flows through this addressing layer, which is why E3s are over-represented among cancer drivers and drug targets.

## Formal notation

Three structural classes:

- **HECT E3s** — receive ubiquitin from E2 onto an active-site cysteine, then transfer to substrate (two-step, covalent intermediate).
- **RING E3s** — bind E2~Ub and substrate simultaneously and catalyze direct E2-to-substrate transfer without a covalent intermediate. Includes monomeric RINGs (CBL, MDM2) and the cullin–RING ligase (CRL) superfamily.
- **RBR E3s** (RING-Between-RING; for example parkin, HOIP) — RING1 recruits E2~Ub, an active-site cysteine in RING2 receives ubiquitin (HECT-like), then transfers to substrate.

Cullin–RING ligases (CRLs) are modular: a cullin scaffold (CUL1–CUL5, CUL7, CUL9), a small RING-box protein (RBX1/RBX2), an adaptor, and a substrate receptor. The SCF complex (SKP1–CUL1–F-box protein) uses ~70 different F-box proteins (FBXW7, SKP2, β-TRCP, FBXL2, FBXO4 …) as interchangeable substrate receptors. CRL3 uses BTB-domain adaptors (for example SPOP). CRL2/CRL5 use VHL-box / SOCS-box receptors (including pVHL itself).

## Variants

- **MDM2** — RING E3, primary ligase for p53; oncogene when overexpressed.
- **BRCA1–BARD1** — RING heterodimer; tumour suppressor; mediates K6-linked and non-degradative ubiquitylation in DNA damage response.
- **SCF–FBXW7** — substrate receptor for cyclin E, MYC, mTOR, c-Jun, Notch; tumour suppressor.
- **SCF–SKP2** — substrate receptor for p27KIP1, p21, FOXOs; oncogene; mediates K63-linked AKT activation in some contexts.
- **CRL3–SPOP** — context-dependent (tumour suppressor in nucleus, oncogene in cytoplasm).
- **CRL2–VHL** — substrate receptor for HIF-α; classical tumour suppressor; reused as PROTAC recruiter.
- **APC/C** with CDC20 or CDH1 coactivators — anaphase-promoting complex; mitotic regulator.
- **parkin (PARK2)** — RBR E3; regulates mitophagy; tumour suppressor in cancer, neuroprotective in Parkinson disease.
- **NEDD4** — HECT E3; degrades RAS and PTEN; context-dependent role in cancer.

## Comparison

E3s differ from kinases — the other major regulatory enzyme class — in that the modification (ubiquitin) is itself a folded protein domain that can be elaborated into chains of varying topology, each read by distinct ubiquitin-binding domains. A single E3 acting on a single substrate can produce mono-, K48-, or K63-linked products with completely different downstream consequences. Inhibitors must therefore consider not just the E3 but the chain topology and reader proteins.

E3s differ from DUBs (deubiquitylating enzymes) in that DUBs remove the modification; the steady-state ubiquitylation of any substrate reflects the balance of E3 and DUB activity, and DUBs are an emerging drug-target class in their own right.

## When to use

Invoke this concept when describing any substrate-specific protein degradation or non-degradative ubiquitylation event, when discussing PROTAC/molecular-glue degrader strategy, when analyzing cancer driver lists for ubiquitin-system mutations (FBXW7, VHL, BRCA1, SPOP, MDM2 amplification), and when reasoning about post-translational regulation of cell cycle, DNA damage response, or oncogenic signalling.

## Known limitations

- E3 substrate networks are large, overlapping, and incompletely mapped, making "inhibit E3 X to stabilize substrate Y" predictions unreliable in cancers expressing alternate ligases for the same substrate.
- Chain-topology readout depends on cellular UBD-containing readers whose roles are still being characterized.
- Many E3 substrate receptors have no known small-molecule ligand, limiting direct E3 inhibition; PROTAC discovery is biased toward the small set of E3s with available ligands (VHL, cereblon, MDM2, IAP).
- Pseudo-E3 activity (catalytically dead E3s that act as scaffolds, for example BRCA1 mutants) confounds genetic separation of ligase and structural roles.

## Open problems

- What rules govern substrate-receptor exchange within cullin–RING ligases, and how does inhibiting one receptor reroute cullin activity to others?
- Can substrate-selective E3 inhibitors be developed that target a single E3–substrate axis without globally perturbing the E3?
- Which of the ~600 human E3s are productively recruitable into PROTAC-style ternary complexes?
- How is non-degradative ubiquitylation (K63, K11, mono-Ub) dynamically remodelled in tumours, and which arms are druggable?

## Key papers

- [[ubiquitin-ligases-oncogenic-transformation-cancer-therapy]] — Senft, Qi & Ronai, Nat Rev Cancer 2018; consolidated review of E3 deregulation in cancer.

## My understanding

For ΩmegaWiki the E3 concept is the unifying mechanism connecting cancer biology, drug design, and structural biology of protein–protein interactions. It is the substrate of choice for any future research thread that asks "how do we degrade an undruggable target" (PROTACs), "why does a tumour suppressor fail in this cancer" (FBXW7, BRCA1, VHL, SPOP), or "how does a post-translational mark route a protein to a fate" (chain topology, UBD readers).
