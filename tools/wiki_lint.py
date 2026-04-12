#!/usr/bin/env python3
"""Extended wiki lint -- structural checks for ΩmegaWiki.

Complements tools/lint.py (entity-schema-aware, frontmatter-focused) with
broader structural checks that apply to any wiki directory layout:
orphan pages, broken wikilinks, stale/ghost index entries, oversized pages,
and duplicate filenames.

Use lint.py for entity-specific schema validation.
Use wiki_lint.py for cross-wiki structural health.

Checks:
    1. Orphan pages: pages with zero inbound links
    2. Broken wikilinks: [[slug]] resolving to no file
    3. Stale index: page exists on disk but not in index.md
    4. Ghost index: entry in index.md with no corresponding file
    5. Oversized pages: page > 500 lines (configurable)
    6. Duplicate filenames: two pages with same slug in different subdirs

Usage:
    python3 tools/wiki_lint.py <wiki_root>
    python3 tools/wiki_lint.py <wiki_root> --fix
    python3 tools/wiki_lint.py <wiki_root> --max-lines 300
    python3 tools/wiki_lint.py <wiki_root> --json

Python 3.9+, no external dependencies.
"""

from __future__ import annotations

import argparse
import io
import json as json_module
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Finding:
    def __init__(self, severity: str, check: str, message: str):
        self.severity = severity  # ERROR or WARN
        self.check = check
        self.message = message

    def __str__(self):
        return f"[{self.severity}] {self.message}"

    def to_dict(self) -> dict:
        return {"severity": self.severity, "check": self.check, "message": self.message}


def collect_md_files(root: Path) -> List[Path]:
    """Recursively collect .md files."""
    return sorted(root.rglob("*.md"))


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def count_lines(path: Path) -> int:
    content = read_file(path)
    if not content:
        return 0
    return content.count("\n") + (1 if not content.endswith("\n") else 0)


def extract_wikilinks(content: str) -> List[Tuple[str, int]]:
    """Extract all [[slug]] wikilinks with line numbers."""
    results = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r'\[\[([^\]]+)\]\]', line):
            raw = m.group(1)
            slug = raw.split("|")[0].strip()
            results.append((slug, i))
    return results


def extract_md_links(content: str) -> List[Tuple[str, int]]:
    """Extract [text](path.md) markdown links with line numbers."""
    results = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r'\[([^\]]*)\]\(([^)]+\.md[^)]*)\)', line):
            results.append((m.group(2), i))
    return results


def build_slug_index(root: Path, all_files: Set[Path]) -> Dict[str, Path]:
    """Build a slug-to-resolved-path index for fast wikilink resolution."""
    index: Dict[str, Path] = {}
    for f in all_files:
        try:
            rel = f.relative_to(root.resolve())
        except ValueError:
            continue
        rel_str = str(rel).replace("\\", "/")
        path_no_ext = rel_str.replace(".md", "")
        if path_no_ext not in index:
            index[path_no_ext] = f
        stem = f.stem
        if stem not in index:
            index[stem] = f
        if stem == "index" and f.parent != root.resolve():
            parent_rel = str(f.parent.relative_to(root.resolve())).replace("\\", "/")
            if parent_rel not in index:
                index[parent_rel] = f
    return index


def resolve_wikilink(slug: str, slug_index: Dict[str, Path]) -> bool:
    slug_clean = slug.strip().replace("\\", "/")
    if slug_clean in slug_index:
        return True
    slug_stripped = slug_clean.strip("/")
    if slug_stripped in slug_index:
        return True
    bare = slug_stripped.split("/")[-1]
    if bare in slug_index:
        return True
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_orphan_pages(root: Path, all_files: Set[Path],
                       slug_index: Dict[str, Path]) -> List[Finding]:
    """Check 1: Pages with no inbound links from other pages."""
    findings = []
    referenced_files: Set[Path] = set()

    for f in all_files:
        content = read_file(f)
        for slug, _ in extract_wikilinks(content):
            slug_clean = slug.strip().replace("\\", "/")
            for key in [slug_clean, slug_clean.strip("/"), slug_clean.split("/")[-1]]:
                if key in slug_index:
                    referenced_files.add(slug_index[key])
                    break
        for link, _ in extract_md_links(content):
            target = (f.parent / link.split("#")[0]).resolve()
            if target in all_files:
                referenced_files.add(target)

    index_file = (root / "index.md").resolve()
    skip_names = {"readme.md", "log.md", "overview.md", "index.md"}

    for f in all_files:
        if f.name.lower() in skip_names:
            continue
        if f.resolve() == index_file:
            continue
        if f.resolve() not in referenced_files:
            rel = f.relative_to(root)
            findings.append(Finding("WARN", "orphan-page",
                                    f"orphan page {rel} (0 inbound links)"))
    return findings


