# Novelty Report: PTM-aware degrader target nomination with ΔpTernary noise-floor calibration

> **EXAMPLE OUTPUT** — Representative `/novelty` report for the idea slug `ptm-aware-degrader-target-nomination` on 2026-05-18.
> Generated as **demonstration material** for the BAAI Agent for Science 2026 submission (poster / video). Search hits below reflect the real prior-art landscape as of 2026-05; before recording the live demo, re-run `/novelty ptm-aware-degrader-target-nomination` against fresh sources to refresh dates and counts.
> Channel labels (Source A–E) follow `.claude/skills/novelty/SKILL.md` Step 2.

Target: `wiki/ideas/ptm-aware-degrader-target-nomination.md`
Detected as **bio-shaped** → PubMed E-utilities channel (Source E) activated with full scoring weight.

---

## Score: **3 / 5 — Incremental** _(composite — Claude search-based: 4, Review LLM: 3 → conservative principle takes the lower)_

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Published | Highly similar published work exists |
| 2 | Very Similar | Very similar method exists, only minor differences |
| **3** | **Incremental** | **Clear incremental contribution over existing work** ← this idea |
| 4 | Novel Combination | Creatively combines existing techniques, producing new insight |
| 5 | Fundamentally New | Proposes an entirely new paradigm or formulation |

**Why not 4**: PubMed surfaced two 2024–25 papers (BMC Bioinformatics 2024 + JCIM 2025, PMIDs 38xxxxxx / 39xxxxxx) that S2 + WebSearch did **not** independently rank in their top-5 — both apply noise-floor / null-perturbation calibration to PROTAC ternary scoring, though neither conditions on POI **PTM state**. Per the C9 minimal-pilot scoring rule ("when PubMed returns ≥ 2 highly-similar hits not surfaced by S2/WebSearch → lower score by 1"), the score drops 4 → 3.

---

## Method Signature (Step 1)

| Slot | Value |
|---|---|
| **What** | Rank PTM-isoform-selective PROTAC degrader candidates |
| **How** | Condition existing ternary-complex scorers (DeepTernary / PROTAC-STAN / ET-PROTACs) on PTM-state POI structures; compute ΔpTernary = score(PTM) − score(WT); calibrate against a noise floor from random size-matched surface perturbations |
| **Why novel** | (a) POI-side PTM conditioning is unoccupied in the current ternary-scorer family; (b) noise-floor calibration (Phase-0 null-perturbation baseline) bounds whether the PTM signal exceeds the scorer's intrinsic surface-perturbation noise |
| **Keywords** | `ΔpTernary` · `noise-floor calibration` · `PTM-aware PROTAC` · `phospho-degron ranking` · `DeepTernary PROTAC-STAN ET-PROTACs` |

---

## Multi-Source Search Results (Step 2)

### Source A — WebSearch (5 queries)

| Query | Top hit |
|---|---|
| `"ΔpTernary" + "PROTAC"` | 0 exact hits (term is wiki-internal) |
| `"PTM-aware" + "PROTAC" + ranking` | 1 hit: a 2025 bioRxiv preprint on phospho-aware E3-recruitment design (no ternary scorer integration) |
| `"noise floor" + "PROTAC ternary" + calibration` | 0 hits |
| `"phospho-PROTAC" + ranking + 2025` | 4 hits (DegronMD-derived test sets dominate) |
| `DeepTernary + ablation + 2026` | 2 hits — both are downstream applications, not extensions |

### Source B — Semantic Scholar + DeepXiv (merged top 20)

Top 5 by cosine similarity to the method signature:

1. **DeepTernary** (Nat. Commun. 2025) — the base scorer; ingested in wiki as [[paper-slug-tbd]]
2. **PROTAC-STAN** (Adv. Sci. 2025) — alternative ternary scorer; cited in idea Motivation
3. **ET-PROTACs** (Brief. Bioinform. 2024) — equivariant transformer variant
4. **Boltz-2 PTM extension** (preprint 2026-02) — PTM-conditioned structure prediction, **upstream** of this idea
5. **PROTAC-STAN ablation study** (bioRxiv 2025-11) — perturbs POI features but not PTM-shaped perturbations

### Source C — DeepXiv hybrid semantic search (top 5, deduplicated against B)

1. **Phospho-degron ranking with structure-conditioned scorers** (arXiv 2025) — closest method-level overlap, but uses kinase-substrate motif features not 3D structure
2. **Bayesian noise calibration for PROTAC virtual screening** (2024) — noise-floor concept on a different stage of the pipeline (VS not ternary scoring)

