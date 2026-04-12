#!/usr/bin/env python3
"""Typed Knowledge Graph Layer for ΩmegaWiki.

CLI tool for managing a JSONL-based knowledge graph over wiki pages.
Supplements the graph commands in research_wiki.py with standalone
traversal, seeding, and orphan detection.

Commands:
    add-edge    Append an edge to edges.jsonl (dedup on from,to,type)
    neighbors   BFS traversal from a node
    find-contradictions  Return all contradiction edges
    orphans     Find wiki pages with zero edges
    seed        Walk wiki files and extract wikilinks as edges
    stats       Print edge/node counts

Usage:
    python3 tools/wiki_graph.py <wiki_root> add-edge --from X --to Y --type T --evidence "reason"
    python3 tools/wiki_graph.py <wiki_root> neighbors papers/attention --depth 2 --type supports
    python3 tools/wiki_graph.py <wiki_root> find-contradictions
    python3 tools/wiki_graph.py <wiki_root> orphans
    python3 tools/wiki_graph.py <wiki_root> seed
    python3 tools/wiki_graph.py <wiki_root> stats

Python 3.9+, no external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from _schemas import ENTITY_DIRS, VALID_EDGE_TYPES

# ---------------------------------------------------------------------------
# Edge I/O
# ---------------------------------------------------------------------------

def _edges_file(wiki_root: Path) -> Path:
    return wiki_root / "graph" / "edges.jsonl"


def load_edges(wiki_root: Path) -> list[dict]:
    """Load all edges from the JSONL file."""
    path = _edges_file(wiki_root)
    edges: list[dict] = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    edges.append(json.loads(line))
    return edges


def save_edge(wiki_root: Path, edge: dict) -> None:
    """Append a single edge to the JSONL file."""
    path = _edges_file(wiki_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(edge, ensure_ascii=False) + "\n")


def edge_key(edge: dict) -> tuple:
    return (edge["from"], edge["to"], edge["type"])


def load_existing_keys(wiki_root: Path) -> set:
    """Return set of (from, to, type) tuples for dedup."""
    return {edge_key(e) for e in load_edges(wiki_root)}


# ---------------------------------------------------------------------------
# Slug resolution
# ---------------------------------------------------------------------------

def resolve_slug(slug: str, wiki_root: Path) -> str | None:
    """Given a bare slug like 'attention', find its canonical relative path
    (e.g., 'concepts/attention'). Returns None if not found."""
    if "/" in slug:
        candidate = wiki_root / (slug + ".md")
        if candidate.exists():
            return slug
        candidate = wiki_root / slug
        if candidate.exists():
            return slug.replace(".md", "")
        return None

    # Search across entity directories
    for subdir_name in ENTITY_DIRS:
        subdir = wiki_root / subdir_name
        if not subdir.is_dir():
            continue
        candidate = subdir / (slug + ".md")
        if candidate.exists():
            return f"{subdir_name}/{slug}"

    # Also check any other top-level dirs
    for subdir in wiki_root.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name == "graph":
            continue
        candidate = subdir / (slug + ".md")
        if candidate.exists():
            return f"{subdir.name}/{slug}"
    return None


def file_to_node(filepath: Path, wiki_root: Path) -> str:
    """Convert a file path to a node identifier like 'concepts/attention'."""
    rel = filepath.relative_to(wiki_root)
    return str(rel).replace("\\", "/").replace(".md", "")


# ---------------------------------------------------------------------------
# Wikilink extraction
# ---------------------------------------------------------------------------

WIKILINK_RE = re.compile(r"\[\[([^\]\|]+?)(?:\|[^\]]+?)?\]\]")

# Frontmatter relationship keys and the edge types they imply
FRONTMATTER_TYPE_MAP = {
    "related_entities": "supports",
    "related_topics": "supports",
    "related_concepts": "supports",
    "key_papers": "supports",
    "source_papers": "supports",
}


def extract_wikilinks_from_file(filepath: Path) -> list[tuple[str, str]]:
    """Extract (target_slug, edge_type) pairs from a wiki file.

    Parses both YAML frontmatter related_* fields and body [[wikilinks]].
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    links: list[tuple[str, str]] = []
    in_frontmatter = False
    frontmatter_done = False
    current_fm_key: str | None = None

    for i, line in enumerate(text.split("\n")):
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line.strip() == "---":
            in_frontmatter = False
            frontmatter_done = True
            continue

        if in_frontmatter:
            for fm_key, etype in FRONTMATTER_TYPE_MAP.items():
                if line.startswith(fm_key + ":"):
                    current_fm_key = fm_key
                    for match in WIKILINK_RE.finditer(line):
                        links.append((match.group(1).strip(), etype))
                    break
            else:
                if current_fm_key and (line.startswith("  ") or line.startswith("- ")):
                    etype = FRONTMATTER_TYPE_MAP.get(current_fm_key, "supports")
                    for match in WIKILINK_RE.finditer(line):
                        links.append((match.group(1).strip(), etype))
                else:
                    current_fm_key = None
        else:
            for match in WIKILINK_RE.finditer(line):
                links.append((match.group(1).strip(), "supports"))

    return links


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add_edge(args) -> None:
    """Add a single edge with dedup."""
    wiki_root = Path(args.wiki_root).resolve()
    if args.type not in VALID_EDGE_TYPES:
        print(f"ERROR: Invalid type '{args.type}'. Valid: {', '.join(sorted(VALID_EDGE_TYPES))}", file=sys.stderr)
        sys.exit(1)

    edge = {
        "from": args.from_node,
        "to": args.to_node,
        "type": args.type,
        "evidence": args.evidence or "",
        "date": date.today().isoformat(),
    }

    existing = load_existing_keys(wiki_root)
    key = edge_key(edge)
    if key in existing:
        print(f"SKIP (duplicate): {key}")
        return

    save_edge(wiki_root, edge)
    print(f"ADDED: {args.from_node} --[{args.type}]--> {args.to_node}")