def check_broken_wikilinks(root: Path, all_files: Set[Path],
                           slug_index: Dict[str, Path]) -> List[Finding]:
    """Check 2: [[slug]] that resolves to no file."""
    findings = []
    for f in all_files:
        content = read_file(f)
        rel = f.relative_to(root)
        for slug, line_no in extract_wikilinks(content):
            if not resolve_wikilink(slug, slug_index):
                findings.append(Finding("ERROR", "broken-wikilink",
                                        f"broken wikilink [[{slug}]] in {rel}:{line_no}"))
    return findings


def check_stale_index(root: Path, all_files: Set[Path],
                      index_content: str) -> List[Finding]:
    """Check 3: Page exists on disk but not listed in index.md."""
    findings = []
    index_path = (root / "index.md").resolve()
    index_text = index_content.lower()
    skip_names = {"readme.md", "log.md", "overview.md", "index.md"}

    for f in all_files:
        if f.name.lower() in skip_names:
            continue
        if f.resolve() == index_path:
            continue

        rel = f.relative_to(root)
        rel_str = str(rel).replace("\\", "/")
        stem = f.stem
        path_no_ext = rel_str.replace(".md", "")

        referenced = (
            rel_str.lower() in index_text
            or path_no_ext.lower() in index_text
            or f"[[{stem}]]".lower() in index_text
            or f"[[{path_no_ext}]]".lower() in index_text
            or f"({rel_str})".lower() in index_text
            or f"({path_no_ext})".lower() in index_text
        )

        if not referenced:
            findings.append(Finding("ERROR", "stale-index",
                                    f"page {rel} exists on disk but not in index.md"))
    return findings


def check_ghost_index(root: Path, all_files: Set[Path],
                      index_content: str,
                      slug_index: Dict[str, Path]) -> List[Finding]:
    """Check 4: Entry in index.md but no corresponding file."""
    findings = []
    index_file = root / "index.md"
    resolved_files = {f.resolve() for f in all_files}

    for slug, line_no in extract_wikilinks(index_content):
        if not resolve_wikilink(slug, slug_index):
            findings.append(Finding("ERROR", "ghost-index",
                                    f"ghost index entry [[{slug}]] in index.md:{line_no}"))

    for link, line_no in extract_md_links(index_content):
        target_path = link.split("#")[0]
        resolved = (index_file.parent / target_path).resolve()
        if resolved not in resolved_files and not resolved.exists():
            findings.append(Finding("ERROR", "ghost-index",
                                    f'ghost index entry "{target_path}" in index.md:{line_no}'))
    return findings


def check_oversized_pages(root: Path, all_files: Set[Path],
                          max_lines: int) -> List[Finding]:
    """Check 5: Page > max_lines lines."""
    findings = []
    for f in all_files:
        lines = count_lines(f)
        if lines > max_lines:
            rel = f.relative_to(root)
            findings.append(Finding("WARN", "oversized-page",
                                    f"oversized page {rel} ({lines} lines, limit {max_lines})"))
    return findings


def check_duplicate_filenames(root: Path, all_files: Set[Path]) -> List[Finding]:
    """Check 6: Two pages with same slug in different subdirs."""
    findings = []
    seen: Dict[str, List[Path]] = {}
    skip_stems = {"index", "readme", "log", "overview"}

    for f in all_files:
        stem = f.stem.lower()
        if stem in skip_stems:
            continue
        seen.setdefault(stem, []).append(f)

    for stem, paths in seen.items():
        if len(paths) > 1:
            rel_paths = [str(p.relative_to(root)) for p in paths]
            findings.append(Finding("WARN", "duplicate-filename",
                                    f"duplicate slug '{stem}' in: {', '.join(rel_paths)}"))
    return findings


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------

