#!/usr/bin/env python3
"""OmegaWiki — Wiki Knowledge Engine.

Core operations for a wiki-centric research knowledge base: entity metadata
read/write, typed graph management, knowledge-state queries, purpose-driven
context compilation, lifecycle enforcement, and audit logging.

Called by skills via:  Bash: python3 tools/research_wiki.py <command> [args]

Commands:
    # Infrastructure
    init <wiki_root>
    slug "<title>"
    log <wiki_root> "<message>"

    # Frontmatter operations
    read-meta <path> [field]
    set-meta <path> <field> <value> [--append]

    # Graph operations
    add-edge <wiki_root> --from <id> --to <id> --type <type> [--evidence "..."] [--confidence high|medium|low]
    add-citation <wiki_root> --from papers/a --to papers/b [--source semantic_scholar]
    batch-edges <wiki_root>                          # reads JSON array from stdin
    dedup-edges <wiki_root>
    dedup-citations <wiki_root>

    # Knowledge queries
    find <wiki_root> <entity_type> [--field value ...]
    query <wiki_root> <subquery> [options]
    neighbors <wiki_root> <node_id> [--depth N] [--edge-type T] [--incoming|--outgoing]

    # Derived data
    compile-context <wiki_root> --for <purpose> [--max-chars 8000]
    rebuild-context-brief <wiki_root> [--max-chars 8000]   # alias for compile-context --for general
    rebuild-open-questions <wiki_root>
    rebuild-index <wiki_root>

    # Lifecycle
    transition <path> --to <status> [--reason "..."]

    # Statistics
    stats <wiki_root> [--json]
    maturity <wiki_root> [--json]

    # Checkpoint (batch operation resume)
    checkpoint-save <wiki_root> <task_id> <item> [--failed]
    checkpoint-load <wiki_root> <task_id>
    checkpoint-clear <wiki_root> <task_id>
    checkpoint-set-meta <wiki_root> <task_id> <key> <value>
    checkpoint-get-meta <wiki_root> <task_id> [<key>]

    # SciEvolve shared spine
    scievolve-init <wiki_root>
    scievolve-record-signal <wiki_root> --source user|task|open --dimension memory|workflow|orchestration --target ... --kind ... --summary ...
    scievolve-report <wiki_root> [--dimension memory|workflow|orchestration] [--target ...] [--propose] [--json]
    dream <wiki_root> [--agent-response path] [--use-llm] [--propose-only] [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except Exception:  # pragma: no cover - optional LLM path
    requests = None  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Schema API lives in runtime/loader.py — single source for both this file and
# tools/lint.py.  The 3-line bridge below makes runtime/ importable from tools/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime.loader import (  # noqa: E402
    CITATION_SOURCES,
    CONVENTIONS,
    EDGE_CONFIDENCE_VALUES,
    EDGES,
    ENTITIES,
    ENTITY_DIRS,
    SYMMETRIC_EDGE_TYPES,
    VALID_EDGE_TYPES,
    edge_is_legacy_for_endpoint,
    edge_endpoint_matches,
    edge_expected_endpoint,
    edge_is_symmetric,
    edge_legacy_replacement_message,
    edge_requires_confidence,
    validate_edge_attributes,
    validate_lifecycle_transition,
)
try:
    from scievolve import (  # noqa: E402
        SCIEVOLVE_CONFIDENCE_VALUES,
        SCIEVOLVE_DIMENSION_VALUES,
        SCIEVOLVE_SEVERITY_VALUES,
        SCIEVOLVE_SOURCE_VALUES,
        load_scievolve_signals,
        scievolve_record_application,
        scievolve_init,
        scievolve_record_signal,
        scievolve_report,
        scievolve_update_proposal_status,
        scievolve_write_proposal,
    )
except ImportError:  # pragma: no cover - supports `python -m tools.research_wiki`
    from tools.scievolve import (  # noqa: E402
        SCIEVOLVE_CONFIDENCE_VALUES,
        SCIEVOLVE_DIMENSION_VALUES,
        SCIEVOLVE_SEVERITY_VALUES,
        SCIEVOLVE_SOURCE_VALUES,
        load_scievolve_signals,
        scievolve_record_application,
        scievolve_init,
        scievolve_record_signal,
        scievolve_report,
        scievolve_update_proposal_status,
        scievolve_write_proposal,
    )

DERIVED_DIR = "graph"

STOP_WORDS = frozenset({
    "a", "an", "the", "of", "for", "in", "on", "with", "via",
    "and", "to", "by", "is", "are", "from", "that", "this",
    "its", "at", "as", "or", "be", "it", "not", "but", "we",
    "can", "do", "has", "have", "was", "were", "been", "our",
})

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def slugify(title: str) -> str:
    """Generate a kebab-case slug from a paper/concept title.

    Rules (from product CLAUDE.md):
      - All lowercase, hyphen-separated, no spaces
      - Extract meaningful keywords from title, drop stop words
      - Keep first 5-6 keywords for reasonable length

    Examples:
        >>> slugify("LoRA: Low-Rank Adaptation of Large Language Models")
        'lora-low-rank-adaptation-large-language-models'
        >>> slugify("Attention Is All You Need")
        'attention-all-you-need'
    """
    # Normalize: lowercase, replace non-alphanum with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    words = text.split()
    # Filter stop words but keep short meaningful words (3+ chars or known terms)
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    if not keywords:
        keywords = [w for w in words if w]  # fallback: keep all
    if not keywords:
        return "untitled"
    # Cap at 6 keywords to keep slugs manageable
    return "-".join(keywords[:6])


# ---------------------------------------------------------------------------
# Wiki init
# ---------------------------------------------------------------------------

def init_wiki(wiki_root: str) -> None:
    """Initialize wiki directory structure with all entity dirs and graph/.

    Creates:
      - one directory per entity kind in runtime.loader.ENTITY_DIRS
      - graph/ with empty edges.jsonl, citations.jsonl, context_brief.md, open_questions.md
      - outputs/
      - index.md, log.md (if they don't exist)
    """
    root = Path(wiki_root)

    # Entity directories
    for d in ENTITY_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Derived graph directory
    graph = root / DERIVED_DIR
    graph.mkdir(parents=True, exist_ok=True)

    # Outputs directory
    (root / "outputs").mkdir(parents=True, exist_ok=True)

    # Seed files (only if they don't already exist)
    _write_if_missing(root / "index.md", _initial_index())
    _write_if_missing(root / "log.md", _initial_log())
    _write_if_missing(graph / "edges.jsonl", "")
    _write_if_missing(graph / "citations.jsonl", "")
    _write_if_missing(graph / "context_brief.md",
                      "# Query Pack\n\n_Auto-generated compressed context. Do not edit._\n")
    _write_if_missing(graph / "open_questions.md",
                      "# Gap Map\n\n_Auto-generated open questions. Do not edit._\n")

    append_log(wiki_root, "init | wiki initialized")
    print(json.dumps({"status": "ok", "wiki_root": str(root)}))


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _initial_index() -> str:
    sections = []
    for entity in ENTITY_DIRS:
        sections.append(f"{entity}:")
    return "# Wiki Index\n\n" + "\n".join(sections) + "\n"


def _initial_log() -> str:
    return "# OmegaWiki Log\n\n"


# ---------------------------------------------------------------------------
# Edge and citation management
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _node_kind(node_id: str) -> str:
    return node_id.split("/", 1)[0] if "/" in node_id else ""


def _validate_node_refs(root: Path, *node_ids: str) -> list[str]:
    warnings: list[str] = []
    for node_id in node_ids:
        if "/" in node_id:
            entity_path = root / f"{node_id}.md"
            if not entity_path.exists():
                warnings.append(f"{node_id}.md not found")
    return warnings


def _edge_topology_issues(edge_type: str, from_id: str, to_id: str,
                          legacy_check: bool = False) -> list[str]:
    """Endpoint / self-edge / legacy checks (the parts that aren't attribute-level)."""
    issues: list[str] = []
    from_kind = _node_kind(from_id)
    to_kind = _node_kind(to_id)

    if legacy_check and edge_is_legacy_for_endpoint(edge_type, from_kind, to_kind):
        issues.append(edge_legacy_replacement_message(edge_type, from_kind, to_kind))
    if not edge_endpoint_matches(edge_type, from_kind, to_kind):
        expected_from = edge_expected_endpoint(edge_type, "from")
        expected_to = edge_expected_endpoint(edge_type, "to")
        issues.append(f"{edge_type} should connect {expected_from}/* -> {expected_to}/*")
    if (edge_expected_endpoint(edge_type, "from") == "papers"
            and edge_expected_endpoint(edge_type, "to") == "papers"
            and from_id == to_id):
        issues.append(f"{edge_type} should not connect a paper to itself")
    return issues


def _semantic_edge_warnings(edge_type: str, from_id: str, to_id: str,
                            confidence: str = "",
                            evidence: str = "") -> list[str]:
    return (_edge_topology_issues(edge_type, from_id, to_id, legacy_check=False)
            + validate_edge_attributes(edge_type,
                                       {"confidence": confidence, "evidence": evidence}))


def _semantic_edge_errors(edge_type: str, from_id: str, to_id: str,
                          confidence: str = "",
                          evidence: str = "") -> list[str]:
    """Hard validation for new writes. Legacy graph rows remain lint-readable."""
    return (_edge_topology_issues(edge_type, from_id, to_id, legacy_check=True)
            + validate_edge_attributes(edge_type,
                                       {"confidence": confidence, "evidence": evidence}))


def _canonical_edge_ids(from_id: str, to_id: str, edge_type: str,
                        symmetric: bool = False) -> tuple[str, str, bool, str]:
    is_symmetric = symmetric or edge_is_symmetric(edge_type)
    if is_symmetric and not edge_is_symmetric(edge_type):
        return from_id, to_id, False, f"symmetric is only valid for {sorted(SYMMETRIC_EDGE_TYPES)}"
    if is_symmetric:
        left, right = sorted([from_id, to_id])
        return left, right, True, ""
    return from_id, to_id, False, ""


def _edge_key(edge: dict) -> tuple[str, str, str]:
    from_id = str(edge.get("from", ""))
    to_id = str(edge.get("to", ""))
    edge_type = str(edge.get("type", ""))
    if edge.get("symmetric") is True or edge_is_symmetric(edge_type):
        from_id, to_id = sorted([from_id, to_id])
    return from_id, to_id, edge_type


def add_edge(wiki_root: str, from_id: str, to_id: str,
             edge_type: str, evidence: str = "", confidence: str = "",
             symmetric: bool = False) -> None:
    """Append a typed edge to graph/edges.jsonl with dedup and entity validation."""
    if edge_type not in VALID_EDGE_TYPES:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown edge type '{edge_type}'. Valid: {sorted(VALID_EDGE_TYPES)}"
        }))
        sys.exit(1)
    if confidence and confidence not in EDGE_CONFIDENCE_VALUES:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown confidence '{confidence}'. Valid: {sorted(EDGE_CONFIDENCE_VALUES)}"
        }))
        sys.exit(1)

    from_id, to_id, is_symmetric, error = _canonical_edge_ids(
        from_id, to_id, edge_type, symmetric
    )
    if error:
        print(json.dumps({"status": "error", "message": error}))
        sys.exit(1)

    root = Path(wiki_root)
    edges_path = root / DERIVED_DIR / "edges.jsonl"
    edges_path.parent.mkdir(parents=True, exist_ok=True)

    errors = _semantic_edge_errors(edge_type, from_id, to_id, confidence, evidence)
    if errors:
        print(json.dumps({"status": "error", "errors": errors},
                         ensure_ascii=False))
        sys.exit(1)

    warnings = _validate_node_refs(root, from_id, to_id)
    warnings.extend(_semantic_edge_warnings(
        edge_type, from_id, to_id, confidence, evidence
    ))
    for msg in warnings:
        print(msg, file=sys.stderr)

    # Dedup: check existing edges
    target_key = _edge_key({
        "from": from_id, "to": to_id, "type": edge_type,
        "symmetric": is_symmetric,
    })
    if edges_path.exists():
        for line in edges_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _edge_key(e) == target_key:
                result: dict = {"status": "exists",
                                "message": f"{from_id} --{edge_type}--> {to_id}"}
                if warnings:
                    result["warnings"] = warnings
                print(json.dumps(result))
                return

    edge = {
        "from": from_id,
        "to": to_id,
        "type": edge_type,
        "evidence": evidence,
        "date": _today(),
    }
    if confidence:
        edge["confidence"] = confidence
    if is_symmetric:
        edge["symmetric"] = True

    with open(edges_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    result2: dict = {"status": "ok",
                     "edge": f"{from_id} --{edge_type}--> {to_id}"}
    if warnings:
        result2["warnings"] = warnings
    print(json.dumps(result2))


def load_citations(wiki_root: str) -> list[dict]:
    """Load all bibliographic citation rows from citations.jsonl."""
    citations_path = Path(wiki_root) / DERIVED_DIR / "citations.jsonl"
    citations = []
    if not citations_path.exists():
        return citations
    for line in citations_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            citations.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return citations


def add_citation(wiki_root: str, from_id: str, to_id: str,
                 source: str = "semantic_scholar") -> None:
    """Append a deterministic bibliographic paper citation to graph/citations.jsonl."""
    if source not in CITATION_SOURCES:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown citation source '{source}'. Valid: {sorted(CITATION_SOURCES)}"
        }))
        sys.exit(1)

    root = Path(wiki_root)
    citations_path = root / DERIVED_DIR / "citations.jsonl"
    citations_path.parent.mkdir(parents=True, exist_ok=True)

    warnings = _validate_node_refs(root, from_id, to_id)
    if _node_kind(from_id) != "papers" or _node_kind(to_id) != "papers":
        warnings.append("cites should connect papers/* -> papers/*")
    for msg in warnings:
        print(msg, file=sys.stderr)

    if citations_path.exists():
        for line in citations_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            if c.get("from") == from_id and c.get("to") == to_id:
                result: dict = {"status": "exists",
                                "citation": f"{from_id} --cites--> {to_id}"}
                if warnings:
                    result["warnings"] = warnings
                print(json.dumps(result))
                return

    citation = {
        "from": from_id,
        "to": to_id,
        "type": "cites",
        "source": source,
        "date": _today(),
    }
    with open(citations_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(citation, ensure_ascii=False) + "\n")

    result2: dict = {"status": "ok",
                     "citation": f"{from_id} --cites--> {to_id}"}
    if warnings:
        result2["warnings"] = warnings
    print(json.dumps(result2))


def _build_arxiv_index(wiki_root: Path) -> dict[str, str]:
    """Map arXiv ID (and S2 ID) → paper slug, for citation resolution.

    Reads each wiki/papers/*.md frontmatter once. Both 'arxiv' and 's2_id'
    fields are indexed so references arriving with either identifier match.
    """
    index: dict[str, str] = {}
    papers_dir = wiki_root / "papers"
    if not papers_dir.is_dir():
        return index
    for md in papers_dir.glob("*.md"):
        slug = md.stem
        fm = _parse_frontmatter(md)
        for key in ("arxiv", "s2_id"):
            v = fm.get(key)
            if isinstance(v, str) and v.strip():
                index[v.strip()] = slug
    return index


def add_citations_batch(wiki_root: str, citer_id: str) -> None:
    """Read a JSON array of S2 reference objects from stdin and append all
    matching `cites` rows to graph/citations.jsonl in one pass.

    Input: a JSON array (as emitted by `tools/fetch_s2.py references <arxiv>`)
    of paper objects, each with optional `externalIds.ArXiv` and `paperId`.

    Output: a single JSON status line with counts (received, matched, added,
    skipped_existing, unmatched).
    """
    if _node_kind(citer_id) != "papers":
        print(json.dumps({"status": "error",
                          "message": f"--citer must be papers/<slug>, got {citer_id}"}))
        sys.exit(1)

    root = Path(wiki_root)
    citations_path = root / DERIVED_DIR / "citations.jsonl"
    citations_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        refs = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error",
                          "message": f"stdin is not valid JSON: {exc}"}))
        sys.exit(1)
    if not isinstance(refs, list):
        print(json.dumps({"status": "error",
                          "message": "stdin must be a JSON array of reference objects"}))
        sys.exit(1)

    arxiv_index = _build_arxiv_index(root)

    existing: set[tuple[str, str]] = set()
    if citations_path.exists():
        for line in citations_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                existing.add((c.get("from", ""), c.get("to", "")))
            except json.JSONDecodeError:
                continue

    today = _today()
    matched = 0
    added = 0
    skipped_existing = 0
    unmatched_samples: list[str] = []
    new_rows: list[str] = []

    for ref in refs:
        if not isinstance(ref, dict):
            continue
        ext_ids = ref.get("externalIds") or {}
        arxiv = ext_ids.get("ArXiv") or ext_ids.get("arxiv")
        s2id = ref.get("paperId")
        target_slug = None
        if arxiv and arxiv in arxiv_index:
            target_slug = arxiv_index[arxiv]
        elif s2id and s2id in arxiv_index:
            target_slug = arxiv_index[s2id]
        if not target_slug:
            if len(unmatched_samples) < 5:
                title = (ref.get("title") or "")[:80]
                unmatched_samples.append(title or "(no title)")
            continue
        matched += 1
        to_id = f"papers/{target_slug}"
        if to_id == citer_id:
            continue  # don't cite yourself
        key = (citer_id, to_id)
        if key in existing:
            skipped_existing += 1
            continue
        existing.add(key)
        row = {
            "from": citer_id,
            "to": to_id,
            "type": "cites",
            "source": "semantic_scholar",
            "date": today,
        }
        new_rows.append(json.dumps(row, ensure_ascii=False))
        added += 1

    if new_rows:
        with open(citations_path, "a", encoding="utf-8") as f:
            f.write("\n".join(new_rows) + "\n")

    print(json.dumps({
        "status": "ok",
        "citer": citer_id,
        "received": len(refs),
        "matched": matched,
        "added": added,
        "skipped_existing": skipped_existing,
        "unmatched": len(refs) - matched,
        "unmatched_samples": unmatched_samples,
    }, ensure_ascii=False))


def _clean_link_slug(s) -> str | None:
    """Normalize a frontmatter link value to a bare slug.

    Wiki convention writes `key_papers: [[slug]]`, which the lightweight parser
    returns as one-element list `["[slug]"]` (or `[[slug]]` for `parent_topic:
    [[slug]]` parsed as scalar). Strip leading/trailing `[` and `]`, plus
    optional surrounding quotes."""
    if not isinstance(s, str):
        return None
    v = s.strip()
    while v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return v.strip() or None


def _resolve_target_kind(target_spec, target_slug: str, root: Path) -> str | None:
    """Given a field's `to` spec (str or list of kinds) and a slug, find which
    entity directory actually contains <slug>.md. Returns None if missing."""
    candidates = [target_spec] if isinstance(target_spec, str) else list(target_spec or [])
    for kind in candidates:
        spec = ENTITIES.get(kind)
        if not spec:
            continue
        entity_dir_name = spec["dir"].rstrip("/").split("/")[-1]
        if (root / entity_dir_name / f"{target_slug}.md").is_file():
            return kind
    # Fall back to first candidate even if file is missing (for orphan edges
    # that point at a not-yet-created entity — still useful for visualization).
    return candidates[0] if candidates else None


