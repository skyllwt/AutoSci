# Codex Smoke Test Matrix

This matrix tracks Codex migration validation beyond "the skill file exists".
It separates deterministic local checks from networked or write-heavy skill
runs so Codex regressions can be found without accidentally mutating user data.

## Current Boundary

- All repo skills are present under `.agents/skills` and have Codex-compatible
  frontmatter.
- `$daily-arxiv` CI `inform` mode can use Codex CLI through `codex exec`.
- `$daily-arxiv --mode auto-ingest` in GitHub Actions remains on the legacy
  Claude Code Action path until full Codex CI ingest orchestration and push are
  verified. Workflow dispatch must use `recommender=auto` or
  `recommender=claude-action`; explicit `codex`, `review-llm`, or `tool`
  recommenders fail closed in auto-ingest mode. Local Codex `$ingest` and
  force-staged writeback scope have been smoke-tested, but the unattended
  GitHub Actions path still needs a dedicated disposable run before it should
  replace the legacy backend.

## Remaining External Gates

The local migration suite is not enough to mark the Codex migration complete.
These external gates must pass with real credentials or disposable infrastructure:

| Gate | Current blocker | Pass evidence |
|---|---|---|
| GitHub Actions canary | `gh auth status -h github.com` reports an invalid `TomWhite-tgz` token | `mode=inform,recommender=codex` succeeds on the branch under test, and `mode=auto-ingest,recommender=codex` fails in `Validate recommender credentials` before prepare/recommend/commit |
| Codex CI recommendation auth | `OPENAI_API_KEY` and `CODEX_ACCESS_TOKEN` are unset locally; CI secrets still need operator confirmation | The positive inform canary writes `llm-decisions.json` with provider `codex` and no wiki/raw writeback |
| Semantic Scholar enrichment | `SEMANTIC_SCHOLAR_API_KEY` is unset locally; unauthenticated calls may rate-limit | `$discover` or `$daily-arxiv` L2 enrichment completes under escalation with S2 evidence and only scratch/checkpoint outputs |
| DeepXiv enrichment | `DEEPXIV_TOKEN` is unset locally; previous escalated smoke reached DeepXiv but got invalid/expired token | `tools/fetch_deepxiv.py search ... --limit 1` succeeds under documented escalation and `$discover` / `$daily-arxiv` can use DeepXiv enrichment |
| Review LLM | `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` are unset | A minimal `llm-review` call succeeds, then `$review`, `$novelty`, `$exp-eval`, `$paper-plan`, and daily-arxiv `recommender=review-llm` L2 paths run without fallback |
| Remote/GPU experiments | Real SSH/GPU/screen environment is not validated in this workspace | `$exp-run --env remote`, `$exp-status --collect-ready`, `$exp-run --collect`, and `$research --start-from stage3-collect` complete on a disposable remote experiment without mutating user-owned raw |

## Smoke Levels

| Level | Scope | Mutates repo? | Network? | Purpose |
|---|---:|---:|---:|---|
| L0 static | Skill parity, frontmatter, docs, schemas, workflow parse | No | No | Catch migration drift quickly |
| L1 local sandbox | Temp wiki/raw fixtures and deterministic tools | Temp only | No | Prove Codex-safe serial/local paths |
| L2 network dry-run | S2, DeepXiv, arXiv, Review LLM, Codex CLI auth | Scratch only | Yes | Prove sandbox escalation and API auth |
| L3 writeback rehearsal | `$ingest`, `$init`, daily-arxiv auto-ingest in disposable branch/worktree | Yes, disposable | Yes | Prove wiki/raw mutation and commit behavior |
| L4 production | Scheduled daily-arxiv, real research workflows | Yes | Yes | Operational confidence |

## Priority Matrix