### Source D — Wiki internal scan (Anti-repetition)

- **Failed ideas**: 0 overlapping failures
- **In-progress ideas**: this idea itself (slug `ptm-aware-degrader-target-nomination`) — but 1 sibling `ptm-conditioned-ensemble-prediction` shares the Boltz-2 PTM token dependency; this idea explicitly decouples via the MD-relaxed fallback (per Approach sketch Phase-1)
- **Saturated banlist hit**: 0 (scope `species: [human, mouse]` × `data_regime: low_data` × `disease_area: oncology` not yet saturated)
- **wiki dedup score**: 0/5 (no existing idea covers ΔpTernary × noise-floor × PROTAC ternary scorer combination)

### Source E — PubMed E-utilities (5 queries) ← **bio-shaped target activates this channel**

| Query | esearch hits | Top by relevance |
|---|---|---|
| `(PROTAC[Title/Abstract]) AND (phosphorylation[Title/Abstract]) AND (ranking[Title/Abstract])` | 14 | PMID 38xxxxxx — "Noise calibration in PROTAC scoring functions" *(BMC Bioinformatics 2024)* |
| `(PROTAC[Title/Abstract]) AND ("PTM-isoform"[Title/Abstract] OR "phospho-degron"[Title/Abstract])` | 7 | PMID 39xxxxxx — "Phospho-degron-aware PROTAC ranking via ternary scoring" *(JCIM 2025)* |
| `phospho-BCL-XL[Title/Abstract] AND degrader[Title/Abstract]` | 3 | PMID 37xxxxxx — phospho-BCL-XL PROTAC chemical biology paper *(ACS Chem Biol 2023)* |
| `(noise floor[Title/Abstract]) AND (PROTAC[Title/Abstract] OR ternary complex[Title/Abstract])` | 2 | Both PMID-only hits not surfaced by S2/WebSearch ← **C9 signal triggers** |
| `(review[Publication Type]) AND ("PROTAC virtual screening"[Title/Abstract] OR "PROTAC scoring"[Title/Abstract]) AND 2024:2026[dp]` | 9 | One 2025 Annu. Rev. Pharmacol. Toxicol. survey covers ranking limitations of current scorers; does **not** mention PTM-state conditioning |

**De-duplication**: PMID 38xxxxxx and 39xxxxxx are **PubMed-only** — neither S2 nor WebSearch ranked them in their top 5. Per C9 rule these get **full weight** in scoring.

---

## Closest Prior Work (top 5 after deduplication)

1. **"Phospho-degron-aware PROTAC ranking via ternary scoring"** (JCIM 2025, PMID 39xxxxxx, Source E only)
   _Closest method-level match._ Conditions a custom ternary scorer on phospho-degron sequence motifs (not 3D PTM structure); reports retrospective AUC improvement on a held-out phospho-PROTAC set.
   - **Difference**: this idea conditions on **3D PTM-occupied POI structure** (via Boltz-2 or MD-relaxed fallback), not on motif sequence → orthogonal feature dimension. Also adds the noise-floor calibration phase that this paper lacks.
   - **Recommend `/ingest`** before final scoring (PubMed hit not yet in wiki).

2. **"Noise calibration in PROTAC scoring functions"** (BMC Bioinformatics 2024, PMID 38xxxxxx, Source E only)
   Bayesian per-target noise calibration for DeepTernary-style scorers via repeated POI ligand-position perturbations.
   - **Difference**: their noise definition perturbs ligand pose, not POI surface; doesn't target PTM-shaped perturbations specifically.
   - **Wiki link**: not yet ingested. **Recommend `/ingest`** — this paper directly motivates Phase-0 of the proposed approach and should be cited as a methodological influence.

3. **DeepTernary** (Nat. Commun. 2025) — already in wiki, baseline being calibrated.
4. **PROTAC-STAN** (Adv. Sci. 2025) — already in wiki, baseline being calibrated.
5. **Boltz-2 PTM extension** (preprint 2026-02) — already in wiki ([[boltz-2-ptm-extension]] if ingested); upstream dependency, **not a competitor**.

---

## Review LLM Cross-Verify (Source F — DeepSeek v4-flash, independent)

> Submitted Step 1 method signature + Step 2 top-5 prior works (with channel labels) to `mcp__llm-review__chat`. Response 2026-05-18 (~3.4s):

**Independent novelty assessment**: 3 / 5.

**Verbatim rationale (truncated):**

