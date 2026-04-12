#!/usr/bin/env python3
"""Context Compilation CLI for ΩmegaWiki.

Parses wiki index.md at runtime to build purpose-to-pages mappings,
then concatenates page content within a token budget (chars/4 estimate).

The index.md must have a "## By Trigger" section with ### subheadings
and [[wikilink]] references to pages. Optionally, a "## By Severity"
section assigns CRITICAL/HIGH/MEDIUM/LOW priority for ordering.

Usage:
    python3 tools/compile_context.py <wiki_root> --for scene-writing --budget 4000
    python3 tools/compile_context.py <wiki_root> --for session-close --budget 2000
    python3 tools/compile_context.py <wiki_root> --list

Python 3.9+, no external dependencies.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_index(index_path: Path) -> dict:
    """Parse an index.md and return trigger_map and severity_map.

    Expected structure:
        ## By Trigger
        ### <Trigger Name>
        - [[page-slug]]
        ...
        ## By Severity
        ### CRITICAL (...)
        - [[page-slug]]
        ...

    Returns dict with keys 'triggers' and 'severity'.
    """
    text = index_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    trigger_map: dict[str, list[str]] = {}
    severity_map: dict[str, str] = {}

    current_h2 = ""
    current_h3 = ""

    wikilink_re = re.compile(r"\[\[([^\]]+)\]\]")

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## ") and not stripped.startswith("### "):
            current_h2 = stripped[3:].strip()
            current_h3 = ""
            continue

        if stripped.startswith("### "):
            current_h3 = stripped[4:].strip()
            continue

        match = wikilink_re.search(stripped)
        if not match:
            continue
        page_slug = match.group(1)

        if current_h2 == "By Trigger" and current_h3:
            trigger_map.setdefault(current_h3, [])
            if page_slug not in trigger_map[current_h3]:
                trigger_map[current_h3].append(page_slug)

        if current_h2 == "By Severity" and current_h3:
            severity_map[page_slug] = current_h3.split("(")[0].strip()

    return {"triggers": trigger_map, "severity": severity_map}


def resolve_page_path(slug: str, wiki_root: Path) -> Path:
    """Convert a page slug to a filesystem Path relative to wiki_root."""
    return wiki_root / (slug + ".md")


def estimate_tokens(text: str) -> int:
    """Estimate token count as chars / 4."""
    return len(text) // 4


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def get_severity_rank(slug: str, severity_map: dict) -> int:
    sev = severity_map.get(slug, "")
    return SEVERITY_ORDER.get(sev, 99)


def slugify_heading(heading: str) -> str:
    """Convert a trigger heading to a CLI-friendly name.

    'Prose Writing (MANDATORY retrieval)' -> 'prose-writing'
    'Session Close' -> 'session-close'
    """
    base = heading.split("(")[0].strip()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def build_purpose_map(trigger_map: dict[str, list[str]]) -> dict[str, str]:
    """Build bidirectional purpose <-> heading lookup from trigger_map keys."""
    purpose_to_heading: dict[str, str] = {}
    for heading in trigger_map:
        purpose = slugify_heading(heading)
        purpose_to_heading[purpose] = heading
    return purpose_to_heading


def get_pages_for_purpose(purpose: str, parsed: dict,
                          purpose_map: dict[str, str]) -> list[str]:
    heading = purpose_map.get(purpose)
    if not heading:
        return []
    return list(parsed["triggers"].get(heading, []))


def compile_context(purpose: str, budget: int, parsed: dict,
                    purpose_map: dict[str, str], wiki_root: Path) -> str:
    """Compile context pages for a purpose within a token budget.

    Pages are sorted by severity (CRITICAL first), then truncated if over budget.
    """
    slugs = get_pages_for_purpose(purpose, parsed, purpose_map)
    if not slugs:
        return f"# No pages found for purpose: {purpose}\n"

    severity_map = parsed["severity"]
    slugs.sort(key=lambda s: get_severity_rank(s, severity_map))

    sections: list[str] = []
    tokens_used = 0

    for slug in slugs:
        page_path = resolve_page_path(slug, wiki_root)
        if not page_path.exists():
            section = f"<!-- WARNING: {slug}.md not found -->"
            section_tokens = estimate_tokens(section)
        else:
            content = page_path.read_text(encoding="utf-8")
            section = content
            section_tokens = estimate_tokens(content)

        header = f"\n# Source: {slug}\n"
        separator = "\n---\n"
        overhead = estimate_tokens(header + separator)
        total_needed = section_tokens + overhead

        if tokens_used + total_needed > budget:
            remaining_tokens = budget - tokens_used - overhead
            if remaining_tokens > 50:
                remaining_chars = remaining_tokens * 4
                truncated = section[:remaining_chars]
                last_nl = truncated.rfind("\n")
                if last_nl > 0:
                    truncated = truncated[:last_nl]
                truncated += "\n\n<!-- TRUNCATED: token budget reached -->"
                sections.append(separator + header + truncated)
                tokens_used = budget
            else:
                sections.append(
                    f"\n---\n# SKIPPED: {slug} (and {len(slugs) - len(sections) - 1} more) -- budget exhausted\n"
                )
            break
        else:
            sections.append(separator + header + section)
            tokens_used += total_needed

    heading_label = purpose_map.get(purpose, purpose)
    preamble = (
        f"# Compiled Context: {purpose} ({heading_label})\n"
        f"# Budget: {budget} tokens | Used: ~{tokens_used} tokens | "
        f"Pages: {len([s for s in sections if 'SKIPPED' not in s])}/{len(slugs)}\n"
    )

    return preamble + "".join(sections) + "\n"


def list_purposes(parsed: dict, purpose_map: dict[str, str]) -> str:
    lines = ["Available purposes:\n"]
    for purpose in sorted(purpose_map):
        heading = purpose_map[purpose]
        page_slugs = parsed["triggers"].get(heading, [])
        lines.append(f"  {purpose:<30s} ({len(page_slugs)} pages) -- {heading}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile wiki context pages for a specific purpose within a token budget."
    )
    parser.add_argument("wiki_root", help="Path to the wiki/ directory (must contain index.md)")
    parser.add_argument(
        "--for", dest="purpose", type=str,
        help="Purpose name (auto-derived from index.md headings, e.g. session-close)"
    )
    parser.add_argument(
        "--budget", type=int, default=4000,
        help="Token budget (estimated as chars/4). Default: 4000"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all available purposes and exit"
    )

    args = parser.parse_args()
    wiki_root = Path(args.wiki_root).resolve()

    index_path = wiki_root / "index.md"
    if not index_path.exists():
        print(f"ERROR: index.md not found at {index_path}", file=sys.stderr)
        return 1

    parsed = parse_index(index_path)
    purpose_map = build_purpose_map(parsed["triggers"])

    if args.list:
        print(list_purposes(parsed, purpose_map))
        return 0

    if not args.purpose:
        parser.print_help()
        return 1

    if args.purpose not in purpose_map:
        print(f"ERROR: Unknown purpose '{args.purpose}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(purpose_map))}", file=sys.stderr)
        return 1

    output = compile_context(args.purpose, args.budget, parsed, purpose_map, wiki_root)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