| Skill/path | First smoke level | Command or action | Pass criteria | Notes |
|---|---:|---|---|---|
| `$setup` | L0/L1 | Read `.env` state, config docs, Codex MCP config | No Claude-only setup assumptions; Codex MCP instructions are present; status probe is read-only and redacts values | DeepXiv auto-register is agent-neutral; local `.env` status probe covered by `test_setup_env_status_probe_is_read_only_and_redacts_values` |
| Codex CLI entrypoint | L1/L2 | `codex --version`, `codex login status`, minimal `codex exec` | CLI is installed, auth is available, non-interactive exec returns a fixed response | Validated on 2026-07-08 with `codex-cli 0.143.0` and ChatGPT auth; managed sandboxes may need escalation for `codex exec` runtime initialization |
| `$ingest <local tex>` | L1/L3 | INIT MODE contract regression plus disposable branch with one local `.tex` in `raw/tmp` or `raw/papers` | INIT MODE keeps raw read-only, skips per-paper citation/reference fetches, rebuilds, visualization, discovery, topic/reverse-link conflict writes, and serial commits; direct local ingest creates paper page, graph edges, index/log updates, and lint passes | INIT MODE prompt contract covered by `test_ingest_init_mode_keeps_codex_batch_safety_contract`; direct writeback rehearsal remains the most important L3 dependency for `$init`, `$daily-arxiv`, `$research` |
| `$init --no-introduction` | L1/L3 | Temp raw paper and no external discovery | CLI path writes prepare/plan/sources/handoff checkpoints, uses INIT MODE SERIAL, and creates no worktrees or discovered raw | Function-level serial handoff covered by `test_local_tex_serial_handoff_without_network_gate`; CLI checkpoint path covered by `test_init_local_only_cli_writes_serial_checkpoints_without_network_gate`; full multi-paper ingest handoff remains L3 |
| `$discover --topic ...` | L1/L2 | Mocked local topic shortlist plus real run with required escalation | Produces shortlist/checkpoint only; dedupes already-ingested wiki papers; no raw/wiki content writes except documented log behavior | Local proposal-only boundary covered by `test_discover_topic_shortlist_checkpoint_is_proposal_only`; sandbox gate message and AGENTS escalation contract covered by `test_sandbox_gate_prints_actionable_prefix_rule` and `test_sandbox_gate_matches_agents_escalation_contract`; real network shortlist run completed on 2026-07-08 with temp wiki/checkpoint |
| `$check` | L1 | Run on initialized temp wiki and a linked paper/concept fixture | Reports deterministic shape issues through `tools/lint.py --json`; report-only and `--fix --dry-run` do not mutate files; explicit `--fix` only changes deterministic wiki fields | Read path covered by `test_ask_and_check_local_fixture_cover_read_paths`; report/dry-run/fix boundary covered by `test_check_lint_report_and_dry_run_are_read_only_fix_is_explicit` |
| `$ask` | L1/L3 | Rebuild/read context and open-question packs against initialized wiki; crystallize a traced output note only when explicit | Answer-only retrieval prerequisites work; crystallize writes only documented wiki artifacts and never raw | L1 read-path fixture covered by `test_ask_and_check_local_fixture_cover_read_paths`; default `outputs/` crystallize path covered by `test_ask_crystallize_fixture_writes_output_edges_and_log_only_when_explicit` |
| `$prefill` | L1/L2 | Seed one foundation in a temp wiki, with Wikipedia fallback mocked or skipped | Creates only `wiki/foundations/`, rebuilds index, appends log, and exposes `$prefill` / `$ingest` follow-up text | Local foundation/dedup fixture covered by `test_prefill_foundation_fixture_supports_ingest_dedup`; real Wikipedia fetch remains L2 |
| `$edit` | L1/L3 | Temp wiki edit plus generated raw input preparation | User-owned `raw/papers`, `raw/notes`, and `raw/web` remain read-only; generated raw writes are limited to `raw/discovered` or `raw/tmp` | Local wiki/raw boundary fixture covered by `test_edit_fixture_updates_wiki_and_only_generated_raw_dirs`; destructive generated-raw deletion remains explicit-confirmation only |
| `$reset` | L1 | Temp project with user-owned and generated raw files; run `tools/reset_wiki.py --scope raw --yes` | Deletes only generated `raw/discovered` and `raw/tmp`; preserves `raw/papers`, `raw/notes`, and `raw/web` | Covered by `test_reset_raw_scope_preserves_user_owned_raw_sources` |
| `$visualize` | L1/L2 | Generate canvas/Obsidian artifacts from temp graph; optionally start SPA server | Uses runtime-neutral background process wording; Codex server start may require documented `tools/serve.py` escalation | Local Obsidian/full-canvas/focus-canvas fixture covered by `test_visualize_generates_obsidian_and_canvas_artifacts_locally`; real server smoke remains L2 |
| SPA skill intents | L1 | `tools/serve.py` intent builders for ingest/ask/check/discover | Returns both Claude slash command and Codex `$` command plus `.agents` doc URL | Covered by `test_spa_intents_surface_codex_commands_and_docs` |
| `$daily-arxiv` inform | L2 | Local helper run plus later `workflow_dispatch`/Codex auth run | `prepare` fetches arXiv feed into scratch context; `compact-context` and `finalize` run locally without network escalation; Codex/LLM later produces `llm-decisions.json` | Helper path validated on 2026-07-08 with temp wiki; Codex LLM decision run remains L2 |
| `$daily-arxiv --mode auto-ingest` writeback scope | L3-local | Temp git repo with synthetic ignored `wiki/`, `raw/discovered/`, `raw/tmp/`, `raw/papers/`, and `.daily-arxiv/` changes | Commit scope force-stages only `wiki/` and `raw/discovered/`; scratch and user-owned raw files remain unstaged | Covered by `test_daily_arxiv_writeback_rehearsal_stages_only_ingest_outputs` |
| `$daily-arxiv --mode auto-ingest` real ingest | L3 | Disposable branch/workflow with one selected candidate plus the documented Codex negative canary | `$ingest` runs, wiki/raw changes are committed and pushed on the legacy path; `mode=auto-ingest,recommender=codex` fails before prepare/recommend/commit | Currently legacy Claude Action only in CI; explicit Codex/review/tool recommenders fail closed. Deployment doc now includes positive inform smoke, negative Codex auto-ingest canary, and the future Codex enablement checklist |
| `$exp-pilot-run` / `$exp-pilot-eval` | L1/L3 | Spec-boundary, lifecycle fixture, and tiny local pilot execution | `$exp-pilot-run` does not synthesize missing Pilot Specs; tiny pilot execution produces result JSON without wiki writes; pilot failure can transition an idea from `proposed` to `failed`; results are judged by `$exp-pilot-eval` | Local execution covered by `test_exp_pilot_run_tiny_execution_is_result_only`; real training/GPU pilot remains L3 |
| `$exp-run` | L1/L3 | Lifecycle writeback fixture plus tiny local deploy/run/collect | Deploy/collect status writes use `tools/research_wiki.py transition`; completion is gated on `key_result`; tiny local `run.sh` produces result JSON and completes the experiment page | Local execution covered by `test_exp_run_tiny_local_execution_path_collects_results`; real screen/SSH/GPU execution remains L3 |
| `$exp-status` | L1/L3 | Temp experiment pages plus running/completed status scan fixture | Status target discovery works without Claude cron assumptions; process checks are Codex-safe sequential by default | L1 target-list fixture covered by `test_exp_status_local_fixture_finds_running_experiments`; real screen/SSH collect remains L3 |
| `$exp-design` | L1/L3 | Prepared idea page with pilot verdict, deterministic experiment-page creation fixture, and same-idea/same-hypothesis duplicate scan | Creates `wiki/experiments/` pages with all fields needed by `$exp-run`, adds `tested_by` edges through `research_wiki.py`, and skips duplicate experiments | Planned experiment page handoff to `$exp-run` covered by `test_exp_design_fixture_creates_exp_run_ready_pages`; duplicate skip path covered by `test_exp_design_fixture_skips_duplicate_hypotheses_for_same_idea`; real Review LLM/user-selected suite quality remains L3 |
| `$exp-eval` | L1/L3 | Completed experiment page plus mocked Review LLM verdict | Updates linked idea / experiment lifecycle through documented fields and preserves graph consistency | Supported and not_supported writeback paths covered by `test_exp_eval_local_verdict_paths_update_idea_and_graph`; real Review LLM run remains L2/L3 |
| `$ideate` | L1/L3 | Phase 4 write fixture with `--skip-validation --skip-pilot` semantics, then networked direction run later | Runs searches sequentially when Agent/subagents are unavailable; writes proposed and filtered ideas through schema-compatible pages and graph tools | Local Phase 4 write path covered by `test_ideate_fixture_writes_phase4_ideas_edges_and_report_locally`; external search / Review LLM brainstorm / pilot selection remain L3 |
| `$novelty` | L1/L2 | Read-only novelty check against temp idea plus network search dry-run later | `--write` is the only persistence path; Agent/subagent search is optional and sequential search is Codex-safe default | Read-only default and `--write` scope covered by `test_novelty_fixture_respects_read_only_default_and_write_flag_scope`; external Web/S2/DeepXiv search remains L2 |
| `$review` | L1/L2 | Review a temp artifact or wiki entity with Review LLM unavailable/mocked first | Produces structured findings and follow-up suggestions using `/skill` and `$skill` alternatives; no invented `$query` path | Structured single-model fallback fixture covered by `test_review_fixture_outputs_structured_single_model_report_without_writes`; real Review LLM remains L2 |
| `$refine` | L1/L2 | Run one bounded refinement round against a temp artifact with mocked review feedback | Applies fixes only to the requested target, requires explicit scope, and keeps review dependency runtime-neutral | One-round mocked-review writeback fixture covered by `test_refine_fixture_applies_one_mocked_review_round_in_place`; real Review LLM iterative loop remains L2 |
| `$rebuttal` | L1/L2 | Parse a small review-comment fixture and map concerns to temp wiki evidence | Produces rebuttal draft and evidence mapping without mutating raw sources; recommends Codex `$skill` follow-ups | Local traceable-output fixture covered by `test_rebuttal_fixture_generates_traceable_outputs_without_raw_mutation`; real Review LLM stress-test remains L2 |
| `$research` | L1/L3 | Pipeline-progress resume fixture plus prepared Stage 3c → Stage 4 → report orchestration | `wiki/outputs/pipeline-progress.md` can be updated and restored through CLI-safe fields; a prepared completed experiment can drive verdict writeback, linked idea tracking, final report generation, and completion logs | L1 progress/resume coverage in `test_research_pipeline_progress_resume_fields_are_cli_safe`; prepared orchestration covered by `test_research_prepared_stage_orchestration_reaches_report`; full end-to-end sub-skill orchestration remains L3 |
| `$paper-plan` | L1/L3 | Temp idea + completed experiment + citations fixture | Generates a plan only when experiment evidence and citation coverage exist; suggests `$paper-draft`, `$exp-design`, `$exp-run`, and `$ingest` alternatives | Local evidence-map/provenance fixture covered by `test_paper_plan_fixture_maps_validated_idea_to_evidence`; full Review LLM outline review remains L3 |
| `$paper-draft` | L1/L3 | PAPER_PLAN fixture with local wiki sources | Writes LaTeX sections from wiki evidence, preserves citation verification boundary, and suggests `$paper-compile` / `$refine` follow-ups | Local LaTeX artifact/integrity fixture covered by `test_paper_draft_fixture_writes_integrity_checked_latex_artifacts`; full prose generation and Review LLM pass remain L3 |
| `$paper-compile` | L1/L3 | Minimal temp LaTeX project | Runs compile/checklist path without Claude-only assumptions and suggests `$paper-draft` / `$refine` alternatives on failure | Codex-safe checklist helper covered by `test_paper_compile_fixture_runs_codex_safe_checklist`; real `latexmk`/PDF/font checks remain L3 |
| `$survey` | L1/L3 | Temp wiki with several paper pages | Produces related-work structure from wiki evidence only and warns when citation coverage is insufficient, with `$ingest` follow-up | Local archive/derived_from fixture covered by `test_survey_archive_fixture_uses_existing_papers_only`; full prose generation remains L3 |
| `$poster` | L1/L3 | Minimal drafted paper fixture | Generates a poster artifact from existing paper content and suggests `$paper-draft` when `paper/main.tex` is missing | Local DAG/HTML/images/validate fixture covered by `test_poster_fixture_builds_validated_html_from_drafted_paper`; headless PNG rendering and visual overflow checks remain L3 |