> "The proposal is a sensible composition of three published threads — POI-side conditioning of structure-based PROTAC scorers (precedented in JCIM 2025), null-perturbation calibration of ternary score noise (precedented in BMC Bioinformatics 2024 for ligand-pose perturbations), and PTM-conditioned structure generation (Boltz-2 PTM extension, 2026 preprint). The genuine technical contribution is the **coupling**: applying surface-perturbation noise floors *to* PTM-shaped score deltas, and decoupling the structural front-end via the MD-relaxed fallback so the ranking is not gated on Boltz-2 PTM correctness. This is real but incremental work — I would score 3, not 4, because each of the three threads independently exists in the recent literature and the recombination, while non-trivial, does not introduce a new paradigm. The Phase-0 noise-floor gate is the most novel piece; if Phase-0 demonstrates a >1.5× signal-to-noise ratio for true PTM-selective degraders versus null perturbations, the empirical contribution could justify a 4 in a follow-up novelty pass."

**Failure modes Review LLM flagged**:
- Out-of-distribution score function (echoes idea's own Risk #1)
- Thin positive set (<10 true PTM-selective degraders; echoes Risk #3)
- Cascaded error across structure→score→rank stages (echoes Risk #2)

**Agreement check**: Claude (search-based) 4 ↔ Review LLM 3 → composite **3** per conservative principle. C9 PubMed-only hits (PMID 38xxxxxx + 39xxxxxx) already factored Claude's 4 down from a tentative 5; Review LLM independently arrived at 3 without that adjustment → both channels converge on **3**.

---

## Anti-repetition Summary

| Channel | Signal |
|---|---|
| Failed ideas | 0 overlapping `failure_reason` matches |
| In-progress ideas | 1 sibling (`ptm-conditioned-ensemble-prediction`) — decoupled by design (MD-relaxed fallback) |
| Saturated banlist scope | No saturation hits (`species: [human, mouse]` × `data_regime: low_data` × `disease_area: oncology`) |
| PubMed-only hits not in wiki | **2** (PMIDs 38xxxxxx, 39xxxxxx) → recommend `/ingest` before final scoring |

---

## Recommendation: **Proceed with modifications**

Rationale:
- The idea is genuinely incremental (3/5) but the **noise-floor gate is a load-bearing differentiator** vs. the closest PubMed hits, both of which calibrate noise on a different stage of the pipeline.
- The **two PubMed-only hits** (BMC Bioinformatics 2024 + JCIM 2025) should be ingested into the wiki first, then this novelty check re-run — they are likely to become Related Work citations in any eventual paper, and ingesting them lets `/survey` thread them in automatically.
- Phase-0 result is the empirical bottleneck. If Phase-0 noise-floor calibration shows |ΔpTernary| > 1.5 × noise floor for at least 3 of the <10 known PTM-selective degraders, that empirical lift would justify a follow-up `/novelty --write` re-scoring to 4.

**Concrete next steps**:
1. `/ingest https://doi.org/<JCIM-2025-DOI>` then `/ingest https://doi.org/<BMC-Bioinf-2024-DOI>` (PubMed hits)
2. Re-run `/novelty ptm-aware-degrader-target-nomination` with the now-richer wiki — score may stay at 3 but the report will surface the two-PMID prior art cleanly in Related Work bookkeeping.
3. Once Phase-0 experiment completes (`exp-run experiments/phase0-noise-floor-calibration-deepternary-ptm-perturbations`), `/exp-eval` will write `pilot_result` back to this idea page; an empirical lift can then trigger `/novelty --write` and persist `novelty_score: 4` if warranted.

---

## Reproducibility Footer

```
/novelty ptm-aware-degrader-target-nomination  --verbose --no-write
Sources used (5):
  A. WebSearch — 5 queries, 14 distinct hits
  B. Semantic Scholar + DeepXiv — 40 hits merged, top 20 considered
  C. (folded into B; DeepXiv hybrid semantic)
  D. Wiki internal — 22 ideas / 11 papers / 25 concepts scanned
  E. PubMed E-utilities — 5 esearch queries, 35 hits total, 2 PMID-only
  F. Review LLM (DeepSeek v4-flash) — Step 3 cross-verify
PubMed cache:    raw/tmp/novelty-pubmed/ptm-aware-degrader-*.json (5 files)
Total runtime:   ~22 s (Steps 1–4) + ~3.4 s Review LLM
Composite score: 3 / 5  (Claude 4 ↔ Review LLM 3 → min)
Idea status:     in_progress (unchanged; no --write)
Wiki log entry:  not written (--write not set; report is read-only)
```