def cmd_neighbors(args) -> None:
    """BFS traversal from a node."""
    wiki_root = Path(args.wiki_root).resolve()
    edges = load_edges(wiki_root)
    target = args.node
    depth = args.depth
    type_filter = args.type

    adj: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for e in edges:
        if type_filter and e["type"] != type_filter:
            continue
        adj[e["from"]].append((e["to"], e["type"], "->"))
        adj[e["to"]].append((e["from"], e["type"], "<-"))

    if target not in adj:
        resolved = resolve_slug(target.split("/")[-1] if "/" in target else target, wiki_root)
        if resolved and resolved in adj:
            target = resolved
        else:
            print(f"Node '{target}' not found in graph.")
            return

    visited = {target}
    queue: deque[tuple[str, int]] = deque([(target, 0)])
    results: list[tuple[str, int, str, str]] = []

    while queue:
        node, d = queue.popleft()
        if d >= depth:
            continue
        for neighbor, etype, direction in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                results.append((neighbor, d + 1, etype, direction))
                queue.append((neighbor, d + 1))

    if not results:
        print(f"No neighbors found for '{target}' within depth {depth}.")
        return

    print(f"Neighbors of '{target}' (depth {depth}):")
    for node, d, etype, direction in sorted(results, key=lambda x: (x[1], x[0])):
        print(f"  [d={d}] {node}  ({direction} {etype})")


def cmd_find_contradictions(args) -> None:
    """Return all edges where type=contradicts."""
    wiki_root = Path(args.wiki_root).resolve()
    edges = load_edges(wiki_root)
    contradictions = [e for e in edges if e["type"] == "contradicts"]

    if not contradictions:
        print("No contradictions found.")
        return

    print(f"Found {len(contradictions)} contradiction(s):")
    for e in contradictions:
        print(f"  {e['from']} <-> {e['to']}: {e.get('evidence', '')}")