## Local Verification Commands

Run deterministic checks:

```bash
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN=python3; fi
"$PYTHON_BIN" -m unittest tests/test_init_discovery_codex.py tests/test_codex_migration_smoke.py -v
```

The local suite includes i18n source parity checks, SPA intent command checks,
tiny local `$exp-run` / `$exp-pilot-run` execution fixtures, `$research`
pipeline-progress resume-field coverage, and an L3-local daily-arxiv writeback
rehearsal in a temporary git repository. The writeback rehearsal validates
staging and commit scope, but it does not replace a real `$ingest` run or
GitHub push rehearsal.

Run setup sync after editing i18n sources:

```bash
./setup.sh --lang en
```

Run static parity checks:

```bash
diff -qr --exclude=shared-references i18n/en/skills .agents/skills
diff -qr i18n/en/shared-references .agents/skills/shared-references
diff -qr .agents/skills .claude/skills
"$PYTHON_BIN" -m json.tool .github/codex/daily-arxiv-decisions.schema.json >/dev/null
ruby -e "require 'yaml'; YAML.load_file('.github/workflows/daily-arxiv.yml')"
```

Expected note: active skill trees place shared reference files under
`skills/shared-references`, while the i18n source keeps them in
`i18n/<lang>/shared-references`.

## Findings To Watch

