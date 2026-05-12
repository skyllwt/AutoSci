# Bio-Adaptation Changelog (EN)

> Cumulative changelog for the bio-adaptation effort. Each entry tracks one item from
> `docs/bioinformatics-adaptation-backlog.en.md`. Entries are append-only.
>
> All changes are written to **mirror copies** under `docs/bio-adaptation/` and **do not touch the
> originals**. Once an item is adopted, the mirror hunk is merged back to its source-of-truth file
> and the corresponding changelog entry is marked `STATUS: merged`.
>
> Mirror layout:
> - `docs/bio-adaptation/section-a/runtime-page-templates.en.md` ↔ source `docs/runtime-page-templates.en.md`
> - `docs/bio-adaptation/section-a/runtime-page-templates.zh.md` ↔ source `docs/runtime-page-templates.zh.md`
> - `docs/bio-adaptation/section-a/CLAUDE.md` ↔ source `i18n/en/CLAUDE.md` (root `CLAUDE.md` is then synced via `./setup.sh --lang en`)
>
> Annotation convention used inside mirrors:
> - YAML blocks: `# bio-A{n}: <one-line rationale>`
> - Markdown body: `<!-- bio-A{n}: <one-line rationale> -->`

Mirror to its zh counterpart: `docs/bio-adaptation/CHANGELOG.zh.md`. Substantive edits must be applied to both.

---

## 2026-05-03 — Section A drafted (A1–A8)

**Scope**: schema-only changes to page templates and the runtime entrypoint. No skill behavior changed.
**Status**: drafted, not yet merged into sources of truth.
**Files written**:
- `docs/bio-adaptation/section-a/runtime-page-templates.en.md`
- `docs/bio-adaptation/section-a/runtime-page-templates.zh.md`
- `docs/bio-adaptation/section-a/CLAUDE.md`

### A1 — [P0] `datasets/` promoted to a first-class entity type

**Where**:
- `runtime-page-templates.{en,zh}.md`: added `### datasets/{slug}.md` template (frontmatter + body sections); promoted heading from "9 Page Types" to "10 Page Types"; added `datasets` to the type list.
- `CLAUDE.md`: same heading bump; added `wiki/datasets/` to the "main product surface" bullets; added two new rows to the Cross-Reference Rules table (papers→datasets, experiments→datasets); added a `[[ternarydb]]` example to the Link Syntax block; added a Constraints bullet declaring datasets first-class and naming the version-drift lint hook for C8.

**Why**: backlog item A1. Every prior `/exp-design` mention of TernaryDB / PROTAC-DB / DegronMD / AlphaFold-DB / PhosphoSitePlus / dbPTM / UniProt / PDB resolved to plain text — no wikilink target, no version field, no access tier. Without a first-class `datasets/` page, future bio ingests cannot anchor dataset references and `/exp-design` cannot fill `setup.dataset` with a wikilink.

**Unlocks**: `setup.dataset` becoming a wikilink (A5); the `dataset_versions` lint check (C8); `/exp-design`'s ability to surface lead-time for restricted-access cohorts (H3).

### A2 — [P1] Optional protein-anchor fields added to `concepts/` (light option)

**Where**: `runtime-page-templates.{en,zh}.md`, `concepts/{concept-name}.md` block. Added optional `gene_symbol`, `uniprot_id`, `pdb_ids`, `species` with comments noting that these are filled only when the concept *is* a specific gene product, and that promotion to a separate `proteins/` entity type is deferred until ≥50 such concepts accumulate.

**Why**: backlog item A2 explicitly recommends the light option first (extend `concepts/`) over the heavy option (a new `proteins/` entity type). Pages like p53, CRBN, VHL, MDM2 currently appear only as plain-text mentions; adding optional UniProt/HGNC anchors lets a concept page double as a protein record without yet creating a new entity type.

**Unlocks**: lint can validate UniProt accession format on these fields (C8); future graph queries like "papers targeting kinase X" can be written without a schema migration.

### A3 — [P0] `papers/` frontmatter extended with bio-native identifiers

**Where**: `runtime-page-templates.{en,zh}.md`, `papers/{slug}.md` block. Added `doi`, `pmid`, `biorxiv`, `pdb_ids`, `uniprot_ids`, `nct_ids`, `gene_symbols`, `species` alongside the kept `arxiv` field. Added a comment that `/ingest` should populate these from CrossRef / PubMed E-utilities / EuropePMC, not only Semantic Scholar.

**Why**: backlog item A3. Of the wiki's 11 papers, the 6 bio-related ones have no arXiv ID — their canonical identifiers are DOI/PMID. The CS-shaped frontmatter forces every bio paper to leave its real identifier in body text where it cannot be queried.

**Unlocks**: `/ingest` PubMed/EuropePMC fallback (C1); identifier-format lint (C8); cross-paper aggregation by gene/protein/structure.

### A4 — [P1] `domain` field documented as a controlled vocabulary

**Where**: `runtime-page-templates.{en,zh}.md`, `papers/`, `ideas/`, `experiments/`, `claims/` blocks (all that carry `domain`). Inline YAML comment lists CS values (NLP / CV / ML Systems / Robotics) plus the recommended bio vocabulary (`structural-bio | chembio | comp-drug-discovery | cancer-bio | systems-bio | bioinformatics | clinical-translation`). Notes that lint enforcement is delegated to C8.

**Why**: backlog item A4. The current free-text `domain` field has drifted across pages (`Computational Drug Design / Chemical Biology`, `Cancer biology / Molecular oncology`, `Structural Bioinformatics`, …). Documenting a vocabulary now lets later writes converge without breaking older pages.

**Unlocks**: a `/check` enum-warning hook reusing the existing status-enum mechanism (C8); H6 (genomics-side vocabulary additions) can append to the same list without restructuring.

### A5 — [P0] `experiments/` setup extended with bio modality fields

**Where**: `runtime-page-templates.{en,zh}.md`, `experiments/{experiment-slug}.md` setup block. Added `in_silico_or_wet`, `species`, `cell_line`, `assay_type`, `force_field`, `solvent_model`, `simulation_length`, `weight_version`, `random_seed_protocol`. All optional; existing `model`, `dataset`, `hardware`, `framework` retained.

**Why**: backlog item A5. The current setup is pure-ML-pipeline shaped, so every bio specifics — force field, solvent model, simulation length, ML weight version, MD vs in-silico vs wet-lab status — has been written in body prose where downstream skills cannot reach it.

**Unlocks**: `/exp-design`'s ability to detect MD experiments and require `force_field` (C8); cost estimation that can ground itself in a real assay reference table (A6 + `docs/bio-compute-references.md`).

### A6 — [P1] `estimated_hours` deprecated in favor of structured `estimated_cost` block

**Where**: `runtime-page-templates.{en,zh}.md`, `experiments/{experiment-slug}.md`. Marked `estimated_hours` deprecated (kept zero default for backward compat). Added `estimated_cost` block with `gpu_hours`, `cpu_hours`, `md_wallclock_hours`, `wet_lab_usd`, `fte_weeks`, `dataset_access_lead_time_days`. Added a Constraints bullet in `CLAUDE.md` formalising the deprecation. Mentioned the companion reference table at `docs/bio-compute-references.md` (not yet created — flagged as follow-up tooling work).

**Why**: backlog item A6 cites the F5 case (`ablation-boltz2-ptm-vs-md-relaxed-route`) where `estimated_hours: 12` undershot the real ~3000 GPU-h budget by ~250×. A single hours field has no way to distinguish GPU from CPU from MD wall-clock from wet-lab dollars from access lead time, so any guess is anchorless.

**Backward-compat plan**: legacy pages keep `estimated_hours: 0`; `/check` can warn (not error) when an experiment carries assay_type that implies MD or wet-lab but `estimated_cost.md_wallclock_hours == 0` and `estimated_cost.wet_lab_usd == 0`. Migration is opportunistic — no mass rewrite required.

**Unlocks**: realistic budget surfacing in `/exp-design`; H8 sequencing-cost extension can land on the same block.

### A7 — [P1] Claim evidence types and strength extended for bio

**Where**:
- `runtime-page-templates.{en,zh}.md`, `claims/{claim-slug}.md` `evidence` block. Extended the `type` enum with `wet_lab_validated`, `clinical_validated`, `mechanistic_basis`, `correlative`, `predicts`. Added optional `grade` field (`very-low | low | moderate | high`). Original `strength` (`weak | moderate | strong`) kept verbatim.
- `CLAUDE.md`: added a Constraints bullet enumerating both the base and extended type sets and noting the grade field.

**Why**: backlog item A7. A clinical-trial positive result and a single in-vitro assay are not the same evidence tier; mechanistic biochemistry (point-mutation abolishes activity) is qualitatively different from correlation. GRADE is the medical-domain standard for evidence certainty.

**Backward-compat plan**: `strength` retained; existing claim pages need no rewrite. `grade` is purely additive.

**Unlocks**: `/exp-eval` can write more discriminating evidence records; `/novelty` can weight bio claims by GRADE rather than a single confidence number (E3).

### A8 — [P2] Optional `reproducibility` block added to `experiments/`

**Where**: `runtime-page-templates.{en,zh}.md`, `experiments/{experiment-slug}.md`. Added optional `reproducibility` block with `rrid`, `cellosaurus`, `addgene`, `pdb_versions`, `dataset_versions` (list of `{dataset_slug, version, accessed_date}`). Skip when fully in-silico.

**Why**: backlog item A8. Even nominally in-silico experiments often consume wet-lab-derived data (V1 of `phase0-noise-floor-calibration-deepternary-ptm-perturbations` ingests phospho-PROTAC positives compiled from published assays). Without antibody RRIDs, cell-line CVCL IDs, plasmid IDs, and dataset version+date, "reproducible" is unverifiable.

**Unlocks**: the C8 lint that compares `reproducibility.dataset_versions[*].version` against `datasets/{slug}.versions[]` to catch silent dataset drift (depends on A1).

---

## Cross-cutting notes (apply to every item above)

- **No source files modified.** `docs/runtime-page-templates.en.md`, `docs/runtime-page-templates.zh.md`, and `i18n/en/CLAUDE.md` are untouched. The originals remain canonical until a follow-up commit promotes the mirror hunks.
- **No skill behavior changed.** Every A-section item is a schema or documentation change. C-section items (skill workflow) and B-section items (graph edge types) are still pending.
- **Bio-adaptation backlog statuses NOT updated.** Per the backlog's "Usage" section, marking items `STATUS: in progress` or `STATUS: done` requires editing the original `docs/bioinformatics-adaptation-backlog.{en,zh}.md`; per the user's instruction in this session those originals are not to be touched. When merging the mirror back, also update the backlog statuses in the same commit.
- **Follow-up tooling deferred (B/C/H sections).** Items that depend on Section A (C1 PubMed fallback, C8 bio-lint, H3 sequencing cohorts in `datasets/`) remain pending and will land in their own changelog entries.

---

## 2026-05-03 — Section B drafted (B1–B3)

**Scope**: graph edge type extension. Touches the graph-rules block in CLAUDE.md and the edge JSON schema documented in `runtime-support-files`. Does not change `tools/research_wiki.py` (tool implementation work is filed under follow-up).
**Status**: drafted, not yet merged into sources of truth.
**Files written**:
- `docs/bio-adaptation/section-b/CLAUDE.md`
- `docs/bio-adaptation/section-b/runtime-support-files.en.md`
- `docs/bio-adaptation/section-b/runtime-support-files.zh.md`

**Independent of Section A.** Both `section-a/CLAUDE.md` and `section-b/CLAUDE.md` are derived from the same source `i18n/en/CLAUDE.md` and target the same merge destination. Each contains only its section's hunks; merge them in order (A then B).

### Cross-cutting design choice — edge metadata layout

B2 (`clinical_trial_for {nct_id, phase}`, `fda_approved_for {indication, year}`, `validates_in_species {species}`) and B3 (`dataset_version_used {slug, version}`) introduce typed per-edge attributes that the existing edge JSON has no slot for. Two options were considered:

1. Promote each attribute to a top-level field on the edge JSON.
2. Group typed attributes inside a nested `metadata` object alongside `evidence`/`confidence`/`date`.

**Chosen: option 2 (nested `metadata`).** Reasons: (a) avoids name collisions with future top-level fields and with reserved JSONL/log fields; (b) edge readers that don't know about a given edge type can ignore `metadata` wholesale rather than learning each attribute key; (c) H9 (variant-disease, expression-outcome) will add more typed attributes (`odds_ratio`, `hazard_ratio`, `p_value`, `cohort`) — the same `metadata` slot absorbs them with no further schema growth.

Backward compatibility: edges without `metadata` remain valid; the field is purely additive.

### B1 — [P1] Bio relation edges added to the graph schema

**Where**:
- `CLAUDE.md`, Graph Rules block: edge enumeration restructured into category-grouped bullets (paper-paper / paper-concept / claim-experiment-provenance / **bio relation** / **validation-translation** / **dataset-version provenance**); B1 row lists `targets_protein`, `binds`, `inhibits`, `activates`, `degrades`, `phosphorylates`, `ubiquitinates`, `methylates`, `acetylates`, `is_substrate_of`. Added a `confidence` requirement bullet for the new relation edges.
- `runtime-support-files.{en,zh}.md`: edges.jsonl row updated; new "Edge type catalogue" table with per-edge endpoint/metadata/semantic columns lists every B1 verb.

**Why**: backlog item B1. Without these edge types, the graph cannot answer "which drugs target protein X", "which kinases phosphorylate substrate Y", "which E3 ligases ubiquitinate substrate Z" — they remain trapped in body prose. The PTM verbs are deliberately separated from generic functional verbs because PTM relationships frequently need their own graph traversals (substrate inference, modification-cascade reconstruction).

