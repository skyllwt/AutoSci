# `/exp-design` — bio-shaped block output (dose_response + negative_control + cross_context)

> **EXAMPLE OUTPUT** — Representative `/exp-design` block output for a follow-up validation experiment on the `ptm-aware-degrader-target-nomination` idea, generated 2026-05-18 as **demonstration material** for the BAAI Agent for Science 2026 submission (video / poster).
> The experiment described below is **planned** (not yet in `wiki/experiments/`); the bio statistical defaults shown are real (see `.claude/skills/exp-design/SKILL.md` lines 115–128, bio-C4 + bio-C6 minimal pilots merged 2026-05-12).

---

## Idea anchor

`wiki/ideas/ptm-aware-degrader-target-nomination.md` (status `in_progress`, GRADE `low`, 8 linked experiments). Phase-0 → Phase-2 already designed (8 experiments). This output proposes the **Phase-3 wet-lab validation block** that completes the in-silico → wet-lab handover.

## Step 1 — Wet-lab gate evaluation

Run wet-lab dependency detection (bio-C5 minimal pilot, 14-signal-word heuristic) over the idea body:

```
Signals matched: ['cell killing', 'IC50', 'phospho-PROTAC', 'BCL-XL', 'experimental degraders']  (5/14)
Wet-lab dependency: HIGH
→ Plan at least one block with setup.in_silico_or_wet: wet_lab
```

## Step 2 — Block-type selection

Active block-type tags for this experiment (multiple allowed per bio-C4 minimal pilot):

- **B. validation** (A–D core type) — headline number is "does top-ranked candidate kill the cell at predicted concentration?"
- **G. dose_response** — biological continuous gradient on PROTAC concentration; expected shape is sigmoidal with hook effect plateau at high concentrations
- **E. negative_control** — sham (scrambled phospho-degron) PROTAC must NOT kill
- **H. cross_context** — orthogonal cell line check (HeLa primary readout + K562 cross-context)

## Step 3 — Statistical defaults routing (bio-C6 minimal pilot)

Routing table application:

| Branch | Match? | Why |
|---|---|---|
| `n_test >= 50` → ≥ 3 random seeds (ML default) | **No** | Wet-lab assay, n_test is the number of PROTACs tested, not a CV fold count |
| `n_test < 50` → bootstrap CI + stratified k-fold | **No** | Same reason — this is wet-lab, not in-silico CV |
| `n_test < 10` → LOO-CV | **No** | Same |
| **Wet-lab assay** → ≥ 3 **biological** × ≥ 3 **technical** replicates with explicit labelling | **YES** | This is the assay branch (`setup.in_silico_or_wet: wet_lab`) |

→ `setup.random_seed_protocol` is **N/A for wet-lab block**. Replication semantics are biological × technical; record explicitly.

## Step 4 — Designed experiment block (frontmatter excerpt)

```yaml
title: "Phase-3 dose-response validation — top-3 ΔpTernary-ranked phospho-BCL-XL PROTACs vs sham"
slug: "phase3-dose-response-phospho-bclxl-protacs"
tags: [validation, dose_response, negative_control, cross_context, wet_lab]
linked_idea: [[ptm-aware-degrader-target-nomination]]
linked_paper: [[deepternary-2025]]

setup:
  dataset: "Top-3 candidates from Phase-2 ΔpTernary ranking + 3 sham PROTAC controls (scrambled phospho-degron); n_test = 6"
  in_silico_or_wet: "wet_lab"
  species: ["human"]
  cell_line: "HeLa"            # primary readout
  assay_type: "viability"       # CellTiter-Glo 2.0 (Promega G9241), 72h endpoint
  force_field: null             # N/A for wet-lab
  solvent_model: null           # N/A for wet-lab
  simulation_length: null       # N/A for wet-lab
  weight_version: null          # N/A for wet-lab
  random_seed_protocol: null    # N/A for wet-lab — see replicate counts below

dose_response:
  variable: "PROTAC concentration"
  concentrations_nM: [0.1, 1, 10, 100, 1000, 10000]
  expected_shape: "sigmoidal IC50 with possible hook-effect plateau at >= 1000 nM (PROTAC hallmark)"
  fit_model: "4-parameter logistic (top, bottom, IC50, Hill slope)"

replication:
  biological_replicates: 3       # 3 independent cell-passage thaws, ≥ 1 week apart
  technical_replicates: 3        # 3 wells per (PROTAC × concentration × replicate) cell
  total_wells: 324               # 6 PROTACs × 6 concs × 3 bio × 3 tech
  vehicle_control: "0.1% DMSO matched to highest-concentration vehicle dose"
  positive_control: "Lenalidomide 10 µM (CRBN-recruiter benchmark, expected IC50 ≈ 30 nM on phospho-BCL-XL HeLa per [[lenalidomide-clinical-trial]])"
  negative_control_PROTACs: 3    # scrambled-phospho-degron variants of the top-3 candidates

cross_context:
  orthogonal_cell_line: "K562"   # human chronic myeloid leukemia — different lineage from HeLa cervical cancer
  rationale: "BCL-XL dependence varies by lineage; K562 is BCL-XL-addicted (per [[bcl-xl-cancer-dependency]]). Cross-context block tests whether ΔpTernary-ranked top hits hold across cell lines, ruling out HeLa-specific cofactor confounds."

reproducibility:
  rrid:
    - "AB_2536179"      # anti-BCL-XL antibody (downstream Western)
    - "AB_2782939"      # CRBN antibody (engagement check)
  cellosaurus:
    - "CVCL_0030"        # HeLa (CCLE / Cellosaurus canonical entry)
    - "CVCL_0004"        # K562 (CCLE / Cellosaurus canonical entry)
  addgene: []             # no plasmid distribution for this assay
  pdb_versions: []        # no structure ref for the assay block (Phase-2 already cited)
  dataset_versions: []    # wet-lab block — generates new data, doesn't consume a dataset version

estimated_cost:
  gpu_hours: 0
  cpu_hours: 8                # only data analysis post-assay
  md_wallclock_hours: 0
  wet_lab_usd: 5800           # CellTiter-Glo (~$1600) + PROTAC synthesis ($2800 for 3 sham + 3 hit) + media/plasticware (~$1400)
  fte_weeks: 3                # 1 wk synthesis QC + 1 wk assay + 1 wk analysis
  dataset_access_lead_time_days: 0
```