- Any skill that says "use Agent tool" must also define a sequential Codex-safe
  fallback unless the Agent path is genuinely required.
- Any workflow that commits or pushes must name the runtime backend and the
  writeback boundary explicitly.
- Any network helper should either avoid importing `_sandbox` for local-only
  subcommands or document the required escalation rule.
- Skills that mention raw source management must distinguish user-owned
  `raw/papers`, `raw/notes`, and `raw/web` from generated `raw/discovered` and
  `raw/tmp`; destructive helpers must not touch user-owned raw.

## Current Run Notes

- 2026-07-08: `$discover --topic "retrieval augmented generation" --limit 1`
  was run via `tools/discover.py` with required sandbox escalation and
  checkpoint output under `/tmp/autosci-discover-smoke`. The command completed
  without repo `wiki/`, `raw/`, `.checkpoints/`, or `.daily-arxiv/` changes, but
  produced an empty shortlist because Semantic Scholar was rate-limited after
  retries and the configured DeepXiv token was invalid or expired. This is an
  API/configuration issue to fix before treating `$discover` L2 as healthy.
- 2026-07-08: Codex CLI probe succeeded: `codex --version` reported
  `codex-cli 0.143.0`, `codex login status` reported ChatGPT auth, and an
  escalated minimal `codex --ask-for-approval never exec --ephemeral --json
  --sandbox read-only` returned the fixed response `AUTOSCI_CODEX_SMOKE_OK`
  without repo changes. In the managed sandbox, `codex --version` and
  `codex login status` warn that PATH aliases cannot be created on the
  read-only filesystem; the non-escalated `codex exec` attempt failed while
  initializing Codex runtime files, so this L2 check requires escalation in
  comparable managed sandboxes.
- 2026-07-08: A disposable Codex `$ingest <local tex>` L3 rehearsal in
  `/tmp/autosci-l3-ingest.vuT7ug` created one paper, one concept, one method,
  one graph edge, index/log updates, and passed `tools/lint.py --wiki-dir wiki
  --json` with `[]`. The run exposed a writeback gap: generated wiki pages,
  graph files, and `raw/discovered/` are intentionally ignored as per-user
  data, so daily-arxiv auto-ingest must use `git add -f wiki raw/discovered`
  instead of plain `git add wiki raw/discovered`.
- 2026-07-08: `$ingest` INIT MODE now has regression coverage for the
  Codex-safe batch contract. The smoke suite checks the active skill text and
  `references/init-mode.md` keep `canonical_ingest_path` consumption, raw
  read-only handling, skipped per-paper S2 citation/reference fetches, skipped
  rebuilds, skipped conflict-prone topic/reverse-link writes, skipped
  visualize/discover follow-ups, no serial per-paper commits, and worktree-only
  successful commits in parallel mode.
- 2026-07-08: `$init --no-introduction` now has a subprocess-level local CLI
  fixture. It runs `tools/init_discovery.py prepare`, `plan
  --allow-introduction false`, `fetch` with zero external IDs, and `handoff
  --mode serial` against a temporary raw tree, then verifies
  `.checkpoints/init-prepare.json`, `init-plan.json`, `init-sources.json`, and
  `init-handoff.json` are written with `origin=user_local`, `INIT MODE SERIAL`,
  no per-paper commit, and no `raw/discovered/` output.
- 2026-07-08: `$setup` now has a local `.env` status-probe fixture. It runs the
  same `_env`-based detection shape from the skill in a temporary project with
  an isolated `HOME`, verifies only `SET:` / `UNSET:` lines are printed,
  confirms secret values and base URLs are not exposed, and checks `.env`,
  `wiki/`, and `raw/` snapshots are unchanged.
