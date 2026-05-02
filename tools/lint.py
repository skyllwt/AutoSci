#!/usr/bin/env python3
"""Wiki lint helper — structural checks for ΩmegaWiki.

Checks performed:
  1. Broken wikilinks: [[slug]] target file does not exist
  2. Orphan pages: pages with zero incoming links
  3. Missing required YAML frontmatter fields per entity type (all 9 types)
  4. Cross-reference asymmetry: forward link without matching reverse link
  5. Field value validation: enum values, ranges (confidence, importance, status)
  6. Claim checks: confidence range, evidence structure, status consistency
  7. Idea checks: failure_reason required when status=failed
  8. Experiment checks: target_claim required, outcome values
  9. Graph edge and citation consistency: from/to nodes exist as wiki pages

Usage:
    python3 tools/lint.py                      # lint wiki/ in current dir
    python3 tools/lint.py --wiki-dir wiki/     # specify wiki directory
    python3 tools/lint.py --json               # output as JSON
    python3 tools/lint.py --fix                # auto-fix deterministic issues
    python3 tools/lint.py --fix --dry-run      # preview fixes without applying
    python3 tools/lint.py --suggest            # output actionable suggestions for non-auto-fixable issues
"""

from __future__ import annotations

import argparse
import json as json_module
import os
import re
import sys
from pathlib import Path

# Schema API lives in runtime/loader.py — single source for both this file and
# research_wiki.py.  The 3-line bridge below makes runtime/ importable from
# tools/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime.loader import (  # noqa: E402
    CITATION_EDGE_TYPES,
    CITATION_SOURCES,
    EDGE_CONFIDENCE_VALUES,
    EDGES,
    ENTITIES,
    ENTITY_DIRS,
    FIELD_DEFAULTS,
    REQUIRED_FIELDS,
    VALID_EDGE_TYPES,
    VALID_VALUES,
    XREF,
    edge_endpoint_matches,
    edge_expected_endpoint,
    edge_is_symmetric,
    edge_is_legacy_for_endpoint,
    edge_legacy_replacement_message,
    edge_requires_confidence,
    validate_edge_attributes,
)

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class LintIssue:
    def __init__(self, level: str, category: str, file: str, message: str,
                 fixable: bool = False, suggestion: str = ""):
        self.level = level      # 🔴 🟡 🔵
        self.category = category
        self.file = file
        self.message = message
        self.fixable = fixable          # can --fix auto-repair this?
        self.suggestion = suggestion    # human-readable suggestion for non-fixable issues

    def __str__(self):
        return f"{self.level} [{self.category}] {self.file}: {self.message}"

    def to_dict(self):
        d = {
            "level": self.level,
            "category": self.category,
            "file": self.file,
            "message": self.message,
        }
        if self.fixable:
            d["fixable"] = True
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


class FixResult:
    """Records a single auto-fix that was applied (or would be applied in dry-run)."""
    def __init__(self, file: str, action: str):
        self.file = file
        self.action = action

    def __str__(self):
        return f"  ✅ {self.file}: {self.action}"

    def to_dict(self):
        return {"file": self.file, "action": self.action}


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter as dict (basic key-value parsing)."""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}
    fm = {}
    current_key = None
    in_list = False
    for line in m.group(1).split("\n"):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue
        # Detect list continuation (indented "- item")
        if in_list and stripped.startswith("- "):
            continue
        # Detect nested key (indented key: value under a parent)
        if line.startswith("  ") and ":" in stripped and current_key:
            continue
        if ":" in stripped:
            key = stripped.split(":")[0].strip()
            value = ":".join(stripped.split(":")[1:]).strip()
            fm[key] = value
            current_key = key
            in_list = value == "" or value.startswith("[")
        else:
            in_list = False
    return fm


def extract_frontmatter_value(content: str, field: str) -> str | None:
    """Extract a specific frontmatter field value as string."""
    fm = extract_frontmatter(content)
    val = fm.get(field)
    if val is None:
        return None
    # Strip quotes
    val = val.strip().strip('"').strip("'")
    return val


def find_all_pages(wiki_dir: Path) -> dict[str, Path]:
    """Map slug -> file path for all wiki pages."""
    pages = {}
    for subdir in ENTITY_DIRS:
        dir_path = wiki_dir / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob("*.md"):
            slug = f.stem
            pages[slug] = f
    return pages


def check_missing_fields(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Check required frontmatter fields for all entity types."""
    issues = []
    for slug, fpath in pages.items():
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))
        page_type = fpath.parent.name
        fm = extract_frontmatter(content)

        for field in REQUIRED_FIELDS.get(page_type, []):
            if field not in fm:
                fixable = field in FIELD_DEFAULTS.get(page_type, {})
                suggestion = ""
                if fixable:
                    suggestion = f"Add '{field}: {FIELD_DEFAULTS[page_type][field]}' to frontmatter"
                else:
                    suggestion = f"Add required field '{field}' to frontmatter (needs manual value)"
                issues.append(LintIssue("🔴", "missing-field", rel,
                                        f"Missing required field: {field}",
                                        fixable=fixable, suggestion=suggestion))
    return issues


