# `/ideate` Phase-3 Filter — Banlist Scope-Overlap Demo

> **EXAMPLE OUTPUT** — Representative `/ideate` Phase-3 filter trace for two candidate ideas evaluated against the wiki's current banlist on 2026-05-18.
> Generated as **demonstration material** for the BAAI Agent for Science 2026 submission (video / poster).
> The two candidate ideas below are **synthetic** (not yet in wiki/); the failed-idea banlist entry (`ptm-site-disorder-predictor`) is real.
> Behavior follows `.claude/skills/ideate/SKILL.md` Phase 3 — specifically the **bio-C3 minimal pilot scope-overlap rule** merged in commit `05e1b8b`.

---

## Active Banlist Entry (under test)

From `wiki/ideas/ptm-site-disorder-predictor.md` (status `failed`, resolved 2026-04-30):

```yaml
failure_reason: |
  [filter] saturated by SAPP (2025), PhosAF (2024), GraphPhos (2025), AstraPTM2 (2025),
  DeepPCT (2024), MTPrompt-PTM (2025) — 'AlphaFold structural features as input to PTM
  site predictor' is a published axis with at least five 2024-2025 entries.

scope:
  species: [human, mouse]
  disease_area: []
  data_regime: high_data
```

This banlist entry says: **"don't pitch any more AF-features → PTM-site classifier on human/mouse phospho corpora — that subspace is saturated."** It does **not** block plant PTM, microbial PTM, or cross-species low-data work.

---

## Candidate A — `arabidopsis-phospho-site-predictor-cross-species-transfer` ✅ **PASS**

> "A pLDDT + ESM-2 sequence-context classifier for phosphorylation sites in **Arabidopsis thaliana**, trained on phospho-Arabidopsis (PhosPhAt 4.0 corpus, ~30k sites) and **cross-species fine-tuned** from a human-mouse pre-trained backbone."

**Phase 3 inferred scope** (from hypothesis + tags + origin_gaps):

```yaml
scope:
  species: [arabidopsis]
  disease_area: []
  data_regime: low_data    # PhosPhAt 4.0 << dbPTM/PhosphoSitePlus
```

**Banlist match procedure** (per SKILL.md Phase 3, rule (a)–(d)):

| Check | Banlist entry | Candidate | Overlap? |
|---|---|---|---|
| (a) Empty/missing scope on banlist? | No (explicit scope set) | — | No universal block |
| (b) `scope.species` intersection | `[human, mouse]` | `[arabidopsis]` | **∅ (empty)** |
| (c) `scope.disease_area` intersection | `[]` (empty either side) | `[]` | Either-side-empty → not a sufficient overlap signal alone |
| (d) `scope.data_regime` match | `high_data` | `low_data` | **Mismatch** |

**Verdict**: rule (b) species intersection is empty **AND** rule (d) data_regime differs → scopes do **not** overlap → candidate is **not eliminated**.

**IDEA_REPORT note**:

> `scope-distinct prior detected` — `ptm-site-disorder-predictor` (failed) cited as relevant context but does NOT block this candidate. Reasoning: failed entry covers human-mouse high-data phospho prediction (saturated by SAPP / PhosAF / GraphPhos et al.); this candidate targets Arabidopsis low-data cross-species transfer, which is **not** in any of those tools' training corpora.

→ Candidate **proceeds to Phase 4 deep validation**.

---

## Candidate B — `plddt-aware-human-phospho-classifier-v2` ❌ **REJECT**

> "A pLDDT + flanking-sequence classifier for **human/mouse phosphorylation sites**, fine-tuned on dbPTM + PhosphoSitePlus with a new cross-attention head over AlphaFold pLDDT trajectories."

**Phase 3 inferred scope**:

```yaml
scope:
  species: [human, mouse]
  disease_area: []
  data_regime: high_data
```

**Banlist match procedure**:

| Check | Banlist entry | Candidate | Overlap? |
|---|---|---|---|
| (b) `scope.species` intersection | `[human, mouse]` | `[human, mouse]` | **`[human, mouse]` (non-empty)** |
| (c) `scope.disease_area` intersection | `[]` | `[]` | Either-side-empty (default OK) |
| (d) `scope.data_regime` match | `high_data` | `high_data` | **Match** |

**Verdict**: rule (b) species overlaps fully **AND** rule (d) data_regime matches → scopes **fully overlap** → candidate is **eliminated**.

**IDEA_REPORT note**:

> `banlist hit: ptm-site-disorder-predictor (scope-matched)` — proposed approach is a methodological variant of an axis already saturated by 6 published 2024-2025 tools. Adding a "cross-attention head over pLDDT trajectories" is incremental and would land inside SAPP / PhosAF ablation tables. **Recommend abandoning** this candidate and redirecting effort to either (i) PTM-conditioned ensemble prediction or (ii) PTM-aware degrader nomination (both currently `in_progress` / `validated` in wiki).

→ Candidate **written to wiki as status `failed`** with `failure_reason` and `scope` populated. Phase 4 skipped.

---

## Why this matters for the contest framing

This demo proves **three** competition framing claims simultaneously:

1. **Self-evolving** — Every failed idea (Candidate B writes itself in as `failed`) becomes part of the banlist that constrains the *next* `/ideate` run. The wiki grows its own anti-repetition memory.
2. **Multi-agent / vertical-specialized** — The scope-overlap algorithm encodes **bio domain knowledge** (species, disease_area, data_regime are not generic ML scope dimensions). This is `bio-C3 minimal pilot` — committed 2026-05-12, file [`wiki/ideas/ptm-site-disorder-predictor.md`](../../wiki/ideas/ptm-site-disorder-predictor.md) line 21–24.
3. **Reproducible** — The scope match is **deterministic boolean intersection logic**, not LLM judgment. Re-running this `/ideate` filter against the same banlist and same two candidates always produces the same accept / reject outcome.

---

## Reproducibility Footer

```
/ideate "PTM site prediction with structural features" --max-ideas 5
Phase 3 (first-pass filter) against banlist:
  Active banlist size: 2 failed ideas
    - ptm-site-disorder-predictor (scope: human-mouse high_data phospho)
    - <one more, omitted from this demo>
  Candidates considered: 5
  Eliminated by scope-matched banlist: 1  (Candidate B-like)
  Passed scope check, advanced to Phase 4: 4  (Candidate A-like + 3 others)
Phase 5 wiki writes:
  status=proposed: 4 (advanced to Phase 4 validation)
  status=failed:   1 (Candidate B — failure_reason + scope written for future banlist)
Wiki log:         appended "ideate | 1 candidate rejected at scope-overlap"
```

---

## See also

- [`bio-novelty-report.md`](bio-novelty-report.md) — sibling example showing the `/novelty` pipeline (Source A–F multi-channel verification)
- [`bio-exp-design-dose-response.md`](bio-exp-design-dose-response.md) — `/exp-design` bio statistical default block
- Live banlist source: [`wiki/ideas/ptm-site-disorder-predictor.md`](../../wiki/ideas/ptm-site-disorder-predictor.md)
- Skill spec: `.claude/skills/ideate/SKILL.md` Phase 3 (bio-C3 minimal pilot)