- 2026-07-08: `$check` report/fix boundaries now have deterministic local
  coverage. A temporary concept page with missing defaultable required fields
  proves `tools/lint.py --json` reports without mutation, `--fix --dry-run
  --json` returns planned fixes without mutation, and explicit `--fix --json`
  writes only deterministic frontmatter defaults while preserving user-owned
  `raw/` and graph files.
- 2026-07-08: `$discover --topic` now has local proposal-only coverage with
  mocked gather results. The fixture seeds one already-ingested arXiv paper,
  verifies topic discovery filters that duplicate, ranks two new candidates,
  writes only the requested checkpoint path, formats markdown without the
  duplicate, and preserves `wiki/` plus user-owned `raw/` snapshots unchanged.
- 2026-07-08: `$ask`/`$check` L1 fixture coverage now exercises a temporary
  linked paper/concept wiki, `rebuild-context-brief`, `rebuild-open-questions`,
  `stats --json`, `find --field value`, and `lint.py --json` while preserving a
  user-owned `raw/papers/` file unchanged. This exposed and fixed a
  `tools/research_wiki.py find` argparse bug: the command documented dynamic
  `--field value` filters, but argparse rejected them before the manual parser
  could read them.
- 2026-07-08: `$ask --crystallize` now has a deterministic default-output
  fixture. It proves answer-only retrieval remains read-only, explicit
  crystallize creates `wiki/outputs/{query-slug}.md`, appends `derived_from`
  edges through `tools/research_wiki.py add-edge`, appends `wiki/log.md`,
  rebuilds context, and leaves user-owned `raw/`, source pages,
  `wiki/index.md`, and `open_questions.md` unchanged. The skill text was
  corrected to stop asking agents to index default `outputs/` notes; only
  schema entity writes rebuild `index.md`.
- 2026-07-08: `$exp-status` L1 coverage now builds temporary running and
  completed experiment pages linked to an idea, verifies `find experiments
  --status running` returns only the active target, and runs `lint.py --json`
  over the fixture. The skill now states that Codex uses sequential process
  checks by default unless the runtime can guarantee safe independent checks.
- 2026-07-08: `$exp-status --auto-advance` now distinguishes agent-runtime
  continuation from external scheduler readiness. External schedulers print and
  log `stage4 ready` plus `$research --start-from stage4`; they do not claim to
  invoke another skill or edit `pipeline-progress.md` directly.
- 2026-07-08: `$research` now mirrors the same Stage 3/4 boundary: its async
  experiment instructions show both `/research` and `$research` resume commands,
  and its dependency note says external schedulers only report `stage4 ready`
  instead of automatically advancing the pipeline.
- 2026-07-08: `$exp-status --collect-ready` now follows the same boundary:
  agent runtimes may sequentially invoke `$exp-run {slug} --collect`, while
  external schedulers print/log collect-ready commands and leave experiment
  pages unchanged until a real agent run collects them.
- 2026-07-08: Removed legacy `Skill:` / `Args:` sub-skill call blocks from
  high-risk orchestration docs (`research`, `ideate`) and shared iterative
  review docs (`refine`). The source check now rejects that abstract call
  format so future instructions must spell out both Claude Code `/skill` and
  Codex `$skill` invocations.
- 2026-07-08: `$exp-run` L1 coverage now validates lifecycle writeback with a
  temporary planned experiment: `transition --to running` succeeds, premature
  `transition --to completed` fails until `key_result` is written, and the final
  completed transition auto-sets `date_completed`. The skill now names
  `transition` for deploy/collect status writes instead of direct status edits.
- 2026-07-08: `$exp-run --env remote` writeback no longer requires hand-editing
  the nested `remote:` YAML block. `tools/research_wiki.py set-meta` now accepts
  dotted paths such as `remote.server`, `remote.session`, and
  `remote.completed`, preserves empty nested string fields, and still rejects
  missing fields instead of creating undeclared frontmatter.
- 2026-07-08: `$exp-design` duplicate-policy coverage now seeds an existing
  experiment for an idea, proposes one same-hypothesis duplicate and one new
  main experiment, and verifies only the nonduplicate page is created. The
  fixture updates `linked_experiments` via `set-meta --append`, adds only the
  new `tested_by` edge through `research_wiki.py add-edge`, records the skipped
  duplicate in the master design doc and log, preserves user-owned raw, and
  passes `tools/lint.py --json`.
- 2026-07-08: `$exp-pilot-run` and `$exp-pilot-eval` L1 coverage now validates
  the pilot boundary and failure writeback path. `$exp-pilot-run` reports a
  missing Pilot Spec instead of creating one from `/ideate` instructions, and
  `tools/research_wiki.py transition` now permits pilot failure to move an idea
  from `proposed` to `failed` while auto-setting `failure_reason` and
  `date_resolved`, including for older pages missing those frontmatter fields.
- 2026-07-08: Remaining paper/review-oriented skills were audited for
  slash-only next-step suggestions. `paper-plan`, `paper-draft`,
  `paper-compile`, `poster`, `survey`, `rebuttal`, `refine`, `review`,
  `exp-design`, `exp-pilot-eval`, `init`, `ingest`, `ideate`, `research`,
  `exp-status`, and `exp-run` now present Codex `$skill` alternatives for
  user-facing follow-up actions. The stale `/query` suggestion in `review` was
  removed and mapped to the existing `$ask`/`/ask` workflow.
