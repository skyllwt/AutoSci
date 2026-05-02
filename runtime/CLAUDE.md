# runtime/ — Wiki Runtime Contract

Single source of truth for what is structurally legal in the wiki.  YAML in
`schema/` and `policy/` is the contract; `loader.py` is the Python access API
consumed by `tools/lint.py` and `tools/research_wiki.py`.  **No codegen step** —
edit YAML, restart the tool.

## Folder layout

```
runtime/
├── __init__.py     marks runtime/ as a Python package
├── loader.py       schema access API (imported by tools/lint.py + research_wiki.py)
├── schema/         data-shape contract (4 YAMLs)
├── policy/         access control (writers.yaml)
└── templates/      per-entity body skeletons used by /init and /ingest
```

## How to add things

Every change below is **YAML-only, zero Python change**.  Edit, save, done.

### Entity-related (`schema/entities.yaml` + `templates/`)

- **New entity type** — add a top-level block (`<kind>:` with `dir`, `fields`,
  optional `lifecycle`, optional `terminal: true`) and create
  `templates/<kind>.md.tmpl` with the body section skeleton.
- **New field on an entity** — add it under that entity's `fields:` block with
  `type` + optional `required` / `default` / `range` / `values` / `to`.
- **New conditional-required rule** — set `required_when: { other_field: value }`
  on the field.  `lint` auto-validates.
- **New lifecycle state or transition** — edit the entity's
  `lifecycle.transitions:` map.  `research_wiki.py transition` auto-validates.

### Edge-related (`schema/edges.yaml`)

- **New edge type** — add a top-level block with `endpoints`, `direction`
  (`directed | symmetric`), `workflow`, `attributes`.
- **New attribute on an edge** — add it under that edge's `attributes:` block
  with `type` + optional `required` / `values`.  `add-edge` collects it,
  `lint` validates it.
- **Different storage location** — list it under
  `conventions.yaml::edge_storage::exceptions` (default is `wiki/graph/edges.jsonl`).

### Cross-reference (`schema/xref.yaml`)

- **New forward → reverse rule** — append to `rules:` with a `forward` block
  (`kind` + one of `frontmatter_field` / `body_section` / `edge_type`, plus
  `target`) and a `reverse` block (`kind` + `frontmatter_field` or
  `body_section`, plus `action: append_slug | append_record`).  `lint` auto-checks.

### Access control (`policy/writers.yaml`)

- **Restrict who writes a field** — add `<kind>.<field>: { writers: [skill1, skill2] }`
  under `fields:`.  Add `frozen_after_first_write: true` if it should not be
  modified after creation.
- **Restrict who writes an edge type** — add `<edge_type>: [skill1, skill2]`
  under `edges:`.

### Conventions (`schema/conventions.yaml`)

- **Change slug rule, log grammar, ownership zones** — edit the corresponding
  top-level key.

## When Python changes ARE needed

Only when extending the **schema language itself**, not when adding more data:

- New field type (e.g. `list_date`, `tuple_str`) — extend `loader.py::_valid_values_for`
- New xref action (e.g. `replace_slug` vs `append_slug`) — extend `lint.py::_has_reverse`
- New cross-cutting helper (e.g. `edge_supports_evidence_search`) — add to `loader.py`

## Out of scope

- Skill prompts and workflow logic — `.claude/skills/<skill>/`
- Lint severity / auto-fix policy — derived from `required` / `default` in schema
- Migration history — git log + one-shot scripts; no `migrations/` folder