**Endpoint policy**: relation edges accept both `concept` (under A2's light protein-anchor extension) and a future `proteins/` entity type (A2 heavy option) as the protein endpoint. No schema change is needed when A2 escalates to heavy.

**Unlocks**: graph-side queries for drug-target / kinase-substrate / E3-substrate relationships; downstream PTM-cascade reasoning in `/ideate` and `/exp-design`.

### B2 — [P1] Validation / translation edges added

**Where**:
- `CLAUDE.md`, Graph Rules block: new edge category row listing `clinical_trial_for`, `fda_approved_for`, `validates_in_species`; bullet noting these carry typed `metadata`.
- `runtime-support-files.{en,zh}.md`: edge type catalogue rows specify required `metadata` keys (`nct_id`+`phase`, `indication`+`year`, `species`).

**Why**: backlog item B2. Statements like "asciminib has FDA approval for CML" or "tazemetostat is approved for epithelioid sarcoma" currently live as prose only. Without these edges, the graph cannot answer "which claims have an FDA-approved drug as evidence" or "which open trials test this mechanism" — exactly the queries a translational researcher needs.

**Edge JSON shape example** (in `runtime-support-files.en.md`):
```json
{"from": "claims/asciminib-cml-effective", "to": "concepts/asciminib", "type": "fda_approved_for",
 "evidence": "FDA Drug Approval Letter, Oct 2021", "confidence": "high", "date": "2026-05-03",
 "metadata": {"indication": "CML", "year": 2021}}
```

**Unlocks**: translational queries; eventual `/novelty` PubMed weighting that prefers approved-drug citations as anchors.

### B3 — [P2] Experiment-to-dataset-version provenance edge added

**Where**:
- `CLAUDE.md`, Graph Rules block: new bullet under the dataset-version edge category. Constraints section adds a new bullet making `dataset_version_used` mandatory whenever `experiments[*].setup.dataset` resolves to a `datasets/{slug}` page with non-empty `versions[]`. `/check` warns when missing or version drift.
- `runtime-support-files.{en,zh}.md`: edge type catalogue row specifies `metadata.version` (and optional `metadata.slug`).

**Why**: backlog item B3. TernaryDB v2 will exist eventually, and a Phase-0 noise floor calibrated against v1 stops being valid for v2. Without a `dataset_version_used` provenance edge, the graph cannot detect when an experiment's evidence anchors against a stale dataset snapshot.

**Cross-section dependency**: depends on A1 (`datasets/` entity type) and A8 (`reproducibility.dataset_versions` block, which is the source of truth for the `metadata.version` value).

**Unlocks**: C8 lint that compares `dataset_version_used` edges against `datasets/{slug}.versions[]`; `/exp-eval` can surface "this evaluation used dataset@v1 — check if v2 changes the verdict" prompts.

---

### A1 follow-up — `index.md` `datasets:` block (deferred)

While drafting Section B I noticed Section A under-specified one carry-over: the `index.md` schema in `docs/runtime-support-files.{en,zh}.md` does not list a `datasets:` block, even though A1 made `datasets/` a first-class entity type. Listed here to avoid losing the thread; **not patched in any Section-B mirror** (would muddle the section-by-section diff). When merging Section A back to the source-of-truth, also append `datasets:` to the index.md schema.

---

## 2026-05-03 — Section C Batch 1, partial (C1 only — `/ingest`)

**Scope**: skill workflow changes. C section is split into 3 batches given size; this entry covers Batch 1 step 1 (`/ingest`). Batch 1 also covers `/exp-design` (C4+C5+C6) which lands in the next response.
**Status**: drafted, not yet merged. **Bio-fetcher tools not yet built** — bio path degrades to existing S2+RSS until `tools/fetch_crossref.py`, `tools/fetch_pubmed.py`, `tools/fetch_europepmc.py`, `tools/fetch_biorxiv.py`, and `tools/extract_bio_ner.py` are implemented (filed as C1 follow-up tooling work; not in the current schema-and-doc effort).
**Files written**:
- `docs/bio-adaptation/section-c/skills/ingest/SKILL.en.md`
- `docs/bio-adaptation/section-c/skills/ingest/SKILL.zh.md`

### C1 — [P0] `/ingest` accepts bio identifiers; bio-aware fallback chain; bio NER pre-pass

**Where**:
- `Inputs` block: `source` enumeration extended to accept DOI / PMID / bioRxiv URL / PMC URL alongside arXiv URL / `.tex` / `.pdf` / INIT MODE handoff. `argument-hint` line in YAML frontmatter updated.
- `Wiki Interaction → Reads`: added `wiki/datasets/*.md` (depends on A1).
- `Wiki Interaction → Writes`: added conservative `wiki/datasets/{slug}.md` write rule (EDIT existing only; CREATE only when paper introduces a dataset and importance ≥ 4).
- `Wiki Interaction → Graph edges created`: added the B1 bio relation edge family (`targets_protein`, `binds`, `inhibits`, `activates`, `degrades`, `phosphorylates`, `ubiquitinates`, `methylates`, `acetylates`, `is_substrate_of`) — emitted only when source text gives a clear cue, with conservative confidence default.
- `Workflow → Step 1 (Resolve the source)`: added a new sub-step 3 detailing routing for DOI / PMID / bioRxiv / PMC. Each route resolves to a `canonical_ingest_path` under `raw/discovered/`.
- `Workflow → Step 2 (Paper identity and enrichment)`: added explicit fallback chain (sub-step 3): `CrossRef → PubMed E-utilities → EuropePMC → bioRxiv API → DeepXiv → Semantic Scholar` for bio-anchored inputs; CS path documented as `S2 → DeepXiv → CrossRef`. Sub-step 4 added: bio identifier extraction from structured metadata (CrossRef abstract subjects, PubMed MeSH, EuropePMC annotations) pre-populates A3 frontmatter fields. Stop-if-exists check (sub-step 2) extended to match on DOI / PMID / bioRxiv DOI.
- `Workflow → Step 3 (Write the paper page)`: shape-check now also sanity-checks DOI / PMID / PDB / UniProt format when populated (full lint deferred to C8).
- `Workflow → Step 4 (Concepts, claims, people)`: added new sub-step 1 (bio NER pre-pass) and new sub-steps 6–7 (dataset wikilink upgrade; bio relation edge extraction). NER profile defaults to `protein-drug`; H5 covers other profiles.
- `Workflow → Step 5 (paper-to-paper edges)`: bio path uses CrossRef + PubMed + EuropePMC for references/citations instead of S2; reference-match key extended to DOI / PMID.
- `Workflow → Step 6 (Topics and index)`: notes the `index.md` `datasets:` block is included once A1 follow-up lands.
- `Workflow → Step 8 (Report)`: report now surfaces metadata-channel winner, NER candidate accept/defer counts, dataset mentions deferred to `/edit`, and access-restricted DOI degradations.
- `Workflow → Step 9 (Optional discovery)`: `/discover` anchor key extended to `--doi` / `--pmid` (depends on C2).
- `Constraints`: bio-path artifacts persist under `raw/discovered/`; JATS XML treated equivalently to `.tex` for body extraction (XML > PDF > vision API); bio NER candidates respect the existing per-paper concept/claim caps.
- `Error Handling`: added bio-path fallback semantics (CrossRef/PubMed/EuropePMC/bioRxiv outage cascade), license-restricted DOI degrade-to-abstract behavior, and graceful skip when `extract_bio_ner.py` is unavailable.
- `Dependencies → Tools`: `add-edge` confidence requirement extended to B1 bio relation edges; `add-citation --source` enum extended with `crossref|pubmed|europepmc|biorxiv`. New "Planned bio-fetcher tools" subsection lists 5 not-yet-built scripts.
- `Dependencies → External APIs`: added CrossRef, NCBI E-utilities, EuropePMC, bioRxiv content API.

**Why**: backlog item C1. Of the 6 bio-related papers in this wiki, none have an arXiv ID — every one had to be coerced through an arXiv-shaped pipeline. The bio-canonical sources are PubMed/EuropePMC/bioRxiv, not Semantic Scholar. Without bio identifier routing, every future bio `/ingest` either fails to match the existing path or gets force-fit through `prepare_paper_source.py` with degraded enrichment.

**Cross-section dependencies**:
- A1 (`datasets/` entity) — needed for dataset wikilink upgrade and the `wiki/datasets/*.md` Reads/Writes rows.
- A3 (`papers/` bio identifier frontmatter) — needed so the new metadata channels have somewhere to write `doi`/`pmid`/`pdb_ids`/`uniprot_ids`/`nct_ids`/`gene_symbols`/`species`.
- B1 (bio relation edge types) — needed so Step 4 sub-step 7 can call `add-edge` with `targets_protein`/etc.
- C2 (`/discover` bio anchors) — needed for `--doi`/`--pmid` anchor key in Step 9; until C2 lands, fall back to title search.
- C8 (`/check` bio-lint) — owns full identifier-format validation that this skill only roughly sanity-checks.
- H5 (NER profiles per subdomain) — extends NER pre-pass beyond the default `protein-drug` profile; out of scope for C1 itself.

**Backward compatibility**: legacy arXiv-only ingest path is unchanged. Bio additions activate only when the source string matches a bio identifier shape, or when bio frontmatter fields end up populated. Graceful degradation at every new dependency.

**Adoption gate** — before merging this skill change to `i18n/en/skills/ingest/SKILL.md`:
1. A1 + A3 must be merged first (the writes have nowhere to go otherwise).
2. At minimum `tools/fetch_pubmed.py paper <pmid>` must be functional (the most-common bio identifier). The other fetchers can be staged.
3. `tools/extract_bio_ner.py` may be stubbed initially (returns empty list); bio NER pre-pass is allowed to no-op and the rest of the workflow continues.

### Pending in Batch 1 — `/exp-design` (C4 + C5 + C6)

Will be drafted in the next response. C4 (block taxonomy gains `negative_control | mechanism | dose_response | cross_context`); C5 (wet-lab vs in-silico routing in Step 1); C6 (bio statistical defaults — bootstrap CI / stratified CV / replicate semantics — added to Step 3 + Step 5 review prompt).

---

## 2026-05-03 — Materialised runnable folder + bio fetcher tools (out-of-band work)

**Out of the per-section batching above** the user requested a runnable bio-optimised fork plus the implementation of all bio fetcher tools so C1 can actually run, not just be drafted.

**Done**:
- Copied `/home/yukino/OmegaWiki/` → `/home/yukino/OmegaWiki_bioinfo_adaptation/` (146→147M); `.venv/` paths in 12 files rewritten via `sed`. Original `.venv` untouched.
- Promoted A1–A8 + B1–B3 + C1 mirror hunks to source-of-truth in the new folder; ran `setup.sh --lang en` to sync root `CLAUDE.md` and `.claude/skills/`.
- Implemented 5 new tools in the new folder's `tools/`: `fetch_pubmed.py`, `fetch_crossref.py`, `fetch_europepmc.py`, `fetch_biorxiv.py`, `extract_bio_ner.py`. All smoke-tested with real bio papers (AlphaFold Nature 2021 PMID 34265844 + DOI 10.1038/s41586-021-03819-2; Boltz-1 bioRxiv 10.1101/2024.11.19.624167).
- Extended `tools/_schemas.py`: `ENTITY_DIRS += ["datasets"]`; `CITATION_SOURCES += {crossref, pubmed, europepmc, biorxiv}`; 14 new edge type specs (B1×10 + B2×3 + B3×1) with `EDGE_METADATA_REQUIRED` keys.
- Extended `tools/research_wiki.py add-edge` with `--metadata key=value` (repeatable); writes nested `metadata` object on edge JSON; validates required keys per edge type.
- Wrote `BIOINFO_ADAPTATION_README.md` + `BIOINFO_ADAPTATION_CHECKPOINT.md` at the new folder root.

**Not done** (carried to next session):
- C section batches 1 finish (C4+C5+C6), 2 (C7/C8/C2/C9), 3 (C3/C10/C11)
- `tools/lint_bio.py` (C8 dependency)
- An actual end-to-end `/ingest` invocation in the new folder against a real bio identifier
- First `wiki/datasets/{slug}.md` page (e.g. TernaryDB)

**Session paused 2026-05-03.** Resume hook: `/home/yukino/OmegaWiki_bioinfo_adaptation/BIOINFO_ADAPTATION_CHECKPOINT.md`.



---

## 2026-05-04 — Section C Batch 1 finish (C4 + C5 + C6 — `/exp-design`)

**Scope**: skill workflow changes to `/exp-design`. Three backlog items bundled because they all touch the same SKILL.md and depend on each other (C4's new block types need C6's stat-protocol selector, C5's wet-lab branch creates a block whose stats must follow C6).
**Status**: drafted, not yet merged into source-of-truth.
**Files written**:
- `docs/bio-adaptation/section-c/skills/exp-design/SKILL.en.md`
- `docs/bio-adaptation/section-c/skills/exp-design/SKILL.zh.md`

### Cross-cutting design choices

- **Bio-conditional, not domain-mandatory.** The four new block types (E–H) and the bio statistical defaults activate when (a) the idea's `domain` matches A4's bio vocabulary **or** (b) the wet-lab keyword scan hits ≥1 anchor. CS ideas pass through with the legacy four-block taxonomy and `seeds_only` protocol unchanged. Reason: a bio-only switch by `domain` alone misses ideas whose `domain` is left blank (the dominant case in the current wiki) but whose Approach sketch obviously names cell-based assays.
- **`statistical_protocol` is now a required scalar, not an inferred attribute.** Made it a YAML field with four allowed values (`seeds_only | bootstrap_ci | stratified_kfold | replicate_matrix_BxT`) so `/exp-eval` and `/check` can both grep for it without re-deriving from `n_test`. Single source of truth for downstream consumers.
- **`--wet-lab yes|no|skip`** added as a user-owned flag so non-interactive callers (`/research`) can pre-answer the probe. Default in non-interactive mode is `skip` + report flag — never silently choose a scope downgrade. This matches CLAUDE.md's "user-facing skill parameters are user-owned" rule.
- **Stage-4 budget-cut order** fixed at `cross_context → robustness → dose_response`. Reason: dose-response yields the most quantitatively useful claim (EC50/IC50 with CI) per unit cost; cross-context generalisation is a scope claim that can be deferred to a follow-up paper without invalidating the current one.

### C4 — [P0] `/exp-design` block taxonomy gains four bio-natural types

**Where**:
- Description and intro: extended block-type list to include `negative_control | mechanism | dose_response | cross_context` alongside the legacy four.
- Step 3: added bio-conditional gating sentence at the top, then four new lettered subsections (E–H) defining each new block type — purpose, when to add, standard designs, success criterion, compute. Updated the per-block schema to extend the `type` enum and clarify what `baseline` should point at for each new block (placebo arm, WT/vehicle arm, zero-dose, within-context effect size).
- Step 4: restructured Stage diagram so negative-control blocks run in parallel with validation (Stage 2), mechanism with ablation (Stage 3), and dose-response + cross-context sit in Stage 4 alongside robustness. Added a Stage-2 negative-control gate ("non-null negative control halts validation interpretation") and a Stage-3 orthogonal-perturbation gate ("two perturbations both null → downgrade `mechanistic_basis` to `correlative`").
- Step 5 review prompt + review questions: added a sixth question explicitly probing for negative-control coverage, ≥2 orthogonal mechanism perturbations, ≥3 orders-of-magnitude dose-response, and pre-registered cross-context retention thresholds.
- Step 6 frontmatter template: extended `type` enum comment.
- Step 6 report template: new sample table with one row per new block type plus a Run Order line that names the new gates.
- Constraints: new bullet making the negative-control gate mandatory.
- Error Handling: budget-insufficient bullet now references the explicit drop order from Step 4.

**Why**: backlog item C4 — the prior 4-type taxonomy was missing the experiment shapes that biologists run by reflex. A "PTM-blind baseline reproduction" is not a negative control; a hyperparameter sweep is not a dose-response; cross-dataset robustness with ML mindset misses species-specific failure modes. Adding these as first-class block types means `/exp-design` can prompt for them, `/exp-eval` can score them with the right gate, and the graph carries the right `tested_by` edges.

**Cross-section dependencies**:
- A7 — `mechanism` blocks target a `mechanistic_basis` evidence claim, which only exists if A7's extended evidence-type enum is in place.
- B1 — Step 5 review prompt mentions the bio relation edges; only relevant once `/ingest` (C1) starts emitting them.

**Backward compatibility**: legacy four-block plans remain valid. The new types are additive; experiments without one of the new types in their `type` field fall through unchanged.

### C5 — [P0] `/exp-design` Step 1 gates wet-lab vs in-silico via keyword probe

**Where**:
- Inputs: new `--wet-lab yes|no|skip` flag with explicit non-interactive default semantics.
- Outputs: report now records the wet-lab decision and matched keywords.
- Step 1: added sub-step 4 — keyword scan over `## Hypothesis` + `## Approach sketch` + `## Risks` against six keyword groups (cell-based assays, animal/clinical, biophysical, structural, interactome, genomics readouts), then a three-branch routing to `plan | retrospective_only | deferred | none`.
- Step 6 frontmatter template: extends `setup` with the optional A5 bio fields and adds the structured `estimated_cost` block (A6) so a `plan` decision has a place to land budget numbers.
- Step 6 idea-page update: when decision is `retrospective_only`, append a `conditions` line documenting the scope downgrade.
- Step 6 log line: trailing `wet_lab_decision: …` for grep-ability.
- Step 6 report: top-block fields for wet-lab decision and matched keywords; bottom-block budget line names all six A6 cost dimensions.
- Constraints: new bullet making the wet-lab decision mandatory in the report and log line, even when `none`.
- Error Handling: explicit non-interactive fallback message.
- Dependencies → Claude Code Native: added `AskUserQuestion`.

**Why**: backlog item C5 — every one of the 8 experiments in the previous F-section audit was in-silico, but the source idea referenced real wet-lab phospho-PROTAC data. The skill never asked "does this idea need new wet-lab data?". The keyword scan is a concrete cheap heuristic; the three-branch prompt forces a record of the answer rather than an implicit assumption.

**Cross-section dependencies**:
- A1 — `setup.dataset` becomes a wikilink to `wiki/datasets/{slug}` only after A1 lands.
- A5 — bio `setup` fields (`in_silico_or_wet`, `species`, `cell_line`, `assay_type`, force_field, …) are filled here.
- A6 — `estimated_cost` block lives here when wet-lab decision is `plan`.

**Backward compatibility**: when no keyword fires (CS ideas), the probe is a no-op; existing plans see no change in shape.

### C6 — [P1] `/exp-design` statistical defaults switch on sample size and modality

**Where**:
- Step 3 B (validation) and C (ablation): replaced the unconditional ">= 3 random seeds" line with a sample-size-and-modality selector. Three branches: `seeds_only` (legacy, n_test ≥ 50, in-silico); `bootstrap_ci` + `stratified_kfold` (n_test < 50 **or** bio domain); `replicate_matrix_BxT` (any wet-lab block).
- Step 3 per-block schema: added `statistical_protocol` field with a four-value enum.
- Step 5 review prompt: question 5 reworded to flag seeds-vs-bootstrap-vs-stratified-vs-replicate-matrix mismatches.
- Step 6 frontmatter template: `statistical_protocol` is now a mandatory YAML scalar with explanatory comment; `seeds` field's meaning narrowed ("only meaningful when statistical_protocol == seeds_only").
- Step 6 `## Setup` body: when `replicate_matrix_BxT`, must state explicitly which dimension is biological vs technical and how many of each.
- Constraints: replaced "At least 3 seeds" bullet with the four-protocol-aware version (seeds_only ≥ 3 seeds; bootstrap_ci default 1000 resamples; stratified_kfold default `k = min(5, n_positives)`; replicate_matrix_BxT default `>= 3 × >= 3`).
- Error Handling: new bullet for `n_test` undeterminable → default to bootstrap_ci, ask user to populate `wiki/datasets/{slug}.versions[*].n_test`.

**Why**: backlog item C6 — the prior ">= 3 random seeds" default is statistically meaningless on a held-out set of 50 phospho-PROTACs with strong class imbalance, and is silent on wet-lab assays where the canonical statistic is biological×technical replicate counts. Bootstrap CI on small in-silico sets, stratified k-fold for class imbalance, and the explicit B×T replicate matrix for wet-lab cover the three regimes that the current default misses.

**Cross-section dependencies**:
- A1 — `n_test` is read from `wiki/datasets/{slug}.versions[*].n_test`. The C8 lint that polices this can warn but cannot itself populate the field.
- A8 — `reproducibility.dataset_versions` block carries the version that the n_test was measured under.

**Backward compatibility**: plans authored before C6 will be missing the `statistical_protocol` scalar. `/check` (C8) can flag this as a deterministic-fix issue; `--fix` can populate it from the existing `seeds`/`metrics` fields when unambiguous (default `seeds_only` when `seeds >= 3` and no bio-domain marker).

### Adoption gate — before merging the three items to source-of-truth

1. A1, A5, A6, A7 must already be merged (the writes have nowhere to go otherwise). All four are in the runnable folder as of 2026-05-03.
2. The `/exp-eval` and `/check` skills must be aware of `statistical_protocol` and the new `type` enum values, otherwise downstream skills will silently drop them. **Both updates are pending** — bundle them with the C8 (`/check` bio-lint) work in Batch C-2 to avoid a scattered merge.
3. `AskUserQuestion` must be present in the harness; it is by default in Claude Code's deferred-tool list.

### Pending in Batch 2 — `/exp-run` + `/check` + `/discover` + `/novelty` (C7 + C8 + C2 + C9)

Will be drafted next. Depends on this batch landing first because C8's lint rules check the new `statistical_protocol` and `type` enum values.

---

## 2026-05-04 — Section C Batch 2 drafted (C7 + C8 + C2 + C9)

**Scope**: skill workflow changes across `/exp-run`, `/check`, `/discover`, `/novelty`. Four backlog items bundled because C8 (bio-lint) needs to know about the field shapes that C7 / C2 / C9 introduce or read, and `/check` is the natural place to verify the new bio fields and edges land coherently.

**Status**: drafted, not yet merged into source-of-truth. **`tools/lint_bio.py` not yet implemented** — `/check`'s bio pass silently skips until that tool lands; the rest of `/check` runs unchanged. The four discovery / novelty subcommands documented here build on the C1 fetcher tools (`fetch_pubmed.py`, `fetch_crossref.py`, `fetch_europepmc.py`, `fetch_biorxiv.py`) which are already implemented; the only new code surface is a `from-bio-anchor` subcommand on `tools/discover.py`.

**Files written**:
- `docs/bio-adaptation/section-c/skills/check/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/discover/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/novelty/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/exp-run/SKILL.{en,zh}.md`

### Cross-cutting design choices

- **`tools/lint_bio.py` is a separate binary, not a `tools/lint.py` flag.** Same JSON output shape so `/check`'s report generator consumes both without branching, but the two binaries do not share state. Reason: bio-lint is a category cluster (identifier formats, dataset version drift, force-field provenance, species coherence, `statistical_protocol` completeness, domain vocab) that does not benefit from being interleaved with the existing structural checks. Keeping them separate also lets a CS-only fork drop the bio binary without touching `tools/lint.py`.
- **`--bio-channels {auto|on|off}`** is the same flag in `/discover` and `/novelty`, with the same auto-detection rule. The two skills MUST resolve `auto` the same way for the same input — otherwise users will see `/discover` activating bio channels but `/novelty` not, on the same target. Documented as a hard invariant in both mirrors.
- **Setup-type detector lives in `/exp-run` Phase 1 sub-step 3, not in `tools/`.** Reason: the detector is a 6-rule decision table over `setup` fields that one could implement as a Python helper, but doing it in SKILL.md keeps the routing transparent and lets the user override via `--setup-type` without an extra CLI surface. When the detector picks `ml` despite bio fields, the mirror prescribes a 🟡 nudge rather than blocking — almost always the user has just left a setup field empty, and forcing them to populate it is the right fix, not silently overriding.
- **Identifier-format auto-fix is disabled even with `--fix`.** A "fixed" DOI / PMID / PDB / UniProt is silently corrupted provenance. The fix-rule field on bio-lint issues is `none` for identifier checks, `deterministic` for missing required fields with safe defaults, `suggestion` for everything else.

### C7 — [P1] `/exp-run` directory layout templated by setup-type

**Where**:
- Description and intro: name the six setup-types and the per-type entrypoint files. Argument hint extended with `--setup-type {auto|ml|md|wet-lab|docking|snakemake|nextflow}`.
- Wiki Interaction → Reads: added `wiki/datasets/*.md` as a read for dataset access tier and version pinning.
- Wiki Interaction → Writes: per-type directory layouts spelled out (file lists with role comments).
- Phase 1 sub-step 3: 6-rule decision table with order-sensitive matching (wet → MD → docking → snakemake → nextflow → ml).
- Phase 1 sub-step 4: per-type template-fill sections — `ml` (legacy), `md` (mdrun.sh + mdp/* + analysis.ipynb), `wet-lab` (protocol.md + materials.csv + data placeholders), `docking` (dock.sh + receptor + library + scoring), `snakemake` / `nextflow` (workflow runner skeleton). Each section names the required fields and refuses to deploy when any required field is missing for that type.
- Phase 1 sub-step 5: Review LLM `system` prompt is specialized to the detected type — MD reviewer flags equilibration / barostat issues; wet-lab reviewer flags missing RRIDs; docking reviewer flags protonation / search-box issues; etc.
- Phase 1 sub-step 6: per-type sanity checks. Wet-lab is the only N/A case.
- Phase 2: per-type deploy paths. Wet-lab deploy is intentionally a no-op (the experiment runs at the bench).
- DEPLOY_REPORT: `Setup type` and `Template` lines added.
- Phase 3 anomaly detection: per-type anomaly catalog (NaN/OOM for ml; LINCS / energy explosion for md; zero poses for docking; rule failure for workflow-manager).
- Phase 4 sub-step 3: parse rule by `statistical_protocol`. `replicate_matrix_BxT` (wet-lab) collapses to mean ± SEM across biological replicates with technical replicates as raw points — does not silently collapse to mean ± std.
- Constraints: setup-type detector is non-authoritative; wet-lab requires materials; multi-seed-mean rule narrowed to `seeds_only` only.
- Error Handling: detector-mis-routes-to-ml (🟡 nudge); template not yet authored (stub generation); wet-lab CSV missing in collect mode (do not auto-fail).
- Local References: 6 planned template paths under `skills/exp-run/references/templates/{type}/`.

**Why**: backlog item C7 — the legacy `train.py + config.yaml + run.sh` layout silently misshapes any non-ML experiment. An MD experiment naturally wants `mdrun.sh + system.gro + mdp/*.mdp`; a wet-lab experiment wants `protocol.md + materials.csv + analysis.ipynb`. Forcing every experiment through a `train.py` skeleton produces correct-looking but unrunnable code.

**Cross-section dependencies**:
- A5 (experiments setup bio fields) — drives the detector.
- A6 (`estimated_cost` block) — non-ML types fill the right cost dimension instead of overloading `estimated_hours`.
- C4 (experiment.type enum) — `mechanism` blocks especially benefit from the wet-lab + docking templates.
- C6 (`statistical_protocol`) — Phase 4 aggregation rule.

**Backward compatibility**: when no bio fields are populated, the detector picks `ml` and the legacy 4-file layout is written exactly as before. CS-only flows are bit-identical to the pre-C7 path.

### C8 — [P1] `/check` adds an auto-detected bio-lint pass

**Where**:
- Description and intro: "10 entity types" and bio-lint pass mention.
- Inputs: new `--bio` / `--no-bio` flags with auto-detection rule documented.
- Wiki Interaction → Reads: `wiki/datasets/*.md` added.
- Step 2 required-fields list: 10th entity (`datasets`) added with its required field set.
- Step 3 enum-value checks: extended with `experiments.type` (C4 enum), `experiments.statistical_protocol` (C6 enum), `claims.evidence[*].type` and `.grade` (A7), `datasets.maturity`, `datasets.access`.
- Step 4 cross-reference matrix: two new rows for the papers→datasets and experiments→datasets bidirectional rules.
- Step 5 graph-edge consistency: new bullet for B1 confidence requirement and B2 / B3 typed `metadata` completeness against `tools/_schemas.py::EDGE_METADATA_REQUIRED`.
- New Step 6b "Bio-Lint Pass" section: 6 categories — identifier formats (DOI / PMID / bioRxiv DOI / PDB / UniProt / NCT / Cellosaurus / HGNC), dataset version drift, force-field provenance on MD, species-mismatch coherence (LLM-assisted), `statistical_protocol` completeness, domain vocab nudge.
- Step 7 report: bio-lint summary line; tier classification for each new bio category.
- Constraints: bio-lint is auto-detected and additive; identifier-format auto-fix is disabled.
- Error Handling: tools/lint_bio.py not installed → graceful skip; datasets/ empty but bio fields present → 🟡 nudge with TernaryDB pilot reference.
- Dependencies: `tools/lint_bio.py` listed as planned follow-up; appended a tool-design comment block specifying expected JSON shape, CLI, and exit-code semantics.

**Why**: backlog item C8 — `/check` ran clean on the existing wiki only because it was missing the structural checks that would have caught real bugs. PDB IDs are easy to mis-write (`6XYZ` vs `6xyz`), UniProt has a strict regex, dataset versions drift silently, and an MD experiment without `force_field` is unreproducible.

**Cross-section dependencies**:
- A1 — datasets/ schema is read by version-drift check.
- A3 — papers/ bio identifier fields are validated.
- A5 — experiments setup bio fields are validated.
- A7 — claim evidence type/grade enums are validated.
- A8 — `reproducibility.dataset_versions` is validated.
- B1/B2/B3 — edge metadata completeness is validated.
- C4/C6 — `experiments.type` and `statistical_protocol` enums are validated.

**Backward compatibility**: when no bio fields exist anywhere in the wiki, the bio pass auto-skips and `/check`'s output is bit-identical to the pre-C8 path. The legacy `tools/lint.py` is unchanged.

### C2 — [P1] `/discover` parallel queries against PubMed + EuropePMC + bioRxiv with DOI / PMID anchor keys

**Where**:
- Description: parallel-channels phrasing added; intro paragraph names the recall-over-precision trade-off.
- Inputs: new `--doi` / `--pmid` anchor flags; new `--bio-channels {auto|on|off}` flag with shared auto-detection rule.
- Wiki Interaction → Reads: `papers.doi/pmid/biorxiv` and bio-anchor frontmatter (`gene_symbols`, `pdb_ids`, etc.) added.
- Step 1 seed-mode picker: new `bio-anchor` mode for DOI / PMID / bioRxiv inputs.
- New Step 2 "channel set determination" section: `bio off` / `bio on` / `bio auto` resolution rules.
- Step 3 tool invocation: planned `tools/discover.py from-bio-anchor` subcommand spec'd in detail (resolve via CrossRef + PubMed → pull similar / citations / related → merge with S2 channels under `doi > pmid > arxiv > biorxiv > title-fuzzy` priority).
- Step 4 shortlist presentation: per-candidate rationale gains source-channel tag for bio candidates; "next step" hint includes bio-canonical `/ingest <doi>` and `/ingest PMID:<pmid>` forms.
- Step 5 log line: trailing `bio-channels={on|off|auto→on|auto→off}`.
- Internal Callers `/ingest --discover`: post-ingest call uses `--doi` / `--pmid` when the just-ingested paper's canonical id is bio.
- Constraints: bio-side dedup uses canonical-id priority order; bio rate limits compound the S2 calls.
- Error Handling: S2-down + bio-up degrades to bio-only (correct behavior, not bug); DOI/PMID lookup miss aborts (do not silently retry as title-fuzzy).
- Dependencies: PubMed / EuropePMC / bioRxiv / CrossRef listed as external APIs; `tools/discover.py from-bio-anchor` listed as planned subcommand.

**Why**: backlog item C2 — DeepXiv search index is sparse for biology/structure domain; S2 alone misses PubMed-only prior art. Parallelizing PubMed + EuropePMC + bioRxiv next to S2 fixes recall in bio discovery.

**Cross-section dependencies**: A3 (bio identifier frontmatter for dedup), C1 (the four bio fetchers, already implemented).

**Backward compatibility**: existing arXiv-anchor and topic-mode flows pass through unchanged. `--bio-channels off` produces the same shortlist as before C2.

### C9 — [P1] `/novelty` adds parallel PubMed + EuropePMC channel

**Where**:
- Description and intro: PubMed + EuropePMC named alongside S2.
- Inputs: bio target types (DOI / PMID / bioRxiv URL) added; `--bio-channels {auto|on|off}` matching `/discover`.
- Outputs: novelty report gains a "Search Coverage" table (per-source hit count + top-5 contribution) so the user can judge whether prior-art coverage was actually broad.
- Wiki Interaction → Reads: bio identifier frontmatter for both `auto` detection and bio-side dedup.
- Step 1: bio-target resolution path via `fetch_crossref.py` / `fetch_pubmed.py`; bio-anchor term generation for MeSH-narrowed queries.
- New Source B-bio in Step 2: PubMed (keyword + MeSH) + EuropePMC (search + annotations). Annotations endpoint is named as the primary similarity signal for bio targets — entity URIs (UniProt / GO / ChEBI) beat abstract bag-of-words.
- Step 3 Review LLM prompt: extended system prompt names the "weight bio channels at full strength" instruction; new question 5 specifically asks the reviewer to surface clinical / wet-lab validation precedents the search may have missed.
- Step 4 report: per-candidate `Source` and `Identifier` fields; new scoring rule — bio-anchored idea with PubMed hit on overlapping method + same protein target + ≤5 years → score 1 (Published) regardless of S2.
- Constraints: bio channels do not down-weight wiki internal search; minimum 2 PubMed queries + 1 EuropePMC query when bio is on.
- Error Handling: PubMed + EuropePMC both unavailable → hard warning at top of report; do not silently produce a confident bio novelty score on S2 alone.

**Why**: backlog item C9 — bio prior art is overwhelmingly in PubMed (>30M abstracts) and only partially indexed by S2. Without PubMed, `/novelty` under-reports bio prior-art collisions and lets users proceed on methods that already exist.

**Cross-section dependencies**: C1 (PubMed + EuropePMC fetchers, already implemented), C2 (shared auto-detection rule), A4 (domain controlled vocabulary).

**Backward compatibility**: when bio channels are off (CS-only flows), Source B-bio is skipped and the rest of the workflow is unchanged.

### Adoption gate — before merging the four items to source-of-truth

1. C1 fetcher tools (`fetch_pubmed.py`, `fetch_crossref.py`, `fetch_europepmc.py`, `fetch_biorxiv.py`) must already be merged. ✅ Done in the runnable folder as of 2026-05-03.
2. **`tools/lint_bio.py` must be implemented** for the C8 bio pass to actually run. Until then `/check` reports "bio-lint pass skipped — tools/lint_bio.py not installed" as documented. The mirror's appended tool-design comment block is the spec.
3. **`tools/discover.py` must gain the `from-bio-anchor` subcommand** for C2's bio-anchor mode to actually run. Until then, bio-anchor mode degrades to title-search via S2.
4. **`/exp-run` per-type templates** under `skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/` should be authored. Until then `/exp-run` falls back to a stub layout for non-ML types and warns.
5. The merge order matters: C8 should land last, because its bio-lint covers the `statistical_protocol` and `experiments.type` fields that C4/C6 introduced and the `setup` bio fields that A5 introduced. Landing C8 first would emit false-positive "missing field" warnings on the existing pre-bio wiki.

### Pending in Batch 3 — `/ideate` + `/paper-plan` + `/paper-draft` + `/rebuttal` (C3 + C10 + C11)

Will be drafted next. C3 (`/ideate` failed-idea banlist gains `scope: species | disease_area | data_regime`); C10 (`/paper-plan` + `/paper-draft` accept `paper_style: cs | bio | clinical`, with bio Vancouver / Results-first templates); C11 (`/rebuttal` tracks promised follow-up wet-lab experiments as evidence in the response, not as blank promises).

---

## 2026-05-04 — C8 spec correction (exit-code claim)

`docs/bio-adaptation/section-c/skills/check/SKILL.{en,zh}.md` had a wrong claim in the `tools/lint_bio.py` design block: "Exit code 0 even when 🔴 issues are found (consistent with tools/lint.py — the report is the artefact)". `tools/lint.py` actually exits 1 when any 🔴 is found (see its `main()` final line: `sys.exit(1 if red > 0 else 0)`). The implementation in `tools/lint_bio.py` matches lint.py's real behavior; the spec is now corrected to match. No code change.

---

## 2026-05-04 — Section C Batch 3 drafted (C3 + C10 + C11)

**Scope**: skill workflow changes across `/ideate`, `/paper-plan`, `/paper-draft`, and `/rebuttal`. Three backlog items bundled because they cover the post-experiment / writing-stage end of the C section, and C10 splits across two skills (`/paper-plan` writes the metadata; `/paper-draft` consumes it).

**Status**: drafted, not yet merged into source-of-truth. **All four mirrors are additive over the legacy CS path** — when bio fields are absent / `--scope` is unset / `--paper-style` resolves to `cs` / `--scaffold-followups` is off, behavior is bit-identical to the pre-C section state.

**Files written**:
- `docs/bio-adaptation/section-c/skills/ideate/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/paper-plan/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/paper-draft/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/rebuttal/SKILL.{en,zh}.md`

### Cross-cutting design choices

- **Scope is per-idea metadata, not a global run flag**. The `scope` block lives on each `wiki/ideas/{slug}.md`, including failed ideas. This means a failed idea's *intended* scope is what gets recorded — not the run's `current_scope`. A later run in a different scope correctly bypasses out-of-scope precedents because the ban records what it bans, not what was banning.
- **`paper_style` is resolved once in `/paper-plan` and recorded in PAPER_PLAN.md metadata**. `/paper-draft` reads it back, never re-infers. This avoids the failure mode where the plan was generated for a bio venue but the draft starts laying out CS sections because the inputs to the inference rule shifted between calls.
- **Venue beats domain on `paper_style` disagreement**. The venue's format requirements are not negotiable; if the user chose Nature but the claims look CS-shaped, the right action is to warn (the content doesn't suit the venue) and use bio structure (the structural requirements are venue-mandated).
- **`--scaffold-followups` is opt-in**. Bio reviewers routinely demand 3-5 follow-up wet-lab experiments per submission; turning each commitment into a tracked `wiki/experiments/{slug}.md` page is high-leverage but high-surprise. The user must opt in. The Review LLM stress-test in Step 5 pushes harder on Strategy B commitments specifically because vague commitments cannot be scaffolded into useful experiment pages.
- **Bio Methods is wiki-driven serialization, not writing**. `/paper-draft` for `paper_style: bio` reads dataset versions from `wiki/datasets/`, replicate counts from `experiments[*].statistical_protocol`, force-fields/cell-lines/RRIDs from `setup`, costs from `estimated_cost`, and serializes them deterministically. The bio Methods section is one of the few places in the wiki where "writing" should be replaced by structured-data dump — the prose adds nothing and obscures reproducibility.

### C3 — [P1] `/ideate` failed-idea banlist gains `scope` (species / disease_area / data_regime)

**Where**:
- `argument-hint`: new `--scope species=...|disease_area=...|data_regime=...` flag.
- Inputs / Outputs: scope flag documented; IDEA_REPORT gains a "Banlist Trace" section with in-scope hits vs out-of-scope precedents.
- Pre-conditions: new step 4 — resolve `current_scope` from `--scope` or infer from direction; emit a 🟡 warning if a clearly bio direction has empty scope.
- Phase 1 sub-step 1: each failed-idea entry annotated with `scope_overlap: True | False` based on overlap with `current_scope`.
- Phase 2 brainstorm prompts: in-scope banlist is a hard blocker; out-of-scope banlist is "informational precedent" — surfaces saturated areas without banning their architecture's application to a different scope.
- Phase 3 filter: only `scope_overlap == True` entries cause elimination.
- Phase 5 frontmatter template: optional `scope:` block with `species`, `disease_area`, `data_regime`. Pre-C3 ideas without it default to "global" (legacy semantics).
- Phase 5 failed-idea writing: `scope` field records the *intended* scope of the failed idea. Genuinely scope-independent failures explicitly leave all three sub-fields empty AND prefix the failure_reason with `[filter] global:`.
- Constraints: scope-aware matching is normative; "failed ideas should record their own scope, not the run's" is a hard rule.

**Why**: backlog item C3 — saturating PROTAC phospho-prediction in human / high-data does not say anything about plant or microbial PTMs. The legacy global banlist over-blocks. Per-idea scope lets a single failed idea correctly record the boundary of what it bans.

**Cross-section dependencies**: A4 (bio domain controlled vocabulary for `disease_area`), A1 (`wiki/datasets/{slug}.versions[*].n_test` informs `data_regime`).

**Backward compatibility**: pre-C3 ideas without `scope` block fall back to global ban semantics — behavior identical to the legacy banlist.

### C10 — [P2] `/paper-plan` + `/paper-draft` accept `paper_style: cs|bio|clinical`

**Where (in `/paper-plan`)**:
- `argument-hint`: new `--paper-style cs|bio|clinical` flag, default `auto`.
- Venue list expanded for bio (`Nature`, `Cell`, `Science`, `Nature Methods`, `Nature Biotech`, `Nat. Commun.`, `eLife`, `bioRxiv`) and clinical (`NEJM`, `JAMA`, `Lancet`, `BMJ`, `Annals`, `medRxiv`).
- New Step 1b ("Resolve paper_style") with explicit rules: `--paper-style` if passed → venue → `claims[*].domain` aggregation → tie-breaker prefers venue.
- Step 2 evidence-map gains `Type/Grade` column (A7 evidence types and grades).
- Step 4 outline: three full per-style templates spelled out — cs (Intro→RW→Method→Experiments→Conclusion), bio (Intro→Results→Discussion→Methods, figure-first storytelling, narrative captions, Results-first), clinical (Intro→Methods→Results→Discussion, Methods front-loaded, CONSORT diagram, baseline table, explicit limitations).
- Step 5 figure plan gains style-specific conventions: cs minimal captions, bio narrative captions with sample sizes + replicate types + statistical test names, clinical CONSORT + ITT/per-protocol naming.
- Step 6 citation plan: cs author-year, bio Vancouver numeric, clinical Vancouver. Bio/clinical prefer CrossRef + PubMed over DBLP.
- Step 7 Review LLM persona is dispatched on `paper_style`: ML area chair / bio editor / clinical editor.
- Step 8 PAPER_PLAN.md metadata records the resolved `paper_style` so `/paper-draft` consumes it without re-inferring.
- Constraints: clinical style requires NCT ID via B2 `clinical_trial_for` edge unless explicitly observational.

**Where (in `/paper-draft`)**:
- Section file naming dispatches on `paper_style`: cs uses `method.tex` + `experiments.tex`; bio uses `results.tex` + `methods.tex`; clinical uses `methods.tex` first, then `results.tex`.
- `main.tex` skeleton dispatches on `paper_style` for both section ordering and bibliography style: cs `\bibliographystyle{plainnat}`, bio `\bibliographystyle{naturemag}` (numeric superscript Vancouver), clinical `\bibliographystyle{vancouver}`.
- Step 3a per-style material collection: bio Results = one subsection per claim, dispatched on `experiments[*].type` (validation → headline; mechanism → "we tested whether the predicted mechanism holds"; dose_response → titration with EC50/IC50; cross_context → generalization; negative_control → folded into validation caption).
- Bio Methods is treated as **wiki-driven serialization, not a writing task**: pull dataset versions from `wiki/datasets/`, replicate counts from `experiments[*].statistical_protocol`, force-fields/cell-lines/RRIDs from `setup`, costs from `estimated_cost`. Step 6 has explicit integrity checks for bio (dataset versions exist) and clinical (NCT ID matches B2 edge).
- Step 3b LaTeX writing: cs claim-first ("We claim X. To verify..."), bio result-first with embedded statistics ("In ABC cells, treatment reduced target abundance by 78% (Fig. 2a; n=4 biological replicates, two-sided t-test, P<0.001)").
- Per-section Review LLM persona: same dispatch as `/paper-plan` — ML researcher / bio researcher / clinical reviewer.

**Why**: backlog item C10 — bio papers are figure-first with Methods last and de-emphasized; clinical papers are pre-registration-driven with CONSORT and Methods front-loaded; CS papers are method-first with experiments validating the method. Forcing all three through a CS-shaped template silently writes the wrong paper.

**Cross-section dependencies**: A1 (datasets/), A6 (estimated_cost), A7 (evidence types & grades), A8 (reproducibility), B2 (clinical_trial_for), C4 (experiment.type enum), C6 (statistical_protocol).

**Backward compatibility**: when `paper_style: cs`, the section structure, citation style, and Review LLM persona are bit-identical to the legacy path. `auto` resolves to `cs` when neither venue nor domain are bio.

### C11 — [P2] `/rebuttal` tracks promised follow-up wet-lab experiments

**Where**:
- `argument-hint`: new opt-in `--scaffold-followups` flag.
- Step 4 Strategy B: in addition to the prose response, the response is captured as a structured `commitment` record (`commitment_id`, `proposed_title`, `target_claim`, `setup_hint.{in_silico_or_wet, assay_type, species, cell_line}`, `estimated_cost_hint`, `rationale`).
- Step 5 Review LLM stress-test: explicit scoring rule — generic "we will run experiments" scores 1-2 because it cannot be scaffolded; concrete "CETSA on HEK293, n=3 biological, 4-week timeline" scores 4-5.
- New Step 6d "Optional follow-up scaffolding": when `--scaffold-followups` is set, every Strategy B commitment whose pre-flight check passes is fed to `/exp-design` (one call per commitment). Each scaffolded experiment carries `triggered_by_rebuttal: <paper-slug>` and `triggered_by_concern: <Rvx-Cy>` provenance fields.
- Step 6b rich-text rebuttal "Suggested Experiments" table gains `Setup Hint`, `Cost Hint`, `Scaffolded?` columns.
- Constraints: Strategy B commitments must be scaffoldable (concrete enough); scaffolded experiments carry provenance fields; `--scaffold-followups` is opt-in by default.
- Error handling: vague commitments that survive stress-test still don't get scaffolded (🟡 nudge to refine); failed `/exp-design` invocation surfaces a 🔴 and the rebuttal ships text-only.

**Why**: backlog item C11 — bio reviewers routinely demand additional wet-lab experiments as conditions for acceptance; without a mechanism to spawn tracked deliverables, those promises rot. The opt-in flag is critical: spawning 5 new "planned" experiments silently from a rebuttal is the kind of action where surprise has high cost.

**Cross-section dependencies**: `/exp-design` (the existing skill is invoked one call per commitment, ideally with new flags `--triggered-by-rebuttal`, `--commitment-id`, `--setup-hint` — those flag additions to `/exp-design` are filed as planned tooling alongside C11; until they land, `/rebuttal` falls back to a post-hoc `tools/research_wiki.py set-meta` call); A5 (setup bio fields populated by the scaffold); C8 (lint_bio future extension can flag missing `triggered_by_rebuttal` on follow-up experiments).

**Backward compatibility**: when `--scaffold-followups` is not set, behavior is identical to the legacy text-only rebuttal flow.

### Adoption gate — before merging the four items to source-of-truth

1. C3 has no tooling dependency; it can land independently.
2. C10 requires the per-style content templates (`skills/paper-draft/references/templates/{cs,bio,clinical}/`) for the best experience, but the inline defaults in the mirror are sufficient until those templates land.
3. C11 ideally requires `/exp-design` to gain `--triggered-by-rebuttal`, `--commitment-id`, `--setup-hint` flags. Until then the post-hoc `set-meta` fallback is functional — the final state of the wiki is identical, just more steps to get there.
4. **Merge order**: any of the three can land in any order. C3 has the smallest blast radius (one skill, additive metadata field); C10 has the widest (two skills, new section ordering, citation style change); C11 spans the rebuttal flow plus an `/exp-design` invocation.

### Section C status

With Batch C-3 drafted, **all 11 C-section items now have either applied (C1) or drafted (C2–C11) mirrors**. The Batch table:

| Batch | Items | Skills touched | Status |
|-------|-------|----------------|--------|
| C-1a (Q1 partial) | C1 | /ingest | ✅ applied to source-of-truth + 5 fetcher tools implemented |
| C-1b (Q1 finish) | C4 + C5 + C6 | /exp-design | ✅ drafted |
| C-2 | C7 + C8 + C2 + C9 | /exp-run, /check, /discover, /novelty | ✅ drafted; tools/lint_bio.py implemented |
| C-3 | C3 + C10 + C11 | /ideate, /paper-plan, /paper-draft, /rebuttal | ✅ drafted |

### Pending — wider sections

Sections D / F / G / H from the original backlog remain deferred per the prior plan. Recommended next moves:
1. Promote any subset of C-1b / C-2 / C-3 to source-of-truth in `/home/yukino/OmegaWiki_bioinfo_adaptation/`. Each batch's CHANGELOG entry has its own adoption gate.
2. Build the four follow-up tooling pieces in priority order: `tools/discover.py from-bio-anchor` subcommand (C2), `skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/` (C7), `skills/paper-draft/references/templates/{cs,bio,clinical}/` (C10), `/exp-design --triggered-by-rebuttal` flag (C11).
3. End-to-end smoke test: pick a bio paper that's not yet in the wiki, run `/ingest` → `/discover` → `/ideate --scope species=human,disease_area=cancer-bio,data_regime=high-data` → `/exp-design` → `/exp-run` (synthetic) → `/exp-eval` → `/paper-plan --paper-style bio` → `/paper-draft` → `/check`. Each missing piece in the runnable folder will be flagged and can be filled in.

---

## 2026-05-04 — C1 completion (`tools/prepare_bio_paper_source.py` + SKILL.md tightening)

**What was incomplete**: per the BIOINFO_ADAPTATION_CHECKPOINT note "C1 has not been exercised end-to-end", the bio path was wired prose-side and the five fetcher tools worked individually, but no tool actually:
- classified an arbitrary bio identifier (DOI / PMID / bioRxiv URL / bioRxiv DOI / PMC ID / PMC URL)
- routed to the right fetcher
- downloaded the OA full-text artefact to `raw/discovered/`
- returned the same JSON envelope as `prepare_paper_source.py` so `/ingest`'s Step 1 sub-step 3 had a single hand-off

**Now done**:
- New tool: `tools/prepare_bio_paper_source.py` (~430 LoC). Single-call dispatcher: `--raw-root raw --source <bio-id-or-url>` →
  classify → fetch metadata → download PDF (bioRxiv) or JATS XML (OA PMC) → return JSON envelope with `canonical_ingest_path`, `doi`, `pmid`, `biorxiv`, `pmcid`, optional `manual_download_url`, and `warnings`.
- Routing rules (in priority order): bioRxiv/medRxiv URL → biorxiv path; PMC URL → pmc path; DOI URL or bare DOI starting with `10.1101/` → biorxiv path; bare PMC ID → pmc path; `PMID:N` or bare numeric → pubmed path; generic DOI → doi (CrossRef + EPMC mirror lookup) path.
- `/ingest` SKILL.md (en + zh) Step 1 sub-step 3 rewritten to call `prepare_bio_paper_source.py` once and consume the envelope, instead of describing per-route prose for Claude to interpret manually.
- Dependencies section updated: removed "planned" qualifier from the bio-fetcher block; added `prepare_bio_paper_source.py` as the single-call dispatcher.
- Synced via `./setup.sh --lang en`.

**Smoke tests** (all passed):
- DOI (Nature paywalled) `10.1038/s41586-021-03819-2` → AlphaFold metadata via CrossRef, no OA mirror, `metadata-only` (correct: Nature is not OA).
- bioRxiv DOI `10.1101/2024.11.19.624167` (Boltz-1) → metadata via bioRxiv API, PDF auto-download blocked by Cloudflare 403 → `manual_download_url` populated with clear actionable warning.
- bioRxiv URL `https://www.biorxiv.org/content/10.1101/2024.11.19.624167v1` → same Boltz-1 record (bug found and fixed: greedy-vs-non-greedy regex was slicing `.11.19.624167` off the date suffix).
- PMID `34265844` (with `PMID:` prefix variant) → routed via PubMed → has PMC mirror → JATS XML downloaded to `raw/discovered/structure-sars-cov-2-orf8-rapidly-evolving-immune.xml` (66 KB).
- PMC URL `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8316889/` → JATS XML downloaded directly via EuropePMC (124 KB).
- PMC ID `PMC8316889` (bare) → same path as PMC URL.
- Invalid input `not-a-real-id` → graceful error envelope with `usable: false` and an actionable `warnings` list.

**Known limitations** (logged, not blockers):
- bioRxiv blocks programmatic PDF download via Cloudflare. The fallback is `manual_download_url` + a warning; the user grabs the PDF, drops it under `raw/papers/`, and re-runs `/ingest <local-path>`. Metadata-only ingest still works for everything else.
- DOI route has no PDF download — only the EPMC mirror check, since publisher-side OA PDFs require per-publisher logic that isn't in scope for C1. Paywalled DOIs and OA DOIs not in EPMC degrade gracefully to metadata-only.
- The CLI surface intentionally does not flip an experiment's `setup.dataset` to a wikilink — that's `/ingest`'s job in Step 4 sub-step 6, not the source-resolver's.

**C1 status**: ✅ complete. `/ingest <bio-id>` now resolves end-to-end without manual fetcher orchestration; the SKILL.md prose contract matches the implementation.

---

## 2026-05-04 — `fetch_pubmed.py` recursive-findall bug fix (merged to source-of-truth)

**Bug**: `tools/fetch_pubmed.py::_parse_pubmed_article()` was reading the article's external IDs with `article.findall(".//ArticleId")`. Since `<PubmedArticle>` contains both the article's own `<PubmedData>/<ArticleIdList>` AND every cited reference's `<Reference>/<ArticleIdList>` under `<PubmedData>/<ReferenceList>`, the recursive descent matched all of them in document order and the LAST one silently overwrote `external["DOI"]`, `external["PMC"]`, and `external["PII"]`. Net effect: for a PMID with N references, the function returned the article's own title but a referenced paper's identifiers.

**Concrete failure**: PMID 40593782 (DeepTernary, Nat. Commun. 2025) → returned `DOI: 10.1073/pnas.2016239118` (which is an ESM paper) and `PMC: 8053943` (also ESM). With `prepare_bio_paper_source.py prepare_pmid` then handing the wrong PMC to the EPMC full-text downloader, an unrelated paper's JATS XML landed in `raw/discovered/`. The DeepTernary ingest in this session caught it because the title and PMC didn't agree.

**Fix**: anchor the path to the article's own ID list:

```python
# Before (recursive, wrong):
for aid in article.findall(".//ArticleId"):
    ...

# After (anchored, correct):
own_ids = article.find("PubmedData/ArticleIdList")
if own_ids is not None:
    for aid in own_ids.findall("ArticleId"):
        ...
```

**Regression test** (now passes):
- PMID 40593782 → DOI `10.1038/s41467-025-61272-5` ✅, PMC `12216337` ✅
- PMID 34265844 → DOI `10.1038/s41586-021-03819-2` (AlphaFold), PMC `8371605` ✅

**Audit of sibling sites**: scanned all other `findall(".//*")` calls in `fetch_pubmed.py` for the same shape:
- `art.findall(".//AbstractText")` — `art` = `MedlineCitation/Article`, which does not contain `ReferenceList`. **Safe.**
- `art.findall(".//Author")` — same scope. **Safe.**
- `citation.findall(".//MeshHeading/...")`, `Chemical/...`, `Keyword/...` — `citation` = `MedlineCitation`. References live under `PubmedData/ReferenceList`, sibling of `MedlineCitation`. **Safe.**
- `_hydrate_pmids` (esummary code path): JSON-keyed by PMID, no shared mutable accumulator. **Safe.**

**Source-of-truth**: tools/ has no mirror layer (per the bio-adaptation work pattern, only `i18n/` files have mirrors under `docs/bio-adaptation/`). `tools/fetch_pubmed.py` in `/home/yukino/OmegaWiki_bioinfo_adaptation/` IS the source-of-truth and the fix is in place there. The fix's intent is documented inline in the file (see the comment block above the `external = {"PMID": pmid}` line).

**Why this didn't surface earlier**: the original C1 smoke tests in CHANGELOG entry "2026-05-03 — Materialised runnable folder + bio fetcher tools" used PMID 34265844 (AlphaFold) and DOI 10.1038/s41586-021-03819-2. These specific identifiers happened to either (a) have a small enough reference set that the right ID survived the overwrite race, or (b) the test only sanity-checked title and didn't probe the DOI/PMC. Either way, the bug went unnoticed until the DeepTernary ingest probed both the title AND the per-paper canonical IDs simultaneously. Lesson: the C1 smoke tests should always assert title-and-IDs-are-consistent rather than just "title is non-empty".

---

## 2026-05-04 — `prepare_bio_paper_source.py::title_to_slug` double-hyphen fix (merged to source-of-truth)

**Bug**: titles with parenthesised version markers like `SE(3)-equivariant` produced double-hyphenated slugs:

```
"SE(3)-equivariant ternary complex prediction towards target protein degradation"
  → se--equivariant-ternary-complex-prediction-towards    (double hyphen, bug)
```

The pipeline lower-cased then ran `re.sub(r"[^\w\s-]", " ", ...)`, which turned `(3)` into a space gap, leaving `se 3 -equivariant`. Splitting then dropping numeric `3` left tokens `["se", "-equivariant"]`. Joining with `-` produced `se--equivariant`.

**Concrete failure**: caught during the DeepTernary ingest (`/home/yukino/OmegaWiki_bioinfo_adaptation/wiki/papers/se-equivariant-...`). The `raw/discovered/se--equivariant-...xml` file was already on disk before the fix; it was deleted and re-prepared after the fix.

**Fix** (in `tools/prepare_bio_paper_source.py::title_to_slug`):

```python
# Before:
parts = [p for p in cleaned.split() if p and p not in _STOPWORDS and not p.isdigit()]
return "-".join(parts[:_KEEP_LEN])

# After:
parts = [p.strip("-") for p in cleaned.split()
         if p and p not in _STOPWORDS and not p.isdigit()]
parts = [p for p in parts if p]   # drop fully-stripped tokens
slug = "-".join(parts[:_KEEP_LEN])
return re.sub(r"-+", "-", slug).strip("-")
```

Three small changes: (a) per-token `strip("-")`, (b) drop fully-stripped tokens, (c) collapse runs of `-` and trim ends.

**Regression matrix** (7 cases tested):

| Title (truncated) | Slug (after fix) | Result |
|-------------------|------------------|--------|
| `SE(3)-equivariant ternary complex prediction…` | `se-equivariant-ternary-complex-prediction-towards` | ✅ matches `research_wiki.py slug` |
| `PROTAC-DB 2.0: an updated database of PROTACs` | `protac-db-updated-database-protacs` | ✅ matches |
| `Highly accurate protein structure prediction with AlphaFold` | `highly-accurate-protein-structure-prediction-alphafold` | ✅ matches |
| `Boltz-1: Democratizing Biomolecular Interaction Modeling` | `boltz-1-democratizing-biomolecular-interaction-modeling` | ✅ **diverges from canonical (intentional)** — see Divergence note below |
| `E(3)-equivariant graph neural networks (EGNN) for molecules` | `e-equivariant-graph-neural-networks-egnn` | ⚠️ truncated at 6 keywords (`_KEEP_LEN`), `for molecules` dropped |
| `p53/MDM2 — selective allosteric inhibition` | `p53-mdm2-selective-allosteric-inhibition` | ✅ matches |
| `SARS-CoV-2 ORF8 structure` | `sars-cov-2-orf8-structure` | ✅ **diverges from canonical (intentional)** |

**Divergence from `research_wiki.py slug` is intentional and beneficial.** The canonical generator drops all-numeric tokens (`Boltz-1` → `boltz-democratizing-…`, dropping the `1`; `SARS-CoV-2 ORF8` → `sars-cov-orf8-structure`, dropping the `2`). For paper slugs where the version number carries semantic meaning ("Boltz-1" vs the future "Boltz-2"; "SARS-CoV-2" vs "SARS-CoV-1"), preserving the digit is correct. `prepare_bio_paper_source.title_to_slug` keeps multi-hyphen tokens intact (`boltz-1`, `sars-cov-2`) because it strips `-` per-token rather than splitting on it. We do not propose changing the canonical `research_wiki.py slug` to match — its drop-numeric rule is fine for arXiv-shaped titles where versioning is encoded elsewhere — but bio papers benefit from the more conservative behavior here.

**Out of scope for this fix**: `_KEEP_LEN=6` truncates titles longer than 6 non-stopword keywords. This shows up in the EGNN test case. Increasing the limit risks bloating slugs for long bio titles ("CRISPR-Cas9 mediated knockout of hexokinase 2 in pancreatic ductal adenocarcinoma cells reveals a novel metabolic vulnerability…"). Keeping `_KEEP_LEN=6` is the right default; the EGNN test case is a known limitation and the user can rename the slug post-hoc when needed.

**Source-of-truth**: same as the fetch_pubmed.py fix — `tools/prepare_bio_paper_source.py` in the runnable folder IS the source-of-truth (no mirror layer). The fix is in place; this CHANGELOG entry is the audit trail.

**Lesson** (carried over from the fetch_pubmed.py entry): a robust C1 smoke test for `prepare_bio_paper_source.py` should assert *slug-matches-canonical-or-explains-divergence* across a small fixture matrix — not just "title is non-empty". The DeepTernary ingest exposed both the fetch_pubmed.py recursive-findall bug AND this slug bug in a single attempt, because it was the first ingest that probed the slug-formation path with a parenthesised title. Future C1 hardening: add a `tests/test_prepare_bio_paper_source.py` with the regression matrix above to prevent regressions during refactors.

---

## 2026-05-04 — All C-section drafts promoted to source-of-truth

After C-1b / C-2 / C-3 batches were drafted (under `docs/bio-adaptation/section-c/skills/{skill}/SKILL.{en,zh}.md`), they all sat as mirrors only. This entry records the promotion of all 9 remaining drafts to source-of-truth in `i18n/{en,zh}/skills/{skill}/SKILL.md`.

**Method**: stripped the top `<!-- bio-CX: Mirror of i18n/... -->` audit-trail comment block (which only documents that the file is a draft) while preserving the inline `<!-- bio-CX -->` annotations in the body (those are the actual C-section markers and serve as audit trail in the source-of-truth too). Done programmatically with a 20-line Python regex helper that anchors on structural position (between frontmatter `---` and first `# /skill` heading) rather than on English keyword — this is what made it work for both EN and ZH mirrors uniformly.

**Promotion order followed the CHANGELOG adoption gates**:
1. **C-1b** (`/exp-design`) — depends on A1/A5/A6/A7 (already merged)
2. **C-3** (`/ideate` C3, `/paper-plan` + `/paper-draft` C10, `/rebuttal` C11) — independent, smallest blast radius first
3. **C-2 partial** (`/discover` C2, `/novelty` C9, `/exp-run` C7) — bio fetcher tools already in place
4. **C-2 last** (`/check` C8) — bio-lint covers fields C4/C6 introduced; landing C8 first would emit false-positive lint warnings on legacy experiments

**Files touched** (in `/home/yukino/OmegaWiki_bioinfo_adaptation/`):
```
i18n/en/skills/{exp-design,ideate,paper-plan,paper-draft,rebuttal,discover,novelty,exp-run,check}/SKILL.md
i18n/zh/skills/{...same...}/SKILL.md
.claude/skills/{...same...}/SKILL.md   (auto-synced via ./setup.sh --lang en)
CLAUDE.md, .claude/.current-lang        (auto-synced)
```

**Verification matrix**:
- All 10 SKILL.md (the 9 just promoted plus C1's `/ingest` already in place) carry a non-zero bio-CX inline annotation count, EN and ZH match within ±2 (small deltas from translation choice).
- Root `.claude/skills/{skill}/SKILL.md` annotation count matches its `i18n/en/skills/{skill}/SKILL.md` source for every skill — `setup.sh --lang en` synced cleanly.
- `tools/lint.py --wiki-dir wiki/`: 0 🔴, 0 🟡, 10 🔵 — no regression
- `tools/lint_bio.py --wiki-dir wiki/`: 0 🔴, 0 🟡, 32 🔵 — no regression
- `python -m unittest discover -s tests`: 52 tests green

**Bio-CX inline marker counts by skill** (post-promotion source-of-truth state):

| Skill | Items | en | zh |
|-------|-------|----|----|
| `/ingest` | C1 | 37 | 37 |
| `/exp-design` | C4 + C5 + C6 | 43 | 43 |
| `/exp-run` | C7 | 60 | 60 |
| `/check` | C8 | 25 | 25 |
| `/discover` | C2 | 28 | 28 |
| `/novelty` | C9 | 27 | 27 |
| `/ideate` | C3 | 30 | 30 |
| `/paper-plan` | C10 | 41 | 41 |
| `/paper-draft` | C10 | 43 | 43 |
| `/rebuttal` | C11 | 24 | 24 |

**What this enables now**: every C-section item is documented inline in the active skill prose (root `.claude/skills/{skill}/SKILL.md`). Claude Code reading these SKILL.md files at runtime now sees the bio-adaptation behavior as the documented contract, not as a parallel mirror.

**What's still open** (per CHANGELOG entries 2026-05-04 Batch C-2 / C-3 adoption gates):
- `tools/discover.py from-bio-anchor` subcommand (C2) — bio-anchor mode degrades to title-search via S2 until landed
- `skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/` (C7) — non-ML setup types fall back to a stub layout with a warning
- `skills/paper-draft/references/templates/{cs,bio,clinical}/` (C10) — `/paper-draft` uses inline defaults from the SKILL.md prose until templates land
- `/exp-design --triggered-by-rebuttal` flag (C11) — `/rebuttal --scaffold-followups` falls back to a post-hoc `set-meta` call until the flag lands

These are **runtime-side gracefully-degraded gaps**, not blockers. The skills are functional now; the gaps mean some ergonomics are worse than they will be once the follow-up tooling lands.

**C-section status: ✅ all 11 items applied to source-of-truth.** Section C is now functionally complete from a documentation standpoint; remaining work is follow-up tooling implementation in priority order.

---

## 2026-05-04 — C7 follow-up tooling: `/exp-run` per-type templates implemented

The `/exp-run` SKILL.md mirror C7 promised per-type scaffolds at `skills/exp-run/references/templates/{ml,md,wet-lab,docking,snakemake,nextflow}/`. Until this entry, those paths were empty — Phase 1 sub-step 4 fell back to a stub layout for non-ML types and warned. This entry records implementing all 6 templates as runnable scaffolds.

**Files written**: 43 files / 256 KB total under `i18n/en/skills/exp-run/references/templates/` (plus an identical copy under `i18n/zh/skills/exp-run/references/templates/` for ZH-side `setup.sh --lang zh` users).

| Template | Files | What it scaffolds |
|----------|-------|--------------------|
| **ml** | 5 | `train.py` (PyTorch supervised skeleton with multi-seed loop + per-`statistical_protocol` aggregation), `config.yaml`, `run.sh`, `requirements.txt`, README |
| **md** | 8 | `mdrun.sh` (GROMACS pipeline: pdb2gmx → solvate → ions → em → nvt → npt → prod), 4 `mdp/*.mdp` files (em / NVT / NPT / production), `system.gro` placeholder, `analysis.ipynb` (RMSD/RMSF/Rg + bootstrap-CI), `requirements.txt`, README |
| **wet-lab** | 7 | `protocol.md` (Materials → Equipment → Procedure → Read-out → Pause points → Safety with replicate-matrix table), `materials.csv` (6 rows showing RRID / CVCL / Addgene / catalog conventions), `analysis.ipynb` (collapse-tech-then-aggregate-bio with RRID sanity check), `data/{raw,processed}/.gitkeep`, `requirements.txt`, README |
| **docking** | 7 | `dock.sh` (AutoDock Vina iterating SMILES library + openbabel SMILES→PDBQT conversion + scoring CSV), `receptor.pdbqt` placeholder, `ligand_library.smi` (4 example SMILES + format documentation), `box.txt` (centre + size with default 25 Å cubic), `scoring.yaml`, `analysis.ipynb` (top-N + score distribution + redocking RMSD), `requirements.txt`, README |
| **snakemake** | 7 | `Snakefile` (DSL with `rule all` + summary), `config.yaml`, `envs/main.yaml` (conda spec), `rules/process.smk` (placeholder rule template), `scripts/process.py` (placeholder), `requirements.txt`, README |
| **nextflow** | 7 | `main.nf` (DSL2 workflow with `include` + summary process), `modules/process.nf` (process template with `stub:` block for dry-run), `nextflow.config` (executor + manifest + tracing), `params.yaml`, `scripts/process.py`, `requirements.txt`, README |

**Convention**: each template's README documents (a) which `setup` fields the deploy-time substitution reads, (b) which fields are required (deploy refuses without them — e.g. `setup.force_field` for MD, `materials.csv` antibody RRIDs for wet-lab antibody-bearing assays), (c) the Phase-1 sanity check shape (e.g. `gmx mdrun -nsteps 100` for MD, `snakemake --dry-run` for Snakemake), (d) Phase-3 anomaly detection rules per type, (e) the Phase-4 aggregation rule per `statistical_protocol`. The README is the human-readable contract; the code files are the machine-readable scaffold.

**Substitution placeholders**: each template uses `{{FIELD_NAME}}` markers (e.g. `{{FORCE_FIELD}}`, `{{SLUG}}`, `{{SEED}}`) that `/exp-run` Phase 1 sub-step 4 substitutes from `wiki/experiments/{slug}.md` frontmatter at deploy time. YAML files use a default-with-comment pattern instead of a bare placeholder (`seed: 42  # default; /exp-run substitutes from setup.random_seed_protocol`) so the templates parse cleanly out-of-the-box; the substitution is a line-replacement, not YAML reserialisation.

**Verification**:
- All 5 YAML config files parse cleanly via `python -c "import yaml; yaml.safe_load(...)"` (no template placeholders that poison YAML).
- All 3 `.ipynb` files are valid JSON and have the correct nbformat/cell shape.
- All 3 `.sh` files pass `bash -n` syntax check.
- `setup.sh --lang en` syncs all 43 files to `.claude/skills/exp-run/references/templates/`.
- `tools/lint.py`: 0 🔴 0 🟡 — no regression
- `tools/lint_bio.py`: 0 🔴 0 🟡 — no regression
- `python -m unittest discover -s tests`: 52 tests still green

**`/exp-run` SKILL.md updated**: the "Local References" block (en + zh) replaced the per-template "(planned)" markers with one-line summaries of what each template ships. The "stub fallback" path in Phase 1 sub-step 4 still exists for the case where a setup-type doesn't match any of the 6 templates — but for the documented 6, fall-back is no longer the operating mode.

**Status**: ✅ C7 follow-up tooling complete. Of the four follow-up items the C-section CHANGELOG flagged as remaining gaps:
1. ~~`tools/discover.py from-bio-anchor` subcommand (C2)~~ — still pending
2. ~~`skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/` (C7)~~ — **done in this entry**
3. ~~`skills/paper-draft/references/templates/{cs,bio,clinical}/` (C10)~~ — still pending
4. ~~`/exp-design --triggered-by-rebuttal` flag (C11)~~ — still pending

Three follow-up items remain. Of those, the `/paper-draft` templates are the largest single piece (3 venue-style scaffolds × multiple LaTeX section files each); the C2 discover subcommand and C11 exp-design flag are smaller.

---

## 2026-05-04 — C10 follow-up tooling: `/paper-draft` per-style templates implemented

The `/paper-draft` SKILL.md mirror C10 promised per-style scaffolds at `skills/paper-draft/references/templates/{cs,bio,clinical}/`. Until this entry, those paths were empty — `/paper-draft` fell back to inline defaults from the SKILL.md prose. This entry records implementing all 3 templates as compilable LaTeX scaffolds.

**Files written**: 25 files / ~64 KB total under `i18n/en/skills/paper-draft/references/templates/` (mirrored to `i18n/zh/...` for ZH-side users).

| Template | Files | Highlights |
|----------|-------|------------|
| **cs** | 9 | Master `main.tex` (Intro → RW → Method → Experiments → Conclusion); `\bibliographystyle{plainnat}` (author-year); 5 section files; rich `math_commands.tex` (probability, linear algebra, ML notation); minimal-caption convention |
| **bio** | 8 | Section ordering Intro → Results → Discussion → Methods (Methods last per Nature/Cell/eLife); `\bibliographystyle{naturemag}` (numeric superscript Vancouver); narrative-caption convention with sample sizes / replicate types / statistical test names; Methods is wiki-driven serialization with explicit `{{DATASETS_PARAGRAPHS}}` / `{{WET_LAB_SUBSECTIONS}}` / `{{COMPUTATIONAL_SUBSECTIONS}}` / `{{STATISTICAL_PARAGRAPHS}}` placeholders for `/paper-draft` Step 3a to fill from `wiki/datasets/`, `wiki/experiments/[*].setup`, `experiments[*].statistical_protocol` (C6), `estimated_cost.*` (A6); explicit `\paragraph*{Limitations.}` mandatory in Discussion |
| **clinical** | 8 | Section ordering Intro → Methods → Results → Discussion (Methods FRONT-LOADED per NEJM/JAMA/Lancet); `\bibliographystyle{vancouver}`; structured abstract (Background / Methods / Results / Conclusions); trial-registration banner (`{{NCT_ID}}` from B2 `clinical_trial_for` edge); Methods has 6 mandatory subsections (Study design / Participants / Interventions / Outcomes / Statistical analysis / Trial registration / Ethics); Results has 5 fixed subsections in order (3.1 CONSORT / 3.2 baseline table / 3.3 primary / 3.4 secondary / 3.5 safety); Discussion has explicit `\paragraph*{Limitations.}` MANDATORY (no hedging) |

**Key design decisions**:

1. **Bio Methods is structured serialization, not writing.** The Methods template ships explicit `{{DATASETS_PARAGRAPHS}}` / `{{WET_LAB_SUBSECTIONS}}` / `{{COMPUTATIONAL_SUBSECTIONS}}` / `{{STATISTICAL_PARAGRAPHS}}` / `{{RESOURCES_PARAGRAPH}}` placeholders that `/paper-draft` Step 3a fills deterministically from wiki state. The user does NOT write Methods prose — they curate the wiki and let `/paper-draft` serialize it. This matches the SKILL.md C10 prescription that bio Methods is "a wiki-driven serialization, not a writing task".

2. **Clinical limitations are syntactically mandated.** The Discussion template ships an explicit `\paragraph*{Limitations.}` block with placeholder content — `/paper-draft` Step 5 cross-review (Review LLM clinical-editor persona) blocks finalisation if the rendered LaTeX has no such paragraph. This makes the C10 mirror's "limitations are mandatory" rule structurally enforceable rather than convention-only.

3. **Caption discipline differs by style.** Bio templates have 4-6-line narrative captions with `n=...` sample sizes + statistical test names; clinical templates name the analysis population (intent-to-treat / per-protocol / safety) per figure; CS templates have minimal captions. Each template's caption shape is the canonical reference for what `/paper-draft` Step 2 produces.

4. **Substitution markers use `{{FIELD_NAME}}`** consistently across cs/bio/clinical so `/paper-draft` has a uniform substitution pass per-template-type. Required substitutions (e.g. `{{NCT_ID}}` for clinical RCT) fail the template-fill if the wiki state can't supply them, surfacing as a clear error rather than a silent placeholder in the output.

**Verification**:
- All 18 `.tex` and 3 `.bib` files structurally sound: matched braces (`{` / `}` counts agree per file) and matched `\begin{env}` / `\end{env}` pairs.
- `setup.sh --lang en` syncs all 25 files to `.claude/skills/paper-draft/references/templates/`.
- `tools/lint.py`: 0 🔴 0 🟡 — no regression
- `tools/lint_bio.py`: 0 🔴 0 🟡 — no regression
- `python -m unittest discover -s tests`: 52 tests still green

**`/paper-draft` SKILL.md updated**: the "Local References" block (en + zh) replaced "(planned)" markers with one-line summaries of what each template ships (section ordering + `\bibliographystyle` + file count). Added a paragraph documenting the per-README contract.

**Status**: ✅ C10 follow-up tooling complete. Of the 4 follow-up items the C-section CHANGELOG flagged:
1. ~~`tools/discover.py from-bio-anchor` subcommand (C2)~~ — still pending
2. ~~`skills/exp-run/references/templates/...` (C7)~~ — done in earlier 2026-05-04 entry
3. ~~`skills/paper-draft/references/templates/...` (C10)~~ — **done in this entry**
4. ~~`/exp-design --triggered-by-rebuttal` flag (C11)~~ — still pending

Two follow-up items remain: C2 discover subcommand (small, builds on already-implemented bio fetchers) and C11 exp-design flag (smallest, three flag additions to `/exp-design` SKILL.md prose + provenance fields to the experiment template).

---

## 2026-05-04 — C11 follow-up tooling: `/exp-design` rebuttal-triggered flags + paired-provenance lint check

The `/rebuttal --scaffold-followups` flow drafted under C11 invokes `/exp-design` with three flags that didn't exist in `/exp-design`'s SKILL.md until this entry: `--triggered-by-rebuttal`, `--commitment-id`, `--setup-hint`. The C11 mirror documented this gap and prescribed an emergency `tools/research_wiki.py set-meta` post-hoc fallback. This entry lands the canonical path: real flags on `/exp-design` + paired-provenance fields on the experiment frontmatter template + a `lint_bio.py` check that catches structural violations + tests.

### Changes

**`/exp-design` SKILL.md (en + zh)**:
- `argument-hint` extended with `[--triggered-by-rebuttal <paper-slug>] [--commitment-id <Rvx-Cy>] [--setup-hint key=value]`
- New `Inputs` documentation for the three flags, including the paired-flag rule (`--triggered-by-rebuttal` and `--commitment-id` must both be present or both absent), the canonical concern-ID format `^Rv[0-9]+-C[0-9]+$`, and the allowed `--setup-hint` keys (`in_silico_or_wet`, `assay_type`, `species`, `cell_line`, `force_field`, `solvent_model`, `simulation_length`)
- New Step 1 sub-step 5 ("Rebuttal-triggered provenance") documenting the flag-validation logic, the wet-lab-probe-skip rule (`/rebuttal` already classified the commitment), and the implicit `--auto` behavior
- Step 6 frontmatter template gains `triggered_by_rebuttal: ""` and `triggered_by_concern: ""` fields (paired)
- Report block gains "Triggered by rebuttal" / "Commitment ID" / "Setup hints applied" lines
- Log line tail extended with `triggered_by_rebuttal` + `commitment_id`
- Two new Constraints bullets enforcing the pairing rule and the implicit-auto behavior
- Three new Error Handling bullets for the failure modes (one-sided pair, invalid concern format, unknown setup-hint key)

**`/rebuttal` SKILL.md (en + zh)**:
- Step 6d note dropped the "until those flags land, fall back to set-meta" disclaimer; replaced with documentation of the now-real flags and the implicit-auto behavior
- Dependencies note for `tools/research_wiki.py set-meta` reframed as an "emergency fallback for retroactive backfill" rather than the primary path

**`tools/lint_bio.py`** — new check category 5b (paired-provenance), wired into the `lint_bio()` orchestrator:
```python
def check_triggered_by_rebuttal_pairing(wiki_dir: Path) -> list[Issue]:
```
- Walks `wiki/experiments/*.md`
- For each: read `triggered_by_rebuttal` and `triggered_by_concern` from frontmatter
- If exactly one is populated → 🟡 paired-provenance violation with actionable backfill instructions
- If both populated, validate concern ID against `^Rv[0-9]+-C[0-9]+$` regex → 🔴 format error if invalid
- Both empty (including pre-C11 experiments missing the fields entirely) → no issue (legacy-tolerant)

**`tests/test_lint_bio.py`** — new test file with 8 cases for the C11 check:
- `test_both_set_with_canonical_concern_id_is_clean` — happy path
- `test_both_empty_is_clean` — explicit-empty path (post-C11 experiment, user-invoked)
- `test_missing_fields_entirely_is_clean` — pre-C11 legacy tolerance
- `test_rebuttal_set_concern_empty_fires_yellow` — pair violation, half 1
- `test_concern_set_rebuttal_empty_fires_yellow` — pair violation, half 2
- `test_invalid_concern_id_format_fires_red` — format error
- `test_canonical_concern_id_variants` — single-digit + multi-digit `Rv12-C34` both valid
- `test_concern_id_lowercase_is_rejected` — case-sensitivity check (regex enforces uppercase Rv/C)

### Verification

| Check | Result |
|-------|--------|
| `python -m unittest discover -s tests` | 60 tests green (was 52, +8 new C11 cases) |
| `tools/lint.py --wiki-dir wiki/` | 0 🔴 0 🟡 — no regression |
| `tools/lint_bio.py --wiki-dir wiki/` | 0 🔴 0 🟡 — no regression on real wiki |
| Synthetic 4-experiment fixture | 1 🔴 (bad concern format) + 1 🟡 (half-pair) — exactly the cases the C11 check should catch |
| `setup.sh --lang en` | synced |

### Why this matters

Before C11 lands the structural enforcement, `/rebuttal`'s scaffolded follow-up experiments would carry an inconsistent `triggered_by_rebuttal` (set) + `triggered_by_concern` (empty) shape, because the `set-meta` fallback only knew about the first field. The lint check makes that drift visible. With the canonical path now in place, `/rebuttal --scaffold-followups` produces consistently-paired records on first write — no backfill needed, and any future drift gets caught at lint time.

### Status

C-section follow-up tooling: **3 of 4 done**.

| Item | Status |
|------|--------|
| `tools/discover.py from-bio-anchor` (C2) | ⏳ pending — last remaining |
| `skills/exp-run/references/templates/...` (C7) | ✅ done earlier |
| `skills/paper-draft/references/templates/...` (C10) | ✅ done earlier |
| `/exp-design --triggered-by-rebuttal` (C11) | ✅ **done in this entry** |

Only the C2 `discover from-bio-anchor` subcommand remains. It builds on the already-implemented bio fetchers (`fetch_pubmed.py`, `fetch_crossref.py`, `fetch_europepmc.py`, `fetch_biorxiv.py`) and adds a single subcommand to `tools/discover.py` that resolves DOI/PMID/bioRxiv-DOI inputs and merges per-channel candidate lists with the existing S2 / DeepXiv channels under canonical-id dedup.


---

## 2026-05-11 — A1 minimal + A5 slice promoted to source-of-truth (pilot merge)

**Scope**: smallest additive slice of Section A that unlocks `[[ternarydb]]`-style wikilinks in
the demo. Does not touch skill prompts or graph rules.
**Status**: **A1 (minimal) and A5 (single-experiment slice) merged**. Full A1 (auto-create on
ingest) and full A5 (all 8 experiments rewired, plus extended `setup` bio fields) remain
deferred — they depend on C1 / C2 skill prompt changes that are still drafted.

### A1 — minimal: `datasets/` registered as 10th entity

**Where**:
- `runtime/schema/entities.yaml`: appended `datasets:` block with fields `title`, `slug`,
  `aliases`, `tags`, `maturity` (stable | active | emerging | deprecated), `access` (public |
  registration | restricted | wet-lab-derived), `versions` (list_object, no inner item spec for
  pilot), `canonical_url`, `license`, `key_papers` (list_link → papers), `key_concepts`
  (list_link → concepts), `date_updated`. Loader picks it up automatically: `ENTITY_DIRS` is now
  10 entries.
- `runtime/templates/datasets.md.tmpl`: new file with body sections `## Overview` / `## Versions`
  / `## Access and licensing` / `## Schema and entries` / `## Known caveats` /
  `## Used by experiments` / `## Key papers`.
- `docs/runtime-page-templates.{en,zh}.md`: heading bumped from "9 Page Types" to "10 Page
  Types"; `datasets/{slug}.md` section added with the same frontmatter shape.
- `wiki/datasets/ternarydb.md`: first dataset page authored. Anchors 8 experiments under the
  PTM-aware degrader pipeline. Version metadata and canonical URL left as TBD pending
  DeepTernary paper ingest.
- `wiki/index.md`: `datasets:` block added (the A1 follow-up note from 2026-05-03 is now
  resolved for the live wiki).
- `xref.yaml`: **not yet updated**. The pilot keeps the experiment→dataset reverse link manual
  (the dataset page lists `## Used by experiments` by hand). Auto-reverse needs a nested-field
  xref rule (`setup.dataset → datasets.??`), which is a follow-up.

**Why merge now**: bio researchers ingesting PROTAC / PTM / ternary-complex papers will keep
referencing TernaryDB, PROTAC-DB, dbPTM, AlphaFold-DB. Without a first-class entity, those
references decay to plain text. The minimal slice gives them a canonical page now; the rest of
A1 (auto-detection in `/ingest`) can land when C1 lands.

### A5 — slice: `setup.dataset` wikilink, one experiment

**Where**:
- `wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md`: `setup.dataset`
  rewritten from the plain string `"TernaryDB CRBN+VHL test split (the same split used in the
  DeepTernary paper)"` to `"[[ternarydb]] CRBN+VHL test split (the same split used in the
  DeepTernary paper)"`. The schema type stays `str` — wikilinks are still strings, just
  Obsidian-resolvable.
- The other 7 experiments (`phase0-noise-floor-calibration-...`,
  `calibrated-deltapternary-...`, the four ablations, the two robustness runs) **keep their
  plain-string `setup.dataset`** as the backward-compat demo: lint accepts both forms.

**Why merge now**: storyboard scene 3 in `DEMO_PLAN.{en,zh}.md` v2 wants a live demo of
`setup.dataset` as a wikilink. The single-experiment slice gives that without forcing the
full A5 (extended `setup` with `in_silico_or_wet`, `species`, `cell_line`, `assay_type`,
`force_field`, …), which depends on C2's `/exp-design` prompt update to populate the new fields.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import ENTITY_DIRS; print(ENTITY_DIRS)"` | 10 entries; `datasets` last |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / informational only |
| `wiki/datasets/ternarydb.md` resolvable from `experiments/deepternary-baseline-...md` | yes — Obsidian-style `[[ternarydb]]` |
| Backward-compat: 7 sibling experiments untouched | yes — `setup.dataset` plain-string still parses |

### What is intentionally NOT in this pilot

- `i18n/{en,zh}/CLAUDE.md` — slim form does not enumerate page types; no edit needed. Active
  root `CLAUDE.md` not regenerated (no `setup.sh --lang` run).
- `runtime/schema/xref.yaml` — no rule added for the experiment→dataset reverse. Manual `##
  Used by experiments` section maintained by hand.
- `.claude/skills/*` — no prompt changes. `/ingest` will still produce plain-string dataset
  mentions; `/exp-design` will still write `estimated_hours`. C1, C2 deferred.
- A2, A3, A4, A6, A7, A8 — all remain `drafted` under `docs/bio-adaptation/section-a/`.

### Rollback

Single `git revert` of the pilot commit restores the 9-entity state. No data destroyed:
`wiki/datasets/ternarydb.md` is the only net-new content; the one experiment's `setup.dataset`
goes back to plain string.

---

## 2026-05-11 — A6 pilot merge: structured `estimated_cost` block

**Scope**: A6 (structured experiment cost), additive merge to source-of-truth. Companion to
the A1+A5 pilot landed earlier the same day.
**Status**: **A6 merged in additive form**. `estimated_hours` remains valid and populated on
every experiment (backward-compat fallback); new structured block `estimated_cost` is now the
canonical place for non-trivial budgets. Skill prompt C2 (`/exp-design`) still emits the legacy
shape until C2 lands.

### Where

- `runtime/schema/entities.yaml`: `experiments.fields.estimated_cost` added as an `object`
  with optional sub-fields `gpu_hours`, `cpu_hours`, `md_wallclock_hours`, `wet_lab_usd`,
  `fte_weeks`, `dataset_access_lead_time_days`. Inline comment marks the field bio-A6 and
  notes C3 (bio-lint) will eventually warn when only `estimated_hours` is set on a bio-domain
  experiment.
- `docs/runtime-page-templates.{en,zh}.md`: `experiments/{slug}.md` template extended with the
  `estimated_cost` block (all defaults 0).
- All 8 `wiki/experiments/*.md` rewritten: each frontmatter now carries an explicit
  `estimated_cost` block with realistic per-experiment values. `estimated_hours` is kept and
  annotated `# legacy; superseded by estimated_cost.gpu_hours below`.

### Per-experiment budget

| Experiment | gpu | cpu | md_wallclock | wet_lab_usd | fte_weeks |
|------------|---:|---:|---:|---:|---:|
| `deepternary-baseline-ternarydb-crbn-vhl-reproduction` | 4 | 0 | 0 | 0 | 0.25 |
| `phase0-noise-floor-calibration-deepternary-ptm-perturbations` | 24 | 4 | 0 | 0 | 1.0 |
| `calibrated-deltapternary-phospho-protac-ranking` | 16 | 2 | 0 | 0 | 0.75 |
| `ablation-uncalibrated-vs-calibrated-deltapternary` | 4 | 1 | 0 | 0 | 0.25 |
| `ablation-boltz2-ptm-vs-md-relaxed-route` | 4 | 1 | **8** | 0 | 0.5 |
| `ablation-deepternary-vs-protac-stan-scorer` | 16 | 2 | 0 | 0 | 0.5 |
| `robustness-cross-ptm-type-ubiq-methyl` | 16 | 2 | 0 | 0 | 0.5 |
| `robustness-mutant-isoform-track-y220c-r175h` | 12 | 1 | 0 | 0 | 0.5 |
| **TOTAL** | **96** | **13** | **8** | **0** | **4.25** |

GPU + MD wall-clock total: **104 h** — matches the ≈104 GPU-h headline in the 2026-05-02
`/exp-design` log and in `ideas/ptm-aware-degrader-target-nomination.md`. **MD wall-clock now
visible** (previously hidden inside the boltz2 ablation's collapsed `estimated_hours: 12`).
All current experiments are compute-only — `wet_lab_usd: 0` across the board. All datasets are
public (TernaryDB, PROTAC-DB, DegronMD reachable) — `dataset_access_lead_time_days: 0`.

### Verification

| Check | Result |
|-------|--------|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 — same blue informational set as before |
| YAML parses on all 8 experiment files | yes; `estimated_cost.gpu_hours` reads as float |
| `sum(estimated_hours) == sum(estimated_cost.gpu_hours + .md_wallclock_hours)` | yes (104 = 104); no budget drift introduced |
| Backward-compat: `estimated_hours` still populated | yes; legacy consumers (lint defaults, future migrations) still see it |

### What is intentionally NOT in this pilot

- **`.claude/skills/exp-design/`** unchanged. The next `/exp-design` invocation will still emit
  `estimated_hours` only. C2 SKILL.md update is drafted in `docs/bio-adaptation/section-c/skills/exp-design/`.
- **No lint enforcement** of "if domain is bio, `estimated_cost` should be present". That is
  C3 (bio-lint) territory.
- **`estimated_hours` not deprecated yet** in the schema (no `deprecated: true` flag —
  loader.py doesn't support that). Field comment notes legacy status.

### Rollback

`git revert <pilot-A6-commit>` restores single-number budgets. No data destroyed: the
`estimated_hours` field on every experiment is still populated with the original value.

---

## 2026-05-11 — B3 pilot merge: `dataset_version_used` provenance edge

**Scope**: Section B's smallest demoable slice. Lights up ternarydb as a connected graph node in
the SPA network view, enabling storyboard scene 4's "bio relation edges" caption to point at a
real edge rather than a static mockup. Depends on the earlier A1 minimal pilot (datasets/ entity).
**Status**: **B3 merged in minimal form**. The `dataset_version_used` edge type is registered;
one real edge (`deepternary-baseline → ternarydb`) is written. Typed `metadata.version`
attribute (the full B3 form) is **deferred** — see "What is intentionally NOT in this pilot"
below.

### Where

- `runtime/schema/edges.yaml`: appended `dataset_version_used` block. Endpoints `from:
  experiments, to: datasets`. Direction directed. Workflow provenance. Attributes:
  `confidence` (enum high/medium/low, required) and `evidence` (str, required). Loader picks
  it up automatically: total registered edge types goes 21 → 22.
- `wiki/graph/edges.jsonl`: one real edge added via
  `tools/research_wiki.py add-edge`:

  ```json
  {"from": "experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction",
   "to": "datasets/ternarydb",
   "type": "dataset_version_used",
   "confidence": "high",
   "evidence": "version: v1 (release alongside DeepTernary, Nat. Commun. 2025); CRBN+VHL test split — the exact split reproduced by this experiment",
   "date": "2026-05-11"}
  ```
- `wiki/graph/context_brief.md`, `wiki/graph/open_questions.md`: rebuilt by
  `tools/research_wiki.py rebuild-*`.

### Demo impact

| Before | After |
|---|---|
| `wiki/datasets/ternarydb.md` exists but is orphan in the SPA network view (no edge points to it) | ternarydb is now a connected node — `tools/serve.py /api/graph` returns the new edge; SPA renders it adjacent to `experiments/deepternary-baseline-...` |
| Storyboard scene 4 had 0 bio relation edges live; B1/B2/B3 all caption-only | 1 B3 edge live; B1/B2 still caption-only |
| Edge type count: 21 | 22 (`dataset_version_used` joins the set) |

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 22 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (informational set unchanged) |
| `python tools/research_wiki.py add-edge wiki --from ... --type dataset_version_used --confidence high --evidence ...` | `{"status": "ok", ...}` |
| `grep dataset_version_used wiki/graph/edges.jsonl` | 1 line; endpoints match `experiments → datasets` |
| `tools/serve.py /api/graph` returns the edge | yes; SPA shows ternarydb as a connected node |

### What is intentionally NOT in this pilot

- **Typed `metadata.version` attribute on the edge.** The full Section B3 plan declares
  `metadata: {version: str, required}` as a top-level edge attribute. Implementing that
  requires extending `tools/research_wiki.py add-edge` CLI to accept `--metadata KEY=VALUE`
  or per-attribute flags. Skipped for pilot risk-reduction — version info is currently
  encoded in the `evidence` string (parseable with a regex).
- **C3 (bio-lint) version-drift check.** Designed in `docs/bio-adaptation/section-c/skills/check/`
  but not implemented. Once C3 lands as `tools/lint_bio.py`, it can either parse evidence
  text or (if `metadata.version` ships first) read the typed attribute.
- **Bulk add for the other 7 experiments.** Only the deepternary-baseline experiment gets a
  `dataset_version_used` edge. The 7 sibling experiments (phase0-noise-floor, calibrated-...,
  4 ablations, 2 robustness runs) reference TernaryDB by plain-string `setup.dataset` and have
  no outgoing dataset-version edge. Bulk migration belongs with full B3 + C3.
- **B1 (bio relation edges) and B2 (validation/translation edges).** Both still drafted under
  `docs/bio-adaptation/section-b/`. Adding them requires more design work on typed metadata
  for `clinical_trial_for {nct_id, phase}`, `fda_approved_for {indication, year}`,
  `validates_in_species {species}`, and 10 B1 relation verbs.

### Rollback

`git revert <pilot-B3-commit>` removes the edge type registration. The single live edge in
`wiki/graph/edges.jsonl` can be cleaned up with a follow-up `rebuild` or hand-edit (graph/
is auto-generated; removing the now-orphan edge is safe per the conventions.yaml `tools_only`
rule).

---

## 2026-05-11 — A7 pilot merge: optional `grade` field on ideas

**Scope**: Section A7's smallest demoable slice. Adds top-level optional GRADE-style evidence
grade on ideas/ frontmatter. The full A7 (per-evidence-edge grade attribute, plus extended
evidence verbs like `wet_lab_validated`, `mechanistic_basis`, `clinical_validated`,
`correlative`, `predicts`) needs add-edge CLI extension and is deferred.
**Status**: **A7 minimal merged**. Idea-page-level grade is live; per-edge grade deferred.

### Where

- `runtime/schema/entities.yaml`: `ideas.fields.grade` added as optional enum
  (`very-low | low | moderate | high`). Schema-additive: existing ideas without `grade`
  remain valid.
- `wiki/ideas/ptm-aware-degrader-target-nomination.md`: `grade: low` populated. Rationale
  (in inline yaml comment): "load-bearing premise (phospho-perturbation > noise floor)
  is empirically unverified. Anchor claim ptm-protein-isoforms-enable-selective-drug
  confidence is 0.6 (weakly_supported). Mechanistic basis exists, but thin positive set
  (< 10 truly PTM-selective experimental degraders) bounds empirical evidence to 'low'
  per GRADE conventions."
- `docs/runtime-page-templates.{en,zh}.md`: `ideas/{slug}.md` template extended with
  optional `grade:` field.

### What is intentionally NOT in this pilot

- **Per-evidence-edge GRADE attribute.** Full A7 puts `grade` on each `supports` / `tested_by`
  edge so different evidence lines can have different grades. Requires extending
  `tools/research_wiki.py add-edge` CLI to accept `--grade` (or generic attribute flags).
  Skipped for pilot risk-reduction.
- **Extended evidence-verb edge types** (`wet_lab_validated`, `clinical_validated`,
  `mechanistic_basis`, `correlative`, `predicts`). Could be registered later as new edge
  types alongside the existing `supports`/`contradicts` set. Deferred — design needed for
  how they interact with confidence + GRADE.
- **Populating `grade` on the other 21 ideas.** Most were migrated from claims with no
  per-claim GRADE input; backfilling is /novelty C5 territory.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import VALID_VALUES; print(VALID_VALUES['ideas.grade'])"` | `{'very-low', 'low', 'moderate', 'high'}` |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (unchanged informational set) |
| `grep '^grade:' wiki/ideas/ptm-aware-degrader-target-nomination.md` | `grade: low` |

---

## 2026-05-11 — A3 minimal pilot merge: DOI + PMID on `papers/`

**Scope**: Section A3's smallest slice. Adds two of the eight A3 bio-identifier fields
(`doi`, `pmid`) to `papers/` frontmatter as optional, and populates them on one paper.
Full A3 (biorxiv, pdb_ids, uniprot_ids, nct_ids, gene_symbols, species — the structured
bio anchors) is deferred to /ingest C1 because populating those at scale needs bio NER
during ingestion, not hand-editing.
**Status**: **A3 minimal merged**. DOI + PMID live on one paper; remaining 10 papers and
6 other A3 fields deferred.

### Where

- `runtime/schema/entities.yaml`: `papers.fields.doi` and `.pmid` added as optional `str`.
  Both additive: papers without either field remain valid.
- `wiki/papers/musitedeep-deep-learning-based-webserver-protein.md`: frontmatter populated
  with `doi: "10.1093/nar/gkaa275"`, `pmid: "32324217"` — the canonical Nucleic Acids
  Research 2020 publication identifiers.
- `docs/runtime-page-templates.{en,zh}.md`: `papers/{slug}.md` template extended with
  the two new fields.

### What is intentionally NOT in this pilot

- **Other A3 fields**: `biorxiv` (DOI suffix), `pdb_ids` (introduced structures),
  `uniprot_ids` (characterised proteins), `nct_ids` (referenced clinical trials),
  `gene_symbols` (HGNC), `species` (model organisms). All need bio NER in `/ingest` (C1)
  to populate at scale. Hand-populating is OK for the pilot's one demonstration paper
  but adding 6 more empty fields just adds template noise without value.
- **Other 10 papers** in the wiki. Their DOI/PMID values aren't all easily available;
  /ingest C1 should backfill systematically when it lands.

### Verification

| Check | Result |
|-------|--------|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E '^(doi|pmid):' wiki/papers/musitedeep-deep-learning-based-webserver-protein.md` | `doi: "10.1093/nar/gkaa275"`, `pmid: "32324217"` |

---

## 2026-05-11 — B1 minimal pilot merge: 2 bio relation edge types + 2 live edges

**Scope**: Section B1's smallest demoable slice. Registers two of the ten B1 verbs
(`targets_protein`, `ubiquitinates`) with broad endpoints (`from: '*', to: concepts`)
under the A2-light "proteins-as-concepts" convention. Writes 2 live edges.
**Status**: **B1 minimal merged**. The remaining 8 verbs (`binds`, `inhibits`, `activates`,
`degrades`, `phosphorylates`, `methylates`, `acetylates`, `is_substrate_of`) and the
tightened endpoint contract (against a future `proteins/` entity from A2-heavy) are
deferred.

### Where

- `runtime/schema/edges.yaml`: appended two new edge types:
  - `targets_protein` — `from: '*'`, `to: concepts`, directed, workflow `ingest`, attrs
    confidence + evidence.
  - `ubiquitinates` — same shape.
  Total edge types: 22 → 24.
- `wiki/graph/edges.jsonl`: two live edges written via `tools/research_wiki.py add-edge`:
  1. `papers/ubiquitin-ligases-oncogenic-transformation-cancer-therapy --targets_protein-->
     concepts/ubiquitin-ligase-e3` — confidence high, evidence describes the paper's framing
     of E3 ligases as druggable oncogenic targets.
  2. `concepts/ubiquitin-ligase-e3 --ubiquitinates--> concepts/ubiquitylation` — confidence
     high, captures the canonical enzymatic relationship between E3 ligases and the
     ubiquitylation reaction.

### Demo impact

| Before | After |
|---|---|
| Storyboard scene 4: 1 B3 edge live (`dataset_version_used`); B1 + B2 caption-only | 1 B3 + 2 B1 edges live; only B2 (validation/translation) remains caption-only |
| Edge type count: 22 | 24 (B1 grows from 0/10 to 2/10) |

### What is intentionally NOT in this pilot

- **Other 8 B1 verbs**: `binds`, `inhibits`, `activates`, `degrades`, `phosphorylates`,
  `methylates`, `acetylates`, `is_substrate_of`. Each is a small additive YAML block but
  the pilot keeps the surface small for fast revert.
- **Tightened endpoints against a `proteins/` entity** (A2 heavy option). The pilot uses
  `to: concepts` because proteins-as-concepts (A2 light) is the current convention.
- **Auto-extraction in /ingest** (C1). Edges added manually for the pilot; /ingest C1
  would emit B1 edges automatically once bio NER lands.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 24 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E 'targets_protein|ubiquitinates' wiki/graph/edges.jsonl` | 2 lines |

### Rollback

`git revert <pilot-commit>` removes A7 + A3 + B1 minimal slices together. None of the
fields/edges is referenced from existing schema validation paths, so revert is a clean
delete.

---

## 2026-05-11 — B1 full pilot merge: remaining 8 verbs registered + 1 new live edge

**Scope**: Promote the B1 minimal pilot (2/10 verbs from earlier this day) to full coverage —
all 10 B1 bio relation verbs are now registered in `runtime/schema/edges.yaml`. One additional
live edge added to demo the new `binds` verb. The other 7 newly-registered verbs (`inhibits`,
`activates`, `degrades`, `phosphorylates`, `methylates`, `acetylates`, `is_substrate_of`) are
registered but **carry zero live edges** — the wiki does not yet have kinase / phosphatase /
acetyltransferase / specific-substrate concept pages to anchor them against. They become
populable as soon as C1 bio NER lands.
**Status**: **B1 fully registered**. Schema surface for all 10 verbs is complete; live edge
coverage is 3/10 verbs (`targets_protein` ×1, `ubiquitinates` ×1, `binds` ×1) with the
remaining 7 verbs awaiting bio-NER-driven content.

### Where

- `runtime/schema/edges.yaml`: appended 8 new edge-type blocks (`binds`, `inhibits`,
  `activates`, `degrades`, `phosphorylates`, `methylates`, `acetylates`, `is_substrate_of`).
  All share the same shape as the earlier `targets_protein` / `ubiquitinates`:
  `endpoints: { from: '*', to: concepts }`, `direction: directed`, `workflow: ingest`,
  attributes `confidence` (enum, required) + `evidence` (str, required). Total registered
  edge types: 24 → 32.
- `wiki/graph/edges.jsonl`: one additional live edge added via `tools/research_wiki.py
  add-edge`:
  - `concepts/posttranslational-modification-inspired-drug-design --binds-->
    concepts/ubiquitin-ligase-e3` (confidence high, evidence describes PROTAC E3-recruitment
    as the load-bearing molecular event in ternary-complex mechanism).
- `wiki/graph/context_brief.md`, `wiki/graph/open_questions.md`: rebuilt.

### Demo impact

| Before | After |
|---|---|
| B1 verbs registered: 2/10 | **10/10** |
| Live B1 edges: 2 | **3** (`targets_protein`, `ubiquitinates`, `binds`) |
| Storyboard scene 4: caption lists 8 deferred verbs | caption can drop the "deferred verbs" overlay (only B2 remains caption-only) |
| Total edge types: 24 | **32** |

### What is intentionally NOT in this pilot

- **Live edges for 7 of the 10 verbs.** `inhibits` / `activates` / `degrades` /
  `phosphorylates` / `methylates` / `acetylates` / `is_substrate_of` are registered but
  zero live edges exist. Anchoring them requires either:
  - bio NER auto-extraction in `/ingest` (C1) — drafted
  - additional concept pages for specific kinases, phosphatases, acetyltransferases,
    and substrate proteins (A2 heavy option — `proteins/` as separate entity type)
- **Tightened `to:` endpoint against a `proteins/` entity**. Still `to: concepts` per
  A2 light convention.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 32 |
| All 10 B1 verbs in VALID_EDGE_TYPES | yes (10/10) |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E '"type": "(targets_protein\|binds\|ubiquitinates\|...)"' wiki/graph/edges.jsonl` | 3 lines |

### Rollback

`git revert <pilot-commit>` removes the 8 newly-registered edge types and the `binds` live
edge. The earlier B1 minimal pilot's 2 verbs and 2 live edges are NOT in this revert window
(they were merged separately).

---

## 2026-05-11 — B2 minimal pilot merge: 3 validation/translation edge types registered

**Scope**: Promotes Section B from partial to fully schema-registered (14/14 edge types).
Adds B2 validation/translation edges (`clinical_trial_for`, `fda_approved_for`,
`validates_in_species`) with the same minimal-pilot shape as B1 / B3 — `confidence` +
`evidence` attributes only, typed metadata (`nct_id`, `phase`, `indication`, `year`,
`species`) encoded in the evidence string for now.
**Status**: **B2 schema fully registered**. Zero live B2 edges — the wiki currently has
no clinical-trial or FDA-approval content to anchor against. Edges become populable as
/ingest (C1) lands bio NER for clinical-translation papers.

### Where

- `runtime/schema/edges.yaml`: appended 3 new edge-type blocks:
  - `clinical_trial_for` — `endpoints: { from: '*', to: concepts }`, directed, workflow
    `evidence`, attrs confidence + evidence. Section B2 plan calls for typed
    `metadata.nct_id` and `metadata.phase`; pilot encodes them in evidence string.
  - `fda_approved_for` — same shape. B2 plan calls for `metadata.indication` and
    `metadata.year`; encoded in evidence string for pilot.
  - `validates_in_species` — same shape. B2 plan calls for `metadata.species`; encoded
    in evidence string for pilot.

  Total registered edge types: 32 → 35.

### Demo impact

| Before | After |
|---|---|
| Section B registration: 11/14 (B1 full + B3 minimal; B2 drafted) | **14/14** (B1 full + B2 minimal + B3 minimal) |
| Storyboard scene 4 caption: "B2 still drafted" | "B2 schema registered but awaiting bio-clinical content + typed metadata extension" |
| Total edge types: 32 | **35** |

### Section B coverage matrix

| Verb family | Verbs registered | Live edges | Typed metadata? |
|------|---|---|---|
| B1 (bio relations, 10 verbs) | 10/10 | 3 (`targets_protein`, `ubiquitinates`, `binds`) | n/a (confidence + evidence only) |
| B2 (validation/translation, 3 verbs) | 3/3 | 0 | deferred (encoded in evidence string for now) |
| B3 (dataset-version provenance, 1 verb) | 1/1 | 1 (`dataset_version_used`) | deferred (encoded in evidence string for now) |
| **Section B total** | **14/14** | **4** | **0/14 typed; 14/14 evidence-string-encoded** |

### What is intentionally NOT in this pilot

- **Live B2 edges.** Our wiki has no clinical-trial or FDA-approval content. The 4 example
  edges in `docs/bio-adaptation/preview/bio-edges-sample.jsonl` predate B2 minimal and
  cover B1-shaped relations, not B2 — adding B2 sample edges to that preview file is a
  small follow-up if storyboard scene 4 wants caption material for B2.
- **Typed `metadata.*` attributes** on any B1 / B2 / B3 edge. All three families currently
  share the same minimal `confidence + evidence` shape. Full Section B with typed metadata
  requires extending `tools/research_wiki.py add-edge` to accept `--metadata KEY=VALUE`
  or per-attribute flags (~30 lines of Python). Until then, version / nct_id / phase /
  indication / year / species values live as substrings inside the evidence field, parsable
  with a regex.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 35 |
| All 14 Section-B edge types registered | yes (B1 ×10 + B2 ×3 + B3 ×1) |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

### Rollback

`git revert <pilot-commit>` removes the 3 newly-registered B2 edge types. No live edges
were added, so revert is a clean schema-only delete.

---

## 2026-05-11 — `tools/research_wiki.py add-edge` extended with `--metadata KEY=VALUE`

**Scope**: First Python code change of the bio-adaptation work. All prior pilot merges
(A1/A3/A5/A6/A7 minimal + B1 full + B2 minimal + B3 minimal) were YAML/markdown-only and
relied on encoding typed metadata inside the `evidence` string. This change unlocks the
typed `metadata.*` form that the original Section B2/B3 design intended.
**Status**: **CLI extension merged**. Two new live edges added using the new flag (one B2,
one B3 — see below). Existing edges from earlier pilots keep their evidence-string encoding
(no remove-edge subcommand exists; deduping prevents in-place rewrite).

### Where

- `tools/research_wiki.py`:
  - `add_edge(...)` signature extended with `metadata: dict | None = None` keyword arg.
    When non-empty, serialized into the edge JSON record as a nested `"metadata": {...}`
    object alongside `evidence` / `confidence` / `date`.
  - argparse for the `add-edge` subcommand grew one new flag: `--metadata KEY=VALUE`
    (`action="append"`, repeatable). Example invocation:

    ```bash
    python tools/research_wiki.py add-edge wiki \
      --from papers/musitedeep-... --to concepts/... --type validates_in_species \
      --confidence high --evidence "..." \
      --metadata species=human --metadata source_db=uniprotkb-swissprot
    ```
  - CLI dispatcher parses each `KEY=VALUE` pair into a dict and passes to `add_edge`.
- `wiki/graph/edges.jsonl`: two new live edges that exercise `--metadata`:
  1. `papers/musitedeep-deep-learning-based-webserver-protein --validates_in_species-->
     concepts/post-translational-modification-site-prediction` — confidence high, evidence
     describes MusiteDeep's UniProtKB/Swiss-Prot human PTM training set, metadata
     `{species: human, source_db: uniprotkb-swissprot}`. **First live B2 edge.**
  2. `experiments/phase0-noise-floor-calibration-deepternary-ptm-perturbations
     --dataset_version_used--> datasets/ternarydb` — confidence high, evidence describes the
     Phase-0 calibration subset use, metadata `{version: v1, subset: crbn-vhl-training}`.
     **Second live B3 edge** (the first one, added in B3 minimal pilot earlier, used
     evidence-string encoding).
- `wiki/graph/context_brief.md`, `wiki/graph/open_questions.md`: rebuilt.

### Demo impact

| Before | After |
|---|---|
| Live bio edges (B1/B2/B3): 4 | **6** (added 1 B2 + 1 B3) |
| Edges with typed `metadata.*`: 0 | **2** |
| Live B2 edges: 0 | **1** (`validates_in_species` with `species: human` metadata) |
| Live B3 edges: 1 (evidence-string version) | **2** (one evidence-string, one typed-metadata) |
| Total edges: 77 | **79** |
| `add-edge` CLI capability | only confidence + evidence | + repeatable typed metadata |

### Loader still unchanged

`runtime/loader.py::validate_edge_attributes` still ignores `metadata.*`. Schema-level
validation of nested metadata against edges.yaml is deferred. This is a deliberate
incrementalism choice: the CLI extension is small and unlocks new edge content immediately;
typed nested-schema enforcement is a separate concern that C3 (bio-lint) can layer on top
when needed.

### Backward compatibility

- Edges without `metadata` continue to serialize without that field (additive).
- The B3 edge added in the earlier B3 minimal pilot keeps its evidence-string encoding —
  going forward, `--metadata` is the canonical way to record typed attributes.
- Skill prompts (C1, C2 still drafted) are untouched. They still emit confidence + evidence
  only. The CLI's new capability is available to manual `add-edge` invocations and to any
  future skill that opts in.

### Verification

| Check | Result |
|-------|--------|
| `python tools/research_wiki.py add-edge --help` | shows `--metadata KEY=VALUE` (repeatable) |
| Invalid pair: `--metadata version` (no `=`) | exits 1 with `--metadata expects KEY=VALUE` |
| Edge JSON with metadata | `{"...", "metadata": {"species": "human", "source_db": "uniprotkb-swissprot"}}` |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| Live bio edges in graph | 6 (3 B1 + 1 B2 + 2 B3) |

### What is intentionally NOT in this change

- **`remove-edge` subcommand.** No way to delete the legacy evidence-string-encoded B3 edge
  short of hand-editing edges.jsonl (which violates the `tools_only` rule on `wiki/graph/`).
  Removed as needed in a future commit if it matters.
- **Nested-metadata schema in `edges.yaml`.** B2/B3 edge types still declare only
  `confidence` + `evidence`. Adding `metadata: { type: object, fields: {...} }` blocks
  would also require extending `validate_edge_attributes` to recurse — deferred.
- **Type coercion** for metadata values. `--metadata phase=II` produces `{"phase": "II"}`
  (string), `--metadata year=2024` produces `{"year": "2024"}` (string). All values are
  strings. Numeric/enum coercion is a downstream concern when schema validation lands.

### Rollback

`git revert <pilot-commit>` reverts both the CLI extension and the 2 new live edges. The
legacy B3 edge from the B3 minimal pilot is unaffected.

---

## 2026-05-11 — C1 minimal pilot merge: bio-aware `/ingest` Step 2.5

**Scope**: First Section C item to land. Adds a lightweight bio identifier extraction step
to `/ingest` so the LLM agent running ingestion populates the A3 minimal frontmatter fields
(`doi`, `pmid`) and upgrades plain-text dataset mentions into `[[{slug}]]` wikilinks against
the live `wiki/datasets/` directory (A1 minimal).

**Status**: **C1 minimal merged in prompt-only form**. The full C1 design (PubMed /
EuropePMC / CrossRef fetcher tools, `tools/extract_bio_ner.py` structured NER, JATS-XML
pipeline, DOI / PMID / bioRxiv / PMC URLs as accepted `/ingest` source inputs) is **deferred**
— those planned Python tools are not yet implemented. The minimal slice relies on the LLM
agent's own in-prompt NER capability for bio-identifier extraction.

### Where

- `i18n/en/skills/ingest/SKILL.md`: inserted a new `### Step 2.5: Bio identifier extraction
  (minimal C1)` block between Step 2 (Paper identity and enrichment) and Step 3 (Write the
  paper page). The block instructs the agent to:
  1. Populate `doi` and `pmid` frontmatter fields on bio-domain papers when the values can
     be read from body / metadata sources — never fabricate, leave empty when unsure. Other
     A3 fields (`biorxiv`, `pdb_ids`, `uniprot_ids`, `nct_ids`, `gene_symbols`, `species`)
     stay deferred to full C1.
  2. Upgrade plain-text dataset mentions to `[[{slug}]]` wikilinks when an existing
     `wiki/datasets/{slug}.md` page matches by title or aliases. Do not create new dataset
     pages in this pilot.
- `i18n/zh/skills/ingest/SKILL.md`: mirror Chinese version of the same Step 2.5.
- `.claude/skills/ingest/SKILL.md`: synced from `i18n/en/` (English active locale; the user
  can run `./setup.sh --lang zh` to switch).

### Demo impact

| Before | After |
|---|---|
| `/ingest` produces papers with empty `doi`/`pmid` even when the source has them | `/ingest` populates `doi`/`pmid` for bio papers (e.g. the musitedeep page would have been correct on first ingest, not patched post-hoc by A3 minimal) |
| `/ingest` writes plain-text "TernaryDB" in body sections | `/ingest` writes `[[ternarydb]]` when the page exists in `wiki/datasets/` |
| Section C status: 0/9 items merged | **1/9** (C1 minimal) |
| `/ingest` SKILL.md line count | 297 → 327 (+30 lines for the new step) |

### What is intentionally NOT in this pilot

- **The 5 planned bio fetcher tools** (`fetch_crossref.py`, `fetch_pubmed.py`,
  `fetch_europepmc.py`, `fetch_biorxiv.py`, `extract_bio_ner.py`). The full C1 calls them
  via Bash; the minimal pilot uses in-prompt LLM NER instead.
- **DOI / PMID / bioRxiv / PMC URLs as `/ingest` source inputs**. Still requires `.tex` / `.pdf`
  / arXiv URL today. Full C1 will add the bio-identifier resolver chain (CrossRef → PubMed →
  EuropePMC → bioRxiv → DeepXiv → Semantic Scholar).
- **Auto-create new `wiki/datasets/{slug}.md` pages.** The minimal pilot only upgrades to
  wikilinks when the page already exists. Page creation is conservative — deferred to `/edit`
  or full C1 (importance ≥ 4 gating).
- **B1 bio relation edge auto-extraction.** Full C1 emits `targets_protein`, `phosphorylates`,
  etc., automatically from body NER + concept linkage. Minimal pilot leaves these to manual
  `add-edge` invocations (which is how the 3 live B1 edges were authored).

### Verification

| Check | Result |
|-------|--------|
| `diff -q .claude/skills/ingest/SKILL.md i18n/en/skills/ingest/SKILL.md` | identical (synced) |
| `grep "Step 2.5" .claude/skills/ingest/SKILL.md` | match found |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (informational set unchanged) |
| Active SKILL.md line count | 327 (up from 297) |

### Rollback

`git revert <pilot-commit>` removes the Step 2.5 block from both i18n languages and the
active `.claude/skills/ingest/SKILL.md`. Any wiki pages that were ingested with the new
Step 2.5 already in effect would keep their populated `doi`/`pmid` fields (those are wiki
content, separate from the skill prompt).

---

## 2026-05-11 — C2 minimal pilot merge: `/exp-design` emits A6 structured `estimated_cost`

**Scope**: Closes the A6 ↔ C2 loop. The A6 pilot earlier today added the structured
`estimated_cost` block to the experiment schema and rewrote the 8 existing experiments by
hand. C2 minimal updates the `/exp-design` SKILL.md so the next `/exp-design` invocation
populates `estimated_cost` directly instead of only the legacy `estimated_hours` — no more
hand-rewriting needed.
**Status**: **C2 minimal merged in prompt-only form**. Full C2 (automated detection of MD
wall-clock from `setup.framework`, wet-lab cost from `setup.hardware`, dataset-access
lead-time from the resolved `[[dataset]]` page's `access` tier, fixed budget-cut order) is
**deferred** — the planned automated inference logic is not yet in the prompt; the minimal
pilot relies on the LLM agent's own judgment to populate sub-fields based on the experiment
design.

### Where

- `i18n/en/skills/exp-design/SKILL.md`: in Step 6's experiment frontmatter template,
  inserted the structured `estimated_cost` block right after the legacy `estimated_hours: 0`
  line. The block lists all 6 sub-fields (`gpu_hours`, `cpu_hours`, `md_wallclock_hours`,
  `wet_lab_usd`, `fte_weeks`, `dataset_access_lead_time_days`) with per-sub-field inline
  guidance for when each value is non-zero.
- `i18n/zh/skills/exp-design/SKILL.md`: mirror Chinese version of the same block.
- `.claude/skills/exp-design/SKILL.md`: synced from `i18n/en/`.

### Demo impact

| Before | After |
|---|---|
| `/exp-design` writes `estimated_hours: 0`, leaving `estimated_cost` absent — A6 schema field is empty unless someone hand-rewrites the page | `/exp-design` writes both `estimated_hours: 0` (legacy) AND the 6-sub-field `estimated_cost` block, populated from the agent's Step 3 / Step 4 budget breakdown |
| The 8 existing PTM-aware degrader experiments were hand-rewritten in the A6 pilot | The next `/exp-design` invocation produces A6-compliant pages with no hand-rewrite — A6 ↔ C2 loop closed |
| Section C status: 1/9 (C1 minimal) | **2/9** (C1 + C2 minimal) |
| `/exp-design` SKILL.md line count | 351 → 366 (+15 lines for the estimated_cost block + inline guidance) |

### Pairing with A6

The A6 pilot's per-experiment budget breakdown (sum gpu+md=104h, fte 4.25 weeks) is now
**reproducible** for new experiments going through `/exp-design`. The agent reads the same
sub-fields off the experiment design (model / dataset / hardware / framework) and emits them
in the structured block instead of collapsing into a single hours figure.

### What is intentionally NOT in this pilot

- **Automated inference of sub-fields from `setup.framework`**. Full C2 would map e.g. "MD
  pipeline with AMBER ff14SB + GROMACS" → `md_wallclock_hours > 0`. Minimal pilot leaves
  this to the LLM agent's judgment.
- **Automated `dataset_access_lead_time_days` lookup** from the resolved `[[dataset]]` page's
  `access` tier (`public` → 0, `registration` → ~7, `restricted` → ~30). Same deferral —
  needs structured access-tier reading.
- **Fixed budget-cut order**. Full C2 plan: when total exceeds `--budget`, cut in the order
  `cross_context → robustness → dose_response`. Minimal pilot keeps `--budget` as today's
  unstructured cap.
- **Wet-lab handoff hooks** (C9 territory). Minimal pilot just exposes the `wet_lab_usd`
  field; downstream wet-lab tracking deferred.

### Verification

| Check | Result |
|-------|--------|
| `diff -q .claude/skills/exp-design/SKILL.md i18n/en/skills/exp-design/SKILL.md` | identical (synced) |
| `grep "bio-C2" .claude/skills/exp-design/SKILL.md` | match found |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (informational set unchanged) |
| Active SKILL.md line count | 366 (up from 351) |

### Rollback

`git revert <pilot-commit>` removes the `estimated_cost` block + bio-C2 guidance from both
i18n locales and the active `.claude/skills/exp-design/SKILL.md`. The 8 existing experiment
pages keep their A6 structured cost blocks (they are wiki content, separate from the prompt).

---

## 2026-05-11 — A2 light pilot merge: protein-anchor fields on `concepts/` + first protein concept page

**Scope**: A2 light option — extend `concepts/` schema with 4 optional fields anchoring a
concept to a specific gene product (HGNC + UniProt + PDB + species). Populates on a new
`wiki/concepts/crbn.md` page that becomes the first **specific protein** concept in the wiki
(prior protein references — p53, CRBN, VHL, MDM2, BCL-XL, BTK — were all inline plain text).
**Status**: **A2 light merged**. A2 heavy (separate `proteins/` entity type) remains deferred
until ≥50 protein concepts accumulate or graph queries demand it.

### Where

- `runtime/schema/entities.yaml`: `concepts.fields` extended with 4 optional fields:
  - `gene_symbol` (str) — HGNC symbol
  - `uniprot_id` (str) — UniProt accession
  - `pdb_ids` (list_str) — representative structures
  - `species` (list_str) — model organisms

  All optional and additive: existing concept pages (alphafold-db, ubiquitylation,
  ubiquitin-ligase-e3, …) that don't fill them stay valid.
- `wiki/concepts/crbn.md`: new concept page for Cereblon, the central CRBN-recruitment E3
  ligase in PROTAC drug discovery. Frontmatter populates `gene_symbol: CRBN`, `uniprot_id:
  Q96SW2`, `pdb_ids: [4CI1, 4CI2, 5HXB, 5FQD]`, `species: [human]`. Body sections cover
  definition, recruitment mechanism, comparison vs VHL/MDM2, the CRBN^Y384A clinical-resistance
  variant, and links back to `[[ptm-aware-degrader-target-nomination]]` /
  `[[ubiquitin-ligase-e3]]` / `[[posttranslational-modification-inspired-drug-design]]`.
- `wiki/index.md`: `crbn` added to the `concepts:` block with bio-A2 fields surfaced.
- `wiki/datasets/ternarydb.md`: `Overview` section's plain-text "CRBN+VHL subset" replaced
  with `[[crbn]]+VHL subset` (preserves the existing prose, just upgrades the dataset's first
  CRBN mention to a wikilink — necessary to clear the lint orphan check on crbn.md).
- `docs/runtime-page-templates.{en,zh}.md`: `concepts/{concept-name}.md` template extended
  with the 4 new fields and inline guidance noting they should ONLY be populated when the
  concept IS a specific gene product.
- `wiki/graph/edges.jsonl`: one additional live B1 edge added via `add-edge --metadata`:
  `concepts/posttranslational-modification-inspired-drug-design --binds--> concepts/crbn`,
  confidence high, metadata `{recruitment_ligand_class: imid, clinical_anchor:
  lenalidomide-pomalidomide}`. This is the more-specific instance of the existing
  class-level edge to `concepts/ubiquitin-ligase-e3`.

### Demo impact

| Before | After |
|---|---|
| Wiki has 0 specific-protein concept pages | **1** (crbn.md) — populated with HGNC / UniProt / PDB / species |
| Concept template documents 11 fields | 15 (the 4 new bio-A2 fields, all optional) |
| Bio relation edges: 6 | **7** (added the CRBN-specific `binds` edge) |
| Edges with typed metadata.*: 3 | **4** |
| Section A status: 5/8 items merged | **6/8** (A2 light joins A1 / A3 / A5 / A6 / A7) |

### Pairing with existing pilots

- **A2 light ↔ A1**: TernaryDB dataset page already exists (A1 minimal pilot); crbn.md plus
  the wikilink upgrade in ternarydb.md now connect CRBN-as-protein to TernaryDB-as-dataset
  at the page-content layer (the dataset's Overview text references `[[crbn]]`).
- **A2 light ↔ B1**: the new `binds` edge from PROTAC drug-class to CRBN is a *more specific*
  bio relation than the existing class-level edge to ubiquitin-ligase-e3. Both stay in the
  graph — they encode different granularities of the same mechanism.
- **A2 light ↔ B3**: the existing `dataset_version_used` edges from experiments to TernaryDB
  now indirectly anchor on CRBN via the dataset page's body wikilink.

### What is intentionally NOT in this pilot

- **A2 heavy** (separate `proteins/` entity type). The light option is the recommended start
  per the backlog ("If by 50+ protein references we want graph queries like 'drugs targeting
  kinase X', upgrade to a separate type"). Current count: 1.
- **UniProt-format lint** (e.g. ensuring `uniprot_id` matches `^[A-NR-Z][0-9][A-Z0-9]{3}[0-9]$`
  or the equivalent 10-character pattern). Belongs in C3 (bio-lint).
- **Other proteins as concept pages.** p53, VHL, MDM2, BCL-XL, BTK — still inline plain text
  in the wiki. The pilot establishes the schema; bulk creation is a follow-up that depends on
  bio NER (C1 full) for systematic extraction.

### Verification

| Check | Result |
|-------|--------|
| `python -c "from runtime.loader import ENTITIES; print([k for k in ENTITIES['concepts']['fields'] if k in ['gene_symbol','uniprot_id','pdb_ids','species']])"` | all 4 fields present |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (informational set unchanged after the wikilink upgrade in ternarydb.md) |
| `grep '\[\[crbn\]\]' wiki/datasets/ternarydb.md` | match found (clears crbn orphan check) |
| `grep -c '"to": "concepts/crbn"' wiki/graph/edges.jsonl` | 1 (the new B1 binds edge) |

### Rollback

`git revert <pilot-commit>` removes the 4 new concept fields, the crbn.md page, the
ternarydb.md `[[crbn]]` upgrade, the index entry, the template additions, and the new
B1 edge. The class-level `binds` edge to ubiquitin-ligase-e3 (from the earlier B1 full pilot)
remains intact.

---

## 2026-05-12 — A5 full pilot merge: `experiments.setup` gains 9 bio-shaped optional fields

**Scope**: The A5 slice (2026-05-11) only rewired `deepternary-baseline`'s `setup.dataset`
into a wikilink. A5 full lands the 9 bio-shaped fields the backlog enumerated for
`experiments.setup` (all optional + additive — pure-ML pages leaving them empty stay
valid), and populates the applicable non-empty values across the 8 existing experiment pages.
**Status**: **A5 full merged**. Downstream C7 (`/exp-run` setup-type routing) will key off
`in_silico_or_wet`; C8 bio-lint plans to warn when `setup.assay_type=MD` lacks `force_field`
(deferred).

### Files touched

- `runtime/schema/entities.yaml`: 9 fields added to `experiments.setup.fields` —
  `in_silico_or_wet` (enum: in_silico|wet_lab|mixed), `species` (list_str), `cell_line`,
  `assay_type`, `force_field`, `solvent_model`, `simulation_length`, `weight_version`,
  `random_seed_protocol`.
- `docs/runtime-page-templates.{en,zh}.md`: `experiments/{slug}.md` setup-block template
  extended with the new fields plus inline guidance.
- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`:
  Step 6 frontmatter template extended in lockstep.
- `wiki/experiments/*.md` (8 files): per-experiment bio fields filled. All 8 are
  in_silico human; `ablation-boltz2-ptm-vs-md-relaxed-route` carries the MD trio
  (force_field=AMBER ff14SB + phosaa14SB, solvent_model=explicit, simulation_length=50 ns);
  the others carry weight_version (Boltz-2 Jan 2026 / DeepTernary Nat Commun 2025 /
  PROTAC-STAN Adv Sci 2025) and random_seed_protocol (ranking-shuffle or bootstrap, split
  by experiment role).

### Verification

| Check | Result |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (informational set unchanged) |
| `grep -c "in_silico_or_wet" wiki/experiments/*.md \| awk -F: '{s+=$2}END{print s}'` | 8 (all 8 experiments populated) |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | identical (synced) |

Section A status: 6/8 → 7/8 (only A4 controlled vocabulary and A8 wet-lab reproducibility
metadata remain).

---

## 2026-05-12 — C4 minimal pilot merge: `/exp-design` block taxonomy gains 4 bio block types

**Scope**: `/exp-design`'s four block types (baseline / validation / ablation / robustness)
are ML-pipeline-shaped; bio-natural block types (negative_control, mechanism, dose_response,
cross_context) were absent. C4 minimal adds them to the SKILL prompt and articulates the
boundary distinction vs A–D.
**Status**: **C4 minimal merged as pure-prompt change**. Block type remains captured as a
tag (no new frontmatter enum, consistent with backlog design). Full C4 (have the
`/exp-design --review` Review LLM prompt explicitly check for "is a mechanism block missing"
etc.) deferred.

### Files touched

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`:
  Step 3 inserts a "Bio-specific block types" section after A–D, listing E negative_control /
  F mechanism / G dose_response / H cross_context with explicit boundary distinctions
  vs the nearest A–D analogue (negative_control ≠ baseline, mechanism ≠ validation,
  dose_response ≠ hyperparameter sweep, cross_context ≠ ML cross-dataset). The Step 3
  "each block carries" `type` line now lists all 8 tags as composable.

### Verification

| Check | Result |
|---|---|
| `grep "negative_control\|mechanism\|dose_response\|cross_context" .claude/skills/exp-design/SKILL.md \| wc -l` | ≥ 4 (all 4 types present) |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | identical |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

Section C status: 2/9 → 3/9.

---

## 2026-05-12 — C5 minimal pilot merge: `/exp-design` Step 1 gains wet-lab dependency detection

**Scope**: `/exp-design` Step 1 never asked "does this idea need new wet-lab data?". C5
minimal inserts a sub-step in Step 1 that scans idea hypothesis / Risks / Approach sketch
for 14 wet-lab indicator phrases; on match, prompts the user once for wet-lab access, and
the answer drives Step 3 block planning. Pairs with A5 full's `setup.in_silico_or_wet`
field.
**Status**: **C5 minimal merged as pure-prompt change**. Full C5 (concrete wet-lab block
templates, `protocol.md` sub-tree layout, wet-lab cost referencing) deferred to C7
(`/exp-run` directory layout).

### Files touched

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`:
  Step 1 inserts sub-step 3 "Detect wet-lab dependencies" after "Load relevant wiki context".
  14 trigger phrases: in cell / cellular target engagement / in vivo / tumor regression /
  binding assay / ELISA / Western blot / co-IP / cryo-EM / point mutation / knockdown /
  knockout / IC50 / Kd. Match → prompt user → record `wet_lab_planned: true|false` →
  drives Step 3 block planning and `setup.in_silico_or_wet`; no match → silent skip.

### Verification

| Check | Result |
|---|---|
| `grep "wet_lab_planned\|Detect wet-lab" .claude/skills/exp-design/SKILL.md \| wc -l` | ≥ 1 |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | identical |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

Section C status: 3/9 → 4/9. P0 backlog closeout: 0 P0 items remain on this branch
(A1/A3/A5/C1/C4/C5 all merged).

---

## 2026-05-12 — C9 minimal pilot merge: `/novelty` gains PubMed E-utilities channel

**Scope**: `/novelty` previously used WebSearch + Semantic Scholar + DeepXiv + wiki + Review LLM.
Bio prior art lives largely in PubMed (>30M abstracts) and is under-represented in Semantic
Scholar — bio prior-art collisions were under-reported. C9 minimal adds Source E
(PubMed E-utilities via WebFetch) in Step 2, full-weight for bio-shaped targets.
**Status**: **C9 minimal merged as pure-prompt change**. Full C9 (`tools/fetch_pubmed.py`
CLI with pagination + MeSH expansion + abstract NER + PMC full-text fallback) deferred —
the minimal pilot lets the agent call NCBI E-utilities URLs directly via WebFetch.

### Files touched

- `i18n/{en,zh}/skills/novelty/SKILL.md` + `.claude/skills/novelty/SKILL.md`:
  - description gains "+ PubMed (bio)"
  - Step 2 inserts Source E after Source D: 3-rule bio-claim detection (domain enum match /
    method signature contains bio tokens / linked idea has A2-light protein-anchor fields);
    5 query shapes (direct / component / PTM-specific / clinical-anchor / survey); esearch +
    esummary + efetch URLs; merge with Sources A/B by DOI / PMID / normalised title; NCBI
    rate-limit ≤ 3 req/sec; cache in raw/tmp/novelty-pubmed/
  - Step 3 Review LLM input: each prior work tagged with source channel
  - Scoring rules: "bio-shaped target AND ≥ 3 PubMed-unique high-similar hits → drop score by 1"
    and "PubMed + WebSearch agree on prior work absent from wiki → flag Recommend /ingest
    before scoring"
  - Constraints: bio-shaped targets get 3–5 additional PubMed queries
  - Error Handling: PubMed unavailable → explicit coverage-gap annotation (no silent degrade)
  - Dependencies: WebFetch added (Source E)

### Verification

| Check | Result |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `diff -q i18n/en/skills/novelty/SKILL.md .claude/skills/novelty/SKILL.md` | identical |
| `grep -c "PubMed\|eutils.ncbi" .claude/skills/novelty/SKILL.md` | ≥ 8 |
| Active SKILL.md line count | 253 (up from 217) |

Section C status: 4/9 → 5/9.

---

## 2026-05-12 — C6 minimal pilot merge: `/exp-design` statistical defaults rebuilt around bio regimes

**Scope**: `/exp-design` previously recommended ">= 3 seeds" blanket for validation / ablation.
Bio test sets are routinely n_test < 50 with class imbalance; multi-seed alone does not produce
reliable CIs — bootstrap CI + stratified k-fold is the standard. Wet-lab assays additionally need
biological vs technical replicate separation. C6 minimal inserts a 4-regime table in Step 3.
**Status**: **C6 minimal merged as pure-prompt change**. Full C6 (per-protocol Review LLM prompt
variants, a `tools/research_wiki.py validate-setup` warning when chosen protocol contradicts
n_test, `/exp-eval` routing to the protocol-specific p-value test) deferred.

### Files touched

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`:
  - Step 3 inserts a "Statistical defaults" 4-row table between Bio-specific block types and
    "Each experiment block carries": ML-large (n_test >= 50 → >= 3 seeds) / Bio small-n
    (n_test < 50 → bootstrap CI ≥ 1000 resamples + stratified k-fold k = min(5, n_positives))
    / Bio very-small-n (n_test < 10 → leave-one-out CV + bootstrap CI on headline) /
    Wet-lab assay (>= 3 biological × >= 3 technical replicates with explicit labelling).
    Each row lists the value to record in `setup.random_seed_protocol` (A5 full field).
  - Adds class-imbalance check: when `min(n_positives, n_negatives) < 20`, stratify k-fold
    by class AND report per-class metrics, not just headline AUC.
  - Step 3 B Validation, Step 3 `seeds` line, Step 5 Review LLM question 5, and Constraints
    "At least 3 seeds" all updated to reference the table.

### Verification

| Check | Result |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | identical |
| `grep -c "bootstrap\|stratified-k-fold\|LOO-CV\|biological.*technical" .claude/skills/exp-design/SKILL.md` | ≥ 10 |
| Active SKILL.md line count | 405 (up from 366) |

Section C status: 5/9 → 6/9.

---

## 2026-05-12 — C8 pilot merge: `tools/lint_bio.py` with 5 bio-specific checks

**Scope**: `/check`'s `tools/lint.py` is entity-type-agnostic (required fields, enums, xref
symmetry, edge consistency) and cannot express bio-shape constraints (PDB ID format, UniProt
accession format, dataset version cross-check, MD requires force_field, etc.). C8 adds
`tools/lint_bio.py` covering these 5 checks; `/check` invokes it when bio fields are present.
**Status**: **C8 merged** (not minimal — the tool is fully engineered and all 5 checks pass
cleanly on this wiki). Second Python code change of bio-adaptation (first was
`add-edge --metadata`).

### Files touched

- **New file `tools/lint_bio.py`** (298 lines):
  1. `check_pdb_ids` — every value in `concepts.pdb_ids` must match
     `^[0-9][A-Za-z0-9]{3}([A-Za-z0-9]{4})?$` (4-char or 8-char alphanum starting with digit);
     🟡 on mismatch.
  2. `check_uniprot_ids` — `concepts.uniprot_id` must match canonical
     `[OPQ][0-9][A-Z0-9]{3}[0-9]` or extended `[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}`;
     🟡 on mismatch.
  3. `check_dataset_versions` — `dataset_version_used` edge `metadata.version` must appear in
     the target dataset's `versions:` list (B3 + A1 cross-check); 🟡 on mismatch. Edges with
     version only in the evidence string are out of scope here.
  4. `check_species_recognised` — `experiments.setup.species` values must be in a 29-entry
     allowlist (human / mouse / rat / yeast / zebrafish / drosophila / c-elegans / e-coli /
     ...); 🔵 informational on outliers — extend `RECOGNISED_SPECIES` when a legit new
     species enters the wiki.
  5. `check_md_force_field` — when `experiments.setup.assay_type` matches
     `\bMD\b|molecular dynamics`, `setup.force_field` must be non-empty; 🟡 when empty.
  - Severity convention + `LintIssue` class reused from `tools/lint.py` via sys.path
    injection (tools/ has no `__init__.py`; mirrors lint.py's import-runtime/loader pattern).
  - Nested setup parsing uses PyYAML (lint.py's regex parser drops indented children).
  - `--json` output and `--wiki-dir` flag mirror lint.py.
  - Exit code: 1 when ≥ 1 🔴, else 0.
- `i18n/{en,zh}/skills/check/SKILL.md` + `.claude/skills/check/SKILL.md`:
  - Step 1 gains a "Bio-specific lint" sub-block describing when to invoke `lint_bio.py` and
    how to merge JSON output (`bio-*` category prefix distinguishes the channel); non-bio
    wikis pay zero cost.
  - Dependencies gain a `lint_bio.py` entry.

### Verification

| Check | Result |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 (baseline unchanged) |
| `python tools/lint_bio.py` | 0 🔴 / 0 🟡 / 0 🔵 (the 13-pilot bio surface is clean) |
| `python tools/lint_bio.py --json` | `[]` (machine-readable) |
| PDB regex smoke | `4CI1 5HXB 6XYZ` ✓; `XYZ4 pdb_001 6X` ✗ |
| UniProt regex smoke | `Q96SW2 P12345 O00533` ✓; `Q96SW XYZ123` ✗ |
| MD pattern smoke | `MD / MD + scoring / molecular dynamics` ✓; `scoring / docking / Cryo-EM` ✗ |
| `diff -q i18n/en/skills/check/SKILL.md .claude/skills/check/SKILL.md` | identical |

Section C status: 6/9 → 7/9.