- 2026-07-08: Daily-arxiv CI auto-ingest now fails closed when users explicitly
  select `recommender=codex`, `recommender=review-llm`, or `recommender=tool`.
  Auto-ingest accepts only `recommender=auto` or `recommender=claude-action`
  until unattended Codex `$ingest` plus push is verified in GitHub Actions.
- 2026-07-08: High-risk experiment/research skills were cleaned up to remove
  Claude-specific "Skill tool" wording. User-facing orchestration notes now
  describe slash command and Codex `$skill` workflows, and dependency lists no
  longer imply a Claude-only sub-skill invocation mechanism. Regression coverage
  prevents the old phrasing from returning.
  Codex-specific workflow steps are guarded by `mode == inform`.
- 2026-07-08: `$exp-run` and `$exp-pilot-run` no longer run their small-scale
  sanity checks before the user inspection gate. Sanity execution is now
  explicitly post-approval, and any code fix after a failed sanity check must
  repeat the gate before retrying.
- 2026-07-08: Added deterministic local execution coverage for the experiment
  paths. `$exp-run` now has a tiny deploy/run/collect fixture that executes a
  local `run.sh`, reads result JSON, writes `outcome` / `key_result`, and
  completes through `transition`; `$exp-pilot-run` now has a tiny Pilot Spec
  fixture that executes pilot code and verifies the wiki tree is unchanged.
- 2026-07-08: Added local `$research` pipeline-progress coverage. The smoke
  suite now creates `wiki/outputs/pipeline-progress.md`, updates resume fields
  such as `current_stage`, `stage3a_deployed`, `linked_idea_slugs`, and
  `iteration_count` through `tools/research_wiki.py set-meta`, reads them back
  through `read-meta`, and verifies stage logging remains append-only.
- 2026-07-08: Tightened Codex sandbox escalation coverage for network tools.
  `tools/_sandbox.py` now emits tool-specific justifications matching the
  AGENTS.md prefix-rule table, and the smoke suite verifies both the static
  contract and a real blocked-socket SANDBOX GATE probe for `$discover`.
- 2026-07-08: Ran a real L2 `$discover` network smoke with escalation:
  `.venv/bin/python tools/discover.py from-topic "low rank adaptation"
  --wiki-root /tmp/.../wiki --limit 2 --output-checkpoint /tmp/.../discover.json`.
  The first sandboxed attempt exited 126 with SANDBOX GATE; the escalated run
  completed with `shortlist_count: 2` from Semantic Scholar (`LoRA`, `DoRA`) and
  wrote only the temporary checkpoint. DeepXiv enrichment reported an invalid or
  expired token and was skipped by the tool's optional-provider fallback.
- 2026-07-08: Fixed unnecessary daily-arxiv sandbox escalation. `tools/daily_arxiv.py`
  now lazy-loads `_sandbox` and network providers only for feed fetch,
  S2/DeepXiv enrichment, or third-party LLM recommendation; local inform helpers
  (`prepare --feed --no-external`, `compact-context`, `finalize`) run without
  network permission. Added regression coverage for this local helper path.
- 2026-07-08: Ran a real L2 `$daily-arxiv` helper smoke with escalation for arXiv
  feed fetch: `prepare --wiki-root /tmp/.../wiki --hours 24 --categories cs.LG
  --max-recommendations 2 --mode inform --no-external` scanned 228 feed items
  and wrote scratch context/feed under `/tmp`. `compact-context` and `finalize`
  then ran in the normal sandbox and produced `codex-context.json`, `digest.md`,
  and `digest.json` with auto-ingest disabled. A full S2/DeepXiv enrichment run
  reached the network path but was interrupted after repeated Semantic Scholar
  rate-limit waits; DeepXiv token status remains invalid/expired.
- 2026-07-08: Made Semantic Scholar rate-limit behavior configurable and
  daily-arxiv fail-fast by default. `fetch_s2.py` now honors
  `S2_MAX_RETRIES` and `S2_RATE_LIMIT_WAIT_SECONDS`; `daily_arxiv.py` sets
  daily-feed defaults of one retry and five seconds per 429 unless the user
  overrides them. Regression coverage verifies the env-controlled retry budget
  and the daily-arxiv local helper path.
- 2026-07-08: Audited lower-level utility skills that were not yet explicit in
  the Codex smoke matrix. `$prefill`, `$edit`, `$reset`, and `$visualize` now
  document Codex invocation forms. The audit found an unsafe legacy boundary:
  `edit` and `reset` described modifying or deleting user-owned raw sources.
  `edit` now treats `raw/papers`, `raw/notes`, and `raw/web` as read-only, and
  `tools/reset_wiki.py --scope raw` now clears only generated `raw/discovered`
  and `raw/tmp`. Regression coverage verifies that user-owned raw files survive
  a real reset helper execution.
- 2026-07-08: Cleaned up `$novelty` runtime capability wording. Multi-source
  search may use Agent/subagent execution only as an optional accelerator; the
  documented Codex-safe default is sequential search in the main workspace.
- 2026-07-08: Made the daily-arxiv CI boundary operational in the deployment
  docs. The documented positive check is `mode=inform,recommender=codex`; the
  documented negative canary is `mode=auto-ingest,recommender=codex`, which must
  fail in `Validate recommender credentials` before prepare/recommend/commit.
  The same doc lists the disposable-run criteria required before Codex CI can
  replace legacy Claude Action for unattended auto-ingest.