def cmd_orphans(args) -> None:
    """Find wiki pages with zero edges."""
    wiki_root = Path(args.wiki_root).resolve()
    edges = load_edges(wiki_root)
    connected = set()
    for e in edges:
        connected.add(e["from"])
        connected.add(e["to"])

    all_pages = set()
    for subdir_name in ENTITY_DIRS:
        subdir = wiki_root / subdir_name
        if not subdir.is_dir():
            continue
        for md_file in subdir.rglob("*.md"):
            node = file_to_node(md_file, wiki_root)
            all_pages.add(node)

    orphans = sorted(all_pages - connected)
    if not orphans:
        print("No orphan pages found -- all pages have at least one edge.")
        return

    print(f"Found {len(orphans)} orphan page(s) with zero edges:")
    for o in orphans:
        print(f"  {o}")


def cmd_seed(args) -> None:
    """Walk wiki files and extract wikilinks as edges."""
    wiki_root = Path(args.wiki_root).resolve()
    existing_keys = load_existing_keys(wiki_root)
    added = 0
    skipped = 0

    for subdir_name in ENTITY_DIRS:
        subdir = wiki_root / subdir_name
        if not subdir.is_dir():
            continue
        for md_file in sorted(subdir.rglob("*.md")):
            from_node = file_to_node(md_file, wiki_root)
            links = extract_wikilinks_from_file(md_file)

            for target_slug, edge_type in links:
                resolved = resolve_slug(target_slug, wiki_root)
                if resolved is None or resolved == from_node:
                    continue

                edge = {
                    "from": from_node,
                    "to": resolved,
                    "type": edge_type,
                    "evidence": f"Wikilink in {from_node}",
                    "date": date.today().isoformat(),
                }

                key = edge_key(edge)
                if key in existing_keys:
                    skipped += 1
                    continue

                existing_keys.add(key)
                save_edge(wiki_root, edge)
                added += 1

    print(f"Seeding complete: {added} edges added, {skipped} duplicates skipped.")


def cmd_stats(args) -> None:
    """Print edge and node counts."""
    wiki_root = Path(args.wiki_root).resolve()
    edges = load_edges(wiki_root)
    nodes: set[str] = set()
    type_counts: dict[str, int] = defaultdict(int)
    for e in edges:
        nodes.add(e["from"])
        nodes.add(e["to"])
        type_counts[e["type"]] += 1

    print(f"Total edges: {len(edges)}")
    print(f"Unique nodes: {len(nodes)}")
    print("Edges by type:")
    for t in sorted(type_counts):
        print(f"  {t}: {type_counts[t]}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Typed Knowledge Graph Layer for ΩmegaWiki"
    )
    parser.add_argument("wiki_root", help="Path to the wiki/ directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add-edge
    p_add = subparsers.add_parser("add-edge", help="Add an edge to the graph")
    p_add.add_argument("--from", dest="from_node", required=True, help="Source node")
    p_add.add_argument("--to", dest="to_node", required=True, help="Target node")
    p_add.add_argument("--type", required=True,
                       help=f"Edge type: {', '.join(sorted(VALID_EDGE_TYPES))}")
    p_add.add_argument("--evidence", default="", help="Evidence/reason for edge")
    p_add.set_defaults(func=cmd_add_edge)

    # neighbors
    p_nb = subparsers.add_parser("neighbors", help="BFS traversal from a node")
    p_nb.add_argument("node", help="Starting node (e.g., concepts/attention)")
    p_nb.add_argument("--depth", type=int, default=1, help="Max traversal depth (default: 1)")
    p_nb.add_argument("--type", default=None, help="Filter by edge type")
    p_nb.set_defaults(func=cmd_neighbors)

    # find-contradictions
    p_fc = subparsers.add_parser("find-contradictions", help="Find all contradiction edges")
    p_fc.set_defaults(func=cmd_find_contradictions)

    # orphans
    p_or = subparsers.add_parser("orphans", help="Find wiki pages with zero edges")
    p_or.set_defaults(func=cmd_orphans)

    # seed
    p_seed = subparsers.add_parser("seed", help="Seed edges from existing wikilinks")
    p_seed.set_defaults(func=cmd_seed)

    # stats
    p_stats = subparsers.add_parser("stats", help="Print graph statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