def project_frontmatter_edges(wiki_root: str | Path) -> list[dict]:
    """Walk all entity .md files and project link/list_link/list_object
    frontmatter fields into synthetic graph edges.

    Each projected edge carries:
      from:   "<kind>/<slug>"
      to:     "<target_kind>/<target_slug>"
      type:   "fm_<field>"     (fm_ prefix avoids collision with edges.yaml)
      source: "frontmatter"
      field:  "<kind>.<field>"

    Skipped:
      - foundations (terminal entities)
      - `papers.cited_by` (already a derived cache of cites)
      - empty or missing field values

    Pattern follows rebuild_index(): glob entity dirs, parse_frontmatter
    each file. No I/O beyond reads. Idempotent.
    """
    edges: list[dict] = []
    root = Path(wiki_root)

    for kind in ENTITY_DIRS:
        spec = ENTITIES.get(kind)
        if not spec or spec.get("terminal"):
            continue
        entity_dir_name = spec["dir"].rstrip("/").split("/")[-1]
        entity_dir = root / entity_dir_name
        if not entity_dir.is_dir():
            continue

        link_fields: list[tuple[str, dict]] = []
        for fname, fspec in spec.get("fields", {}).items():
            ftype = fspec.get("type")
            if ftype not in ("link", "list_link", "list_object"):
                continue
            if kind == "papers" and fname == "cited_by":
                continue  # cited_by is the derived reverse cache of cites
            link_fields.append((fname, fspec))

        if not link_fields:
            continue

        for md_path in sorted(entity_dir.glob("*.md")):
            slug = md_path.stem
            try:
                fm = _parse_frontmatter(md_path)
            except Exception:
                continue

            for fname, fspec in link_fields:
                target_spec = fspec.get("to")
                ftype = fspec["type"]
                raw_val = fm.get(fname)

                if ftype == "link":
                    if not raw_val or not isinstance(raw_val, str):
                        continue
                    targets = [raw_val]
                else:
                    if not raw_val:
                        continue
                    if not isinstance(raw_val, list):
                        continue
                    targets = raw_val

                for target in targets:
                    # list_link → str slug; list_object → dict with 'slug'
                    if isinstance(target, dict):
                        target_slug = _clean_link_slug(target.get("slug"))
                    else:
                        target_slug = _clean_link_slug(target)
                    if not target_slug:
                        continue

                    target_kind = _resolve_target_kind(target_spec, target_slug, root)
                    if not target_kind:
                        continue

                    edges.append({
                        "from": f"{kind}/{slug}",
                        "to":   f"{target_kind}/{target_slug}",
                        # fm_<kind>_<field> disambiguates fields that share a
                        # name across entities (e.g. concepts.key_papers vs
                        # topics.key_papers). Always derived from `kind` so
                        # adding a new entity that uses the same field name
                        # never collides with existing data.
                        "type": f"fm_{kind}_{fname}",
                        "source": "frontmatter",
                        "field": f"{kind}.{fname}",
                    })

    return edges


def rebuild_projected_edges(wiki_root: str) -> None:
    """Write projected frontmatter edges to graph/projected_edges.jsonl
    (overwrite). Useful for canvas / Obsidian generators that read on-disk
    artifacts; serve.py reads them dynamically and does not need this file."""
    root = Path(wiki_root)
    out_path = root / DERIVED_DIR / "projected_edges.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    edges = project_frontmatter_edges(root)
    lines = [json.dumps(e, ensure_ascii=False) for e in edges]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(out_path), "count": len(edges)}))


def load_edges(wiki_root: str) -> list[dict]:
    """Load all edges from edges.jsonl."""
    edges_path = Path(wiki_root) / DERIVED_DIR / "edges.jsonl"
    edges = []
    if not edges_path.exists():
        return edges
    for line in edges_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            edges.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return edges


def dedup_edges(wiki_root: str) -> None:
    """Deduplicate edges.jsonl by canonical (from, to, type), keeping first occurrence.

    Intended for use after parallel ingest: multiple agents may have added
    identical edges in their isolated worktrees, resulting in duplicates after
    the worktree branches are merged.
    """
    edges_path = Path(wiki_root) / DERIVED_DIR / "edges.jsonl"
    if not edges_path.exists():
        print(json.dumps({"status": "ok", "kept": 0, "removed": 0}))
        return

    lines = edges_path.read_text(encoding="utf-8").splitlines()
    seen: set[tuple[str, str, str]] = set()
    kept: list[str] = []
    removed = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            e = json.loads(stripped)
            edge_type = str(e.get("type", ""))
            if edge_is_symmetric(edge_type) or e.get("symmetric") is True:
                e["from"], e["to"] = sorted([str(e.get("from", "")),
                                             str(e.get("to", ""))])
                e["symmetric"] = True
            triple = _edge_key(e)
            if triple not in seen:
                seen.add(triple)
                kept.append(json.dumps(e, ensure_ascii=False))
            else:
                removed += 1
        except json.JSONDecodeError:
            kept.append(stripped)  # preserve malformed lines

    edges_path.write_text(
        "\n".join(kept) + ("\n" if kept else ""), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "kept": len(kept), "removed": removed}))


def dedup_citations(wiki_root: str) -> None:
    """Deduplicate citations.jsonl by (from, to), keeping first occurrence."""
    citations_path = Path(wiki_root) / DERIVED_DIR / "citations.jsonl"
    if not citations_path.exists():
        print(json.dumps({"status": "ok", "kept": 0, "removed": 0}))
        return

    lines = citations_path.read_text(encoding="utf-8").splitlines()
    seen: set[tuple[str, str]] = set()
    kept: list[str] = []
    removed = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            c = json.loads(stripped)
            key = (str(c.get("from", "")), str(c.get("to", "")))
            if key not in seen:
                seen.add(key)
                kept.append(stripped)
            else:
                removed += 1
        except json.JSONDecodeError:
            kept.append(stripped)

    citations_path.write_text(
        "\n".join(kept) + ("\n" if kept else ""), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "kept": len(kept), "removed": removed}))


# ---------------------------------------------------------------------------
# Query pack generation
# ---------------------------------------------------------------------------

def _is_linked_worktree() -> bool:
    # Linked worktrees have distinct --git-dir and --git-common-dir; the primary
    # checkout has them equal. Used to block graph rebuilds from /init subagents:
    # their worktree rebuilds collide on merge with the orchestrator's final one.
    try:
        git_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        common_dir = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return Path(git_dir).resolve() != Path(common_dir).resolve()


def _refuse_in_linked_worktree(cmd: str) -> None:
    if _is_linked_worktree():
        print(
            f"error: {cmd} is not permitted inside a linked git worktree.\n"
            "Graph rebuilds must run from the primary checkout; the /init "
            "orchestrator rebuilds once after all subagent merges. See "
            "init/SKILL.md INIT MODE.",
            file=sys.stderr,
        )
        sys.exit(2)


def rebuild_context_brief(wiki_root: str, max_chars: int = 8000) -> None:
    """Backward-compatible alias for ``compile_context --for general``."""
    _refuse_in_linked_worktree("rebuild-context-brief")
    compile_context(wiki_root, "general", max_chars)


# ---------------------------------------------------------------------------
# Gap map generation
# ---------------------------------------------------------------------------

def rebuild_open_questions(wiki_root: str) -> None:
    """Scan wiki pages for open questions / research gaps and write open_questions.md.

    Sources:
      - papers/:   ## Open questions
      - topics/:   ## Open problems  (including its ### Known gaps and ### Methodological gaps subsections)
      - concepts/: ## Open problems
    """
    _refuse_in_linked_worktree("rebuild-open-questions")
    root = Path(wiki_root)
    gaps: list[str] = []

    _collect_section_items(root / "papers",   "Open questions", gaps, "paper")
    _collect_section_items(root / "topics",   "Open problems",  gaps, "topic")
    _collect_section_items(root / "concepts", "Open problems",  gaps, "concept")

    content = "# Gap Map\n\n_Auto-generated open questions. Do not edit._\n\n"
    if gaps:
        content += "\n".join(gaps) + "\n"
    else:
        content += "_No gaps detected yet._\n"

    gap_path = root / DERIVED_DIR / "open_questions.md"
    gap_path.write_text(content, encoding="utf-8")
    print(json.dumps({"status": "ok", "gaps": len(gaps)}))