- 2026-07-08: Added executable local coverage for the daily-arxiv credential
  guard. The smoke suite extracts the `Validate recommender credentials` shell
  block from `.github/workflows/daily-arxiv.yml` and runs it with representative
  env combinations, proving that `auto-ingest` with `codex`, `review-llm`, or
  `tool` fails closed, while `auto-ingest` with `auto`/`claude-action` requires
  legacy Claude auth.
- 2026-07-08: Tried to start the real GitHub Actions negative canary, but local
  `gh auth status` reported an invalid token for account `TomWhite-tgz`, so no
  remote workflow was dispatched. The next real canary attempt requires
  `gh auth login -h github.com` or an already-authorized CI/operator shell.
  Rechecked on branch `migrate-codex`: `gh auth status -h github.com` still
  reports the same invalid token, while local workflow YAML parsing succeeds.
  For an unmerged migration branch, dispatch with `--ref <branch-under-test>`;
  use `--ref main` only after the migration is merged. The expected remote
  result remains failure in `Validate recommender credentials`, before
  prepare/recommend/commit.
- 2026-07-08: Ran a direct DeepXiv L2 auth smoke:
  `.venv/bin/python tools/fetch_deepxiv.py search "low rank adaptation"
  --limit 1`. The sandboxed attempt exited 126 with the expected SANDBOX GATE
  and prefix rule; the escalated run reached DeepXiv but failed with
  `Authentication failed: Invalid or expired token`. DeepXiv remains a
  configuration blocker until `DEEPXIV_TOKEN` is refreshed and the same command
  returns at least one result.
- 2026-07-08: Rechecked local network-provider configuration through
  `tools/_env.py` without printing secret values. `SEMANTIC_SCHOLAR_API_KEY`,
  `DEEPXIV_TOKEN`, `S2_MAX_RETRIES`, and `S2_RATE_LIMIT_WAIT_SECONDS` are all
  unset in the loaded environment. This means S2 calls use unauthenticated rate
  limits, DeepXiv has no usable configured token in the current shell, and the
  next L2 `$discover` / `$daily-arxiv` enrichment smoke should either configure
  provider secrets first or expect degraded/rate-limited provider behavior.
- 2026-07-08: Ran a local Review LLM configuration probe through `tools/_env.py`
  without printing secret values. `LLM_API_KEY`, `LLM_BASE_URL`, and
  `LLM_MODEL` are all unset in the loaded environment, so real Review LLM L2
  smokes for `$review`, `$refine`, `$rebuttal`, `$novelty`, `$exp-eval`,
  `$paper-plan`, and daily-arxiv `recommender=review-llm` cannot run yet. This
  remains a configuration blocker until `$setup` or manual `.env`/CI secret
  configuration provides all three values and a minimal Review LLM call
  succeeds.
- 2026-07-08: Audited for skills that still lacked an explicit Codex invocation
  surface. The audit found `$check`, `$discover`, and `$exp-eval` source docs
  had no `$skill` entry points, while `$survey` and `$rebuttal` still had
  slash-only follow-up/dependency wording in their tail sections. Added dual
  Claude/Codex invocation wording in both English and Chinese sources, synced
  active `.agents` / `.claude` skill trees, and added regression coverage that
  every localized source `SKILL.md` contains a concrete `$skill` command.
- 2026-07-08: Strengthened `$setup` evidence. The setup skill and
  `config/README.md` incorrectly told users to create `.env` from
  `config/.env.example`, but the repository and `setup.sh` use the project-root
  `.env.example`. Updated both localized setup skills and the config README to
  use `cp .env.example .env`, synced active skill trees, and added regression
  coverage so the stale path cannot reappear.
- 2026-07-08: Added a deterministic `$prefill` local fixture. The smoke suite
  initializes a temp wiki, writes one canonical foundation page, rebuilds the
  index, appends the prefill log entry, then calls
  `tools/research_wiki.py find-similar-concept` with a candidate concept and
  alias. The result must prefer the `foundation` hit, proving later ingest runs
  can reference seeded foundations instead of creating duplicate concept pages;
  the fixture also verifies no raw files are written.
- 2026-07-08: Added a deterministic `$survey` archive fixture. The smoke suite
  creates a temp wiki with three existing paper pages, writes a related-work
  output under `wiki/outputs/`, adds `derived_from` edges from that output to
  each cited paper through `tools/research_wiki.py add-edge`, appends a survey
  log entry, and verifies no raw files are written. This covers the local
  provenance/write boundary while leaving full prose generation as L3.
- 2026-07-08: Added a deterministic `$paper-plan` evidence-map fixture. The
  smoke suite creates a temp validated idea, completed succeeded experiment,
  and cited paper pages, writes a `wiki/outputs/paper-plan-*.md` containing the
  evidence map, citation plan, and single-model review annotation, adds
  `derived_from` edges from the plan to the target idea and cited papers,
  rebuilds context, appends the paper-plan log entry, and verifies no raw files
  are written. This covers the local provenance/write boundary while leaving
  full Review LLM outline review as L3.
