# Changelog

All notable changes to OmegaWiki will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [1.4.0] - 2026-05-18

### Added

- **`/poster` skill** (`/poster [paper-dir]`): generate a self-contained 1400×900 HTML academic poster + 2× PNG render from a drafted-and-compiled paper. Pipeline adapted from [PaperX](https://github.com/yutao1024/PaperX) ([arXiv:2602.03866](https://arxiv.org/abs/2602.03866)) — DAG intermediate (`tools/wiki2dag.py`), per-section distillation, interactive figure picker, critique-revise convergence pass, event-driven Playwright render with programmatic DOM overflow check. Reads `paper/main.tex` + `paper/sections/*.tex` + `paper/figures/` and grounds distillation in `wiki/outputs/paper-plan-*.md` when available. Authors are cached in `paper/.author_display.txt` for double-blind workflows. Supports affiliation/conference logos (PNG/JPG/PDF; PDF auto-converted at 200 DPI) and two header layouts (`corners` / `stacked`). Export to PDF from the browser's print dialog.
- **TikZ figure rasterization** (`tools/rasterize_latex.py`): figures defined as inline TikZ (without `\includegraphics`) are auto-compiled via `pdflatex` + `pdftoppm` into PNGs under `paper/figures/` and flow through the existing poster figure-injection pipeline. `TEXINPUTS` is augmented with the source `paper_dir` so `\input{figures/data/foo.tex}` and pgfplots `.dat` references resolve correctly. Optional dependency: TeX Live + poppler-utils (graceful failure with `_failed/<slug>/` artifacts saved for debugging).
- **Live HTML `<table class="poster-table">` rendering**: booktabs `tabular` environments inside `\begin{table}…\end{table}` become real HTML tables with cell-level scrubbing (`\textbf`/`\emph`/`\texttt`/`\textsc`, `\multicolumn` → `colspan`, citation key → bibliography ordinal, `\ensuremath{X}` → `$X$` for KaTeX). Tables auto-detect booktabs `\midrule` to split thead/tbody; tables without `\midrule` render entirely as `<tbody>`. `\input{tables/foo}` is expanded inline (comment-aware, so `% \input{...}` is ignored). Numeric cells wrapped in `$..$` for math/text rendering parity. Table font unified to `KaTeX_Main`.
- **Multi-figure layouts (Step 2.5)**: per-section figure picker supports selecting ≥ 2 figures with explicit layout choice — side-by-side (`inline-multi-side`), vertical stack (`inline-multi-stack`), or after-table.
- **Optional `playwright>=1.40` dependency** for event-driven rendering with deterministic font/asset wait semantics. Without it, `/poster` falls back to a system-browser subprocess render path (Chrome/Edge preferred, Firefox at 1× scale).
- **`templates/poster/poster_template.html`** with 3-column auto-fit layout, KaTeX math support, `.poster-table` CSS (KaTeX_Main font, alternating striping), and an iterative `fit()` algorithm that shrinks `--base-font` until content settles inside the poster bounds.
- **`wiki/log.md` session entries** for poster runs (paper title, section/figure/table counts, header config, refine iterations, check-overflow result).
- **README "What's New"** entry with anonymized demo image (`assets/poster_demo_tikz_tables.png`) — placeholder title/authors/prose, real tables/figures preserved to demonstrate the pipeline.

### Changed

- `setup.sh` adds import smoke-test for `tools/wiki2dag.py` and `tools/poster.py` (`tools/rasterize_latex.py` transitively validated via `wiki2dag` module-level import).
- `requirements.txt` notes `playwright>=1.40` as optional with one-shot `python -m playwright install chromium` setup hint.

### No breaking changes

Existing skills (`/init`, `/ingest`, `/discover`, `/paper-draft`, `/paper-compile`, `/visualize`, etc.) are unchanged. The new `/poster` skill is purely additive — no existing entity schemas, edge types, runtime contracts, or skill outputs are modified.

## [1.3.0] - 2026-05-12

### Added

- **`/discover` venue mode** (`--venue <slug> --year <int>`): rank a conference's full paper list by relevance to the existing wiki. Data source is [`papercopilot/paperlists`](https://github.com/papercopilot/paperlists) public JSON — no Semantic Scholar / DeepXiv calls, no extra API keys. Supports NeurIPS (slug `neurips` aliases to `nips`), ICLR, ICML, and any other venue covered by Paper Copilot.
- 20 unit tests in `.sleepcode/tests/test_discover_from_venue.py` covering URL aliasing, JSON normalization, transient-failure retry, title-based dedup, sparse-wiki guard, and the no-write contract.

### Changed

- `/discover` skill argument-hint expanded from 3 to 4 seed modes (anchor / topic / wiki / venue) across `.claude/`, `i18n/en/`, and `i18n/zh/`. References (`seed-modes.md`, `ranking-signals.md`, `wiki-dedup.md`) updated for venue-mode picking, scoring, and title-based dedup against candidates that lack arXiv IDs.
- Venue mode is stricter than other `/discover` modes: it does **not** write to `wiki/` at all, including `wiki/log.md`. Sparse wikis (< 20 unique relevance terms) fail with an actionable error rather than returning an unpersonalized ranking.

## [1.1.0] - 2026-05-06

### Added

- **Knowledge graph visualization** (`/visualize`): two output modes — Web SPA (Cytoscape, served by `tools/serve.py`) with BFS-highlight, entity/edge filtering, and in-app Reader; Obsidian mode (`--obsidian` / `--canvas`) generating color-coded graph config and force-layout Canvas files with labeled semantic edges.
- **Local research dashboard** (`#/dashboard` in web UI): paper ingestion timeline, method-type breakdown, novelty histogram, and experiment status charts.

### Changed (BREAKING)

- **Replace `claims` entity with `methods` entity.** The wiki no longer carries a separate testable-claim entity; verifiable hypotheses now live on `ideas` pages, and reusable techniques are first-class via `wiki/methods/*.md` (with `name`, `slug`, `type` enum, `source_papers`, `parent_methods`, `child_methods`, `code_repo`).
- **Drop `experiments.target_claim`; require `experiments.linked_idea`.** Every experiment must reference its source idea; `/exp-eval` now updates the linked idea's `status` / `pilot_result` / `failure_reason` instead of a separate claim entity.
- **`ideas.origin_gaps` retargets `[concepts, topics]`** (was `[claims]`). Reverse links land in `concepts.linked_ideas` / `topics.linked_ideas` (new frontmatter fields).
- **`ideas` schema**: gains `target_venue`, `novelty_score (1-5 int)`. Drops `domain`. Body template adds `## Novelty argument` and `## Target venue`; drops `## Expected outcome`.
- **`papers` schema**: gains `tldr`, `contribution_type` (multi-select from a fixed enum), `datasets`. Drops `keywords`, `domain`. Body renames `## Problem` → `## Problem & Context`, `## Results` → `## Experiment & Results`.
- **`concepts` schema**: drops `part_of`. Gains `definition` (1-sentence machine-readable) and `linked_ideas`. Body drops `## Formal notation`, `## When to use`, `## Key papers`; gains `## Relationship to foundations`.
- **`topics` schema**: drops `my_involvement`, `sota_updated`. Gains `linked_ideas`. Body drops `## Research gaps`, `## Key people`, `## My position`; gains `## Key benchmarks` and splits `## Open problems` into `### Known gaps` / `### Methodological gaps` subsections.
- **`people` schema**: drops `tags`. Gains `research_areas` and `type: object {kind: enum, subtype: str}`. Body drops `## Key papers` and `## Collaborators`.
- **`/novelty`**: adds `--write` flag — when set with an idea slug as target, persists `novelty_score` to the idea page (skill is otherwise still read-only).
- **`/paper-plan`**: argument-hint changes from `<claim-slugs>` to `<idea-slugs>`. The plan is built from validated ideas + their linked experiments and methods, not from a separate claim graph.
- **CLI**: `tools/research_wiki.py` removes `find-similar-claim`, `query weak-claims`, `query evidence-for`. The `query` subcommand now exposes only `ready-to-test` and `orphans`.
- **Edge workflow rename**: `claim_evidence` → `evidence` on `supports` / `contradicts` (endpoints unchanged at `*->*`).

### Migration notes

- Pre-existing `wiki/claims/*.md` content is **not migrated**; in this repo the directory was empty so it has been removed. Any external repo with content there should run `/edit` to fold relevant assertions into the appropriate idea / method pages before pulling this change.
- The `experiments.target_claim` field is dropped, not migrated; pre-existing experiment pages must be hand-edited to set `linked_idea` instead.

## [0.1.0] - 2026-04-09

### Added

- 20 Claude Code skills for full research lifecycle: `/init`, `/ingest`, `/ask`, `/edit`, `/check`, `/daily-arxiv`, `/ideate`, `/novelty`, `/review`, `/exp-design`, `/exp-run`, `/exp-status`, `/exp-eval`, `/refine`, `/survey`, `/paper-plan`, `/paper-draft`, `/paper-compile`, `/research`, `/rebuttal`
- Wiki knowledge engine (`tools/research_wiki.py`) with 20 CLI commands
- 8 entity types: papers, concepts, topics, people, ideas, experiments, claims, summaries _(superseded by 0.2.0 — see Unreleased; `claims` is replaced by `methods`)_
- Typed semantic relationship graph (`graph/edges.jsonl`) plus bibliographic citation layer (`graph/citations.jsonl`)
- Daily arXiv automation via GitHub Actions
- Cross-model review via any OpenAI-compatible API (DeepSeek, OpenAI, Qwen, OpenRouter, SiliconFlow, etc.)
- Multi-source data integration: arXiv RSS, Semantic Scholar, DeepXiv
- Remote GPU experiment support (`tools/remote.py`)
- Structural wiki linter with auto-fix (`tools/lint.py`)
- Bilingual support (English + Chinese) with `setup.sh --lang` switching
- One-click setup (`setup.sh`)
- Obsidian-compatible `[[wikilink]]` format throughout
- 2125 tests
