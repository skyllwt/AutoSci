# AutoSci — Runtime Contract (Qoder Edition)

Edit `i18n/en/AGENTS.md`, not the active copy at root. Run `setup-qoder.sh --lang en` (or `setup-qoder.ps1`) to sync.

## Repository Layout

- `wiki/` — product surface. `index.md` is the catalog; `log.md` is append-only; subdirs per entity kind; `wiki/graph/` is auto-generated.
- `runtime/` — contract source (schema + policy + templates). Read `runtime/CLAUDE.md` before changing any rule.
- `raw/` — user-owned `{papers,notes,web}/` (read-only) + skill-writable `discovered/`, `tmp/`.
- `tools/` — Python helpers (`research_wiki.py` is the wiki engine; `lint.py` is the validator).
- `.qoder/skills/` — Qoder-native skills generated from `i18n/en/skills` by `tools/convert_to_qoder.py`. Never hand-edit; change the i18n source and re-run setup.

Full tree: `docs/runtime-directory-structure.en.md`.

## Link Syntax

Wikilinks: `[[slug]]`. Slugs are lowercase, hyphen-separated, no spaces.

## Skill Invocation Convention (Qoder)

- Skills live in `.qoder/skills/<name>/SKILL.md`. A doc reference such as `/init` or `/ingest` means "invoke skill `init`" / "invoke skill `ingest`" — follow that skill's `SKILL.md` workflow step by step.
- When a skill delegates work to another skill (e.g. `/init` Step 5 fans out to `/ingest`), launch one Qoder subagent (Agent tool) per unit of work and hand it the delegated skill's instructions plus its inputs.
- Parallel fan-out uses Qoder subagents; the git-worktree isolation contract in `.qoder/skills/init/references/parallel-ingest.md` applies unchanged. Subagent prompts must use relative paths and the subagent's working directory must be the worktree path.
- MCP tools of the `llm-review` server are referenced as `llm-review.chat`, `llm-review.chat-reply`, and `llm-review.web_search`. Register the server from `.qoder/mcp.json` (or Qoder MCP settings) before using `/review`, `/rebuttal`, etc.
- Long-running services (e.g. `tools/serve.py`) run as background Bash processes owned by the Qoder session; do not wrap them in a subagent.

## Hard Rules

1. `raw/{papers,notes,web}` are user-owned, read-only. Skills append only to `raw/discovered/` or `raw/tmp/`.
2. `wiki/graph/` is derived. Modify only via `tools/research_wiki.py` (`add-edge`, `add-citation`, `rebuild-*`).
3. `wiki/log.md` is append-only. Never rewrite in place.
4. Forward link → write reverse simultaneously. Rules in `runtime/schema/xref.yaml`.
5. User-facing skill flags (those documented in a skill's **Usage** line) are user-owned. Do not invent, flip, or drop them based on repo state. If the user omitted one, use a default only when the skill documents omission behavior; otherwise ask.

## Where to look

| Need | Source |
|---|---|
| Page frontmatter fields, enums, defaults, lifecycle | `runtime/schema/entities.yaml` |
| Page body section structure                          | `runtime/templates/{kind}.md.tmpl` |
| Edge types, attributes, direction, confidence       | `runtime/schema/edges.yaml` |
| Forward → reverse link rules                         | `runtime/schema/xref.yaml` |
| Slug rule, ownership, edge storage location          | `runtime/schema/conventions.yaml` |
| Field/edge write permissions per skill               | `runtime/policy/writers.yaml` |
| Changing the contract / regen                        | `runtime/CLAUDE.md` |

## Python Environment

Prefer in order: `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) → active conda env → `python3` (`python` on Windows). Tools auto-load API keys from `~/.env` and project-root `.env` via `tools/_env.py`.