def fix_stale_index(root: Path, stale_findings: List[Finding]) -> None:
    """Add missing entries to index.md for stale-index findings."""
    index_path = root / "index.md"
    content = read_file(index_path)

    additions = []
    for f in stale_findings:
        match = re.search(r'page (\S+) exists on disk', f.message)
        if match:
            page_path = match.group(1).replace("\\", "/")
            additions.append(f"\n- [[{page_path.replace('.md', '')}]] -- (auto-added by wiki_lint)")

    if additions:
        content += "\n\n## Auto-added by wiki_lint (stale-index fix)\n"
        content += "\n".join(additions) + "\n"
        index_path.write_text(content, encoding="utf-8")
        print(f"  [FIX] added {len(additions)} stale entries to index.md")


def fix_ghost_index(root: Path, ghost_findings: List[Finding]) -> None:
    """Comment out ghost index entries."""
    index_path = root / "index.md"
    content = read_file(index_path)
    lines = content.splitlines()

    fixed_count = 0
    for f in ghost_findings:
        line_match = re.search(r':(\d+)$', f.message)
        if line_match:
            line_no = int(line_match.group(1)) - 1
            if 0 <= line_no < len(lines):
                original = lines[line_no]
                if not original.strip().startswith("<!-- GHOST:"):
                    lines[line_no] = f"<!-- GHOST: {original.strip()} -->"
                    fixed_count += 1

    if fixed_count:
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  [FIX] commented out {fixed_count} ghost entries in index.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def lint_wiki(root: Path, max_lines: int = 500,
              fix: bool = False) -> List[Finding]:
    """Run all checks on a wiki directory."""
    if not root.exists():
        return [Finding("ERROR", "missing-directory",
                        f"wiki directory {root} does not exist")]

    all_files_list = collect_md_files(root)
    all_files = {f.resolve() for f in all_files_list}

    index_path = root / "index.md"
    index_content = read_file(index_path) if index_path.exists() else ""

    slug_index = build_slug_index(root, all_files)
    findings: List[Finding] = []

    findings.extend(check_orphan_pages(root, all_files, slug_index))
    findings.extend(check_broken_wikilinks(root, all_files, slug_index))

    stale = check_stale_index(root, all_files, index_content)
    findings.extend(stale)

    ghost = check_ghost_index(root, all_files, index_content, slug_index)
    findings.extend(ghost)

    findings.extend(check_oversized_pages(root, all_files, max_lines))
    findings.extend(check_duplicate_filenames(root, all_files))

    if fix:
        stale_only = [f for f in stale if f.check == "stale-index"]
        if stale_only:
            fix_stale_index(root, stale_only)
        ghost_only = [f for f in ghost if f.check == "ghost-index"]
        if ghost_only:
            fix_ghost_index(root, ghost_only)

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Structural lint checks for an ΩmegaWiki wiki directory")
    parser.add_argument("wiki_root", help="Path to the wiki/ directory")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix safe issues (stale index, ghost entries)")
    parser.add_argument("--max-lines", type=int, default=500,
                        help="Max lines per page before warning (default: 500)")
    parser.add_argument("--json", action="store_true",
                        help="Output findings as JSON")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root).resolve()
    findings = lint_wiki(wiki_root, args.max_lines, args.fix)

    if args.json:
        print(json_module.dumps([f.to_dict() for f in findings], indent=2))
        sys.exit(1 if any(f.severity == "ERROR" for f in findings) else 0)

    if not findings:
        print("All checks passed. No findings.")
        sys.exit(0)

    errors = [f for f in findings if f.severity == "ERROR"]
    warns = [f for f in findings if f.severity == "WARN"]

    for f in sorted(findings, key=lambda x: (0 if x.severity == "ERROR" else 1)):
        print(f)

    print(f"\n--- Summary: {len(errors)} ERROR(s), {len(warns)} WARN(s) ---")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