def check_broken_links(wiki_dir: Path, pages: dict[str, Path]) -> tuple[list[LintIssue], dict[str, set]]:
    """Check wikilinks and track incoming links."""
    issues = []
    incoming: dict[str, set[str]] = {slug: set() for slug in pages}

    for slug, fpath in pages.items():
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))

        for match in WIKILINK_RE.finditer(content):
            target = match.group(1).strip()
            if target in pages:
                incoming.setdefault(target, set()).add(slug)
            else:
                issues.append(LintIssue("🟡", "broken-link", rel,
                                        f"[[{target}]] → file not found",
                                        suggestion=f"Remove [[{target}]] or create a page for it"))

    return issues, incoming


def check_orphan_pages(wiki_dir: Path, pages: dict[str, Path],
                       incoming: dict[str, set]) -> list[LintIssue]:
    """Find pages with zero incoming links.

    Foundations are NOT exempt: under correct usage every foundation should
    receive an inward link from at least one paper or concept (via /ingest
    dedup). An orphan foundation is a real signal — either /prefill seeded
    background that no paper references, or /ingest is failing to dedup
    against it. Orphan is 🔵 (informational), so this stays as a soft hint.
    """
    issues = []
    for slug, fpath in pages.items():
        if not incoming.get(slug):
            rel = str(fpath.relative_to(wiki_dir))
            issues.append(LintIssue("🔵", "orphan", rel, "No incoming links"))
    return issues


def check_field_values(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Validate enum/range field values."""
    issues = []
    for slug, fpath in pages.items():
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))
        page_type = fpath.parent.name

        # Check enum fields
        enum_checks = {
            "papers": [("importance", "papers.importance")],
            "concepts": [("maturity", "concepts.maturity")],
            "ideas": [("status", "ideas.status"), ("priority", "ideas.priority")],
            "experiments": [("status", "experiments.status"), ("outcome", "experiments.outcome")],
            "claims": [("status", "claims.status")],
            "foundations": [("status", "foundations.status")],
        }

        for field, valid_key in enum_checks.get(page_type, []):
            val = extract_frontmatter_value(content, field)
            if val is not None and val not in VALID_VALUES[valid_key]:
                issues.append(LintIssue("🔴", "invalid-value", rel,
                                        f"{field}={val!r} not in {VALID_VALUES[valid_key]}"))

        # Claim confidence range check
        if page_type == "claims":
            val = extract_frontmatter_value(content, "confidence")
            if val is not None:
                try:
                    conf = float(val)
                    if not (0.0 <= conf <= 1.0):
                        issues.append(LintIssue("🔴", "invalid-value", rel,
                                                f"confidence={conf} out of range [0.0, 1.0]"))
                except ValueError:
                    issues.append(LintIssue("🔴", "invalid-value", rel,
                                            f"confidence={val!r} is not a number"))

    return issues


def check_required_when(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Generic conditional-required check.

    Scans every entity field with a `required_when: { other_field: value }`
    declaration in entities.yaml.  Replaces the old hardcoded
    check_idea_failure_reason — adding a new conditional-required rule now
    requires only a YAML edit.
    """
    issues = []
    for slug, fpath in pages.items():
        kind = fpath.parent.name
        ent = ENTITIES.get(kind)
        if not ent:
            continue
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))
        for fname, fspec in ent['fields'].items():
            condition = fspec.get('required_when')
            if not condition:
                continue
            matches = all(
                extract_frontmatter_value(content, cf) == cv
                for cf, cv in condition.items()
            )
            if matches and not extract_frontmatter_value(content, fname):
                cond_str = ", ".join(f"{k}={v}" for k, v in condition.items())
                issues.append(LintIssue("🔴", "missing-required-when", rel,
                                        f"{fname} is required when {cond_str}"))
    return issues


