"""Schema access API for OmegaWiki.

Hand-written, fully data-driven loader.  Reads runtime/schema/*.yaml at import
time and exposes:

  - raw YAML:        ENTITIES, EDGES, XREF, CONVENTIONS, WRITERS
  - derived dicts:   ENTITY_DIRS, REQUIRED_FIELDS, VALID_VALUES, FIELD_DEFAULTS,
                     EDGE_TYPE_SPECS
  - derived sets:    PAPER_PAPER_EDGE_TYPES, PAPER_CONCEPT_EDGE_TYPES,
                     SYMMETRIC_EDGE_TYPES, CONFIDENCE_REQUIRED_EDGE_TYPES,
                     VALID_EDGE_TYPES
  - static enums:    EDGE_CONFIDENCE_VALUES, CITATION_EDGE_TYPES, CITATION_SOURCES
  - legacy sets:     LEGACY_EDGE_TYPES, LEGACY_PAPER_PAPER_EDGE_TYPES,
                     LEGACY_PAPER_CONCEPT_EDGE_TYPES
  - helpers:         edge_types_matching, edge_type_spec, edge_is_symmetric,
                     edge_requires_confidence, edge_expected_endpoint,
                     edge_endpoint_matches, edge_is_legacy_for_endpoint,
                     edge_legacy_replacement_message

All derivations are dict comprehensions over ENTITIES / EDGES — adding a new
entity or edge to YAML automatically propagates without any code change here.
"""

from __future__ import annotations

from pathlib import Path
import yaml

# ── Raw YAML ────────────────────────────────────────────────────────────────

_SCHEMA = Path(__file__).resolve().parent / 'schema'
_POLICY = Path(__file__).resolve().parent / 'policy'

def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))

ENTITIES    = _load(_SCHEMA / 'entities.yaml')
EDGES       = _load(_SCHEMA / 'edges.yaml')
XREF        = _load(_SCHEMA / 'xref.yaml')
CONVENTIONS = _load(_SCHEMA / 'conventions.yaml')
WRITERS     = _load(_POLICY / 'writers.yaml')

# ── Static / wildcard constants ─────────────────────────────────────────────

ANY_ENDPOINT        = "*"
DIRECTION_DIRECTED  = "directed"
DIRECTION_SYMMETRIC = "symmetric"
CONFIDENCE_REQUIRED = "required"
CONFIDENCE_NONE     = "none"

EDGE_CONFIDENCE_VALUES = {"high", "medium", "low"}
CITATION_EDGE_TYPES    = {"cites"}
CITATION_SOURCES       = set(EDGES['cites']['attributes']['source']['values'])

# Legacy edge types kept for /lint backwards-compat reports.
LEGACY_EDGE_TYPES = {"extends", "supersedes"}
LEGACY_PAPER_PAPER_EDGE_TYPES   = LEGACY_EDGE_TYPES | {"inspired_by", "contradicts", "supports"}
LEGACY_PAPER_CONCEPT_EDGE_TYPES = {"supports", "extends"}

# ── Derived constants (data-driven dict comprehensions) ─────────────────────

ENTITY_DIRS = list(ENTITIES.keys())

REQUIRED_FIELDS = {
    kind: [n for n, f in e['fields'].items() if f.get('required')]
    for kind, e in ENTITIES.items()
}

# Valid enum/range values per "{entity}.{field}".  Kept as string sets to match
# the historical /lint contract (importance "1".."5", outcome includes "").
def _valid_values_for(kind: str, fname: str, fspec: dict) -> set[str] | None:
    if fspec.get('type') == 'enum':
        vals = {str(v) for v in fspec['values']}
        if kind == 'experiments' and fname == 'outcome':
            vals.add('')
        return vals
    if fspec.get('type') == 'int' and 'range' in fspec:
        lo, hi = fspec['range']
        return {str(i) for i in range(int(lo), int(hi) + 1)}
    return None

def _build_valid_values() -> dict[str, set[str]]:
    out = {}
    for kind, e in ENTITIES.items():
        for fname, fspec in e['fields'].items():
            v = _valid_values_for(kind, fname, fspec)
            if v is not None:
                out[f"{kind}.{fname}"] = v
    return out

VALID_VALUES = _build_valid_values()

def _fmt_default(v):
    if isinstance(v, list) and not v:
        return '[]'
    return str(v)

def _build_field_defaults() -> dict[str, dict[str, str]]:
    out = {}
    for kind, e in ENTITIES.items():
        d = {n: _fmt_default(f['default'])
             for n, f in e['fields'].items()
             if f.get('required') and 'default' in f}
        if d:
            out[kind] = d
    return out

FIELD_DEFAULTS = _build_field_defaults()

# Edge specs (the cites edge is excluded — it has its own CITATION_* registry).
EDGE_TYPE_SPECS: dict[str, dict[str, str]] = {
    et: {
        'from_kind':  e['endpoints']['from'],
        'to_kind':    e['endpoints']['to'],
        'direction':  e['direction'],
        'confidence': (CONFIDENCE_REQUIRED
                       if e.get('attributes', {}).get('confidence', {}).get('required')
                       else CONFIDENCE_NONE),
        'workflow':   e['workflow'],
    }
    for et, e in EDGES.items()
    if et != 'cites'
}

