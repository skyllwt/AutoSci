# AutoSci - Codex Project Instructions

Edit `i18n/en/AGENTS.md`, not the active copy at root. Run `./setup.sh --lang en` to sync.

`CLAUDE.md` is the Claude Code companion file. Keep shared repository rules equivalent between `AGENTS.md` and `CLAUDE.md` unless a rule is specific to one agent runtime.

## Agent Surfaces

- Claude Code skills live in `.claude/skills` and are invoked as slash commands such as `/init` and `/ingest`.
- Codex skills live in `.agents/skills` and are invoked with `$init`, `$ingest`, or from Codex `/skills`.
- The source for both active skill trees is `i18n/<lang>/skills`. When changing a workflow, edit the localized source files, keep English and Chinese copies aligned, then run setup to regenerate active files.
- Codex requires each `SKILL.md` frontmatter to include both `name` and `description`; keep that metadata when adding or editing skills.

## Repository Layout

- `wiki/` - product surface. `index.md` is the catalog; `log.md` is append-only; subdirs per entity kind; `wiki/graph/` is auto-generated.
- `runtime/` - contract source (schema + policy + templates). Read `runtime/CLAUDE.md` before changing any rule; despite the filename, it is the shared runtime contract.
- `raw/` - user-owned `{papers,notes,web}/` (read-only) + skill-writable `discovered/`, `tmp/`.
- `tools/` - Python helpers (`research_wiki.py` is the wiki engine; `lint.py` is the validator).

Full tree: `docs/runtime-directory-structure.en.md`.

## Link Syntax

Wikilinks: `[[slug]]`. Slugs are lowercase, hyphen-separated, no spaces.

## Hard Rules

1. `raw/{papers,notes,web}` are user-owned, read-only. Skills append only to `raw/discovered/` or `raw/tmp/`.
2. `wiki/graph/` is derived. Modify only via `tools/research_wiki.py` (`add-edge`, `add-citation`, `rebuild-*`).
3. `wiki/log.md` is append-only. Never rewrite in place.
4. Forward link -> write reverse simultaneously. Rules in `runtime/schema/xref.yaml`.
5. User-facing skill flags (those listed in a skill's `argument-hint`) are user-owned. Do not invent, flip, or drop them based on repo state. If the user omitted one, use a default only when the skill documents omission behavior; otherwise ask.

## Where To Look

| Need | Source |
|---|---|
| Page frontmatter fields, enums, defaults, lifecycle | `runtime/schema/entities.yaml` |
| Page body section structure | `runtime/templates/{kind}.md.tmpl` |
| Edge types, attributes, direction, confidence | `runtime/schema/edges.yaml` |
| Forward -> reverse link rules | `runtime/schema/xref.yaml` |
| Slug rule, ownership, edge storage location | `runtime/schema/conventions.yaml` |
| Field/edge write permissions per skill | `runtime/policy/writers.yaml` |
| Changing the contract / regen | `runtime/CLAUDE.md` |

## Python Environment

Prefer in order: `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) -> active conda env -> `python3` (`python` on Windows). Tools auto-load API keys from `~/.env` and project-root `.env` via `tools/_env.py`.


## Sandbox — escalation contract

Codex runs Python tools in a seccomp sandbox that blocks `socket(2)`. Tools that
reach out to Semantic Scholar, DeepXiv, arXiv, or any HTTP API will exit with
code 126 and print a "SANDBOX GATE" message. **Do not silently degrade when you
see this.** Rerun the failing command with `sandbox_permissions: "require_escalated"`
and the matching prefix rule from the table below.

### Prefix-rule table

| Tool | Prefix rule | Justification |
|---|---|---|
| `tools/discover.py` | `["$PYTHON_BIN", "tools/discover.py"]` | "AutoSci discover needs network access (S2/DeepXiv)" |
| `tools/init_discovery.py` | `["$PYTHON_BIN", "tools/init_discovery.py"]` | "AutoSci init discovery needs network access (S2/DeepXiv/arXiv)" |
| `tools/fetch_s2.py` | `["$PYTHON_BIN", "tools/fetch_s2.py"]` | "AutoSci fetch_s2 needs network access" |
| `tools/fetch_deepxiv.py` | `["$PYTHON_BIN", "tools/fetch_deepxiv.py"]` | "AutoSci fetch_deepxiv needs network access" |
| `tools/fetch_arxiv.py` | `["$PYTHON_BIN", "tools/fetch_arxiv.py"]` | "AutoSci fetch_arxiv needs network access" |
| `tools/fetch_wikipedia.py` | `["$PYTHON_BIN", "tools/fetch_wikipedia.py"]` | "AutoSci fetch_wikipedia needs network access" |
| `tools/daily_arxiv.py` | `["$PYTHON_BIN", "tools/daily_arxiv.py"]` | "AutoSci daily_arxiv needs network access" |
| `tools/prepare_paper_source.py` | `["$PYTHON_BIN", "tools/prepare_paper_source.py"]` | "AutoSci prepare_paper_source needs network access" |
| `tools/backfill_citations.py` | `["$PYTHON_BIN", "tools/backfill_citations.py"]` | "AutoSci backfill_citations needs network access" |
| `tools/serve.py` | `["$PYTHON_BIN", "tools/serve.py"]` | "AutoSci serve needs network access" |

`$PYTHON_BIN` is resolved by the skill as `.venv/bin/python` (or equivalent).
The agent should expand it to the actual absolute path, e.g.:

- `["/path/to/AutoSci/.venv/bin/python", "tools/discover.py"]`

### Responding to SANDBOX GATE

When a tool exits with code 126 and prints "SANDBOX GATE":

1. Read the `prefix_rule` suggestion from the stderr output.
2. Rerun the **exact same command** with:
   - `sandbox_permissions: "require_escalated"`
   - `justification` from the table above
   - `prefix_rule` from the table above
3. Do **not** skip, replace with a different approach, or silently degrade to
   local-only analysis. Network tools are the authoritative source for
   citations, cross-references, novelty checks, and discovery.

## Review Guidelines

- Treat loss or mutation of user-owned `raw/`, `wiki/`, `.env`, and generated experiment outputs as high severity.
- Check that changes keep `.claude/skills`, `.agents/skills`, and `i18n/<lang>/skills` synchronized when workflow instructions move.
- Prefer deterministic tool changes in `tools/` over duplicating logic inside skill prompts.