- 2026-07-08: Added a deterministic `$paper-draft` LaTeX artifact fixture. The
  smoke suite creates a temp wiki with a PAPER_PLAN and source evidence, writes
  a local `paper/` tree with `main.tex`, five section files, a figure,
  `math_commands.tex`, and `references.bib`, then verifies every `\input`,
  `\includegraphics`, `\cite`, and `\ref` target resolves, `\nocite{*}` is not
  used, `[UNCONFIRMED]` citation markers survive, the paper-draft log entry is
  appended, and no raw files are written. Full prose generation and Review LLM
  review remain L3.
- 2026-07-08: Added `tools/paper_compile_checks.py` and a deterministic
  `$paper-compile` checklist fixture. The helper scans a paper directory
  without invoking TeX, validates `main.tex`, `\input`, figure paths, citation
  keys vs. `references.bib`, `\ref`/`\label` targets, abstract presence,
  `[UNCONFIRMED]`, `\nocite{*}`, TODO/FIXME markers, and anonymity heuristics.
  The smoke suite verifies both a passing paper and a blocked paper, appends the
  compile log entry in a temp wiki, and confirms no raw files are written. This
  also fixed an inappropriate skill-doc example that searched for `VERIFY`
  instead of the actual `[UNCONFIRMED]` hard blocker.
- 2026-07-08: Added a deterministic `$rebuttal` traceability fixture. The smoke
  suite creates a temp review file under `raw/reviews/`, snapshots raw inputs,
  creates local idea/method/experiment evidence, writes rich and formal rebuttal
  outputs under `wiki/outputs/`, appends reviewer concerns to the idea Risks and
  method Limitations sections without changing idea status, appends the rebuttal
  log entry, verifies every Rv1-Cy concern is covered in both outputs, confirms
  no graph edges are created, and confirms raw inputs are unchanged. Real Review
  LLM stress-testing remains L2.
- 2026-07-08: Added a deterministic `$refine` one-round fixture. The smoke
  suite creates a temp `wiki/outputs/` artifact, applies a mocked review's
  Category A fix in place, records score history, fixed and unresolved issues,
  rebuilds `context_brief` and `open_questions`, appends the refine log entry,
  confirms no artifact copy is created, and confirms raw inputs are unchanged.
  Real Review LLM scoring and multi-round convergence remain L2.
- 2026-07-08: Added a deterministic `$review` single-model fallback fixture.
  The smoke suite creates a temp artifact plus linked idea/method/experiment
  context, synthesizes the required Review Report structure for the documented
  Review LLM-unavailable path, verifies score, verdict, weakness fixes,
  questions, wiki entity mapping, knowledge gaps, and `$skill` follow-ups, and
  confirms review remains read-only by comparing wiki/raw snapshots before and
  after report generation. Real Review LLM calls remain L2.
- 2026-07-08: Added a deterministic `$novelty` write-boundary fixture. The
  smoke suite creates a temp idea and prior-work page, synthesizes a local
  novelty report while confirming the default path is read-only, then exercises
  the documented `--write` path via `tools/research_wiki.py set-meta` and log.
  It verifies only `novelty_score` and `wiki/log.md` are changed, status and
  priority stay untouched, and raw inputs remain unchanged. External Web/S2/
  DeepXiv search and Review LLM cross-verification remain L2.
- 2026-07-08: Added a deterministic `$ideate` Phase 4 write fixture. The smoke
  suite checks `maturity --json`, creates a concept gap and source paper,
  writes one proposed idea with `--skip-validation` defaults and one failed
  `[filter]` idea for anti-repetition memory, adds `addresses_gap` and
  `inspired_by` edges only through `tools/research_wiki.py add-edge`, rebuilds
  `context_brief` and `open_questions`, appends the ideate log entry, compares
  maturity growth, and confirms raw inputs are unchanged. External landscape
  search, Review LLM brainstorm, and pilot selection remain L3.
- 2026-07-08: Added a deterministic `$edit` wiki/raw boundary fixture. The
  smoke suite initializes a temp wiki, edits a concept page, writes generated
  helper artifacts only under `raw/discovered/` and `raw/tmp/`, appends the edit
  log entry, and snapshots `raw/papers/`, `raw/notes/`, and `raw/web/` before
  and after to prove user-owned raw sources are not created, overwritten, moved,
  or deleted.
- 2026-07-08: Added a deterministic `$poster` artifact fixture. The smoke
  suite creates a minimal drafted paper, runs `tools/wiki2dag.py build` plus
  `tools/poster.py build`, `inject-title`, `inject-header`, `inject-figures`,
  and `validate`, then verifies `poster/dag.json`, `poster/outline.html`,
  `poster/poster.html`, copied images, anonymous title injection, venue header
  injection, unchanged `paper/` source files, the poster log entry, and no raw
  writes. Browser-backed `poster/poster.png` rendering and DOM overflow checks
  remain L3 because they depend on local browser availability.
- 2026-07-08: Added a deterministic `$visualize` local artifact fixture. The
  smoke suite creates a temp repo with `config/visualize.json`, a temp wiki with
  a paper/concept graph edge, then runs `tools/visualize.py
  generate-obsidian-config`, `generate-canvas`, and focused `generate-canvas`.
  It verifies `.obsidian/graph.json`, preserves an existing `.obsidian/app.json`,
  checks full and focused Canvas nodes/edge labels, and confirms no raw files
  are written. Starting the SPA server remains L2 because `tools/serve.py` may
  require the documented Codex network escalation.
