---
title: "Drug design targeting active posttranslational modification protein isoforms"
slug: "drug-design-targeting-active-posttranslational-modification"
arxiv: ""
venue: "Medicinal Research Reviews"
year: 2021
tags: [drug-design, posttranslational-modification, ptm-isoforms, allosteric-inhibitor, covalent-inhibitor, protac, protein-protein-interaction, precision-medicine]
importance: 3
date_added: 2026-04-30
source_type: tex
s2_id: ""
keywords: [PTMI-DD, allosteric inhibitor, covalent inhibitor, posttranslational modifications, precision medicine, PROTAC protein degradation, protein-protein interactions, PTM protein isoforms, rational drug design]
domain: "Computational Drug Design / Chemical Biology"
code_url: ""
cited_by: []
---

## Problem

Modern drug discovery is bottlenecked by the small intersection of an almost-infinite chemical space (>10^60 molecules with MW < 500 Da) and a small, discrete biological space (only ~667 unique human protein efficacy targets among ~20,000 druggable genome candidates; only ~7% of biological space has been probed by small molecules). Within that limited space, achieving high selectivity for a wild-type-like target is very hard: poor selectivity drives off-target toxicity and is a leading reason for clinical drug attrition. Existing strategies for expanding pharmacological space (DOS, BIOS, DEL, target fishing, allosteric pocket mining) have helped but cannot overcome the fundamental scarcity of distinct, druggable, disease-specific binding modes.

## Key idea

Treat post-translational modification (PTM) protein isoforms as a first-class, disease-specific extension of the biological target space, and design drugs against them. The authors coin **Posttranslational Modification Inspired Drug Design (PTMI-DD)**: a framework that targets the active, disease-relevant PTM-modified isoform of a protein rather than its wild-type counterpart. Because PTM isoforms (i) carry distinct chemistry at the modified site, (ii) often exhibit altered conformations or new pockets, (iii) participate in PTM-dependent PPIs, and (iv) can be redirected to the ubiquitin–proteasome system, they offer four concrete bridges between chemical and biological space and naturally yield more selective drugs that spare normal-state proteins.

## Method

The paper is a review/position piece structured around four PTMI-DD strategies and the supporting computational/experimental scaffolding:

1. **Covalent inhibition by mimicking PTMs** — design electrophilic warheads that recapitulate the PTM bond on the same residue (e.g., cysteine-targeted Bruton's tyrosine kinase inhibitor ibrutinib), achieving long residence time and high selectivity by reacting with non-conserved residues.
2. **Targeting PTM-induced novel binding sites** — use structural and dynamics methods (X-ray, NMR, MD, elastic network models, normal mode analysis, Markov state models, protein structure networks) to find pockets that only appear or become druggable on the PTM-isoform; case in point is the asciminib (ABL001) myristoyl pocket of Bcr–Abl.
3. **Targeting PTM-induced PPIs** — disrupt or stabilize protein–protein interfaces whose binding is contingent on a PTM (e.g., methylated H3K9–HP1γ, phosphotyrosine-mediated SH2/PTB interactions), often via small-molecule PPI modulators or peptide-mimetic stapled peptides.
4. **PTM-driven targeted protein degradation** — exploit ubiquitin-proteasome system bifunctional degraders (PROTACs) that recruit E3 ligases (CRBN, VHL) specifically to the PTM-isoform, removing previously "undruggable" disease drivers.

The paper surveys the supporting toolchain: PTM databases (PhosphoSitePlus, dbPTM, UniProt PTM list with 676 PTM types), ML-based PTM-site predictors (incl. CNN/DCNN/SVM/HMM approaches and MusiteDeep-class methods), structural-dynamics simulations, and case studies from kinases (CDK2, ABL1, HER2), epigenetic writers (EZH2, SMYD2, G9a, BET, HDAC), checkpoint receptors (PD-1/PD-L1 palmitoylation/glycosylation), and small GTPases (RhoA).

## Results

This is a synthesis paper, not an empirical benchmark. Key qualitative results highlighted:

- The authors used PTMI-DD reasoning to identify a covalent inhibitor of RhoA, a long-considered "undruggable" target whose disease-relevant isoform is amenable to covalent ligation at a non-conserved cysteine.
- Statistical analysis of modified vs. unmodified PDB chains shows N-glycosylation and phosphorylation induce significant but non-extreme structural changes (with phosphorylation having larger effects).
- PTMs can drive disorder-to-order transitions (phospho-Ser/Thr, mono/di/tri-methyl-Lys, sulfotyrosine, 4-carboxy-Glu, 4-hydroxy-Pro), creating new ordered surfaces that are druggable.
- Concrete clinical wins of the framework: asciminib (ABL001, allosteric Bcr-Abl, Phase III positive); tazemetostat (first-in-class EZH2 inhibitor, FDA-approved 2020 for epithelioid sarcoma); HDAC inhibitors vorinostat/romidepsin/belinostat/panobinostat for T-cell lymphomas; thalidomide-class CRBN binders (PROTAC precursors) for myeloma; BET inhibitors (Mivebresib, CC-90010, Molibresib) in oncology trials.

## Limitations

- Identifying de novo allosteric pockets on PTM-isoforms still requires expensive HTS plus functional follow-up; computational pocket detection is suggestive, not predictive at scale.
- PTMs are transient and labile, complicating crystallography, NMR, and MS characterization; dynamic PTM effects are poorly captured by current ML predictors, which mostly classify sites without modeling the resulting conformational ensembles.
- The framework leans heavily on success stories; it does not quantify a base rate for how often a given PTM yields a tractable isoform-selective drug.
- Coverage of PROTAC-style PTM degradation is conceptual; the catalogue of PTM-aware E3 ligases that can be hijacked specifically (vs. CRBN/VHL alone) is small.
- The review is heavily small-molecule focused; antibody and biologic approaches to PTM isoforms are surveyed only briefly.

## Open questions

- Can ML methods that currently predict PTM sites be extended to predict the resulting conformational ensembles, allosteric couplings, and emergent druggable pockets, in a way that can drive PTMI-DD prospectively rather than retrospectively?
- How to systematically expand the set of E3 ligases usable for PTM-isoform-selective PROTACs beyond the CRBN/VHL/MDM2/IAP canon?
- What are the right benchmarks for PTM-isoform selectivity in cellular contexts (vs. wild-type counterpart) so that PTMI-DD candidates can be triaged early in lead optimization?
- Can structurally-resolved PPI networks (e.g., from AlphaFold-class models) be filtered for PTM-dependent interfaces to nominate PTMI-DD targets at scale?

## My take

The PTMI-DD framing is a useful organizing principle for an existing collection of mechanism-of-action stories — covalent inhibitors, allosteric isoform inhibitors, PTM-PPI disruptors, and PROTACs — but its real value is downstream rather than upstream: it tells medicinal chemists where to look for selectivity once a PTM-isoform is implicated in disease. The bottleneck the paper does not solve is the prospective one: nominating, from sequence and PTM site data alone, which PTM isoforms will yield a tractable pocket. That is exactly where PTM-site predictors (MusiteDeep family) and isoform-aware structural models (AlphaFold-class methods conditioned on PTMs) should plug in, and the paper effectively maps out the demand side of that future workflow. For our medpredict thread, this paper is the best argument for treating PTM-aware structure prediction as a drug-discovery primitive, not just a biology curiosity.

## Related

- [[posttranslational-modification-inspired-drug-design]]
- [[ptm-protein-isoforms-enable-selective-drug]]