## Step 5 — Pre-registration analysis plan

**Primary metric**: Δlog(IC50) = log10(IC50_sham) − log10(IC50_top-ranked). A positive Δlog(IC50) ≥ 0.5 (i.e. top-ranked is at least 3.16× more potent than sham) on **≥ 2 of the 3 top-ranked candidates** is the success criterion. Bootstrapped 95% CI on Δlog(IC50) per candidate via case-resampling of the 9 replicate measurements (3 bio × 3 tech) at each concentration.

**Failure-mode pre-registration** (per `failure_taxonomy` extension under design):
| Failure type | Symptom in this assay |
|---|---|
| `negative-control-fail` | Sham PROTACs also show IC50 < 1 µM → ΔpTernary ranking is non-specific |
| `dose-range` | All candidates flat-line (no sigmoidal fit) within 0.1–10000 nM → outside assay window |
| `cross-context-fail` | HeLa shows hit, K562 does not → cell-line-specific confound, not BCL-XL-dependent |
| `dataset-version-mismatch` | N/A (no dataset version consumed) |
| `species-mismatch` | N/A (single species, human) |

## Step 6 — `/exp-eval` verdict path on completion

When the wet-lab data arrives, `/exp-eval` will (per skill spec):
- Lift `ptm-aware-degrader-target-nomination.status` from `in_progress` → `validated` if ≥ 2 of 3 top candidates pass primary metric AND all 3 negative controls fail (sham IC50 > 10 µM)
- Lift `linked_idea` connected concept `posttranslational-modification-inspired-drug-design` maturity: `hypothesis` → `well-supported`
- Write a new graph edge: `phase3-dose-response-...` → `crbn` with type `wet_lab_validated`, `confidence: high`
- If any negative_control fires, set `failure_reason` and route through `failure_taxonomy = negative-control-fail`; idea status → `failed`

---

## Why this matters for the contest framing

1. **Multi-agent / vertical-specialized** — Block-type selection (Step 2) is bio-domain code (`negative_control` / `dose_response` / `cross_context` are not generic ML block types); statistical defaults routing (Step 3) is bio-specific (wet-lab biological × technical replicates ≠ ML random seeds). Both pieces of `/exp-design` are vertical-specialized agent behaviour.
2. **Reproducible** — Every reproducibility ID slot is filled: 2 `CVCL_*` Cellosaurus IDs, 2 `AB_*` RRIDs, explicit positive and vehicle controls with cited benchmarks. A reviewer reading the experiment page can in principle re-order reagents and reproduce.
3. **Self-evolving** — `/exp-eval`'s verdict path (Step 6) writes back into idea status, concept maturity, and graph edges; future `/ideate` runs see the validated state.

---

## Reproducibility Footer

```
/exp-design ptm-aware-degrader-target-nomination --add-block dose_response,negative_control,cross_context
Wet-lab gate evaluation: HIGH (5/14 signal words matched)
Block types added:        validation + dose_response + negative_control + cross_context
Statistical defaults:     wet-lab branch → 3 biological × 3 technical replicates
Total wells designed:     324  (6 PROTACs × 6 concs × 3 bio × 3 tech)
Estimated cost:           $5800 + 3 FTE-weeks  (per A6 structured cost block)
Wiki writes (planned):    1 experiment page + 2 graph edges (linked_idea, linked_paper)
                          + Cellosaurus / RRID lookup deferred to /exp-run pre-flight
Wiki log:                 not written (design only; /exp-run will log when ready)
```

---

## See also

- [`bio-novelty-report.md`](bio-novelty-report.md) — `/novelty` 5-channel verification
- [`bio-ideate-banlist.md`](bio-ideate-banlist.md) — `/ideate` Phase-3 scope-overlap filter
- Anchor idea: [`../../wiki/ideas/ptm-aware-degrader-target-nomination.md`](../../wiki/ideas/ptm-aware-degrader-target-nomination.md)
- Existing Phase-0..2 experiments: 8 entries under `wiki/experiments/` (see idea's `linked_experiments` list)
- Skill spec: `.claude/skills/exp-design/SKILL.md` §3 (bio-C4 + bio-C6 minimal pilots)