def check_link_field_targets(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Verify that frontmatter `type: link` field values reference existing pages.

    Replaces the old hardcoded check_experiment_claim_link with a generic check
    over every link-typed field declared in entities.yaml.  list_link is left to
    check_broken_links which already handles [[wikilink]] syntax in lists.
    """
    issues = []
    for slug, fpath in pages.items():
        kind = fpath.parent.name
        ent = ENTITIES.get(kind)
        if not ent:
            continue
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))
        for fname, fspec in ent['fields'].items():
            if fspec.get('type') != 'link':
                continue
            target = extract_frontmatter_value(content, fname)
            if not target:
                continue
            target_kinds = fspec.get('to')
            if isinstance(target_kinds, str):
                target_kinds = [target_kinds]
            if not any((wiki_dir / k / f"{target}.md").exists() for k in target_kinds):
                issues.append(LintIssue("🟡", "broken-link-field", rel,
                                        f"{fname}={target!r} not found in {target_kinds}"))
    return issues


def _extract_list_field_slugs(content: str, field: str) -> list[str]:
    """Pull bare slugs from `field: [a, b, c]` (no [[wikilink]] brackets)."""
    out = []
    for match in re.finditer(rf"{re.escape(field)}:\s*\[(.*?)\]", content):
        for ref in re.findall(r"(\S+)", match.group(1)):
            ref = ref.strip(",").strip().strip("[]").strip()
            if ref:
                out.append(ref)
    return out


def _extract_forward_targets(content: str, forward: dict, source_slug: str,
                             source_kind: str, wiki_dir: Path) -> list[str]:
    """Return target slugs from a single forward-link declaration."""
    target_kind = forward['target']
    if 'frontmatter_field' in forward:
        field = forward['frontmatter_field']
        # link (single value) or list_link (list)
        single = extract_frontmatter_value(content, field)
        if single and (wiki_dir / target_kind / f"{single}.md").exists():
            return [single]
        return _extract_list_field_slugs(content, field)
    if 'body_section' in forward:
        sect = forward['body_section']
        # body wikilinks; '*' = any body section
        targets = []
        for match in WIKILINK_RE.finditer(content):
            t = match.group(1).strip()
            if (wiki_dir / target_kind / f"{t}.md").exists():
                targets.append(t)
        return targets
    if 'edge_type' in forward:
        edge_type = forward['edge_type']
        edges_path = wiki_dir / 'graph' / 'edges.jsonl'
        if not edges_path.exists():
            return []
        targets = []
        source_id = f"{source_kind}/{source_slug}"
        for line in edges_path.read_text().split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                e = json_module.loads(line)
            except json_module.JSONDecodeError:
                continue
            if e.get('type') != edge_type or e.get('from') != source_id:
                continue
            to = str(e.get('to', ''))
            if '/' in to:
                targets.append(to.split('/', 1)[1])
        return targets
    return []


def _has_reverse(target_path: Path, source_slug: str, reverse: dict) -> bool:
    """Check whether the target page records the reverse reference back to source."""
    content = target_path.read_text(encoding="utf-8")
    # Both append_slug and append_record reduce to "source slug appears somewhere
    # in the target field/section".  The structured-record case (claims.evidence)
    # checks the source_slug substring rather than parsing the YAML list of objects.
    if 'frontmatter_field' in reverse:
        field = reverse['frontmatter_field']
        # Check field's flow-style list, or value, contains source_slug
        for match in re.finditer(rf"{re.escape(field)}:\s*\[(.*?)\]", content,
                                 flags=re.DOTALL):
            if source_slug in match.group(1):
                return True
        # Or block-style: scan section starting with `field:`
        m = re.search(rf"^{re.escape(field)}:\s*$\n((?:[ -].*\n?)+)",
                      content, flags=re.MULTILINE)
        if m and source_slug in m.group(1):
            return True
        # Or single-value field
        val = extract_frontmatter_value(content, field)
        return bool(val) and source_slug in val
    if 'body_section' in reverse:
        sect = reverse['body_section']
        # Find `## sect` block
        pat = rf"^##\s+{re.escape(sect)}\s*$\n(.*?)(?=^##\s|\Z)"
        m = re.search(pat, content, flags=re.MULTILINE | re.DOTALL)
        if not m:
            return False
        body = m.group(1)
        return f"[[{source_slug}]]" in body or f"[[{source_slug}|" in body \
               or source_slug in body
    return True   # unknown reverse spec — don't flag


def _describe_reverse(reverse: dict) -> str:
    if 'frontmatter_field' in reverse:
        return f"frontmatter `{reverse['frontmatter_field']}`"
    if 'body_section' in reverse:
        return f"body section `## {reverse['body_section']}`"
    return "<unknown>"


def check_xref_asymmetry(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Generic forward → reverse link checker.

    Reads runtime/schema/xref.yaml and walks every rule.  Each rule maps a
    forward link source (frontmatter field, body section, or graph edge) to a
    required reverse update on the target.  Adding a new xref rule requires
    only a YAML edit.

    Foundations are exempt (declared in xref.yaml::terminal_targets).
    """
    issues = []
    rules = XREF.get('rules', [])
    terminal = set(XREF.get('terminal_targets', []))

    for rule in rules:
        forward = rule['forward']
        reverse = rule['reverse']
        target_kind = forward['target']
        if target_kind in terminal:
            continue
        forward_kind = forward['kind']

        for slug, fpath in pages.items():
            if fpath.parent.name != forward_kind:
                continue
            content = fpath.read_text(encoding="utf-8")
            rel = str(fpath.relative_to(wiki_dir))
            for target_slug in _extract_forward_targets(
                    content, forward, slug, forward_kind, wiki_dir):
                target_path = wiki_dir / target_kind / f"{target_slug}.md"
                if not target_path.exists():
                    continue
                if not _has_reverse(target_path, slug, reverse):
                    issues.append(LintIssue(
                        "🟡", "xref-asymmetry", rel,
                        f"{forward_kind}/{slug} → {target_kind}/{target_slug} "
                        f"forward link exists but reverse {_describe_reverse(reverse)} "
                        f"missing",
                        fixable=True))
    return issues


def _node_kind(node_id: str) -> str:
    return node_id.split("/", 1)[0] if "/" in node_id else ""


def _check_graph_node_exists(wiki_dir: Path, node_id: str,
                             file_label: str, line_num: int,
                             endpoint: str) -> LintIssue | None:
    if "/" not in node_id:
        return None
    entity_dir, node_slug = node_id.split("/", 1)
    node_path = wiki_dir / entity_dir / f"{node_slug}.md"
    if not node_path.exists():
        return LintIssue("🟡", "dangling-edge", f"{file_label}:{line_num}",
                         f"{endpoint}={node_id!r} but file not found")
    return None


def check_graph_edges(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Check graph/edges.jsonl for consistency."""
    issues = []
    edges_path = wiki_dir / "graph" / "edges.jsonl"
    if not edges_path.exists():
        return issues

    valid_types = VALID_EDGE_TYPES
    text = edges_path.read_text(encoding="utf-8")
    if not text.strip():
        return issues

    line_num = 0
    for line in text.split("\n"):
        line_num += 1
        line = line.strip()
        if not line:
            continue
        try:
            edge = json_module.loads(line)
        except json_module.JSONDecodeError:
            issues.append(LintIssue("🔴", "invalid-edge", f"graph/edges.jsonl:{line_num}",
                                    "Invalid JSON"))
            continue

        for field in ("from", "to", "type"):
            if field not in edge:
                issues.append(LintIssue("🔴", "invalid-edge", f"graph/edges.jsonl:{line_num}",
                                        f"Missing required field: {field}"))

        edge_type = edge.get("type", "")
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        from_kind = _node_kind(str(from_id))
        to_kind = _node_kind(str(to_id))

        if "type" in edge and edge_type not in valid_types:
            issues.append(LintIssue("🟡", "unknown-edge-type", f"graph/edges.jsonl:{line_num}",
                                    f"Unknown edge type: {edge_type}"))
        elif edge_type:
            # Endpoint-aware semantic edge checks. Legacy edge types stay readable
            # but get migration warnings on old /ingest-shaped endpoints.
            if not edge_endpoint_matches(edge_type, from_kind, to_kind):
                expected_from = edge_expected_endpoint(edge_type, "from")
                expected_to = edge_expected_endpoint(edge_type, "to")
                issues.append(LintIssue("🟡", "invalid-edge-endpoint",
                                        f"graph/edges.jsonl:{line_num}",
                                        f"{edge_type} should connect {expected_from}/* -> {expected_to}/*"))
            if (edge_expected_endpoint(edge_type, "from") == "papers"
                    and edge_expected_endpoint(edge_type, "to") == "papers"
                    and str(from_id) == str(to_id)):
                issues.append(LintIssue("🟡", "self-edge",
                                        f"graph/edges.jsonl:{line_num}",
                                        f"{edge_type} should not connect a paper to itself"))
            if edge_is_symmetric(edge_type):
                if edge.get("symmetric") is not True:
                    issues.append(LintIssue("🟡", "missing-symmetric-marker",
                                            f"graph/edges.jsonl:{line_num}",
                                            f"{edge_type} should include symmetric: true"))
                if str(from_id) > str(to_id):
                    issues.append(LintIssue("🟡", "noncanonical-symmetric-edge",
                                            f"graph/edges.jsonl:{line_num}",
                                            "symmetric paper edge endpoints should be sorted"))
            # Generic attribute validation, driven by edges.yaml::attributes.
            for err in validate_edge_attributes(edge_type, edge):
                issues.append(LintIssue("🟡", "edge-attribute",
                                        f"graph/edges.jsonl:{line_num}", err))

            if edge_is_legacy_for_endpoint(edge_type, from_kind, to_kind):
                issues.append(LintIssue("🟡", "legacy-edge-type",
                                        f"graph/edges.jsonl:{line_num}",
                                        edge_legacy_replacement_message(
                                            edge_type, from_kind, to_kind
                                        )))

        # Check from/to nodes exist (strip directory prefix for slug lookup)
        for endpoint in ("from", "to"):
            if endpoint not in edge:
                continue
            node_id = edge[endpoint]
            issue = _check_graph_node_exists(
                wiki_dir, str(node_id), "graph/edges.jsonl", line_num, endpoint
            )
            if issue:
                issues.append(issue)

    return issues


def check_graph_citations(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Check graph/citations.jsonl for bibliographic citation consistency."""
    issues = []
    citations_path = wiki_dir / "graph" / "citations.jsonl"
    if not citations_path.exists():
        return issues

    text = citations_path.read_text(encoding="utf-8")
    if not text.strip():
        return issues

    line_num = 0
    seen: set[tuple[str, str]] = set()
    for line in text.split("\n"):
        line_num += 1
        line = line.strip()
        if not line:
            continue
        try:
            citation = json_module.loads(line)
        except json_module.JSONDecodeError:
            issues.append(LintIssue("🔴", "invalid-citation",
                                    f"graph/citations.jsonl:{line_num}",
                                    "Invalid JSON"))
            continue

        for field in ("from", "to", "type", "source", "date"):
            if field not in citation:
                issues.append(LintIssue("🔴", "invalid-citation",
                                        f"graph/citations.jsonl:{line_num}",
                                        f"Missing required field: {field}"))

        from_id = str(citation.get("from", ""))
        to_id = str(citation.get("to", ""))
        if _node_kind(from_id) != "papers" or _node_kind(to_id) != "papers":
            issues.append(LintIssue("🟡", "invalid-citation-endpoint",
                                    f"graph/citations.jsonl:{line_num}",
                                    "cites should connect papers/* -> papers/*"))

        if citation.get("type") not in CITATION_EDGE_TYPES:
            issues.append(LintIssue("🟡", "unknown-citation-type",
                                    f"graph/citations.jsonl:{line_num}",
                                    f"Unknown citation type: {citation.get('type')}"))
        if citation.get("source") not in CITATION_SOURCES:
            issues.append(LintIssue("🟡", "unknown-citation-source",
                                    f"graph/citations.jsonl:{line_num}",
                                    f"Unknown citation source: {citation.get('source')}"))
        if "confidence" in citation:
            issues.append(LintIssue("🟡", "invalid-citation-field",
                                    f"graph/citations.jsonl:{line_num}",
                                    "Citation rows should not include confidence"))
        if "date" in citation and not re.match(r"^\d{4}-\d{2}-\d{2}$",
                                                str(citation.get("date", ""))):
            issues.append(LintIssue("🟡", "invalid-citation-date",
                                    f"graph/citations.jsonl:{line_num}",
                                    "Citation date should be YYYY-MM-DD"))

        key = (from_id, to_id)
        if key in seen:
            issues.append(LintIssue("🟡", "duplicate-citation",
                                    f"graph/citations.jsonl:{line_num}",
                                    f"Duplicate citation {from_id} -> {to_id}"))
        seen.add(key)

        for endpoint in ("from", "to"):
            if endpoint not in citation:
                continue
            issue = _check_graph_node_exists(
                wiki_dir, str(citation[endpoint]), "graph/citations.jsonl",
                line_num, endpoint
            )
            if issue:
                issues.append(issue)

    return issues


def check_content_quality(wiki_dir: Path, pages: dict[str, Path]) -> list[LintIssue]:
    """Content quality suggestions."""
    issues = []
    for slug, fpath in pages.items():
        content = fpath.read_text(encoding="utf-8")
        rel = str(fpath.relative_to(wiki_dir))
        page_type = fpath.parent.name

        # importance=5 paper should be referenced by at least one concept
        if page_type == "papers":
            val = extract_frontmatter_value(content, "importance")
            if val == "5":
                referenced = False
                for cslug, cpath in pages.items():
                    if cpath.parent.name == "concepts":
                        cc = cpath.read_text(encoding="utf-8")
                        if slug in cc:
                            referenced = True
                            break
                if not referenced:
                    issues.append(LintIssue("🔵", "quality", rel,
                                            "importance=5 but no concept page references this paper"))

        # concepts with maturity=stable but only 1 key_paper
        if page_type == "concepts":
            mat = extract_frontmatter_value(content, "maturity")
            if mat == "stable":
                match = re.search(r"key_papers:\s*\[(.*?)\]", content)
                if match:
                    papers_list = [p.strip().strip(",") for p in match.group(1).split() if p.strip().strip(",")]
                    if len(papers_list) <= 1:
                        issues.append(LintIssue("🔵", "quality", rel,
                                                "maturity=stable but only 1 key_paper (consider adding more)"))

        # topics with empty open_problems
        if page_type == "topics":
            if "## Open problems" in content:
                idx = content.index("## Open problems")
                # Get text until next ## or end
                rest = content[idx + len("## Open problems"):]
                next_section = rest.find("\n## ")
                section_text = rest[:next_section] if next_section != -1 else rest
                if section_text.strip() == "" or section_text.strip() == "—":
                    issues.append(LintIssue("🔵", "quality", rel,
                                            "Open problems section is empty"))

    return issues


def lint(wiki_dir: Path) -> list[LintIssue]:
    """Run all lint checks and return sorted issues."""
    pages = find_all_pages(wiki_dir)
    issues = []

    issues.extend(check_missing_fields(wiki_dir, pages))
    link_issues, incoming = check_broken_links(wiki_dir, pages)
    issues.extend(link_issues)
    issues.extend(check_orphan_pages(wiki_dir, pages, incoming))
    issues.extend(check_field_values(wiki_dir, pages))
    issues.extend(check_required_when(wiki_dir, pages))
    issues.extend(check_link_field_targets(wiki_dir, pages))
    issues.extend(check_xref_asymmetry(wiki_dir, pages))
    issues.extend(check_graph_edges(wiki_dir, pages))
    issues.extend(check_graph_citations(wiki_dir, pages))
    issues.extend(check_content_quality(wiki_dir, pages))

    return issues


# ---------------------------------------------------------------------------
# Auto-fix functions
# ---------------------------------------------------------------------------

def _append_to_section(fpath: Path, section_heading: str, line_to_add: str) -> bool:
    """Append a line to a markdown section. Returns True if modified."""
    content = fpath.read_text(encoding="utf-8")
    if line_to_add.strip() in content:
        return False  # already present

    idx = content.find(f"\n{section_heading}\n")
    if idx == -1:
        idx = content.find(f"\n{section_heading}")
    if idx == -1:
        # Section doesn't exist — append it at end
        content = content.rstrip() + f"\n\n{section_heading}\n\n{line_to_add}\n"
    else:
        # Find end of section heading line, insert after next blank or content line
        section_start = idx + len(f"\n{section_heading}")
        # Skip to first content position after heading
        rest = content[section_start:]
        # Find insert point: after any blank lines following heading
        insert_offset = 0
        for ch in rest:
            if ch == '\n':
                insert_offset += 1
            else:
                break
        insert_pos = section_start + insert_offset
        content = content[:insert_pos] + f"{line_to_add}\n" + content[insert_pos:]

    fpath.write_text(content, encoding="utf-8")
    return True


def _add_frontmatter_field(fpath: Path, field: str, value: str) -> bool:
    """Add a missing field to YAML frontmatter. Returns True if modified."""
    content = fpath.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    if not m:
        return False

    fm_text = m.group(1)
    if re.search(rf"^{re.escape(field)}\s*:", fm_text, re.MULTILINE):
        return False  # field already exists

    # Insert before closing ---
    new_fm = fm_text.rstrip() + f"\n{field}: {value}"
    content = f"---\n{new_fm}\n---" + content[m.end():]
    fpath.write_text(content, encoding="utf-8")
    return True


def fix_issues(wiki_dir: Path, issues: list[LintIssue], dry_run: bool = False) -> list[FixResult]:
    """Apply auto-fixes for fixable issues. Returns list of fixes applied."""
    fixes = []

    for issue in issues:
        if not issue.fixable:
            continue

        if issue.category == "xref-asymmetry":
            fix = _fix_xref(wiki_dir, issue, dry_run)
            if fix:
                fixes.append(fix)
        elif issue.category == "missing-field":
            fix = _fix_missing_field(wiki_dir, issue, dry_run)
            if fix:
                fixes.append(fix)

    return fixes


def _fix_xref(wiki_dir: Path, issue: LintIssue, dry_run: bool) -> FixResult | None:
    """Fix a single xref-asymmetry issue by adding the reverse link."""
    msg = issue.message
    source_rel = issue.file  # e.g. "concepts/foo.md"

    # Parse the issue message to determine what fix is needed
    # Pattern: "key_papers has {ref} but papers/{ref}.md doesn't link back to [[{slug}]]"
    if "key_papers has" in msg and "papers/" in msg:
        m = re.search(r"key_papers has (\S+) but papers/\S+\.md doesn't link back to \[\[(\S+)\]\]", msg)
        if not m:
            return None
        paper_slug, concept_slug = m.group(1), m.group(2)
        target_path = wiki_dir / "papers" / f"{paper_slug}.md"
        action = f"Add [[{concept_slug}]] to papers/{paper_slug}.md ## Related"
        if not dry_run:
            _append_to_section(target_path, "## Related", f"- [[{concept_slug}]]")
        return FixResult(f"papers/{paper_slug}.md", action)

    # Pattern: "links to people/{target} but person doesn't link back to [[{slug}]]"
    if "links to people/" in msg and "doesn't link back" in msg:
        m = re.search(r"links to people/(\S+) but person doesn't link back to \[\[(\S+)\]\]", msg)
        if not m:
            return None
        person_slug, paper_slug = m.group(1), m.group(2)
        target_path = wiki_dir / "people" / f"{person_slug}.md"
        action = f"Add [[{paper_slug}]] to people/{person_slug}.md ## Key papers"
        if not dry_run:
            _append_to_section(target_path, "## Key papers", f"- [[{paper_slug}]]")
        return FixResult(f"people/{person_slug}.md", action)

    # Pattern: "source_papers has {ref} but papers/{ref}.md doesn't link back to [[{slug}]]"
    if "source_papers has" in msg and "papers/" in msg:
        m = re.search(r"source_papers has (\S+) but papers/\S+\.md doesn't link back to \[\[(\S+)\]\]", msg)
        if not m:
            return None
        paper_slug, claim_slug = m.group(1), m.group(2)
        target_path = wiki_dir / "papers" / f"{paper_slug}.md"
        action = f"Add [[{claim_slug}]] to papers/{paper_slug}.md ## Related"
        if not dry_run:
            _append_to_section(target_path, "## Related", f"- [[{claim_slug}]]")
        return FixResult(f"papers/{paper_slug}.md", action)

    # Pattern: "origin_gaps has {ref} but claims/{ref}.md doesn't link back to [[{slug}]]"
    if "origin_gaps has" in msg and "claims/" in msg:
        m = re.search(r"origin_gaps has (\S+) but claims/\S+\.md doesn't link back to \[\[(\S+)\]\]", msg)
        if not m:
            return None
        claim_slug, idea_slug = m.group(1), m.group(2)
        target_path = wiki_dir / "claims" / f"{claim_slug}.md"
        action = f"Add [[{idea_slug}]] to claims/{claim_slug}.md ## Linked ideas"
        if not dry_run:
            _append_to_section(target_path, "## Linked ideas", f"- [[{idea_slug}]]")
        return FixResult(f"claims/{claim_slug}.md", action)

    # Pattern: "target_claim={target} but claims/{target}.md doesn't reference this experiment"
    if "target_claim=" in msg and "doesn't reference this experiment" in msg:
        m = re.search(r"target_claim=(\S+) but", msg)
        if not m:
            return None
        claim_slug = m.group(1)
        # Extract experiment slug from issue.file: "experiments/foo.md" → "foo"
        exp_slug = Path(issue.file).stem
        target_path = wiki_dir / "claims" / f"{claim_slug}.md"
        action = f"Add {exp_slug} reference to claims/{claim_slug}.md ## Evidence summary"
        if not dry_run:
            _append_to_section(target_path, "## Evidence summary",
                               f"- Tested by: [[{exp_slug}]]")
        return FixResult(f"claims/{claim_slug}.md", action)

    return None


def _fix_missing_field(wiki_dir: Path, issue: LintIssue, dry_run: bool) -> FixResult | None:
    """Fix a missing frontmatter field by inserting a safe default."""
    m = re.search(r"Missing required field: (\S+)", issue.message)
    if not m:
        return None
    field = m.group(1)

    page_type = issue.file.split("/")[0]
    defaults = FIELD_DEFAULTS.get(page_type, {})
    if field not in defaults:
        return None

    fpath = wiki_dir / issue.file
    if not fpath.exists():
        return None

    default_val = defaults[field]
    action = f"Add '{field}: {default_val}' to frontmatter"
    if not dry_run:
        _add_frontmatter_field(fpath, field, default_val)
    return FixResult(issue.file, action)


def main():
    parser = argparse.ArgumentParser(description="OmegaWiki linter")
    parser.add_argument("--wiki-dir", default="wiki/", help="Path to wiki directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix deterministic issues (xref reverse links, missing field defaults)")
    parser.add_argument("--dry-run", action="store_true",
                        help="With --fix: preview fixes without applying them")
    parser.add_argument("--suggest", action="store_true",
                        help="Show actionable suggestions for non-auto-fixable issues")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"Error: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    issues = lint(wiki_dir)

    # Apply fixes if requested
    fixes: list[FixResult] = []
    if args.fix:
        fixes = fix_issues(wiki_dir, issues, dry_run=args.dry_run)

    red = sum(1 for i in issues if i.level == "🔴")

    if args.json:
        if args.fix:
            output: dict = {
                "issues": [i.to_dict() for i in issues],
                "fixes": [f.to_dict() for f in fixes],
                "dry_run": args.dry_run,
            }
            print(json_module.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(json_module.dumps([i.to_dict() for i in issues], indent=2, ensure_ascii=False))
    else:
        level_order = {"🔴": 0, "🟡": 1, "🔵": 2}
        yellow = sum(1 for i in issues if i.level == "🟡")
        blue = sum(1 for i in issues if i.level == "🔵")
        print(f"Lint: {red} 🔴, {yellow} 🟡, {blue} 🔵\n")
        for issue in sorted(issues, key=lambda i: (level_order.get(i.level, 9), i.file)):
            print(issue)
            if args.suggest and issue.suggestion:
                print(f"  💡 {issue.suggestion}")
        if not issues:
            print("No issues found.")

        if args.fix and fixes:
            verb = "Would fix" if args.dry_run else "Fixed"
            print(f"\n{verb} {len(fixes)} issue(s):\n")
            for fix in fixes:
                print(fix)

        if args.fix and not fixes and any(i.fixable for i in issues):
            print("\nNo new fixes to apply (already fixed or dry-run).")

    sys.exit(1 if red > 0 else 0)


if __name__ == "__main__":
    main()