def _collect_section_items(directory: Path, section_name: str,
                           out: list[str], source_type: str) -> None:
    """Extract bullet items from a named markdown section across all files in a dir.

    The section is the H2 ``## {section_name}`` block. The block ends at the
    next H2 heading (``## ``) or end of file. H3+ subsections (``### ...``)
    inside the block are NOT treated as a break — their headings are skipped
    and their bullet items are collected — so topic ``## Open problems``
    pages with ``### Known gaps`` and ``### Methodological gaps`` are folded
    in as one stream of gaps.
    """
    if not directory.exists():
        return
    for f in sorted(directory.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        in_section = False
        for line in content.split("\n"):
            if re.match(rf"^##\s+{re.escape(section_name)}\s*$", line, re.IGNORECASE):
                in_section = True
                continue
            if in_section and re.match(r"^##\s+", line):
                break  # next H2 ends the block
            if in_section and re.match(r"^#{3,}\s+", line):
                continue  # H3+ heading inside the block: skip header, keep collecting
            if in_section and line.strip().startswith("-"):
                item = line.strip().lstrip("- ").strip()
                if item:
                    out.append(f"- [{source_type}/{f.stem}] {item}")


# ---------------------------------------------------------------------------
# Entity search: find
# ---------------------------------------------------------------------------

_COMPARE_RE = re.compile(r"^([<>]=?|!=)(.+)$")


def _match_filter(actual, pattern_str: str) -> bool:
    """Check if *actual* matches *pattern_str* (supports <, >, <=, >=, !=)."""
    m = _COMPARE_RE.match(pattern_str)
    if m:
        op, threshold_s = m.group(1), m.group(2)
        try:
            threshold = float(threshold_s)
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
        except (ValueError, TypeError):
            return False
        if op == "<":
            return actual_num < threshold
        if op == ">":
            return actual_num > threshold
        if op == "<=":
            return actual_num <= threshold
        if op == ">=":
            return actual_num >= threshold
        if op == "!=":
            return actual_num != threshold
    # Exact string match
    return str(actual) == pattern_str


def find_entities(wiki_root: str, entity_type: str,
                  filters: list[tuple[str, str]]) -> None:
    """Search entities of a given type by frontmatter field filters."""
    root = Path(wiki_root)
    entity_dir = root / entity_type

    if not entity_dir.exists():
        print(json.dumps([]))
        return

    results: list[dict] = []
    for f in sorted(entity_dir.glob("*.md")):
        fm = _parse_frontmatter(f)
        if not fm:
            continue

        match = True
        for field, pattern in filters:
            val = fm.get(field)
            if val is None:
                match = False
                break
            # If val is a list, check if pattern is in the list
            if isinstance(val, list):
                if pattern not in [str(x) for x in val]:
                    match = False
                    break
            elif not _match_filter(val, pattern):
                match = False
                break

        if match:
            results.append({"slug": f.stem, **fm})

    print(json.dumps(results, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Semantic dedup: find-similar-concept
# ---------------------------------------------------------------------------
#
# This query answers the question: "before I create a new concept with this
# title, does the wiki already have one that means the same thing?"
#
# It is deterministic (no LLM) and uses only token-level matching, but it is
# tuned for high recall — the LLM caller does the final semantic judgment
# from a small ranked list. Designed to be invoked from /ingest BEFORE any
# concept is created, to prevent the "subagent A and subagent B both create
# textual-gradient-descent under different slugs" failure mode.
#
# find-similar-concept ALSO scans wiki/foundations/ so that /ingest cannot
# accidentally create a concept that duplicates an existing foundation page
# (foundations are seeded by /prefill with their own title + aliases). A
# foundation hit is marked with entity_type="foundation" in the output so the
# caller can route to "reference instead of create" rather than merging.
#
# Score calibration:
#   1.00  exact normalized match (case + stop-words ignored)
#   0.85  one phrase fully contains the other (after normalization)
#   0.40-0.84  Jaccard similarity of content tokens, scaled
#   < 0.40  not returned
#
# Returns a JSON list sorted descending by score so the LLM can scan the
# top-k. Empty list means "safe to create a new entity".


def _normalize_text(text: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace. Used for phrase match."""
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(text.split())


def _content_tokens(text: str) -> set[str]:
    """Tokenize text into a set of content words (drop stop words and short tokens).

    Used for Jaccard similarity. The same tokenizer is used on both sides of
    each comparison so the result is symmetric.
    """
    if not text:
        return set()
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = set()
    for w in text.split():
        if len(w) >= 3 and w not in STOP_WORDS:
            tokens.add(w)
    return tokens


def _phrase_match_score(a: str, b: str) -> float:
    """Score two short phrases (titles, aliases) for semantic similarity.

    Returns 0.0 - 1.0. Score floor for return is 0.4 (lower → caller drops it).
    """
    if not a or not b:
        return 0.0
    na, nb = _normalize_text(a), _normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        shorter = na if len(na) < len(nb) else nb
        if len(shorter.split()) >= 2:
            return 0.85
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    j = inter / union
    if j >= 0.7:
        return j
    if j >= 0.4:
        return 0.4 + (j - 0.4) * 0.5
    return 0.0


def _scan_entity_dir_for_similar(entity_dir: Path, entity_type: str,
                                 candidate_names: list[str]) -> list[dict]:
    """Scan one directory for concept-shaped entities similar to the candidate.

    Works for both concepts/ and foundations/ because both carry title + aliases.
    Returns match dicts tagged with entity_type so the caller can branch on it.
    """
    if not entity_dir.exists():
        return []
    matches: list[dict] = []
    for f in sorted(entity_dir.glob("*.md")):
        fm = _parse_frontmatter(f)
        if not fm:
            continue
        existing_title = fm.get("title", "") or ""
        existing_aliases = fm.get("aliases", []) or []
        if not isinstance(existing_aliases, list):
            existing_aliases = []
        existing_names = [existing_title] + [str(a) for a in existing_aliases]

        best_score = 0.0
        best_pair: tuple[str, str] | None = None
        for cn in candidate_names:
            for en in existing_names:
                s = _phrase_match_score(cn, en)
                if s > best_score:
                    best_score = s
                    best_pair = (cn, en)

        if best_score >= 0.40:
            reason = ""
            if best_pair:
                cn, en = best_pair
                if best_score >= 1.0:
                    reason = f"exact normalized match: '{cn}' == '{en}'"
                elif best_score >= 0.85:
                    reason = f"phrase containment: '{cn}' ↔ '{en}'"
                else:
                    reason = f"token overlap (Jaccard): '{cn}' ↔ '{en}'"
            matches.append({
                "entity_type": entity_type,
                "slug": f.stem,
                "title": existing_title,
                "aliases": [str(a) for a in existing_aliases],
                "key_papers": fm.get("key_papers", []) or [],
                "maturity": fm.get("maturity", ""),
                "score": round(best_score, 3),
                "match_reason": reason,
            })
    return matches


def find_similar_concept(wiki_root: str, candidate_title: str,
                         candidate_aliases: list[str] | None = None) -> None:
    """Find existing concepts AND foundations that overlap with the candidate.

    Scans both wiki/concepts/ and wiki/foundations/. Results include an
    entity_type field so the caller can distinguish:
      - entity_type == "foundation" → reference the foundation, do not create
      - entity_type == "concept"    → merge with existing concept

    Output: JSON list of {entity_type, slug, title, aliases, score, match_reason}.
    Empty list means "safe to create a new concept page".
    """
    root = Path(wiki_root)
    candidate_aliases = candidate_aliases or []
    candidate_names = [candidate_title] + [a for a in candidate_aliases if a]

    matches: list[dict] = []
    matches.extend(_scan_entity_dir_for_similar(
        root / "foundations", "foundation", candidate_names))
    matches.extend(_scan_entity_dir_for_similar(
        root / "concepts", "concept", candidate_names))

    # Sort: foundations with high score first (they're terminal — prefer them),
    # then by score descending.
    def sort_key(m: dict) -> tuple:
        is_found = 0 if m["entity_type"] == "foundation" else 1
        return (is_found, -m["score"])
    matches.sort(key=sort_key)
    print(json.dumps(matches, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Named queries: cross-entity knowledge state
# ---------------------------------------------------------------------------

def query_ready_to_test(wiki_root: str) -> None:
    """Find ideas in proposed status with no linked experiments."""
    root = Path(wiki_root)
    ideas_dir = root / "ideas"
    if not ideas_dir.exists():
        print(json.dumps([]))
        return

    results: list[dict] = []
    for f in sorted(ideas_dir.glob("*.md")):
        fm = _parse_frontmatter(f)
        if not fm:
            continue
        status = fm.get("status", "")
        linked = fm.get("linked_experiments", [])
        if status == "proposed" and not linked:
            results.append({
                "slug": f.stem,
                "title": fm.get("title", f.stem),
                "priority": fm.get("priority", 3),
                "origin_gaps": fm.get("origin_gaps", []),
                "target_venue": fm.get("target_venue", ""),
                "novelty_score": fm.get("novelty_score", ""),
            })

    # Sort by priority descending
    results.sort(key=lambda x: x.get("priority", 0), reverse=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def query_orphans(wiki_root: str) -> None:
    """Find entities with no edges in the graph."""
    root = Path(wiki_root)
    edges = load_edges(wiki_root)

    # Collect all nodes referenced in edges
    referenced: set[str] = set()
    for e in edges:
        referenced.add(e.get("from", ""))
        referenced.add(e.get("to", ""))

    # Scan all entity files
    orphans: list[dict] = []
    for entity_type in ENTITY_DIRS:
        entity_dir = root / entity_type
        if not entity_dir.exists():
            continue
        for f in sorted(entity_dir.glob("*.md")):
            node_id = f"{entity_type}/{f.stem}"
            if node_id not in referenced:
                orphans.append({"entity": node_id, "type": entity_type})

    print(json.dumps(orphans, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Graph traversal: neighbors
# ---------------------------------------------------------------------------

def neighbors(wiki_root: str, node_id: str, depth: int = 1,
              edge_types: list[str] | None = None,
              direction: str = "both") -> None:
    """BFS traversal from a node in the edge graph.

    Args:
        direction: "both", "incoming", or "outgoing"
    """
    edges = load_edges(wiki_root)

    # Build adjacency lists
    adj_out: dict[str, list[dict]] = defaultdict(list)
    adj_in: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        etype = e.get("type", "")
        if edge_types and etype not in edge_types:
            continue
        src, dst = e.get("from", ""), e.get("to", "")
        adj_out[src].append({"id": dst, "edge": etype, "direction": "outgoing",
                             "evidence": e.get("evidence", "")})
        adj_in[dst].append({"id": src, "edge": etype, "direction": "incoming",
                            "evidence": e.get("evidence", "")})
        if e.get("symmetric") is True or edge_is_symmetric(etype):
            adj_out[dst].append({"id": src, "edge": etype, "direction": "symmetric",
                                 "evidence": e.get("evidence", "")})
            adj_in[src].append({"id": dst, "edge": etype, "direction": "symmetric",
                                "evidence": e.get("evidence", "")})

    # BFS
    visited: set[str] = {node_id}
    current_level: set[str] = {node_id}
    all_nodes: list[dict] = []

    for _ in range(depth):
        next_level: set[str] = set()
        for nid in current_level:
            if direction in ("both", "outgoing"):
                for neighbor in adj_out.get(nid, []):
                    if neighbor["id"] not in visited:
                        visited.add(neighbor["id"])
                        next_level.add(neighbor["id"])
                        all_nodes.append(neighbor)
            if direction in ("both", "incoming"):
                for neighbor in adj_in.get(nid, []):
                    if neighbor["id"] not in visited:
                        visited.add(neighbor["id"])
                        next_level.add(neighbor["id"])
                        all_nodes.append(neighbor)
        current_level = next_level
        if not current_level:
            break

    print(json.dumps({"center": node_id, "depth": depth, "nodes": all_nodes},
                      ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Purpose-driven context compilation
# ---------------------------------------------------------------------------

CONTEXT_BUDGETS = {
    #                Methods Evolve Gaps  Failed  Papers  Experiments  Edges  Stale
    "ideation":     (1500,  1200,  1800, 2000,   1000,   500,         500,   400),
    "experiment":   (2500,  800,   500,  500,    1000,   2500,        500,   0),
    "writing":      (2000,  600,   500,  200,    2500,   500,         800,   0),
    "review":       (2500,  1200,  1000, 500,    1000,   1500,        500,   500),
    "general":      (2000,  1200,  1500, 1500,   2000,   0,           1000,  0),
}


def _entity_edge_counts(wiki_root: str) -> dict[str, int]:
    """Count edges per entity node for connectivity-based ranking."""
    edges = load_edges(wiki_root)
    counts: dict[str, int] = defaultdict(int)
    for e in edges:
        counts[e.get("from", "")] += 1
        counts[e.get("to", "")] += 1
    return dict(counts)


def _scievolve_memory_guidance(root: Path) -> list[str]:
    """Return applied /dream memory guidance for downstream context packs."""
    lines: list[str] = []
    for etype in ENTITY_DIRS:
        edir = root / etype
        if not edir.exists():
            continue
        for path in sorted(edir.glob("*.md")):
            fm = _parse_frontmatter(path)
            entity_id = f"{etype}/{path.stem}"
            title = fm.get("title") or fm.get("name") or path.stem
            weight = str(fm.get("scievolve_memory_weight") or "")
            consolidates = _dream_as_list(fm.get("scievolve_consolidates_with"))
            associations = _dream_as_list(fm.get("scievolve_associations"))
            notes = _dream_as_list(fm.get("scievolve_dream_notes"))
            note = f" — {notes[-1]}" if notes else ""
            if weight:
                lines.append(f"- downweight {entity_id} ({title}): {weight}{note}")
            if consolidates:
                lines.append(
                    f"- consolidate {entity_id} ({title}) with "
                    f"{', '.join(consolidates)}{note}"
                )
            if associations:
                lines.append(
                    f"- associate {entity_id} ({title}) with "
                    f"{', '.join(associations)}{note}"
                )
    return lines


def compile_context(wiki_root: str, purpose: str,
                    max_chars: int = 8000,
                    emit: bool = True) -> dict:
    """Generate purpose-specific compressed context for downstream skills.

    Replaces the old one-size-fits-all rebuild_context_brief with budget
    allocations tuned per skill category.
    """
    root = Path(wiki_root)
    budgets = CONTEXT_BUDGETS.get(purpose, CONTEXT_BUDGETS["general"])
    (
        b_methods,
        b_evolution,
        b_gaps,
        b_failed,
        b_papers,
        b_experiments,
        b_edges,
        b_stale,
    ) = budgets

    edge_counts = _entity_edge_counts(wiki_root)
    sections: list[str] = []

    # 1. Methods summary — most-connected reusable methods first.
    if b_methods > 0:
        methods_dir = root / "methods"
        if methods_dir.exists():
            items: list[tuple[int, str]] = []
            for f in sorted(methods_dir.glob("*.md")):
                fm = _parse_frontmatter(f)
                title = fm.get("name", fm.get("title", f.stem))
                mtype = fm.get("type", "other")
                connectivity = edge_counts.get(f"methods/{f.stem}", 0)
                items.append((connectivity,
                              f"- [{mtype}] {title}"))
            if items:
                items.sort(key=lambda x: x[0], reverse=True)
                text = "\n".join(line for _, line in items)[:b_methods]
                sections.append(f"## Methods ({len(items)} total)\n{text}\n")

    # 2. Applied SciEvolve memory guidance — lets /dream affect future retrieval.
    if b_evolution > 0:
        guidance = _scievolve_memory_guidance(root)
        if guidance:
            text = "\n".join(guidance)[:b_evolution]
            sections.append(f"## SciEvolve Memory Guidance\n{text}\n")

    # 3. Gap map snapshot
    if b_gaps > 0:
        gap_path = root / DERIVED_DIR / "open_questions.md"
        if gap_path.exists():
            gap_text = gap_path.read_text(encoding="utf-8")
            body_lines = [l for l in gap_text.split("\n")
                          if not l.startswith("#") and l.strip()]
            body = "\n".join(body_lines)
            if body.strip():
                sections.append(f"## Open Gaps\n{body[:b_gaps]}\n")

    # 4. Failed ideas (anti-repetition memory)
    if b_failed > 0:
        ideas_dir = root / "ideas"
        if ideas_dir.exists():
            failed: list[str] = []
            for f in sorted(ideas_dir.glob("*.md")):
                fm = _parse_frontmatter(f)
                status = fm.get("status", "")
                if status in ("failed", "rejected"):
                    title = fm.get("title", f.stem)
                    reason = fm.get("failure_reason", "")
                    line = f"- {title}"
                    if reason:
                        line += f" — {reason}"
                    failed.append(line)
            if failed:
                text = "\n".join(failed)[:b_failed]
                sections.append(f"## Failed Ideas (avoid repeating)\n{text}\n")

    # 5. Paper summaries
    if b_papers > 0:
        papers_dir = root / "papers"
        if papers_dir.exists():
            items2: list[tuple[int, str]] = []
            for f in sorted(papers_dir.glob("*.md")):
                fm = _parse_frontmatter(f)
                title = fm.get("title", f.stem)
                importance = fm.get("importance", "?")
                tldr = fm.get("tldr", "")
                connectivity = edge_counts.get(f"papers/{f.stem}", 0)
                line = f"- [{importance}] {title}"
                if tldr:
                    line += f" — {tldr}"
                items2.append((connectivity, line))
            if items2:
                items2.sort(key=lambda x: x[0], reverse=True)
                text = "\n".join(line for _, line in items2[:15])[:b_papers]
                sections.append(f"## Papers ({len(items2)} total)\n{text}\n")

    # 6. Experiment summaries
    if b_experiments > 0:
        exp_dir = root / "experiments"
        if exp_dir.exists():
            exp_lines: list[str] = []
            for f in sorted(exp_dir.glob("*.md")):
                fm = _parse_frontmatter(f)
                title = fm.get("title", f.stem)
                status = fm.get("status", "")
                outcome = fm.get("outcome", "")
                target = fm.get("linked_idea", "")
                line = f"- [{status}] {title}"
                if target:
                    line += f" → {target}"
                if outcome:
                    line += f" ({outcome})"
                exp_lines.append(line)
            if exp_lines:
                text = "\n".join(exp_lines)[:b_experiments]
                sections.append(f"## Experiments ({len(exp_lines)} total)\n{text}\n")

    # 7. Recent edges
    if b_edges > 0:
        edges = load_edges(wiki_root)
        if edges:
            chain_lines = [f"  {e['from']} --{e['type']}--> {e['to']}"
                           for e in edges[-25:]]
            text = "\n".join(chain_lines)[:b_edges]
            sections.append(f"## Recent Relationships ({len(edges)} total)\n{text}\n")

    # 8. Stale entities
    if b_stale > 0:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        stale_lines: list[str] = []
        for etype in ENTITY_DIRS:
            edir = root / etype
            if not edir.exists():
                continue
            for f in sorted(edir.glob("*.md")):
                fm = _parse_frontmatter(f)
                date_str = (fm.get("date_updated") or fm.get("date_added")
                            or fm.get("date_proposed") or "")
                if isinstance(date_str, str) and date_str:
                    try:
                        d = datetime.strptime(date_str, "%Y-%m-%d").replace(
                            tzinfo=timezone.utc)
                        if d < cutoff:
                            stale_lines.append(
                                f"- {etype}/{f.stem} (last: {date_str})")
                    except ValueError:
                        pass
        if stale_lines:
            text = "\n".join(stale_lines[:10])[:b_stale]
            sections.append(f"## Stale Entities\n{text}\n")

    # Assemble within budget
    header = (f"# Query Pack ({purpose})\n\n"
              f"_Auto-generated compressed context. Do not edit._\n\n")
    pack = header
    for s in sections:
        if len(pack) + len(s) <= max_chars:
            pack += s
        else:
            remaining = max_chars - len(pack) - 25
            if remaining > 100:
                pack += s[:remaining] + "\n...(truncated)\n"
            break

    pack_path = root / DERIVED_DIR / "context_brief.md"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack, encoding="utf-8")
    result = {
        "status": "ok",
        "purpose": purpose,
        "chars": len(pack),
        "path": str(pack_path),
        "scievolve_memory_items": len(_scievolve_memory_guidance(root)),
    }
    if emit:
        print(json.dumps(result))
    return result


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def get_stats(wiki_root: str, as_json: bool = False) -> dict:
    """Collect and print wiki statistics."""
    root = Path(wiki_root)

    def count_md(subdir: str) -> int:
        d = root / subdir
        return len(list(d.glob("*.md"))) if d.exists() else 0

    def count_by_field(subdir: str, field: str, value: str) -> int:
        d = root / subdir
        if not d.exists():
            return 0
        count = 0
        for f in d.glob("*.md"):
            fm = _parse_frontmatter(f)
            if fm.get(field) == value:
                count += 1
        return count

    stats = {
        "papers": count_md("papers"),
        "concepts": count_md("concepts"),
        "topics": count_md("topics"),
        "people": count_md("people"),
        "ideas": count_md("ideas"),
        "ideas_validated": count_by_field("ideas", "status", "validated"),
        "ideas_failed": count_by_field("ideas", "status", "failed"),
        "experiments": count_md("experiments"),
        "methods": count_md("methods"),
        "foundations": count_md("foundations"),
        "manuscripts": count_md("manuscripts"),
        "reviews": count_md("reviews"),
        "edges": len(load_edges(wiki_root)),
        "citations": len(load_citations(wiki_root)),
    }

    if as_json:
        print(json.dumps(stats, indent=2))
    else:
        print("OmegaWiki Stats")
        print(f"  Papers:      {stats['papers']}")
        print(f"  Concepts:    {stats['concepts']}")
        print(f"  Topics:      {stats['topics']}")
        print(f"  People:      {stats['people']}")
        print(f"  Ideas:       {stats['ideas']} "
              f"({stats['ideas_validated']} validated, {stats['ideas_failed']} failed)")
        print(f"  Experiments: {stats['experiments']}")
        print(f"  Methods:     {stats['methods']}")
        print(f"  Foundations: {stats['foundations']}")
        print(f"  Manuscripts: {stats['manuscripts']}")
        print(f"  Reviews:     {stats['reviews']}")
        print(f"  Edges:       {stats['edges']}")
        print(f"  Citations:   {stats['citations']}")

    return stats


# ---------------------------------------------------------------------------
# Maturity assessment
# ---------------------------------------------------------------------------

MATURITY_WARM = {"papers": 5, "ideas": 5}
MATURITY_HOT = {"papers": 20, "ideas": 15}


def get_maturity(wiki_root: str, as_json: bool = False) -> dict:
    """Assess wiki maturity level (cold/warm/hot) and related metrics."""
    root = Path(wiki_root)

    # Collect stats silently (suppress get_stats output).
    import io as _io
    _old_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    try:
        stats = get_stats(wiki_root, as_json=True)
    finally:
        sys.stdout = _old_stdout

    # Count completed experiments
    exp_completed = 0
    exp_dir = root / "experiments"
    if exp_dir.exists():
        for f in exp_dir.glob("*.md"):
            fm = _parse_frontmatter(f)
            if fm.get("outcome") == "succeeded":
                exp_completed += 1

    # Check for experiment evidence edges
    edges = load_edges(wiki_root)
    has_experiment_evidence = any(
        e.get("type") in ("supports", "invalidates")
        and str(e.get("from", "")).startswith("experiments/")
        for e in edges
    )

    # Total entities counted toward maturity / density. Any kind flagged
    # `terminal: true` is excluded; the stats key matches the entity kind.
    total_entities = sum(
        stats.get(k, 0)
        for k, e in ENTITIES.items() if not e.get("terminal")
    )

    # Graph density: edges / max(1, N*(N-1))
    n_edges = stats["edges"]
    max_possible = max(1, total_entities * (total_entities - 1))
    graph_density = round(min(1.0, n_edges / max_possible), 4)

    # Coverage score: weighted sum, capped at 1.0. Ideas are the validation
    # axis — each validated idea is one unit of supported research.
    coverage_score = round(min(1.0, (
        stats["papers"] / 20 * 0.3
        + stats["ideas"] / 15 * 0.3
        + exp_completed / 5 * 0.2
        + n_edges / 50 * 0.2
    )), 4)

    # Determine level
    papers = stats["papers"]
    ideas = stats["ideas"]
    if (papers >= MATURITY_HOT["papers"]
            and ideas >= MATURITY_HOT["ideas"]
            and has_experiment_evidence):
        level = "hot"
    elif (papers >= MATURITY_WARM["papers"]
          and ideas >= MATURITY_WARM["ideas"]):
        level = "warm"
    else:
        level = "cold"

    result = {
        "level": level,
        "papers": papers,
        "ideas": ideas,
        "experiments_completed": exp_completed,
        "ideas_total": stats["ideas"],
        "ideas_failed": stats["ideas_failed"],
        "edges": n_edges,
        "graph_density": graph_density,
        "coverage_score": coverage_score,
        "has_experiment_evidence": has_experiment_evidence,
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Wiki Maturity: {level}")
        if level == "cold":
            print(f"  Papers: {papers}/{MATURITY_WARM['papers']}"
                  f" (need {MATURITY_WARM['papers']} for warm)")
            print(f"  Ideas:  {ideas}/{MATURITY_WARM['ideas']}"
                  f" (need {MATURITY_WARM['ideas']} for warm)")
        elif level == "warm":
            print(f"  Papers: {papers}/{MATURITY_HOT['papers']}"
                  f" (need {MATURITY_HOT['papers']} for hot)")
            print(f"  Ideas:  {ideas}/{MATURITY_HOT['ideas']}"
                  f" (need {MATURITY_HOT['ideas']} for hot)")
            if not has_experiment_evidence:
                print("  Experiment evidence: missing (needed for hot)")
        else:
            print(f"  Papers: {papers} | Ideas: {ideas}"
                  f" | Experiments completed: {exp_completed}")
        print(f"  Coverage: {int(coverage_score * 100)}%")

    return result


# ---------------------------------------------------------------------------
# SciEvolve /dream: agent-first memory evolution
# ---------------------------------------------------------------------------

DREAM_OPERATIONS = ("forgetting", "consolidation", "association")
FORGE_OPERATIONS = ("patch-prompt", "add-check", "adjust-handoff", "add-recovery")
DREAM_ASSOCIATION_KINDS = {
    "papers",
    "concepts",
    "topics",
    "ideas",
    "methods",
    "experiments",
    "foundations",
}


def _dream_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _dream_parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _dream_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                slug = item.get("slug") or item.get("id") or item.get("title")
                if slug:
                    out.append(str(slug).strip())
            elif str(item).strip():
                out.append(str(item).strip())
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dream_body(path: Path, max_chars: int = 1200) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    match = FRONTMATTER_RE.match(text)
    if match:
        text = text[match.end():]
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)[:max_chars]


def _dream_label(kind: str, slug: str, fm: dict) -> str:
    if kind == "methods":
        return str(fm.get("name") or fm.get("title") or slug)
    return str(fm.get("title") or fm.get("name") or slug)


def _dream_collect_entities(root: Path, max_entities: int) -> list[dict]:
    entities: list[dict] = []
    for kind in ENTITY_DIRS:
        directory = root / kind
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            fm = _parse_frontmatter(path)
            slug = path.stem
            dates = {
                key: fm.get(key)
                for key in (
                    "date_added",
                    "date_updated",
                    "date_proposed",
                    "date_resolved",
                    "date_planned",
                    "date_completed",
                )
                if fm.get(key)
            }
            entities.append({
                "id": f"{kind}/{slug}",
                "kind": kind,
                "slug": slug,
                "path": str(path.relative_to(root)),
                "label": _dream_label(kind, slug, fm),
                "tags": _dream_list(fm.get("tags")),
                "status": str(fm.get("status") or fm.get("maturity") or ""),
                "importance": fm.get("importance"),
                "scievolve_memory": {
                    key: fm.get(key)
                    for key in (
                        "scievolve_memory_weight",
                        "scievolve_consolidates_with",
                        "scievolve_associations",
                        "scievolve_last_dream",
                    )
                    if fm.get(key)
                },
                "dates": dates,
                "links": {
                    key: _dream_list(value)
                    for key, value in fm.items()
                    if isinstance(value, list) or key.endswith("_topic") or key.endswith("_idea")
                },
                "summary": (
                    str(fm.get("tldr") or fm.get("definition") or fm.get("key_result")
                        or fm.get("hypothesis") or fm.get("failure_reason") or "")
                    or _dream_body(path, 600)
                )[:600],
                "body_excerpt": _dream_body(path, 600),
            })
            if max_entities > 0 and len(entities) >= max_entities:
                return entities
    return entities


def _dream_edge_ref(edge: dict, index: int, source: str = "graph") -> dict:
    return {
        "id": f"{source}-edge-{index + 1}",
        "from": str(edge.get("from", "")),
        "to": str(edge.get("to", "")),
        "type": str(edge.get("type", "")),
        "evidence": str(edge.get("evidence", "")),
    }


def _dream_edge_counts(edges: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for edge in edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src:
            counts[src] += 1
        if dst:
            counts[dst] += 1
    return dict(counts)


def _dream_pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _dream_existing_pairs(edges: list[dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src and dst:
            pairs.add(_dream_pair_key(src, dst))
    return pairs


def _dream_signal_operation(signal: dict) -> str:
    text = " ".join(
        str(signal.get(key, ""))
        for key in ("memory_operation", "proposal_kind", "category", "kind", "summary", "evidence_text")
    ).lower()
    if any(word in text for word in ("forget", "archive", "stale", "obsolete", "noise", "down-weight")):
        return "forgetting"
    if any(word in text for word in ("merge", "cluster", "consolidat", "duplicate", "organize")):
        return "consolidation"
    if any(word in text for word in ("associate", "association", "bridge", "link", "connect")):
        return "association"
    return ""


def _dream_add_candidate(
    candidates: list[dict],
    operation: str,
    title: str,
    *,
    target: str = "",
    related_entities: list[str] | None = None,
    evidence: list[dict] | None = None,
    cues: list[str] | None = None,
    confidence_hint: str = "medium",
) -> None:
    candidates.append({
        "id": f"dream-candidate-{len(candidates) + 1:03d}",
        "operation": operation,
        "title": title,
        "target": target,
        "related_entities": related_entities or ([target] if target else []),
        "evidence": evidence or [],
        "cues": cues or [],
        "confidence_hint": confidence_hint,
        "note": (
            "This is a context cue for the agent, not a proposal. "
            "The agent must decide whether it is meaningful."
        ),
    })


def _dream_candidate_context(
    entities: list[dict],
    edges: list[dict],
    projected_edges: list[dict],
    citations: list[dict],
    signals: list[dict],
    max_candidates: int,
) -> list[dict]:
    all_edges = edges + projected_edges + citations
    edge_counts = _dream_edge_counts(all_edges)
    existing_pairs = _dream_existing_pairs(all_edges)
    by_id = {entity["id"]: entity for entity in entities}
    candidates: list[dict] = []
    now = datetime.now(timezone.utc)

    for signal in signals:
        operation = _dream_signal_operation(signal)
        if not operation:
            continue
        target = str(signal.get("target") or "")
        _dream_add_candidate(
            candidates,
            operation,
            f"Recorded memory signal suggests {operation}",
            target=target if target in by_id else "",
            related_entities=[target] if target in by_id else [],
            evidence=[{
                "source": str(signal.get("id", "")),
                "summary": str(signal.get("summary", "")),
                "kind": str(signal.get("kind", "")),
            }],
            cues=["Recorded SciEvolve signal"],
            confidence_hint=str(signal.get("confidence") or "medium"),
        )

    for entity in entities:
        status = entity.get("status", "").lower()
        latest = None
        for raw in entity.get("dates", {}).values():
            parsed = _dream_parse_date(raw)
            if parsed and (latest is None or parsed > latest):
                latest = parsed
        age_days = (now - latest).days if latest else None
        body_len = len(entity.get("body_excerpt", ""))
        connectivity = edge_counts.get(entity["id"], 0)
        cues = []
        if status in {"deprecated", "historical", "failed", "abandoned"}:
            cues.append(f"status is {status}")
        if age_days is not None and age_days >= 180 and connectivity <= 1:
            cues.append(f"latest timestamp is {age_days} days old with connectivity {connectivity}")
        if body_len < 120 and connectivity == 0:
            cues.append("short page body with no graph links")
        if cues:
            _dream_add_candidate(
                candidates,
                "forgetting",
                f"Review low-signal memory trace: {entity['label']}",
                target=entity["id"],
                evidence=[{
                    "source": entity["id"],
                    "path": entity["path"],
                    "summary": "; ".join(cues),
                }],
                cues=cues,
                confidence_hint="low" if len(cues) == 1 else "medium",
            )

    comparable = [e for e in entities if e["kind"] in {"concepts", "methods", "foundations", "topics"}]
    for i, left in enumerate(comparable):
        for right in comparable[i + 1:]:
            if left["kind"] != right["kind"]:
                continue
            name_score = _phrase_match_score(left["label"], right["label"])
            shared_tags = sorted(set(left.get("tags", [])) & set(right.get("tags", [])))
            if name_score >= 0.75 or len(shared_tags) >= 2:
                _dream_add_candidate(
                    candidates,
                    "consolidation",
                    f"Possible memory consolidation: {left['label']} / {right['label']}",
                    target=left["id"],
                    related_entities=[left["id"], right["id"]],
                    evidence=[
                        {"source": left["id"], "path": left["path"], "summary": left["summary"]},
                        {"source": right["id"], "path": right["path"], "summary": right["summary"]},
                    ],
                    cues=[
                        f"name_score={round(name_score, 3)}",
                        f"shared_tags={', '.join(shared_tags) if shared_tags else 'none'}",
                    ],
                    confidence_hint="medium" if name_score >= 0.75 else "low",
                )

    tag_buckets: dict[str, list[dict]] = defaultdict(list)
    for entity in entities:
        if entity["kind"] not in DREAM_ASSOCIATION_KINDS:
            continue
        for tag in entity.get("tags", []):
            tag_buckets[tag].append(entity)
    for tag, members in sorted(tag_buckets.items()):
        kinds = {member["kind"] for member in members}
        if len(members) >= 3 and len(kinds) >= 2:
            related = [member["id"] for member in members[:8]]
            _dream_add_candidate(
                candidates,
                "consolidation",
                f"Scattered memories share the theme '{tag}'",
                related_entities=related,
                evidence=[
                    {"source": member["id"], "path": member["path"], "summary": member["label"]}
                    for member in members[:8]
                ],
                cues=[f"{len(members)} pages across {len(kinds)} entity types share tag '{tag}'"],
                confidence_hint="medium",
            )

    methods = [e for e in entities if e["kind"] == "methods"]
    concepts = [e for e in entities if e["kind"] == "concepts"]
    ideas = [e for e in entities if e["kind"] == "ideas"]
    papers = [e for e in entities if e["kind"] == "papers"]
    topics = [e for e in entities if e["kind"] == "topics"]
    assoc_pairs: list[tuple[dict, dict, str]] = []
    for method in methods:
        for concept in concepts:
            shared = sorted(set(method.get("tags", [])) & set(concept.get("tags", [])))
            if len(shared) >= 2 and _dream_pair_key(method["id"], concept["id"]) not in existing_pairs:
                assoc_pairs.append((method, concept, "method-concept shared tags: " + ", ".join(shared)))
    for idea in ideas:
        for method in methods:
            shared = sorted(set(idea.get("tags", [])) & set(method.get("tags", [])))
            if len(shared) >= 2 and _dream_pair_key(idea["id"], method["id"]) not in existing_pairs:
                assoc_pairs.append((idea, method, "idea-method shared tags: " + ", ".join(shared)))
    for paper in papers:
        for concept in concepts + topics:
            shared = sorted(set(paper.get("tags", [])) & set(concept.get("tags", [])))
            if len(shared) >= 2 and _dream_pair_key(paper["id"], concept["id"]) not in existing_pairs:
                assoc_pairs.append((paper, concept, "paper-memory shared tags: " + ", ".join(shared)))
    for left, right, cue in assoc_pairs[: max(0, max_candidates)]:
        _dream_add_candidate(
            candidates,
            "association",
            f"Latent association candidate: {left['label']} <-> {right['label']}",
            target=left["id"],
            related_entities=[left["id"], right["id"]],
            evidence=[
                {"source": left["id"], "path": left["path"], "summary": left["summary"]},
                {"source": right["id"], "path": right["path"], "summary": right["summary"]},
            ],
            cues=[cue, "No existing graph/frontmatter pair found"],
            confidence_hint="low",
        )

    if max_candidates > 0:
        return candidates[:max_candidates]
    return candidates


def _dream_build_context(
    wiki_root: str,
    max_entities: int,
    max_signals: int,
    max_candidates: int,
) -> dict:
    root = Path(wiki_root)
    entities = _dream_collect_entities(root, max_entities)
    edges = [_dream_edge_ref(edge, i, "graph") for i, edge in enumerate(load_edges(wiki_root))]
    projected = [
        _dream_edge_ref(edge, i, "projected")
        for i, edge in enumerate(project_frontmatter_edges(root))
    ]
    citations = [
        _dream_edge_ref(edge, i, "citation")
        for i, edge in enumerate(load_citations(wiki_root))
    ]
    signals, malformed = load_scievolve_signals(root)
    memory_signals = [s for s in signals if s.get("dimension") == "memory"]
    if max_signals > 0:
        memory_signals = memory_signals[-max_signals:]
    counts = Counter(entity["kind"] for entity in entities)
    candidates = _dream_candidate_context(
        entities,
        edges,
        projected,
        citations,
        memory_signals,
        max_candidates,
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "mode": "agent-first-dream",
        "wiki_root": str(root),
        "stats": {
            "entities": dict(sorted(counts.items())),
            "edges": len(edges),
            "projected_edges": len(projected),
            "citations": len(citations),
            "memory_signals": len(memory_signals),
            "malformed_signal_rows": malformed,
        },
        "entities": entities,
        "edges": edges[-80:],
        "projected_edges": projected[-80:],
        "citations": citations[-80:],
        "signals": memory_signals,
        "candidate_memory_cues": candidates,
    }


def _dream_context_markdown(context: dict) -> str:
    lines = [
        "# Dream Context",
        "",
        "This is deterministic context for an agent. It is not the dream decision.",
        "",
        "## Stats",
        "",
    ]
    for key, value in context.get("stats", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Candidate Memory Cues", ""])
    for candidate in context.get("candidate_memory_cues", []):
        lines.append(
            f"- {candidate['id']} [{candidate['operation']}]: {candidate['title']}"
        )
        if candidate.get("related_entities"):
            lines.append(f"  - related: {', '.join(candidate['related_entities'])}")
        if candidate.get("cues"):
            lines.append(f"  - cues: {'; '.join(candidate['cues'])}")
    lines.extend(["", "## Memory Signals", ""])
    for signal in context.get("signals", []):
        lines.append(
            "- {id} [{kind}] target={target}: {summary}".format(
                id=signal.get("id", ""),
                kind=signal.get("kind", ""),
                target=signal.get("target", ""),
                summary=signal.get("summary", ""),
            )
        )
    lines.extend(["", "## Entity Snapshot", ""])
    for entity in context.get("entities", [])[:80]:
        tags = ", ".join(entity.get("tags", []))
        memory_state = entity.get("scievolve_memory") or {}
        suffix = ""
        if memory_state:
            suffix = f" scievolve={json.dumps(memory_state, ensure_ascii=False)}"
        lines.append(f"- {entity['id']}: {entity['label']} ({tags}){suffix}")
    return "\n".join(lines).rstrip() + "\n"


def _dream_agent_prompt(context: dict) -> str:
    return (
        "# /dream Agent Prompt\n\n"
        "You are AutoSci's /dream agent. Your job is memory self-evolution, not lint repair.\n"
        "A good proposal should explain how memory will behave differently in a later "
        "retrieval, ideation, or experiment-planning cycle.\n\n"
        "Use the supplied context to propose reversible memory-evolution operations:\n"
        "- forgetting: archive, down-weight, or review low-signal/superseded traces\n"
        "- consolidation: merge, cluster, summarize, or cross-link scattered related memories\n"
        "- association: propose latent high-value links between existing pages\n\n"
        "Rules:\n"
        "- Use only evidence present in the context.\n"
        "- Treat candidate_memory_cues as hints, not decisions.\n"
        "- Do not propose deletion. Safe reversible metadata application may happen later.\n"
        "- Do not repackage broken links or missing fields as the core dream output.\n"
        "- Every proposal must cite candidate ids, entity ids, signal ids, or edge ids from the context.\n"
        "- Prefer a few high-signal proposals over a broad mechanical list.\n\n"
        "Return strict JSON only with this shape:\n\n"
        "{\n"
        "  \"proposals\": [\n"
        "    {\n"
        "      \"operation\": \"forgetting|consolidation|association\",\n"
        "      \"target\": \"entities/slug or blank for cluster-level proposal\",\n"
        "      \"title\": \"short title\",\n"
        "      \"proposed_action\": \"reversible proposal-first action\",\n"
        "      \"rationale\": \"why this is a meaningful memory operation and how it improves a future cycle\",\n"
        "      \"confidence\": \"low|medium|high\",\n"
        "      \"related_entities\": [\"kind/slug\"],\n"
        "      \"candidate_ids\": [\"dream-candidate-001\"],\n"
        "      \"evidence\": [\n"
        "        {\"source\": \"entity/signal/candidate id\", \"summary\": \"supporting note\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Context JSON:\n\n"
        "```json\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def _dream_extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(stripped[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("dream agent response must be a JSON object")
    return data


def _dream_call_openai_compatible(
    prompt: str,
    *,
    timeout: int,
    temperature: float,
) -> tuple[dict, dict]:
    if requests is None:
        raise RuntimeError("LLM call unavailable; requests is not installed")
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("LLM_MODEL", "").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError("LLM call unavailable; set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL")
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are AutoSci /dream. Return strict JSON only. "
                    "Use only the provided memory context."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=body,
        timeout=timeout,
    )
    if response.status_code >= 400 and body.get("response_format"):
        body.pop("response_format", None)
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=timeout,
        )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    trace = {
        "provider": "openai-compatible",
        "model": model,
        "base_url": base_url,
        "policy_runtime": "openai-compatible-api",
    }
    return _dream_extract_json_object(content), trace


def _dream_allowed_refs(context: dict) -> set[str]:
    refs = {entity["id"] for entity in context.get("entities", [])}
    refs.update(candidate["id"] for candidate in context.get("candidate_memory_cues", []))
    refs.update(str(signal.get("id", "")) for signal in context.get("signals", []))
    for section in ("edges", "projected_edges", "citations"):
        refs.update(str(edge.get("id", "")) for edge in context.get(section, []))
    refs.discard("")
    return refs


def _dream_proposal_refs(raw: dict) -> set[str]:
    refs: set[str] = set()
    for key in ("target",):
        if raw.get(key):
            refs.add(str(raw[key]))
    for key in ("related_entities", "candidate_ids", "triggering_signals"):
        value = raw.get(key)
        if isinstance(value, list):
            refs.update(str(item) for item in value if str(item).strip())
    evidence = raw.get("evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                for key in ("source", "id", "entity_id", "signal_id", "candidate_id", "edge_id"):
                    if item.get(key):
                        refs.add(str(item[key]))
            elif str(item).strip():
                refs.add(str(item).strip())
    return refs


def _dream_normalize_evidence(raw: dict, context: dict) -> list[dict]:
    entity_paths = {entity["id"]: entity.get("path", "") for entity in context.get("entities", [])}
    evidence = []
    for item in raw.get("evidence") or []:
        if isinstance(item, dict):
            source = str(
                item.get("source")
                or item.get("id")
                or item.get("entity_id")
                or item.get("signal_id")
                or item.get("candidate_id")
                or item.get("edge_id")
                or ""
            )
            evidence.append({
                "source": source,
                "summary": str(item.get("summary") or item.get("note") or ""),
                "path": entity_paths.get(source, ""),
            })
        elif str(item).strip():
            source = str(item).strip()
            evidence.append({"source": source, "summary": "", "path": entity_paths.get(source, "")})
    for candidate_id in raw.get("candidate_ids") or []:
        if not any(e.get("source") == candidate_id for e in evidence):
            evidence.append({"source": str(candidate_id), "summary": "Agent cited candidate memory cue", "path": ""})
    return evidence


def _dream_normalize_agent_response(
    payload: dict,
    context: dict,
    agent_trace: dict,
) -> tuple[list[dict], list[dict]]:
    allowed = _dream_allowed_refs(context)
    signals = {str(signal.get("id", "")) for signal in context.get("signals", [])}
    raw_proposals = payload.get("proposals")
    if not isinstance(raw_proposals, list):
        raise ValueError("dream agent response must contain a proposals list")

    accepted: list[dict] = []
    rejected: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_proposals):
        if not isinstance(raw, dict):
            rejected.append({"index": index, "reason": "proposal is not an object"})
            continue
        operation = str(raw.get("operation") or raw.get("proposal_kind") or "").strip().lower()
        if operation not in DREAM_OPERATIONS:
            rejected.append({"index": index, "reason": f"invalid operation: {operation}"})
            continue
        target = str(raw.get("target") or "").strip()
        related_entities = [
            str(item).strip()
            for item in (raw.get("related_entities") or [])
            if str(item).strip()
        ]
        unknown_related = [ref for ref in related_entities if ref not in allowed]
        if target and target not in allowed:
            rejected.append({"index": index, "reason": f"unknown target: {target}"})
            continue
        if unknown_related:
            rejected.append({"index": index, "reason": f"unknown related_entities: {unknown_related}"})
            continue
        refs = _dream_proposal_refs(raw)
        if not refs or not (refs & allowed):
            rejected.append({"index": index, "reason": "proposal cites no known context evidence"})
            continue
        action = str(raw.get("proposed_action") or raw.get("action") or "").strip()
        rationale = str(raw.get("rationale") or "").strip()
        if not action or not rationale:
            rejected.append({"index": index, "reason": "missing proposed_action or rationale"})
            continue
        confidence = str(raw.get("confidence") or "medium").strip().lower()
        if confidence not in SCIEVOLVE_CONFIDENCE_VALUES:
            confidence = "medium"
        title = str(raw.get("title") or operation.title()).strip()
        proposal_target = target or (related_entities[0] if related_entities else "memory")
        dedup_key = (operation, proposal_target, action)
        if dedup_key in seen:
            rejected.append({"index": index, "reason": "duplicate proposal"})
            continue
        seen.add(dedup_key)
        evidence = _dream_normalize_evidence(raw, context)
        signal_refs = sorted(ref for ref in refs if ref in signals)
        accepted.append({
            "dimension": "memory",
            "target": proposal_target,
            "proposal_kind": operation,
            "title": title,
            "confidence": confidence,
            "related_entities": related_entities,
            "triggering_signals": signal_refs,
            "proposed_action": action,
            "rationale": rationale,
            "risk": (
                "Agent-generated /dream proposal. Only safe metadata-level "
                "application is allowed without a separate page-edit pass."
            ),
            "evidence": evidence,
            "agent_trace": agent_trace,
        })
    return accepted, rejected


def _dream_entity_path(root: Path, entity_id: str) -> Path | None:
    parts = entity_id.split("/", 1)
    if len(parts) != 2:
        return None
    kind, slug = parts
    if kind not in ENTITY_DIRS or not slug:
        return None
    return root / kind / f"{slug}.md"


def _dream_as_list(value: object) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _dream_update_frontmatter_memory(
    path: Path,
    *,
    set_fields: dict[str, object],
    append_fields: dict[str, list[str]],
) -> dict:
    content = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError(f"No frontmatter found in {path}")

    fm = _parse_yaml_block(match.group(1))
    before = {
        field: fm.get(field)
        for field in sorted(set(set_fields) | set(append_fields))
    }
    for field, value in set_fields.items():
        fm[field] = value
    for field, additions in append_fields.items():
        values = _dream_as_list(fm.get(field))
        for item in additions:
            if item and item not in values:
                values.append(item)
        if values:
            fm[field] = values

    after = {
        field: fm.get(field)
        for field in sorted(set(set_fields) | set(append_fields))
    }
    if before == after:
        return {
            "path": str(path),
            "changed": False,
            "before": before,
            "after": after,
        }

    next_content = f"---\n{_serialize_frontmatter(fm)}---{content[match.end():]}"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(next_content, encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {
        "path": str(path),
        "changed": True,
        "before": before,
        "after": after,
    }


def _dream_link_frontmatter_append(
    fm: dict,
    append_fields: dict[str, list[str]],
    entity: str,
) -> None:
    """Append a related entity to the appropriate standard frontmatter link field."""
    kind = entity.split("/")[0] if "/" in entity else ""
    mapping = {
        "concepts": "related_concepts",
        "topics": "parent_topics",
        "ideas": "linked_ideas",
        "methods": "parent_methods",
        "papers": "key_papers",
        "foundations": "grounded_in",
    }
    field = mapping.get(kind)
    if field and field in fm:
        append_fields.setdefault(field, [])
        if entity not in append_fields[field]:
            append_fields[field].append(entity)


def _dream_append_evolution_note(
    path: Path,
    proposal_id: str,
    operation: str,
    related: list[str],
    title: str = "",
    rationale: str = "",
) -> dict:
    """Append a visible SciEvolve evolution note to the end of a page body."""
    content = path.read_text(encoding="utf-8")
    marker = f"<!-- /dream: {proposal_id} -->"
    if marker in content:
        return {"path": str(path), "changed": False, "reason": "note already present"}

    lines = [
        "",
        "---",
        "",
        "## SciEvolve Memory Evolution Note",
        "",
        marker,
        "",
        f"**Operation:** `{operation}`",
    ]
    if title:
        lines.append(f"**Title:** {title}")
    if related:
        lines.append(f"**Related entities:** {', '.join(f'`{r}`' for r in related)}")
    if rationale:
        lines.append(f"**Rationale:** {rationale}")
    lines.append(f"**Proposal:** `{proposal_id}`")
    lines.append("")

    note = "\n".join(lines)
    new_content = content.rstrip("\n") + "\n" + note

    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(new_content, encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()

    return {"path": str(path), "changed": True, "note_length": len(note)}


def _dream_safe_apply_plan(
    root: Path, item: dict, proposal: dict, *, yolo: bool = False
) -> tuple[dict | None, str]:
    operation = str(item.get("proposal_kind", ""))
    confidence = str(item.get("confidence", ""))
    target = str(item.get("target", ""))
    target_path = _dream_entity_path(root, target)
    if operation not in DREAM_OPERATIONS:
        return None, f"unsupported operation: {operation}"
    if confidence == "low":
        return None, "low-confidence proposals remain review-only"
    if target_path is None or not target_path.exists():
        return None, "target is not a writable entity page"

    related = []
    for entity in item.get("related_entities", []):
        related_path = _dream_entity_path(root, entity)
        if entity and entity != target and related_path and related_path.exists():
            related.append(entity)
    if operation in ("consolidation", "association") and not related:
        return None, f"{operation} needs at least one related entity"

    # Read current frontmatter to determine safe standard-field mutations
    fm = _parse_frontmatter(target_path)

    note = (
        f"{proposal.get('id', '')} {operation}: "
        f"{item.get('title') or item.get('proposed_action', '')}"
    )[:220]
    set_fields: dict[str, object] = {
        "scievolve_last_dream": proposal.get("id", ""),
    }
    append_fields: dict[str, list[str]] = {
        "scievolve_dream_notes": [note],
    }
    if operation == "forgetting":
        set_fields["scievolve_memory_weight"] = "downweighted"
        # Promote deprecation into standard frontmatter when applicable
        if fm.get("maturity") in ("stable", "active", "emerging"):
            set_fields["maturity"] = "deprecated"
    elif operation == "consolidation":
        append_fields["scievolve_consolidates_with"] = related
        if "tags" in fm:
            tags = _dream_as_list(fm.get("tags"))
            if "consolidated" not in tags:
                append_fields.setdefault("tags", []).append("consolidated")
        for entity in related:
            _dream_link_frontmatter_append(fm, append_fields, entity)
    elif operation == "association":
        append_fields["scievolve_associations"] = related
        if "tags" in fm:
            tags = _dream_as_list(fm.get("tags"))
            if "associated" not in tags:
                append_fields.setdefault("tags", []).append("associated")
        for entity in related:
            _dream_link_frontmatter_append(fm, append_fields, entity)

    plan: dict[str, object] = {
        "proposal_id": proposal.get("id", ""),
        "operation": operation,
        "target": target,
        "target_path": target_path,
        "set_fields": set_fields,
        "append_fields": append_fields,
        "body_note": {
            "proposal_id": proposal.get("id", ""),
            "operation": operation,
            "related": related,
            "title": str(item.get("title", "")),
            "rationale": str(item.get("rationale", "")),
        },
    }

    # Yolo mode: high-confidence proposals may mutate page bodies and archive pages
    if yolo and confidence == "high":
        if operation == "forgetting":
            archive = root / "archive" / target_path.relative_to(root)
            plan["yolo_action"] = "archive"
            plan["archive_path"] = archive
        elif operation == "consolidation":
            merge_sources = []
            for entity in related:
                source_path = _dream_entity_path(root, entity)
                if source_path and source_path.exists():
                    archive = root / "archive" / source_path.relative_to(root)
                    merge_sources.append({
                        "source_entity": entity,
                        "source_path": source_path,
                        "archive_path": archive,
                    })
            if merge_sources:
                plan["yolo_action"] = "merge-and-archive"
                plan["merge_sources"] = merge_sources

    return plan, ""


def _dream_archive_page(source: Path, archive: Path) -> dict:
    """Move a page to the archive directory."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    source.rename(archive)
    return {
        "path": str(source),
        "archive_path": str(archive),
        "changed": True,
        "action": "archived",
    }


def _dream_merge_page_body(
    target: Path,
    source: Path,
    proposal_id: str,
    source_entity: str,
) -> dict:
    """Append source page body into target page under a consolidated section."""
    source_content = source.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(source_content)
    source_body = source_content[match.end():] if match else source_content

    target_content = target.read_text(encoding="utf-8")
    marker = f"<!-- /dream merge: {proposal_id} {source_entity} -->"
    if marker in target_content:
        return {"path": str(target), "changed": False, "reason": "already merged"}

    section = [
        "",
        f"### Consolidated Content from `{source_entity}`",
        "",
        marker,
        "",
        source_body.strip(),
        "",
    ]

    new_content = target_content.rstrip("\n") + "\n" + "\n".join(section)
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(new_content, encoding="utf-8")
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()

    return {
        "path": str(target),
        "changed": True,
        "action": "merged",
        "source": str(source),
    }


def _dream_apply_safe(
    root: Path,
    run_dir: Path,
    accepted: list[dict],
    proposals: list[dict],
    *,
    yolo: bool = False,
) -> tuple[list[dict], list[dict], Path, Path]:
    applied: list[dict] = []
    skipped: list[dict] = []
    for item, proposal in zip(accepted, proposals):
        if proposal.get("status") == "applied":
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": "already applied"})
            continue
        plan, reason = _dream_safe_apply_plan(root, item, proposal, yolo=yolo)
        if plan is None:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": reason})
            continue
        try:
            changed_paths: list[dict] = []

            # Yolo actions run first (merge body, archive pages)
            yolo_action = plan.get("yolo_action")
            if yolo_action == "archive":
                archive_change = _dream_archive_page(
                    plan["target_path"],
                    plan["archive_path"],
                )
                changed_paths.append(archive_change)
            elif yolo_action == "merge-and-archive":
                for source_info in plan.get("merge_sources", []):
                    merge_change = _dream_merge_page_body(
                        plan["target_path"],
                        source_info["source_path"],
                        plan["proposal_id"],
                        source_info["source_entity"],
                    )
                    changed_paths.append(merge_change)
                    archive_change = _dream_archive_page(
                        source_info["source_path"],
                        source_info["archive_path"],
                    )
                    changed_paths.append(archive_change)

            # Frontmatter mutations (scievolve_* + standard fields)
            # For yolo forgetting the file has moved; update the archived copy
            if yolo_action == "archive":
                fm_target = plan.get("archive_path", plan["target_path"])
            else:
                fm_target = plan["target_path"]
            if isinstance(fm_target, Path) and fm_target.exists():
                fm_change = _dream_update_frontmatter_memory(
                    fm_target,
                    set_fields=plan["set_fields"],
                    append_fields=plan["append_fields"],
                )
                changed_paths.append(fm_change)

                # Body evolution note on the archived/merged target
                if plan.get("body_note"):
                    body_change = _dream_append_evolution_note(
                        fm_target,
                        **plan["body_note"],
                    )
                    changed_paths.append(body_change)

                validation = {
                    "frontmatter_parseable": bool(_parse_frontmatter(fm_target)),
                }
            else:
                validation = {"frontmatter_parseable": False}

            application = scievolve_record_application(root, {
                "proposal_id": proposal.get("id", ""),
                "skill": "/dream",
                "operation": plan["operation"],
                "target": plan["target"],
                "mode": "yolo" if yolo_action else "auto-apply",
                "changed_paths": changed_paths,
                "validation": validation,
            })
            updated = scievolve_update_proposal_status(
                root,
                proposal,
                "applied",
                note=(
                    "Applied by /dream yolo-apply as archived/merged memory."
                    if yolo_action else
                    "Applied by /dream auto-apply as reversible memory metadata and body note."
                ),
                application=application,
            )
            applied.append({
                "proposal_id": proposal.get("id", ""),
                "application_id": application.get("id", ""),
                "target": plan["target"],
                "path": str(plan["target_path"]),
                "changed_paths": changed_paths,
                "proposal": updated,
            })
        except Exception as exc:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": str(exc)})

    context_rebuild = None
    if applied:
        context_rebuild = compile_context(str(root), "general", emit=False)

    json_path = run_dir / "dream_apply_report.json"
    md_path = run_dir / "dream_apply_report.md"
    payload = {
        "status": "ok",
        "mode": "auto-apply",
        "applied": applied,
        "skipped": skipped,
        "context_rebuild": context_rebuild,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_lines = [
        "# /dream Auto-Apply Report",
        "",
        f"- Applied: {len(applied)}",
        f"- Skipped: {len(skipped)}",
        f"- Context rebuilt: {str(bool(context_rebuild)).lower()}",
        "",
        "## Applied",
        "",
    ]
    if applied:
        for item in applied:
            md_lines.append(f"- {item['proposal_id']} -> `{item['path']}`")
            for change in item.get("changed_paths", []):
                if isinstance(change, dict):
                    md_lines.append(
                        f"  - {change.get('path', '')}: changed={str(change.get('changed')).lower()}"
                    )
    else:
        md_lines.append("_No proposals were auto-applied._")
    if skipped:
        md_lines.extend(["", "## Skipped", ""])
        for item in skipped:
            md_lines.append(f"- {item.get('proposal_id')}: {item.get('reason')}")
    if context_rebuild:
        md_lines.extend(["", "## Downstream Linkage", ""])
        md_lines.append(
            f"- Rebuilt `{context_rebuild.get('path')}` with "
            f"{context_rebuild.get('scievolve_memory_items')} SciEvolve memory item(s)."
        )
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    return applied, skipped, json_path, md_path


def _dream_report_markdown(
    context: dict,
    *,
    run_dir: Path,
    context_path: Path,
    prompt_path: Path,
    response_path: Path | None,
    proposals: list[dict],
    rejected: list[dict],
    proposed: bool,
    applied: list[dict] | None = None,
    apply_skipped: list[dict] | None = None,
) -> str:
    applied = applied or []
    apply_skipped = apply_skipped or []
    lines = [
        "# /dream Memory Evolution Report",
        "",
        f"- Generated: {context['generated_at']}",
        "- Mode: agent-first memory evolution",
        f"- Context: `{context_path.name}`",
        f"- Agent prompt: `{prompt_path.name}`",
        f"- Agent response: `{response_path.name if response_path else '(not supplied)'}`",
        f"- Proposal artifacts written: {len(proposals) if proposed else 0}",
        f"- Safe applications: {len(applied)}",
        "",
        "## Interpretation",
        "",
        (
            "Deterministic tooling prepared memory cues; an agent response is "
            "required to turn those cues into SciEvolve proposals. The tool "
            "validates, records, optionally applies safe memory metadata, and "
            "rebuilds downstream context when the memory state changes."
        ),
        "",
        "## Candidate Cue Counts",
        "",
    ]
    counts = Counter(candidate["operation"] for candidate in context.get("candidate_memory_cues", []))
    for operation in DREAM_OPERATIONS:
        lines.append(f"- {operation}: {counts.get(operation, 0)}")
    lines.extend(["", "## Proposals", ""])
    if proposals and proposed:
        for proposal in proposals:
            lines.append(
                f"- {proposal['id']} [{proposal.get('proposal_kind')}]: "
                f"`{proposal['output_path']}`"
            )
    elif proposals:
        lines.append("_Agent proposals were validated, but `--propose` was not set._")
    else:
        lines.append("_No validated agent proposals._")
    if rejected:
        lines.extend(["", "## Rejected Agent Items", ""])
        for item in rejected:
            lines.append(f"- index {item.get('index')}: {item.get('reason')}")
    lines.extend(["", "## Apply Semantics", ""])
    if applied:
        lines.append(
            "Safe auto-apply updated reversible SciEvolve metadata and append-only "
            "audit notes on memory pages. The derived context brief is rebuilt so "
            "later skills can consume the changed memory state. No page body "
            "sections, graph edges, schemas, skills, or templates were rewritten."
        )
        lines.extend(["", "## Safe Applications", ""])
        for item in applied:
            lines.append(f"- {item['proposal_id']} -> `{item['path']}`")
    else:
        lines.append("No wiki entity pages are changed by this report.")
    if apply_skipped:
        lines.extend(["", "## Apply-Safe Skips", ""])
        for item in apply_skipped:
            lines.append(f"- {item.get('proposal_id')}: {item.get('reason')}")
    return "\n".join(lines)


def dream(
    wiki_root: str,
    *,
    max_entities: int = 120,
    max_signals: int = 30,
    max_candidates: int = 30,
    agent_response: str = "",
    use_llm: bool = False,
    propose: bool = True,
    apply_safe: bool = True,
    propose_only: bool = False,
    yolo: bool = False,
    as_json: bool = False,
    timeout: int = 90,
    temperature: float = 0.2,
) -> None:
    root = Path(wiki_root)
    if propose_only:
        propose = True
        apply_safe = False
    if apply_safe:
        propose = True
    run_id = _dream_run_id()
    run_dir = root / "outputs" / "evolution" / "dream" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = _dream_build_context(wiki_root, max_entities, max_signals, max_candidates)
    context_path = run_dir / "dream_context.json"
    context_md_path = run_dir / "dream_context.md"
    prompt_path = run_dir / "dream_agent_prompt.md"
    response_path: Path | None = None
    context_path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    context_md_path.write_text(_dream_context_markdown(context), encoding="utf-8")
    prompt = _dream_agent_prompt(context)
    prompt_path.write_text(prompt, encoding="utf-8")

    payload: dict | None = None
    agent_trace = {
        "provider": "supplied-policy-response",
        "model": "external-policy-runtime",
        "policy_runtime": "caller-supplied",
        "prompt_path": str(prompt_path.relative_to(root)),
    }
    if agent_response:
        source = Path(agent_response)
        payload = _dream_extract_json_object(source.read_text(encoding="utf-8"))
        response_path = run_dir / "dream_agent_response.json"
        response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        agent_trace["response_path"] = str(response_path.relative_to(root))
    elif use_llm:
        payload, llm_trace = _dream_call_openai_compatible(
            prompt,
            timeout=timeout,
            temperature=temperature,
        )
        response_path = run_dir / "dream_agent_response.json"
        response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        agent_trace.update(llm_trace)
        agent_trace["response_path"] = str(response_path.relative_to(root))

    accepted: list[dict] = []
    rejected: list[dict] = []
    proposals: list[dict] = []
    if payload is not None:
        accepted, rejected = _dream_normalize_agent_response(payload, context, agent_trace)
        if propose:
            for item in accepted:
                proposals.append(scievolve_write_proposal(root, **item))
    applied: list[dict] = []
    apply_skipped: list[dict] = []
    apply_report_json: Path | None = None
    apply_report_md: Path | None = None
    if apply_safe and proposals:
        applied, apply_skipped, apply_report_json, apply_report_md = _dream_apply_safe(
            root,
            run_dir,
            accepted,
            proposals,
            yolo=yolo,
        )
        applied_by_id = {
            item["proposal_id"]: item["proposal"]
            for item in applied
            if item.get("proposal")
        }
        proposals = [
            applied_by_id.get(proposal.get("id"), proposal)
            for proposal in proposals
        ]

    report_path = run_dir / "dream_report.md"
    report_path.write_text(
        _dream_report_markdown(
            context,
            run_dir=run_dir,
            context_path=context_path,
            prompt_path=prompt_path,
            response_path=response_path,
            proposals=proposals if propose else accepted,
            rejected=rejected,
            proposed=propose,
            applied=applied,
            apply_skipped=apply_skipped,
        ),
        encoding="utf-8",
    )

    result = {
        "status": "ok",
        "mode": "agent-first-dream",
        "run_dir": str(run_dir),
        "context_path": str(context_path),
        "context_markdown_path": str(context_md_path),
        "prompt_path": str(prompt_path),
        "response_path": str(response_path) if response_path else "",
        "report_path": str(report_path),
        "candidate_count": len(context.get("candidate_memory_cues", [])),
        "accepted_agent_proposals": len(accepted),
        "rejected_agent_items": len(rejected),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "safe_application_count": len(applied),
        "safe_applications": applied,
        "safe_application_skips": apply_skipped,
        "apply_report_path": str(apply_report_json) if apply_report_json else "",
        "apply_report_markdown_path": str(apply_report_md) if apply_report_md else "",
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"/dream report: {report_path}")
        print(f"Agent prompt: {prompt_path}")
        if response_path:
            print(f"Agent response: {response_path}")
        print(f"Candidate cues: {result['candidate_count']}")
        print(f"Proposals written: {result['proposal_count']}")
        print(f"Safe applications: {result['safe_application_count']}")


#!/usr/bin/env python3
"""Forge implementation to be inserted into research_wiki.py."""

# ---------------------------------------------------------------------------
# SciEvolve /forge: agent-first workflow evolution
# ---------------------------------------------------------------------------


def _forge_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _forge_build_context(
    wiki_root: str,
    target_skill: str,
    max_signals: int,
) -> dict:
    root = Path(wiki_root)
    signals, malformed = load_scievolve_signals(root)
    workflow_signals = [s for s in signals if s.get("dimension") == "workflow"]
    if target_skill:
        workflow_signals = [
            s for s in workflow_signals
            if str(s.get("target", "")).lower() == target_skill.lower()
        ]
    if max_signals > 0:
        workflow_signals = workflow_signals[-max_signals:]

    # Group signals by target skill
    by_target: dict[str, list[dict]] = {}
    for s in workflow_signals:
        t = str(s.get("target", "")).strip() or "general"
        by_target.setdefault(t, []).append(s)

    # Load skill content for each targeted skill
    skill_contents: dict[str, str] = {}
    skill_paths: dict[str, Path] = {}
    for skill_name in by_target:
        # Try i18n first, then .claude
        for base in (root.parent / "i18n" / "en" / "skills", root.parent / ".claude" / "skills"):
            skill_md = base / skill_name / "SKILL.md"
            if skill_md.exists():
                skill_paths[skill_name] = skill_md
                skill_contents[skill_name] = skill_md.read_text(encoding="utf-8")
                break

    # Compute signal density per skill
    signal_density = {
        name: len(group) for name, group in by_target.items()
    }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "mode": "agent-first-forge",
        "wiki_root": str(root),
        "target_skill": target_skill,
        "stats": {
            "workflow_signals": len(workflow_signals),
            "malformed_signal_rows": malformed,
            "targeted_skills": len(by_target),
            "signal_density": signal_density,
        },
        "signals": workflow_signals,
        "skill_groups": [
            {
                "skill_name": name,
                "signal_count": len(group),
                "signals": group,
                "skill_path": str(skill_paths.get(name, "")),
                "skill_preview": _forge_skill_preview(skill_contents.get(name, "")),
            }
            for name, group in sorted(by_target.items())
        ],
    }


def _forge_skill_preview(content: str, max_lines: int = 60) -> str:
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    # Keep frontmatter + first chunk + ellipsis + last chunk
    header_end = 0
    in_fm = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
            else:
                header_end = i + 1
                break
    front = "\n".join(lines[:header_end + 20]) if header_end else "\n".join(lines[:30])
    tail = "\n".join(lines[-20:])
    return f"{front}\n\n... ({len(lines) - max_lines} lines omitted) ...\n\n{tail}"


def _forge_context_markdown(context: dict) -> str:
    lines = [
        "# Forge Context",
        "",
        "Deterministic context for workflow evolution. Not the forge decision.",
        "",
        "## Stats",
        "",
    ]
    for key, value in context.get("stats", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Workflow Signals", ""])
    for signal in context.get("signals", []):
        lines.append(
            "- {id} [{kind}] target={target}: {summary}".format(
                id=signal.get("id", ""),
                kind=signal.get("kind", ""),
                target=signal.get("target", ""),
                summary=signal.get("summary", ""),
            )
        )
    lines.extend(["", "## Skill Groups", ""])
    for group in context.get("skill_groups", []):
        name = group.get("skill_name", "")
        count = group.get("signal_count", 0)
        path = group.get("skill_path", "")
        lines.append(f"- {name}: {count} signal(s)  path: `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def _forge_agent_prompt(context: dict) -> str:
    skill_groups = context.get("skill_groups", [])
    skill_blocks = []
    for group in skill_groups:
        name = group.get("skill_name", "")
        preview = group.get("skill_preview", "")
        signals = group.get("signals", [])
        signal_lines = "\n".join(
            f"  - {s.get('id', '')} [{s.get('kind', '')}]: {s.get('summary', '')}"
            for s in signals
        )
        skill_blocks.append(
            f"### Skill: {name}\n\n"
            f"Signals:\n{signal_lines}\n\n"
            f"Content preview:\n```markdown\n{preview}\n```\n"
        )
    skills_text = "\n\n".join(skill_blocks) if skill_blocks else "_No targeted skill content loaded._"

    return (
        "# /forge Agent Prompt\n\n"
        "You are AutoSci's /forge agent. Your job is workflow self-evolution: "
        "propose concrete, evidence-backed patches to skills and protocols.\n\n"
        "Use the supplied context to propose workflow-evolution operations:\n"
        "- patch-prompt: rewrite or clarify a specific prompt/step in a skill\n"
        "- add-check: add a validation, precondition, or guard step\n"
        "- adjust-handoff: change how this skill hands off to or receives from another skill\n"
        "- add-recovery: add a recovery protocol for a known failure mode\n\n"
        "Rules:\n"
        "- Every proposal must cite a specific skill file path and, where possible, a line range or prompt text.\n"
        "- Proposals must be grounded in the provided signals. Do not invent failure modes.\n"
        "- Do not change a skill's core purpose — only improve clarity, robustness, or inter-skill coordination.\n"
        "- Do not repackage lint or structural repairs as workflow evolution (those are /check concerns).\n"
        "- Prefer additive changes (append checks, add recovery) over destructive rewrites.\n"
        "- A few high-signal proposals beat a broad mechanical list.\n\n"
        "Return strict JSON only with this shape:\n\n"
        "{\n"
        '  "proposals": [\n'
        "    {\n"
        '      "operation": "patch-prompt|add-check|adjust-handoff|add-recovery",\n'
        '      "target": "skill-name",\n'
        '      "title": "short title",\n'
        '      "proposed_action": "concrete proposal-first action with file path and line reference",\n'
        '      "rationale": "why the signals justify this patch and how it improves execution",\n'
        '      "confidence": "low|medium|high",\n'
        '      "skill_path": "relative/path/to/SKILL.md",\n'
        '      "line_hint": "optional: quoted text or line range to locate the patch",\n'
        '      "evidence": [\n'
        '        {"source": "signal-id", "summary": "supporting note"}\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Context:\n\n"
        f"{skills_text}"
    )


def _forge_allowed_refs(context: dict) -> set[str]:
    refs: set[str] = set()
    for group in context.get("skill_groups", []):
        refs.add(group.get("skill_name", ""))
        refs.add(str(group.get("skill_path", "")))
    refs.update(str(s.get("id", "")) for s in context.get("signals", []))
    refs.discard("")
    return refs


def _forge_normalize_agent_response(
    payload: dict,
    context: dict,
    agent_trace: dict,
) -> tuple[list[dict], list[dict]]:
    allowed = _forge_allowed_refs(context)
    signal_ids = {str(s.get("id", "")) for s in context.get("signals", [])}
    raw_proposals = payload.get("proposals")
    if not isinstance(raw_proposals, list):
        raise ValueError("forge agent response must contain a proposals list")

    accepted: list[dict] = []
    rejected: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_proposals):
        if not isinstance(raw, dict):
            rejected.append({"index": index, "reason": "proposal is not an object"})
            continue
        operation = str(raw.get("operation") or raw.get("proposal_kind") or "").strip().lower()
        if operation not in FORGE_OPERATIONS:
            rejected.append({"index": index, "reason": f"invalid operation: {operation}"})
            continue
        target = str(raw.get("target") or "").strip()
        skill_path = str(raw.get("skill_path") or "").strip()
        if not target:
            rejected.append({"index": index, "reason": "missing target skill"})
            continue
        if target not in allowed:
            rejected.append({"index": index, "reason": f"unknown target skill: {target}"})
            continue
        action = str(raw.get("proposed_action") or raw.get("action") or "").strip()
        rationale = str(raw.get("rationale") or "").strip()
        if not action or not rationale:
            rejected.append({"index": index, "reason": "missing proposed_action or rationale"})
            continue
        confidence = str(raw.get("confidence") or "medium").strip().lower()
        if confidence not in SCIEVOLVE_CONFIDENCE_VALUES:
            confidence = "medium"
        title = str(raw.get("title") or operation.title()).strip()
        dedup_key = (operation, target, action)
        if dedup_key in seen:
            rejected.append({"index": index, "reason": "duplicate proposal"})
            continue
        seen.add(dedup_key)
        evidence = []
        for item in raw.get("evidence") or []:
            if isinstance(item, dict):
                source = str(item.get("source") or item.get("id") or item.get("signal_id") or "")
                evidence.append({"source": source, "summary": str(item.get("summary") or ""), "path": skill_path})
            elif str(item).strip():
                evidence.append({"source": str(item).strip(), "summary": "", "path": skill_path})
        accepted.append({
            "dimension": "workflow",
            "target": target,
            "proposal_kind": operation,
            "title": title,
            "confidence": confidence,
            "related_entities": [],
            "triggering_signals": sorted(
                str(item.get("source", "")) for item in evidence
                if str(item.get("source", "")) in signal_ids
            ),
            "proposed_action": action,
            "rationale": rationale,
            "risk": (
                "Agent-generated /forge proposal. Workflow changes affect execution semantics; "
                "review before applying. Safe auto-apply is limited to additive/append-only changes."
            ),
            "evidence": evidence,
            "agent_trace": agent_trace,
        })
    return accepted, rejected


def _forge_apply_safe(
    wiki_root: Path,
    run_dir: Path,
    accepted: list[dict],
    proposals: list[dict],
) -> tuple[list[dict], list[dict], Path | None, Path | None]:
    """Apply safe workflow mutations: additive frontmatter metadata + append-only notes only.

    Unlike /dream, /forge does NOT rewrite skill prompts or workflow steps automatically.
    Safe apply is limited to:
    - scievolve_forge_notes frontmatter (append-only list)
    - scievolve_last_forge frontmatter (set)
    - Append-only ## SciEvolve Workflow Evolution Note section in skill body
    """
    applied: list[dict] = []
    skipped: list[dict] = []
    changed_paths: list[str] = []
    for item, proposal in zip(accepted, proposals):
        target = item.get("target", "")
        if not target:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": "missing target"})
            continue
        # Locate skill file
        skill_file: Path | None = None
        for base in (wiki_root.parent / "i18n" / "en" / "skills", wiki_root.parent / ".claude" / "skills"):
            candidate = base / target / "SKILL.md"
            if candidate.exists():
                skill_file = candidate
                break
        if skill_file is None:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": f"skill file not found: {target}"})
            continue

        content = skill_file.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(content)
        if not match:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": "no frontmatter in skill file"})
            continue

        fm = _parse_yaml_block(match.group(1))
        body = content[match.end():]

        # Build the note text
        note_lines = [
            f"## SciEvolve Workflow Evolution Note",
            "",
            f"- Proposal: `{proposal.get('id', '')}`",
            f"- Operation: {item.get('proposal_kind', '')}",
            f"- Confidence: {item.get('confidence', '')}",
            f"- Action: {item.get('proposed_action', '')}",
            f"- Rationale: {item.get('rationale', '')}",
            "",
        ]
        note_text = "\n".join(note_lines)

        # Append note to body if not already present
        if note_text.strip() not in body:
            if not body.endswith("\n"):
                body += "\n"
            body += "\n" + note_text + "\n"
        else:
            skipped.append({"proposal_id": proposal.get("id", ""), "reason": "note already present"})
            continue

        # Update frontmatter
        fm["scievolve_last_forge"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        notes = _dream_as_list(fm.get("scievolve_forge_notes"))
        note_entry = f"[{proposal.get('id', '')}] {item.get('proposal_kind', '')}: {item.get('title', '')}"
        if note_entry not in notes:
            notes.append(note_entry)
        fm["scievolve_forge_notes"] = notes

        # Rebuild file
        new_yaml = _serialize_frontmatter(fm)
        new_content = f"---\n{new_yaml}---\n{body}"
        skill_file.write_text(new_content, encoding="utf-8")
        changed_paths.append(str(skill_file))

        _ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        _digest_input = {"proposal": proposal.get("id", ""), "target": target}
        _digest = hashlib.sha1(json.dumps(_digest_input, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
        application = {
            "id": f"app-forge-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{_digest}",
            "timestamp": _ts,
            "proposal_id": proposal.get("id", ""),
            "target": target,
            "changed_paths": [{"path": str(skill_file), "note": "append-only workflow evolution note + frontmatter metadata"}],
        }
        scievolve_record_application(wiki_root, application)
        applied.append({"proposal_id": proposal.get("id", ""), "proposal": proposal, "application": application})

    apply_report = {
        "run_type": "forge_safe_apply",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": [a["application"] for a in applied],
        "skipped": skipped,
        "changed_paths": changed_paths,
    }
    json_path = run_dir / "forge_apply_report.json"
    md_path = run_dir / "forge_apply_report.md"
    json_path.write_text(json.dumps(apply_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_lines = [
        "# Forge Safe Apply Report",
        "",
        f"- Applied: {len(applied)}",
        f"- Skipped: {len(skipped)}",
        "",
        "## Changed Paths",
        "",
    ]
    for cp in changed_paths:
        md_lines.append(f"- `{cp}`")
    md_lines.extend(["", "## Skipped", ""])
    for sk in skipped:
        md_lines.append(f"- {sk['proposal_id']}: {sk['reason']}")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return applied, skipped, json_path, md_path


def _forge_report_markdown(
    context: dict,
    *,
    run_dir: Path,
    context_path: Path,
    prompt_path: Path,
    response_path: Path | None,
    proposals: list[dict],
    rejected: list[dict],
    proposed: bool,
    applied: list[dict],
    apply_skipped: list[dict],
) -> str:
    lines = [
        "# Forge Report",
        "",
        f"- Run: {run_dir.name}",
        f"- Target skill: {context.get('target_skill') or '(all)'}",
        f"- Workflow signals: {context['stats']['workflow_signals']}",
        f"- Targeted skills: {context['stats']['targeted_skills']}",
        "",
        "## Signal Density",
        "",
    ]
    for name, count in sorted((context["stats"].get("signal_density") or {}).items()):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Proposals", ""])
    if proposals:
        for p in proposals:
            state = "created" if p.get("created") else "existing"
            lines.append(f"- {p['id']} ({state}, {p['status']}): `{p['output_path']}`")
    else:
        lines.append("_No proposals._")
    lines.extend(["", "## Rejected Agent Items", ""])
    if rejected:
        for r in rejected:
            lines.append(f"- index {r.get('index', '?')}: {r.get('reason', '')}")
    else:
        lines.append("_None._")
    if applied or apply_skipped:
        lines.extend(["", "## Safe Applications", ""])
        lines.append(f"- Applied: {len(applied)}")
        lines.append(f"- Skipped: {len(apply_skipped)}")
    lines.extend(["", "## Artifacts", ""])
    lines.append(f"- Context: `{context_path}`")
    lines.append(f"- Prompt: `{prompt_path}`")
    if response_path:
        lines.append(f"- Response: `{response_path}`")
    lines.append("")
    return "\n".join(lines)


def forge(
    wiki_root: str,
    *,
    target_skill: str = "",
    max_signals: int = 20,
    agent_response: str = "",
    use_llm: bool = False,
    propose: bool = True,
    auto_apply: bool = False,
    as_json: bool = False,
    timeout: int = 90,
    temperature: float = 0.2,
) -> None:
    root = Path(wiki_root)
    run_id = _forge_run_id()
    run_dir = root / "outputs" / "evolution" / "forge" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = _forge_build_context(wiki_root, target_skill, max_signals)
    context_path = run_dir / "forge_context.json"
    context_md_path = run_dir / "forge_context.md"
    prompt_path = run_dir / "forge_agent_prompt.md"
    response_path: Path | None = None
    context_path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    context_md_path.write_text(_forge_context_markdown(context), encoding="utf-8")
    prompt = _forge_agent_prompt(context)
    prompt_path.write_text(prompt, encoding="utf-8")

    payload: dict | None = None
    agent_trace = {
        "provider": "supplied-policy-response",
        "model": "external-policy-runtime",
        "policy_runtime": "caller-supplied",
        "prompt_path": str(prompt_path.relative_to(root)),
    }
    if agent_response:
        source = Path(agent_response)
        payload = _dream_extract_json_object(source.read_text(encoding="utf-8"))
        response_path = run_dir / "forge_agent_response.json"
        response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        agent_trace["response_path"] = str(response_path.relative_to(root))
    elif use_llm:
        payload, llm_trace = _dream_call_openai_compatible(
            prompt,
            timeout=timeout,
            temperature=temperature,
        )
        response_path = run_dir / "forge_agent_response.json"
        response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        agent_trace.update(llm_trace)
        agent_trace["response_path"] = str(response_path.relative_to(root))

    accepted: list[dict] = []
    rejected: list[dict] = []
    proposals: list[dict] = []
    if payload is not None:
        accepted, rejected = _forge_normalize_agent_response(payload, context, agent_trace)
        if propose:
            for item in accepted:
                proposals.append(scievolve_write_proposal(root, **item))

    applied: list[dict] = []
    apply_skipped: list[dict] = []
    apply_report_json: Path | None = None
    apply_report_md: Path | None = None
    if auto_apply and proposals:
        applied, apply_skipped, apply_report_json, apply_report_md = _forge_apply_safe(
            root,
            run_dir,
            accepted,
            proposals,
        )
        applied_by_id = {
            item["proposal_id"]: item["proposal"]
            for item in applied
            if item.get("proposal")
        }
        proposals = [
            applied_by_id.get(proposal.get("id"), proposal)
            for proposal in proposals
        ]

    report_path = run_dir / "forge_report.md"
    report_path.write_text(
        _forge_report_markdown(
            context,
            run_dir=run_dir,
            context_path=context_path,
            prompt_path=prompt_path,
            response_path=response_path,
            proposals=proposals if propose else accepted,
            rejected=rejected,
            proposed=propose,
            applied=applied,
            apply_skipped=apply_skipped,
        ),
        encoding="utf-8",
    )

    result = {
        "status": "ok",
        "mode": "agent-first-forge",
        "run_dir": str(run_dir),
        "context_path": str(context_path),
        "context_markdown_path": str(context_md_path),
        "prompt_path": str(prompt_path),
        "response_path": str(response_path) if response_path else "",
        "report_path": str(report_path),
        "signal_count": len(context.get("signals", [])),
        "accepted_agent_proposals": len(accepted),
        "rejected_agent_items": len(rejected),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "safe_application_count": len(applied),
        "safe_applications": applied,
        "safe_application_skips": apply_skipped,
        "apply_report_path": str(apply_report_json) if apply_report_json else "",
        "apply_report_markdown_path": str(apply_report_md) if apply_report_md else "",
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"/forge report: {report_path}")
        print(f"Agent prompt: {prompt_path}")
        if response_path:
            print(f"Agent response: {response_path}")
        print(f"Workflow signals: {result['signal_count']}")
        print(f"Proposals written: {result['proposal_count']}")
        if auto_apply:
            print(f"Safe applications: {result['safe_application_count']}")



# ---------------------------------------------------------------------------
# Lifecycle: transition
# ---------------------------------------------------------------------------

# Lifecycle transitions are declared in runtime/schema/entities.yaml — derived
# here so adding a new lifecycle requires only a YAML edit.
TRANSITIONS: dict[str, dict[str, list[str]]] = {
    kind: e['lifecycle']['transitions']
    for kind, e in ENTITIES.items()
    if 'lifecycle' in e
}

# Fields auto-set on transition
AUTO_FIELDS: dict[tuple[str, str], dict[str, str]] = {
    ("ideas", "failed"): {"date_resolved": "_today_"},
    ("ideas", "validated"): {"date_resolved": "_today_"},
    ("experiments", "completed"): {"date_completed": "_today_"},
}


def transition(path: str, new_status: str, reason: str = "") -> None:
    """Enforce lifecycle state transitions with validation."""
    p = Path(path)
    if not p.exists():
        print(json.dumps({"status": "error", "message": f"File not found: {path}"}))
        sys.exit(1)

    # Determine entity type from path
    entity_type = p.parent.name
    if entity_type not in TRANSITIONS:
        print(json.dumps({"status": "error",
                          "message": f"No lifecycle rules for entity type '{entity_type}'"}))
        sys.exit(1)

    fm = _parse_frontmatter(p)
    current_status = fm.get("status", "")
    rules = TRANSITIONS[entity_type]

    if current_status not in rules:
        print(json.dumps({"status": "error",
                          "message": f"Current status '{current_status}' is terminal or unknown"}))
        sys.exit(1)

    allowed = rules[current_status]
    if new_status not in allowed:
        print(json.dumps({
            "status": "error",
            "message": f"Invalid: {current_status} -> {new_status}. "
                       f"Allowed: {allowed}",
        }))
        sys.exit(1)

    # Precondition checks
    if entity_type == "ideas" and new_status == "in_progress":
        linked = fm.get("linked_experiments", [])
        if not linked:
            print(json.dumps({"status": "error",
                              "message": "linked_experiments must be non-empty "
                                         "to transition to in_progress"}))
            sys.exit(1)

    if entity_type == "ideas" and new_status == "failed":
        if not reason:
            print(json.dumps({"status": "error",
                              "message": "--reason is required to transition to failed"}))
            sys.exit(1)

    if entity_type == "experiments" and new_status == "completed":
        if not fm.get("key_result"):
            print(json.dumps({"status": "error",
                              "message": "key_result must be non-empty "
                                         "to transition to completed"}))
            sys.exit(1)

    # Apply transition
    content = p.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content, _, _ = _update_frontmatter_field(content, "status", new_status)

    # Auto-set related fields
    auto_set: list[str] = []
    auto_key = (entity_type, new_status)
    if auto_key in AUTO_FIELDS:
        for field, val in AUTO_FIELDS[auto_key].items():
            actual_val = today if val == "_today_" else val
            try:
                content, _, _ = _update_frontmatter_field(content, field, actual_val)
                auto_set.append(field)
            except ValueError:
                pass  # Field doesn't exist, skip

    # Set failure_reason if transitioning idea to failed
    if entity_type == "ideas" and new_status == "failed" and reason:
        try:
            content, _, _ = _update_frontmatter_field(content, "failure_reason", reason)
            auto_set.append("failure_reason")
        except ValueError:
            pass

    # Atomic write
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.rename(p)
    finally:
        if tmp.exists():
            tmp.unlink()

    result: dict = {
        "status": "ok",
        "entity": f"{entity_type}/{p.stem}",
        "old_status": current_status,
        "new_status": new_status,
    }
    if auto_set:
        result["auto_set"] = auto_set
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Batch edge creation
# ---------------------------------------------------------------------------

def batch_edges(wiki_root: str) -> None:
    """Create multiple edges from a JSON array on stdin."""
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
        sys.exit(1)

    if not isinstance(data, list):
        print(json.dumps({"status": "error", "message": "Expected JSON array"}))
        sys.exit(1)

    edges_path = Path(wiki_root) / DERIVED_DIR / "edges.jsonl"
    edges_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing edges for dedup
    existing: set[tuple[str, str, str]] = set()
    if edges_path.exists():
        for line in edges_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                existing.add(_edge_key(e))
            except json.JSONDecodeError:
                continue

    added = 0
    existed = 0
    warnings: list[str] = []
    errors: list[str] = []
    root = Path(wiki_root)

    new_lines: list[str] = []
    for index, item in enumerate(data, start=1):
        from_id = item.get("from", "")
        to_id = item.get("to", "")
        edge_type = item.get("type", "")
        evidence = item.get("evidence", "")
        confidence = item.get("confidence", "")
        symmetric = _truthy(item.get("symmetric", False))
        item_label = f"item {index} ({from_id} -> {to_id}, type={edge_type})"

        if edge_type not in VALID_EDGE_TYPES:
            errors.append(f"{item_label}: unknown edge type '{edge_type}'")
            continue
        if confidence and confidence not in EDGE_CONFIDENCE_VALUES:
            errors.append(f"{item_label}: unknown confidence '{confidence}'")
            continue

        from_id, to_id, is_symmetric, error = _canonical_edge_ids(
            from_id, to_id, edge_type, symmetric
        )
        if error:
            errors.append(f"{item_label}: {error}")
            continue
        item_errors = _semantic_edge_errors(
            edge_type, from_id, to_id, confidence, evidence
        )
        if item_errors:
            errors.extend(f"{item_label}: {msg}" for msg in item_errors)
            continue

        triple = _edge_key({
            "from": from_id, "to": to_id, "type": edge_type,
            "symmetric": is_symmetric,
        })
        if triple in existing:
            existed += 1
            continue

        # Entity validation
        warnings.extend(_validate_node_refs(root, from_id, to_id))
        warnings.extend(_semantic_edge_warnings(
            edge_type, from_id, to_id, confidence, evidence
        ))

        edge = {
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "evidence": evidence,
            "date": _today(),
        }
        if confidence:
            edge["confidence"] = confidence
        if is_symmetric:
            edge["symmetric"] = True
        new_lines.append(json.dumps(edge, ensure_ascii=False))
        existing.add(triple)
        added += 1

    if errors:
        print(json.dumps({"status": "error", "added": 0, "existed": existed,
                          "errors": errors, "warnings": warnings},
                         ensure_ascii=False))
        sys.exit(1)

    if new_lines:
        with open(edges_path, "a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    print(json.dumps({"status": "ok", "added": added, "existed": existed,
                       "warnings": warnings}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Rebuild index.md
# ---------------------------------------------------------------------------

def rebuild_index(wiki_root: str) -> None:
    """Regenerate index.md by scanning all entity directories."""
    root = Path(wiki_root)
    counts: dict[str, int] = {}

    sections: list[str] = []
    for entity_type in ENTITY_DIRS:
        entity_dir = root / entity_type
        if not entity_dir.exists():
            counts[entity_type] = 0
            sections.append(f"{entity_type}:\n")
            continue

        entries: list[str] = []
        for f in sorted(entity_dir.glob("*.md")):
            fm = _parse_frontmatter(f)
            slug = f.stem
            line_parts = [f"  - slug: {slug}"]

            # Include key fields per entity type
            if "title" in fm:
                title = fm["title"]
                line_parts.append(f'    title: "{title}"')
            if "tags" in fm and fm["tags"]:
                tags = fm["tags"]
                if isinstance(tags, list):
                    line_parts.append(f"    tags: [{', '.join(str(t) for t in tags)}]")
            if "status" in fm:
                line_parts.append(f"    status: {fm['status']}")
            if "importance" in fm:
                line_parts.append(f"    importance: {fm['importance']}")
            if "novelty_score" in fm and fm["novelty_score"] not in ("", None):
                line_parts.append(f"    novelty_score: {fm['novelty_score']}")
            if "target_venue" in fm and fm["target_venue"]:
                line_parts.append(f'    target_venue: "{fm["target_venue"]}"')
            if "linked_idea" in fm:
                line_parts.append(f"    linked_idea: {fm['linked_idea']}")
            if "type" in fm and isinstance(fm["type"], str):
                line_parts.append(f"    type: {fm['type']}")
            if "type" in fm and isinstance(fm["type"], dict):
                kind = fm["type"].get("kind")
                if kind:
                    line_parts.append(f"    kind: {kind}")
            if "priority" in fm:
                line_parts.append(f"    priority: {fm['priority']}")
            if "affiliation" in fm:
                line_parts.append(f'    affiliation: "{fm["affiliation"]}"')
            if "maturity" in fm:
                line_parts.append(f"    maturity: {fm['maturity']}")

            entries.append("\n".join(line_parts))

        counts[entity_type] = len(entries)
        if entries:
            sections.append(f"{entity_type}:\n" + "\n".join(entries) + "\n")
        else:
            sections.append(f"{entity_type}:\n")

    content = "# Wiki Index\n\n" + "\n".join(sections)
    index_path = root / "index.md"
    index_path.write_text(content, encoding="utf-8")

    print(json.dumps({"status": "ok", "entities": counts}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Topic backfill (post-merge sweep for /init INIT MODE)
# ---------------------------------------------------------------------------

def topic_backfill(wiki_root: str) -> None:
    """Append matching papers to each topic's seminal_works / SOTA tracker.

    Re-implements the deterministic half of /ingest Step 5 Part B in a
    post-merge sweep. /init's INIT MODE tells subagents to skip topic updates
    so parallel ingest doesn't conflict on shared topic files; this command
    is what finally repairs them after Phase B merges complete.

    Matching rule (matches /ingest Part B):
      - paper.tags ∩ topic.tags must be non-empty
      - importance >= 4 → append `- [[paper-slug]]` to ## Seminal works
      - importance < 4  → append `- [[paper-slug]]` to ## SOTA tracker
      - existing entries are detected and skipped (idempotent)

    NOT handled here (deferred to a later /ingest or /edit pass):
      - topic.key_people backfill (requires "is the author a key figure"
        judgment, which is fuzzy and not safe to automate)
      - topic.tags inference (topics that have no tags get no matches)

    Idempotent: re-running on a wiki that's already backfilled is a no-op.
    """
    root = Path(wiki_root)
    topics_dir = root / "topics"
    papers_dir = root / "papers"

    if not topics_dir.exists() or not papers_dir.exists():
        print(json.dumps({
            "status": "ok",
            "topics_scanned": 0,
            "topics_matched": 0,
            "lines_added": 0,
            "lines_skipped_existing": 0,
            "per_topic": {},
            "note": "topics/ or papers/ missing",
        }))
        return

    def _as_str_set(val) -> set[str]:
        if not val:
            return set()
        if isinstance(val, str):
            return {val.strip().lower()} if val.strip() else set()
        if isinstance(val, list):
            return {str(t).strip().lower() for t in val if str(t).strip()}
        return set()

    # Pre-load all paper frontmatter once
    papers: list[dict] = []
    for p in sorted(papers_dir.glob("*.md")):
        fm = _parse_frontmatter(p)
        slug = p.stem
        tags = _as_str_set(fm.get("tags"))
        # papers.domain was removed in the schema refactor; topic matching is
        # now driven solely by paper.tags ∩ topic.tags.
        try:
            importance = int(str(fm.get("importance", "3")).strip())
        except (TypeError, ValueError):
            importance = 3
        papers.append({"slug": slug, "tags": tags, "importance": importance})

    added = 0
    skipped_existing = 0
    matched_topics = 0
    per_topic: dict[str, dict[str, int]] = {}

    for tpath in sorted(topics_dir.glob("*.md")):
        topic_slug = tpath.stem
        tfm = _parse_frontmatter(tpath)
        ttags = _as_str_set(tfm.get("tags"))
        if not ttags:
            per_topic[topic_slug] = {"added": 0, "skipped": 0,
                                      "note": "topic has no tags"}
            continue

        seminal: list[str] = []
        sota: list[str] = []
        for paper in papers:
            if not (ttags & paper["tags"]):
                continue
            link = f"- [[{paper['slug']}]]"
            if paper["importance"] >= 4:
                seminal.append(link)
            else:
                sota.append(link)

        if not seminal and not sota:
            per_topic[topic_slug] = {"added": 0, "skipped": 0}
            continue

        matched_topics += 1
        t_added, t_skipped = 0, 0
        if seminal:
            a, s = _append_lines_to_section(tpath, "## Seminal works", seminal)
            t_added += a
            t_skipped += s
        if sota:
            a, s = _append_lines_to_section(tpath, "## SOTA tracker", sota)
            t_added += a
            t_skipped += s

        added += t_added
        skipped_existing += t_skipped
        per_topic[topic_slug] = {"added": t_added, "skipped": t_skipped}

    print(json.dumps({
        "status": "ok",
        "topics_scanned": len(per_topic),
        "topics_matched": matched_topics,
        "lines_added": added,
        "lines_skipped_existing": skipped_existing,
        "per_topic": per_topic,
    }, ensure_ascii=False))


def _find_section_heading(content: str, heading: str) -> int:
    """Locate an exact markdown heading in `content`.

    Returns the offset of the leading newline of the matched heading line, or
    -1 if not found. The match must be exact: the character following
    `heading` has to be `\\n`, `\\r`, or end-of-string. This rejects prefix
    collisions like `## Seminal works (extended)` matching `## Seminal works`,
    which would otherwise let the caller insert text inside another heading.
    """
    needle = f"\n{heading}"
    start = 0
    while True:
        idx = content.find(needle, start)
        if idx == -1:
            return -1
        end_of_match = idx + len(needle)
        if end_of_match == len(content) or content[end_of_match] in "\n\r":
            return idx
        start = idx + 1


def _append_lines_to_section(fpath: Path, heading: str,
                              lines: list[str]) -> tuple[int, int]:
    """Append lines under a markdown heading. Returns (added, skipped).

    - Idempotent: re-appending an already-present line in the same section
      returns it as `skipped`, not `added`.
    - Dedup is **section-scoped** in both branches (existing section AND
      newly-created section). The previous version dedup'd the
      missing-section path against the entire file, which silently dropped
      lines that happened to appear in unrelated prose like ## Overview.
    - Heading match is exact (see `_find_section_heading`) to prevent
      `## Seminal works (extended)` collisions corrupting the file.
    - Inserts new lines immediately after the heading (and any blank lines
      that follow it), before existing content.
    """
    content = fpath.read_text(encoding="utf-8")
    section_start = _find_section_heading(content, heading)

    if section_start == -1:
        # Section missing — create it at EOF. The new section starts empty,
        # so dedup is unnecessary; just append all requested lines.
        body = "\n".join(lines)
        content = content.rstrip() + f"\n\n{heading}\n\n{body}\n"
        fpath.write_text(content, encoding="utf-8")
        return (len(lines), 0)

    # Slice that belongs to this section (up to next ## heading or EOF).
    body_start = section_start + 1 + len(heading)
    rest = content[body_start:]
    next_section = re.search(r"\n## ", rest)
    section_end = body_start + (next_section.start() if next_section else len(rest))
    section_text = content[body_start:section_end]

    new_lines = [l for l in lines if l.strip() not in section_text]
    skipped = len(lines) - len(new_lines)
    if not new_lines:
        return (0, skipped)

    # Insert immediately after the heading line + any blank lines following it.
    insert_pos = body_start
    while insert_pos < section_end and content[insert_pos] == "\n":
        insert_pos += 1

    insertion = "\n".join(new_lines) + "\n"
    new_content = content[:insert_pos] + insertion + content[insert_pos:]
    fpath.write_text(new_content, encoding="utf-8")
    return (len(new_lines), skipped)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def append_log(wiki_root: str, message: str) -> None:
    """Append a timestamped entry to log.md.

    Format matches product CLAUDE.md spec:
      ## [YYYY-MM-DD] skill | action | details
    """
    log_path = Path(wiki_root) / "log.md"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"## [{date_str}] {message}\n"

    if log_path.exists():
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        log_path.write_text(f"# OmegaWiki Log\n\n{entry}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Frontmatter engine (parse / serialize / update)
# ---------------------------------------------------------------------------

def _parse_scalar(val: str):
    """Parse a YAML scalar value to Python type."""
    if not val:
        return ""
    # Strip quotes
    if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        return val[1:-1]
    # Inline list: [a, b, c]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        if not inner.strip():
            return []
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
    # Boolean
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    # Float (must check before int — "0.5" has digits but also a dot)
    if re.match(r"^-?\d+\.\d+$", val):
        return float(val)
    # Integer
    if re.match(r"^-?\d+$", val):
        return int(val)
    return val


def _parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter as a dict.

    Handles:
      - Simple scalars: ``key: value``
      - Inline lists: ``tags: [a, b, c]``
      - Block lists: ``tags:\\n  - a\\n  - b``
      - Nested dicts: ``setup:\\n  model: gpt-4\\n  dataset: mmlu``
      - List of dicts (evidence format)::

            evidence:
              - source: paper-slug
                type: supports
                strength: moderate
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}

    return _parse_yaml_block(m.group(1))


def _parse_yaml_block(text: str) -> dict:
    """Parse a block of YAML text into a dict (no PyYAML dependency)."""
    fm: dict = {}
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Must be a top-level key: value
        if ":" not in stripped:
            i += 1
            continue

        # Only process lines that start at column 0 (top-level keys)
        if line[0] == " ":
            i += 1
            continue

        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()

        if val:
            # Inline value
            fm[key] = _parse_scalar(val)
            i += 1
        else:
            # Block value: peek at subsequent indented lines
            block_lines: list[str] = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # Stop at non-indented line (next top-level key or ---)
                if next_line and not next_line[0].isspace():
                    break
                block_lines.append(next_line)
                i += 1

            fm[key] = _parse_block_value(block_lines)

    return fm


def _parse_block_value(lines: list[str]) -> list | dict | str:
    """Parse indented lines that follow a key with no inline value.

    Returns a list (if lines start with ``- ``), a dict (if lines are
    ``key: value``), or an empty string if no content.
    """
    # Filter to non-empty lines
    content_lines = [l for l in lines if l.strip()]
    if not content_lines:
        return ""

    first = content_lines[0].strip()

    # Block list (starts with "- ")
    if first.startswith("- "):
        return _parse_block_list(lines)

    # Nested dict (indented key: value pairs)
    if ":" in first:
        result: dict = {}
        for line in content_lines:
            s = line.strip()
            if ":" in s:
                k, _, v = s.partition(":")
                result[k.strip()] = _parse_scalar(v.strip())
        return result

    return ""


def _parse_block_list(lines: list[str]) -> list:
    """Parse a YAML block list, handling both simple items and list-of-dicts."""
    items: list = []
    current_dict: dict | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("- "):
            # New list item — flush previous dict if any
            if current_dict is not None:
                items.append(current_dict)
                current_dict = None

            item_content = stripped[2:].strip()

            if ":" in item_content:
                # Dict item start: "- source: paper-slug"
                current_dict = {}
                k, _, v = item_content.partition(":")
                current_dict[k.strip()] = _parse_scalar(v.strip())
            else:
                # Simple item: "- value"
                items.append(_parse_scalar(item_content))

        elif current_dict is not None and ":" in stripped:
            # Continuation of a dict item (indented key: value)
            k, _, v = stripped.partition(":")
            current_dict[k.strip()] = _parse_scalar(v.strip())

    # Flush last dict
    if current_dict is not None:
        items.append(current_dict)

    return items


def _serialize_frontmatter(fm: dict) -> str:
    """Serialize a dict back to YAML frontmatter string (between --- markers).

    Handles scalars, inline lists, block lists-of-dicts, and nested dicts.
    """
    lines: list[str] = []

    for key, val in fm.items():
        if val is None or val == "":
            lines.append(f"{key}: \"\"")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, (int, float)):
            lines.append(f"{key}: {val}")
        elif isinstance(val, str):
            # Quote strings that contain special chars
            if any(c in val for c in ":#{}[]&*!|>',\""):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
        elif isinstance(val, list):
            if not val:
                lines.append(f"{key}: []")
            elif all(isinstance(x, (str, int, float, bool)) for x in val):
                # Short inline list for simple items
                formatted = ", ".join(
                    f'"{x}"' if isinstance(x, str) and any(c in x for c in ":#,[]") else str(x)
                    for x in val
                )
                lines.append(f"{key}: [{formatted}]")
            else:
                # List of dicts — block form
                lines.append(f"{key}:")
                for item in val:
                    if isinstance(item, dict):
                        first = True
                        for dk, dv in item.items():
                            prefix = "  - " if first else "    "
                            first = False
                            if isinstance(dv, str) and any(c in dv for c in ":#{}[]"):
                                lines.append(f'{prefix}{dk}: "{dv}"')
                            else:
                                lines.append(f"{prefix}{dk}: {dv}")
                    else:
                        lines.append(f"  - {item}")
        elif isinstance(val, dict):
            lines.append(f"{key}:")
            for dk, dv in val.items():
                if isinstance(dv, str) and any(c in dv for c in ":#{}[]"):
                    lines.append(f'  {dk}: "{dv}"')
                else:
                    lines.append(f"  {dk}: {dv}")

    return "\n".join(lines) + "\n"


def _update_frontmatter_field(content: str, field: str, value,
                               append: bool = False) -> tuple[str, str, str]:
    """Update a single field in a file's frontmatter text.

    Returns ``(new_content, old_value_str, new_value_str)``.
    Raises ``ValueError`` if frontmatter or field not found.
    """
    m = FRONTMATTER_RE.match(content)
    if not m:
        raise ValueError("No frontmatter found")

    fm_text = m.group(1)
    after_fm = content[m.end():]

    # Parse existing frontmatter
    fm = _parse_yaml_block(fm_text)

    if field not in fm and not append:
        raise ValueError(f"Field '{field}' not found in frontmatter")

    old_val = fm.get(field, "")
    old_str = json.dumps(old_val, ensure_ascii=False) if not isinstance(old_val, str) else old_val

    if append:
        # Append to list field
        existing = fm.get(field, [])
        if isinstance(existing, list):
            if value not in existing:
                existing.append(value)
        elif isinstance(existing, str) and existing:
            existing = [existing, value]
        else:
            existing = [value]
        fm[field] = existing
    else:
        fm[field] = value

    new_val = fm[field]
    new_str = json.dumps(new_val, ensure_ascii=False) if not isinstance(new_val, str) else new_val

    # Rebuild file
    new_fm_text = _serialize_frontmatter(fm)
    new_content = f"---\n{new_fm_text}---{after_fm}"

    return new_content, old_str, new_str


# ---------------------------------------------------------------------------
# Frontmatter CLI commands
# ---------------------------------------------------------------------------

def read_meta(path: str, field: str | None = None) -> None:
    """Read frontmatter from a wiki page, output as JSON."""
    p = Path(path)
    if not p.exists():
        print(json.dumps({"status": "error", "message": f"File not found: {path}"}))
        sys.exit(1)

    fm = _parse_frontmatter(p)
    if not fm:
        print(json.dumps({"status": "error", "message": "No frontmatter found"}))
        sys.exit(1)

    if field is None:
        print(json.dumps(fm, ensure_ascii=False, indent=2))
    else:
        if field not in fm:
            print(json.dumps({"status": "error",
                              "message": f"Field '{field}' not in frontmatter"}))
            sys.exit(1)
        val = fm[field]
        print(json.dumps(val, ensure_ascii=False))


def set_meta(path: str, field: str, value: str, append: bool = False) -> None:
    """Set a frontmatter field value in a wiki page."""
    p = Path(path)
    if not p.exists():
        print(json.dumps({"status": "error", "message": f"File not found: {path}"}))
        sys.exit(1)

    content = p.read_text(encoding="utf-8")

    # Parse the value string into appropriate Python type
    parsed_value = _parse_scalar(value)

    try:
        if append:
            # For append, value is always treated as a string to add to a list
            new_content, old_str, new_str = _update_frontmatter_field(
                content, field, value, append=True)
        else:
            new_content, old_str, new_str = _update_frontmatter_field(
                content, field, parsed_value, append=False)
    except ValueError as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

    # Atomic write via temp file + replace.
    # Path.rename() raises FileExistsError on Windows when the target
    # exists (which is always, for set-meta). Path.replace() is atomic
    # on POSIX and overwrites on Windows — works on both.
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(new_content, encoding="utf-8")
        tmp.replace(p)
    finally:
        if tmp.exists():
            tmp.unlink()

    result = {"status": "ok", "field": field, "old": old_str, "new": new_str}
    if append:
        result["action"] = "append"
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
# Checkpoint management (for resumable batch operations)
# ---------------------------------------------------------------------------

def _checkpoint_path(wiki_root: str, task_id: str) -> Path:
    return Path(wiki_root) / ".checkpoints" / f"{task_id}.json"


def _checkpoint_read(wiki_root: str, task_id: str, strict: bool = False) -> dict:
    """Load a checkpoint file and normalize it to the current schema.

    Backward-compat: old checkpoints written before the `metadata` field existed
    load cleanly — the missing key is filled with an empty dict on next write.

    strict=False (default, used by writers like checkpoint_save / checkpoint_set_meta):
        Corrupt files are silently treated as empty so the next write repairs them.
        A non-dict top-level JSON (e.g. `[]` or `"null"`) is also ignored.
    strict=True (used by checkpoint_load):
        Re-raises json.JSONDecodeError and raises ValueError on non-dict top-level JSON.
        Lets checkpoint_load surface an explicit corruption report to the caller.
    """
    cp_file = _checkpoint_path(wiki_root, task_id)
    data = {"task_id": task_id, "completed": [], "failed": [], "metadata": {}}
    _PARSE_FAILED = object()  # sentinel: distinguishes parse-failed from parsed-to-None
    if cp_file.exists():
        try:
            loaded = json.loads(cp_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            if strict:
                raise
            loaded = _PARSE_FAILED
        if isinstance(loaded, dict):
            data.update(loaded)
        elif loaded is not _PARSE_FAILED and strict:
            # loaded parsed successfully but is not a dict (e.g. null, [], "str", 42)
            raise ValueError("checkpoint top-level JSON is not an object")
    data.setdefault("completed", [])
    data.setdefault("failed", [])
    data.setdefault("metadata", {})
    if not isinstance(data["metadata"], dict):
        data["metadata"] = {}
    return data


def _checkpoint_write(wiki_root: str, task_id: str, data: dict) -> None:
    cp_dir = Path(wiki_root) / ".checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    cp_file = cp_dir / f"{task_id}.json"
    cp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def checkpoint_save(wiki_root: str, task_id: str, item: str,
                    status: str = "completed") -> None:
    """Record an item as completed/failed in a checkpoint file."""
    data = _checkpoint_read(wiki_root, task_id)

    target_list = "completed" if status == "completed" else "failed"
    if item not in data[target_list]:
        data[target_list].append(item)

    _checkpoint_write(wiki_root, task_id, data)
    print(json.dumps({"status": "ok", "task_id": task_id,
                      "item": item, "item_status": status}))


def checkpoint_set_meta(wiki_root: str, task_id: str, key: str, value: str) -> None:
    """Persist a key/value pair in the checkpoint's metadata dict.

    Creates the checkpoint file if it does not exist. Preserves the existing
    completed/failed lists. Designed for small pieces of cross-step state
    like the `/init` stash ref that must survive an interrupted run.
    """
    data = _checkpoint_read(wiki_root, task_id)
    data["metadata"][key] = value
    _checkpoint_write(wiki_root, task_id, data)
    print(json.dumps({"status": "ok", "task_id": task_id,
                      "key": key, "value": value}))


def checkpoint_get_meta(wiki_root: str, task_id: str, key: str = "") -> None:
    """Read a metadata value (by key) or the whole metadata dict (if key is empty).

    - With a key: prints the raw value (empty string if missing). Exit code 0 either way.
    - Without a key: prints the metadata dict as JSON.
    Useful for bash capture via `$(...)` — a missing key prints nothing, so
    callers can safely `[ -n "$x" ]` to check.
    """
    data = _checkpoint_read(wiki_root, task_id)
    meta = data.get("metadata", {})
    if key:
        value = meta.get(key, "")
        # Print a raw value (no JSON wrapping) so shell capture is clean.
        print(value)
    else:
        print(json.dumps(meta, ensure_ascii=False))


def checkpoint_load(wiki_root: str, task_id: str) -> None:
    """Load checkpoint state for a task. Returns JSON with completed/failed/metadata.

    A missing file reports `exists: false` with empty lists/dict.
    A corrupt or non-dict file reports `exists: false` with `error: "corrupt checkpoint"`
    — the writers (checkpoint_save / checkpoint_set_meta) will silently repair it on
    the next write, but the read path surfaces the corruption so tooling can flag it.
    """
    cp_file = _checkpoint_path(wiki_root, task_id)

    if not cp_file.exists():
        print(json.dumps({"task_id": task_id, "completed": [], "failed": [],
                          "metadata": {}, "exists": False}))
        return

    try:
        data = _checkpoint_read(wiki_root, task_id, strict=True)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"task_id": task_id, "completed": [], "failed": [],
                          "metadata": {}, "exists": False,
                          "error": "corrupt checkpoint"}))
        return

    data["exists"] = True
    print(json.dumps(data))


def checkpoint_clear(wiki_root: str, task_id: str) -> None:
    """Remove a checkpoint file."""
    root = Path(wiki_root)
    cp_file = root / ".checkpoints" / f"{task_id}.json"
    if cp_file.exists():
        cp_file.unlink()
    print(json.dumps({"status": "ok", "task_id": task_id, "cleared": True}))


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="OmegaWiki — core graph operations and utilities")
    sub = parser.add_subparsers(dest="command")

    # init
    p = sub.add_parser("init", help="Initialize wiki directory structure")
    p.add_argument("wiki_root", help="Path to wiki/ directory")

    # slug
    p = sub.add_parser("slug", help="Generate kebab-case slug from title")
    p.add_argument("title", help="Paper or concept title")

    # add-edge
    p = sub.add_parser("add-edge", help="Add typed edge to graph")
    p.add_argument("wiki_root")
    p.add_argument("--from", dest="from_id", required=True)
    p.add_argument("--to", dest="to_id", required=True)
    p.add_argument("--type", dest="edge_type", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--confidence", default="",
                   choices=["", *sorted(EDGE_CONFIDENCE_VALUES)])
    p.add_argument("--symmetric", action="store_true")

    # add-citation
    p = sub.add_parser("add-citation", help="Add paper citation to graph/citations.jsonl")
    p.add_argument("wiki_root")
    p.add_argument("--from", dest="from_id", required=True)
    p.add_argument("--to", dest="to_id", required=True)
    p.add_argument("--source", default="semantic_scholar",
                   choices=sorted(CITATION_SOURCES))

    # add-citations-batch
    p = sub.add_parser("add-citations-batch",
                       help="Batch append cites rows from stdin (JSON array of "
                            "S2 reference objects); matches by arxiv/s2_id and "
                            "skips duplicates")
    p.add_argument("wiki_root")
    p.add_argument("--citer", dest="citer_id", required=True,
                   help="papers/<slug> of the citing paper")

    # rebuild-context-brief
    p = sub.add_parser("rebuild-context-brief", help="Regenerate context_brief.md")
    p.add_argument("wiki_root")
    p.add_argument("--max-chars", type=int, default=8000)

    # rebuild-open-questions
    p = sub.add_parser("rebuild-open-questions", help="Regenerate open_questions.md")
    p.add_argument("wiki_root")

    # rebuild-projected-edges
    p = sub.add_parser("rebuild-projected-edges",
                       help="Project frontmatter link/list_link/list_object "
                            "fields into graph/projected_edges.jsonl "
                            "(idempotent, overwrite)")
    p.add_argument("wiki_root")

    # stats
    p = sub.add_parser("stats", help="Print wiki statistics")
    p.add_argument("wiki_root")
    p.add_argument("--json", action="store_true")

    # maturity
    p = sub.add_parser("maturity",
                        help="Assess wiki maturity level (cold/warm/hot)")
    p.add_argument("wiki_root")
    p.add_argument("--json", action="store_true")

    # log
    p = sub.add_parser("log", help="Append audit log entry")
    p.add_argument("wiki_root")
    p.add_argument("message")

    # read-meta
    p = sub.add_parser("read-meta", help="Read frontmatter field(s) as JSON")
    p.add_argument("path", help="Path to .md file")
    p.add_argument("field", nargs="?", default=None, help="Specific field (omit for all)")

    # set-meta
    p = sub.add_parser("set-meta", help="Set a frontmatter field")
    p.add_argument("path")
    p.add_argument("field")
    p.add_argument("value")
    p.add_argument("--append", action="store_true",
                   help="Append value to a list field instead of replacing")

    # find
    p = sub.add_parser("find", help="Search entities by frontmatter fields")
    p.add_argument("wiki_root")
    p.add_argument("entity_type", choices=ENTITY_DIRS)

    # find-similar-concept
    p = sub.add_parser("find-similar-concept",
                       help="Detect existing concepts/foundations that semantically overlap with a candidate (call this BEFORE creating a new concept page)")
    p.add_argument("wiki_root")
    p.add_argument("title", help="Candidate concept title")
    p.add_argument("--aliases", default="",
                   help="Comma-separated list of candidate aliases / alternative names")

    # query
    p = sub.add_parser("query", help="Cross-entity knowledge queries")
    p.add_argument("wiki_root")
    p.add_argument("subquery",
                   choices=["ready-to-test", "orphans"])
    p.add_argument("slug", nargs="?", help="Reserved for future per-entity queries")

    # neighbors
    p = sub.add_parser("neighbors", help="Graph neighborhood traversal")
    p.add_argument("wiki_root")
    p.add_argument("node_id", help="Node ID (e.g. papers/lora)")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--edge-type", default=None,
                   help="Comma-separated edge types to filter")
    direction = p.add_mutually_exclusive_group()
    direction.add_argument("--incoming", action="store_true")
    direction.add_argument("--outgoing", action="store_true")

    # compile-context
    p = sub.add_parser("compile-context",
                       help="Generate purpose-specific context")
    p.add_argument("wiki_root")
    p.add_argument("--for", dest="purpose", required=True,
                   choices=list(CONTEXT_BUDGETS.keys()))
    p.add_argument("--max-chars", type=int, default=8000)

    # transition
    p = sub.add_parser("transition", help="Transition entity lifecycle status")
    p.add_argument("path")
    p.add_argument("--to", dest="new_status", required=True)
    p.add_argument("--reason", default="")

    # batch-edges
    p = sub.add_parser("batch-edges", help="Create edges from stdin JSON array")
    p.add_argument("wiki_root")

    # dedup-edges
    p = sub.add_parser("dedup-edges",
                       help="Deduplicate edges.jsonl after parallel ingest merge")
    p.add_argument("wiki_root")

    # dedup-citations
    p = sub.add_parser("dedup-citations",
                       help="Deduplicate citations.jsonl by paper pair")
    p.add_argument("wiki_root")

    # rebuild-index
    p = sub.add_parser("rebuild-index", help="Regenerate index.md from entity dirs")
    p.add_argument("wiki_root")

    # topic-backfill
    p = sub.add_parser("topic-backfill",
                       help="Append matching papers to topic seminal_works / SOTA tracker (post-merge sweep for /init)")
    p.add_argument("wiki_root")

    # checkpoint-save
    p = sub.add_parser("checkpoint-save", help="Save item to batch checkpoint")
    p.add_argument("wiki_root")
    p.add_argument("task_id", help="Unique task identifier (e.g. init-2026-04-09)")
    p.add_argument("item", help="Item identifier (e.g. paper filename or slug)")
    p.add_argument("--failed", action="store_true", help="Mark item as failed instead of completed")

    # checkpoint-load
    p = sub.add_parser("checkpoint-load", help="Load batch checkpoint state")
    p.add_argument("wiki_root")
    p.add_argument("task_id")

    # checkpoint-clear
    p = sub.add_parser("checkpoint-clear", help="Remove a batch checkpoint")
    p.add_argument("wiki_root")
    p.add_argument("task_id")

    # checkpoint-set-meta
    p = sub.add_parser("checkpoint-set-meta",
                       help="Persist a key/value pair in checkpoint metadata")
    p.add_argument("wiki_root")
    p.add_argument("task_id")
    p.add_argument("key")
    p.add_argument("value")

    # checkpoint-get-meta
    p = sub.add_parser("checkpoint-get-meta",
                       help="Read a metadata value (raw) or the whole metadata dict (JSON)")
    p.add_argument("wiki_root")
    p.add_argument("task_id")
    p.add_argument("key", nargs="?", default="",
                   help="If given, print the raw value; otherwise print the whole metadata dict as JSON")

    # SciEvolve shared spine
    p = sub.add_parser("scievolve-init",
                       help="Initialize the proposal-first SciEvolve store")
    p.add_argument("wiki_root")

    p = sub.add_parser("scievolve-record-signal",
                       help="Record a user/task/open-environment signal for SciEvolve")
    p.add_argument("wiki_root")
    p.add_argument("--source", required=True,
                   choices=SCIEVOLVE_SOURCE_VALUES)
    p.add_argument("--dimension", required=True,
                   choices=SCIEVOLVE_DIMENSION_VALUES)
    p.add_argument("--target", default="",
                   help="Entity slug, skill name, DAG/template name, or other target")
    p.add_argument("--kind", required=True,
                   help="Signal kind, e.g. correction, failure, warning, success, cost")
    p.add_argument("--summary", required=True,
                   help="Short human-readable signal summary")
    p.add_argument("--evidence-path", default="",
                   help="Optional path to supporting evidence")
    p.add_argument("--evidence-text", default="",
                   help="Optional short evidence text")
    p.add_argument("--confidence", default="medium",
                   choices=SCIEVOLVE_CONFIDENCE_VALUES)
    p.add_argument("--severity", default="info",
                   choices=SCIEVOLVE_SEVERITY_VALUES)

    p = sub.add_parser("scievolve-report",
                       help="Generate a dry-run SciEvolve summary and optional proposals")
    p.add_argument("wiki_root")
    p.add_argument("--dimension", default="",
                   help="Optional filter: memory, workflow, or orchestration")
    p.add_argument("--target", default="")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--propose", action="store_true",
                   help="Write proposal artifacts for matching signal groups")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("dream",
                       help="Prepare and finalize agent-first /dream memory evolution")
    p.add_argument("wiki_root")
    p.add_argument("--max-entities", type=int, default=120,
                   help="Maximum entity pages to include in the agent context")
    p.add_argument("--max-signals", type=int, default=30,
                   help="Maximum recent memory signals to include")
    p.add_argument("--max-candidates", type=int, default=30,
                   help="Maximum deterministic memory cues to include")
    p.add_argument("--agent-response", default="",
                   help="Path to strict JSON returned by the /dream agent")
    p.add_argument("--use-llm", action="store_true",
                   help="Call an OpenAI-compatible LLM using LLM_* environment variables")
    p.add_argument("--propose-only", action="store_true",
                   help="Write proposal artifacts but do not auto-apply mutations")
    p.add_argument("--apply-safe", action="store_true",
                   help="Legacy alias; auto-apply is now the default when agent-response is provided")
    p.add_argument("--yolo", action="store_true",
                   help="High-confidence proposals may merge page bodies or archive pages")
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("forge",
                       help="Prepare and finalize agent-first /forge workflow evolution")
    p.add_argument("wiki_root")
    p.add_argument("--target-skill", default="",
                   help="Focus on a specific skill; default all workflow-signaled skills")
    p.add_argument("--max-signals", type=int, default=20,
                   help="Maximum recent workflow signals to include")
    p.add_argument("--agent-response", default="",
                   help="Path to strict JSON returned by the /forge agent")
    p.add_argument("--use-llm", action="store_true",
                   help="Call an OpenAI-compatible LLM using LLM_* environment variables")
    p.add_argument("--auto-apply", action="store_true",
                   help="Auto-apply additive safe workflow mutations (default is propose-only)")
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        init_wiki(args.wiki_root)
    elif args.command == "slug":
        print(slugify(args.title))
    elif args.command == "add-edge":
        add_edge(args.wiki_root, args.from_id, args.to_id,
                 args.edge_type, args.evidence, args.confidence,
                 args.symmetric)
    elif args.command == "add-citation":
        add_citation(args.wiki_root, args.from_id, args.to_id, args.source)
    elif args.command == "add-citations-batch":
        add_citations_batch(args.wiki_root, args.citer_id)
    elif args.command == "rebuild-context-brief":
        rebuild_context_brief(args.wiki_root, args.max_chars)
    elif args.command == "rebuild-open-questions":
        rebuild_open_questions(args.wiki_root)
    elif args.command == "rebuild-projected-edges":
        rebuild_projected_edges(args.wiki_root)
    elif args.command == "stats":
        get_stats(args.wiki_root, as_json=args.json)
    elif args.command == "maturity":
        get_maturity(args.wiki_root, as_json=args.json)
    elif args.command == "log":
        append_log(args.wiki_root, args.message)
    elif args.command == "read-meta":
        read_meta(args.path, args.field)
    elif args.command == "set-meta":
        set_meta(args.path, args.field, args.value, args.append)
    elif args.command == "find":
        # Parse remaining args as --field value pairs
        filters: list[tuple[str, str]] = []
        remaining = sys.argv[sys.argv.index("find") + 3:]  # skip find, wiki_root, entity_type
        it = iter(remaining)
        for arg in it:
            if arg.startswith("--"):
                field_name = arg[2:]
                try:
                    val = next(it)
                except StopIteration:
                    break
                filters.append((field_name, val))
        find_entities(args.wiki_root, args.entity_type, filters)
    elif args.command == "find-similar-concept":
        aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
        find_similar_concept(args.wiki_root, args.title, aliases)
    elif args.command == "query":
        if args.subquery == "ready-to-test":
            query_ready_to_test(args.wiki_root)
        elif args.subquery == "orphans":
            query_orphans(args.wiki_root)
    elif args.command == "neighbors":
        edge_type_list = (args.edge_type.split(",")
                          if args.edge_type else None)
        direction = ("incoming" if args.incoming
                     else "outgoing" if args.outgoing
                     else "both")
        neighbors(args.wiki_root, args.node_id, args.depth,
                  edge_type_list, direction)
    elif args.command == "compile-context":
        compile_context(args.wiki_root, args.purpose, args.max_chars)
    elif args.command == "transition":
        transition(args.path, args.new_status, args.reason)
    elif args.command == "batch-edges":
        batch_edges(args.wiki_root)
    elif args.command == "dedup-edges":
        dedup_edges(args.wiki_root)
    elif args.command == "dedup-citations":
        dedup_citations(args.wiki_root)
    elif args.command == "rebuild-index":
        rebuild_index(args.wiki_root)
    elif args.command == "topic-backfill":
        topic_backfill(args.wiki_root)
    elif args.command == "checkpoint-save":
        checkpoint_save(args.wiki_root, args.task_id, args.item,
                        status="failed" if args.failed else "completed")
    elif args.command == "checkpoint-load":
        checkpoint_load(args.wiki_root, args.task_id)
    elif args.command == "checkpoint-clear":
        checkpoint_clear(args.wiki_root, args.task_id)
    elif args.command == "checkpoint-set-meta":
        checkpoint_set_meta(args.wiki_root, args.task_id, args.key, args.value)
    elif args.command == "checkpoint-get-meta":
        checkpoint_get_meta(args.wiki_root, args.task_id, args.key)
    elif args.command == "scievolve-init":
        scievolve_init(args.wiki_root)
    elif args.command == "scievolve-record-signal":
        scievolve_record_signal(
            args.wiki_root,
            args.source,
            args.dimension,
            args.target,
            args.kind,
            args.summary,
            args.evidence_path,
            args.evidence_text,
            args.confidence,
            args.severity,
        )
    elif args.command == "scievolve-report":
        scievolve_report(
            args.wiki_root,
            args.dimension,
            args.target,
            args.limit,
            args.propose,
            args.json,
        )
    elif args.command == "dream":
        dream(
            args.wiki_root,
            max_entities=args.max_entities,
            max_signals=args.max_signals,
            max_candidates=args.max_candidates,
            agent_response=args.agent_response,
            use_llm=args.use_llm,
            propose=True,
            apply_safe=not args.propose_only,
            propose_only=args.propose_only,
            yolo=args.yolo,
            as_json=args.json,
            timeout=args.timeout,
            temperature=args.temperature,
        )
    elif args.command == "forge":
        forge(
            args.wiki_root,
            target_skill=args.target_skill,
            max_signals=args.max_signals,
            agent_response=args.agent_response,
            use_llm=args.use_llm,
            propose=True,
            auto_apply=args.auto_apply,
            as_json=args.json,
            timeout=args.timeout,
            temperature=args.temperature,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