# ── Helper functions (operate on EDGE_TYPE_SPECS) ───────────────────────────

def _spec_matches(spec: dict, key: str, value):
    return value is None or spec.get(key) == value


def edge_types_matching(*, from_kind=None, to_kind=None, direction=None,
                        confidence=None, workflow=None) -> set[str]:
    """Return edge types whose registry metadata matches all provided filters."""
    return {
        et for et, spec in EDGE_TYPE_SPECS.items()
        if _spec_matches(spec, 'from_kind',  from_kind)
        and _spec_matches(spec, 'to_kind',    to_kind)
        and _spec_matches(spec, 'direction',  direction)
        and _spec_matches(spec, 'confidence', confidence)
        and _spec_matches(spec, 'workflow',   workflow)
    }


def edge_type_spec(edge_type: str):
    return EDGE_TYPE_SPECS.get(edge_type)


def edge_is_symmetric(edge_type: str) -> bool:
    spec = edge_type_spec(edge_type)
    return bool(spec and spec.get('direction') == DIRECTION_SYMMETRIC)


def edge_requires_confidence(edge_type: str) -> bool:
    spec = edge_type_spec(edge_type)
    return bool(spec and spec.get('confidence') == CONFIDENCE_REQUIRED)


def edge_expected_endpoint(edge_type: str, endpoint: str) -> str:
    spec = edge_type_spec(edge_type)
    if not spec:
        return ANY_ENDPOINT
    return spec.get(f'{endpoint}_kind', ANY_ENDPOINT)


def edge_endpoint_matches(edge_type: str, from_kind: str, to_kind: str) -> bool:
    spec = edge_type_spec(edge_type)
    if not spec:
        return True
    expected_from = spec.get('from_kind', ANY_ENDPOINT)
    expected_to   = spec.get('to_kind',   ANY_ENDPOINT)
    return ((expected_from == ANY_ENDPOINT or expected_from == from_kind)
            and (expected_to == ANY_ENDPOINT or expected_to == to_kind))


def edge_is_legacy_for_endpoint(edge_type: str, from_kind: str, to_kind: str) -> bool:
    if from_kind == 'papers' and to_kind == 'papers':
        return edge_type in LEGACY_PAPER_PAPER_EDGE_TYPES
    if from_kind == 'papers' and to_kind == 'concepts':
        return edge_type in LEGACY_PAPER_CONCEPT_EDGE_TYPES
    return False


def edge_legacy_replacement_message(edge_type: str, from_kind: str, to_kind: str) -> str:
    if from_kind == 'papers' and to_kind == 'papers':
        return f"Legacy paper-paper edge {edge_type!r}; use the new paper relation types"
    if from_kind == 'papers' and to_kind == 'concepts':
        return (f"Legacy paper-concept edge {edge_type!r}; use introduces_concept, "
                "uses_concept, extends_concept, or critiques_concept")
    return f"Legacy edge {edge_type!r}"


# ── Derived sets used by call sites ─────────────────────────────────────────

PAPER_PAPER_EDGE_TYPES         = edge_types_matching(from_kind='papers', to_kind='papers',  workflow='ingest')
PAPER_CONCEPT_EDGE_TYPES       = edge_types_matching(from_kind='papers', to_kind='concepts', workflow='ingest')
SYMMETRIC_EDGE_TYPES           = edge_types_matching(direction=DIRECTION_SYMMETRIC)
CONFIDENCE_REQUIRED_EDGE_TYPES = edge_types_matching(confidence=CONFIDENCE_REQUIRED)
VALID_EDGE_TYPES               = set(EDGE_TYPE_SPECS) | LEGACY_EDGE_TYPES


# ── Generic edge-attribute validator (used by lint + research_wiki) ─────────

def validate_edge_attributes(edge_type: str, attrs: dict) -> list[str]:
    """Validate a dict of edge attributes against edges.yaml::attributes spec.
    Returns a list of error messages (empty if valid)."""
    errors = []
    spec = EDGES.get(edge_type, {}).get('attributes', {})
    for attr_name, attr_spec in spec.items():
        value = attrs.get(attr_name)
        if attr_spec.get('required') and not value:
            errors.append(f"{edge_type} requires --{attr_name}")
            continue
        if value is None:
            continue
        if attr_spec.get('type') == 'enum':
            if value not in attr_spec['values']:
                errors.append(
                    f"{edge_type}.{attr_name}={value!r} not in {attr_spec['values']}"
                )
    return errors


# ── Lifecycle transition validator ──────────────────────────────────────────

def validate_lifecycle_transition(kind: str, from_state: str, to_state: str) -> str | None:
    """Return None if transition is legal, an error message otherwise.
    Returns None if the entity has no lifecycle declared (no validation)."""
    transitions = ENTITIES.get(kind, {}).get('lifecycle', {}).get('transitions', {})
    if not transitions:
        return None
    if from_state == to_state:
        return None
    legal = transitions.get(from_state, [])
    if to_state not in legal:
        return (f"{kind}: illegal transition {from_state!r} → {to_state!r}; "
                f"legal from {from_state!r}: {legal}")
    return None
