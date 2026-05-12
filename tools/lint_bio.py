#!/usr/bin/env python3
"""Bio-specific wiki lint — bio-C8 minimal pilot (merged 2026-05-12).

Runs alongside ``tools/lint.py``. The base linter covers entity-type-agnostic
structure (required fields, enum values, xref symmetry, edge consistency).
This linter covers bio-shaped constraints that base lint cannot express:

  1. PDB ID format on ``concepts.pdb_ids`` (A2-light)
  2. UniProt accession format on ``concepts.uniprot_id`` (A2-light)
  3. ``dataset_version_used`` edge metadata.version must hit the target
     dataset's ``versions:`` list (B3 + A1 cross-check)
  4. ``experiments.setup.species`` values are in a recognised set (A5-full)
  5. ``experiments.setup.assay_type`` containing MD/molecular dynamics
     requires ``setup.force_field`` to be populated (A5-full)

Severity convention matches ``tools/lint.py``: 🔴 hard error, 🟡 fix
recommended, 🔵 informational.

Exits 1 iff at least one 🔴 issue was emitted (mirrors lint.py).

Usage:
    python3 tools/lint_bio.py                # lint wiki/ in current dir
    python3 tools/lint_bio.py --wiki-dir wiki/
    python3 tools/lint_bio.py --json         # JSON output for skill consumers
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# Reuse LintIssue + FRONTMATTER_RE from lint.py so output format stays consistent.
# tools/ has no __init__.py; same path-injection trick lint.py uses for runtime/loader.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint import FRONTMATTER_RE, LintIssue  # noqa: E402

# PDB IDs: legacy 4-char (1 digit + 3 alphanum) or extended 8-char.
# Examples: 6XYZ, 4CI1, pdb_00000001 (extended) — we accept the legacy form
# and the 8-char alphanum form. Case-insensitive but conventionally upper.
PDB_ID_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}([A-Za-z0-9]{4})?$")

# UniProt accession canonical regex (from uniprot.org):
#   [OPQ][0-9][A-Z0-9]{3}[0-9]                  # 6-char legacy form (Q96SW2, P12345, …)
# | [A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}   # 6- or 10-char extended form (A0A123BCD45)
UNIPROT_ACCESSION_RE = re.compile(
    r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$"
)

# A small allowlist of species names lint_bio recognises. Free-text outside the
# set is informational only — extend this when a new species enters the wiki.
RECOGNISED_SPECIES = {
    "human", "mouse", "rat", "yeast", "zebrafish", "drosophila", "c-elegans",
    "c. elegans", "fruit fly", "fruitfly", "e. coli", "e-coli", "arabidopsis",
    "xenopus", "chicken", "pig", "dog", "rabbit", "macaque", "monkey",
    "hamster", "guinea pig", "sheep", "cow", "bovine",
}

# Patterns identifying an assay as MD (requires force_field).
MD_ASSAY_PATTERN = re.compile(r"\bMD\b|molecular dynamics", re.IGNORECASE)


def _parse_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter with PyYAML (handles nested objects).

    The regex-based parser in lint.py drops indented children, which is fine
    for flat enum checks but wrong for nested setup/versions/pdb_ids reads.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def check_pdb_ids(wiki_dir: Path) -> list[LintIssue]:
    """concepts.pdb_ids entries must match the PDB ID format."""
    issues: list[LintIssue] = []
    concepts_dir = wiki_dir / "concepts"
    if not concepts_dir.exists():
        return issues
    for p in sorted(concepts_dir.glob("*.md")):
        fm = _parse_frontmatter(p)
        if not fm:
            continue
        pdb_ids = fm.get("pdb_ids")
        if pdb_ids is None or pdb_ids == []:
            continue
        rel = f"concepts/{p.name}"
        if not isinstance(pdb_ids, list):
            issues.append(LintIssue(
                "🟡", "bio-pdb-format", rel,
                f"pdb_ids must be a list, got {type(pdb_ids).__name__}",
                suggestion="Use flow-list syntax: pdb_ids: [4CI1, 4CI2]"))
            continue
        for pid in pdb_ids:
            if not isinstance(pid, str) or not PDB_ID_RE.match(pid):
                issues.append(LintIssue(
                    "🟡", "bio-pdb-format", rel,
                    f"Invalid PDB ID format: {pid!r} "
                    "(expect 4 alphanum starting with a digit, or 8-char extended form)",
                    suggestion="Verify the entry at rcsb.org; PDB IDs are conventionally upper-cased."))
    return issues


def check_uniprot_ids(wiki_dir: Path) -> list[LintIssue]:
    """concepts.uniprot_id must match the canonical accession regex."""
    issues: list[LintIssue] = []
    concepts_dir = wiki_dir / "concepts"
    if not concepts_dir.exists():
        return issues
    for p in sorted(concepts_dir.glob("*.md")):
        fm = _parse_frontmatter(p)
        if not fm:
            continue
        uid = fm.get("uniprot_id")
        if not uid:
            continue
        if not isinstance(uid, str) or not UNIPROT_ACCESSION_RE.match(uid.strip()):
            issues.append(LintIssue(
                "🟡", "bio-uniprot-format", f"concepts/{p.name}",
                f"Invalid UniProt accession format: {uid!r}",
                suggestion=(
                    "Canonical form is 6 chars matching [OPQ][0-9][A-Z0-9]{3}[0-9] "
                    "(e.g. Q96SW2) or the 10-char extended form. Verify at uniprot.org."
                )))
    return issues


def check_dataset_versions(wiki_dir: Path) -> list[LintIssue]:
    """``dataset_version_used`` edges carrying metadata.version must reference a
    version present in the target dataset's ``versions:`` list."""
    issues: list[LintIssue] = []
    edges_path = wiki_dir / "graph" / "edges.jsonl"
    if not edges_path.exists():
        return issues
    # Build dataset_slug -> set(version strings).
    dataset_versions: dict[str, set[str]] = {}
    datasets_dir = wiki_dir / "datasets"
    if datasets_dir.exists():
        for p in datasets_dir.glob("*.md"):
            fm = _parse_frontmatter(p)
            if not fm:
                continue
            versions = fm.get("versions") or []
            if not isinstance(versions, list):
                continue
            dataset_versions[p.stem] = {
                str(v.get("version")) for v in versions
                if isinstance(v, dict) and v.get("version") not in (None, "")
            }
    try:
        with edges_path.open(encoding="utf-8") as f:
            for line_num, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    edge = json.loads(raw)
                except json.JSONDecodeError:
                    continue  # base lint already flags malformed edges
                if edge.get("type") != "dataset_version_used":
                    continue
                metadata = edge.get("metadata") or {}
                version = metadata.get("version")
                if not version:
                    continue  # version stored only in free-text evidence — not checkable
                to = edge.get("to", "")
                if not to.startswith("datasets/"):
                    continue  # base lint catches misrouted endpoints
                dataset_slug = to.split("/", 1)[1]
                known = dataset_versions.get(dataset_slug, set())
                if str(version) not in known:
                    known_str = sorted(known) if known else "empty"
                    issues.append(LintIssue(
                        "🟡", "bio-dataset-version",
                        f"graph/edges.jsonl:{line_num}",
                        f"Edge references dataset version {version!r} not listed in "
                        f"datasets/{dataset_slug}.md::versions (known: {known_str})",
                        suggestion=(
                            f"Either add version {version!r} to "
                            f"datasets/{dataset_slug}.md::versions or correct the edge metadata.version."
                        )))
    except OSError:
        return issues
    return issues


def check_species_recognised(wiki_dir: Path) -> list[LintIssue]:
    """experiments.setup.species values should be in a recognised set (informational)."""
    issues: list[LintIssue] = []
    experiments_dir = wiki_dir / "experiments"
    if not experiments_dir.exists():
        return issues
    for p in sorted(experiments_dir.glob("*.md")):
        fm = _parse_frontmatter(p)
        if not fm:
            continue
        setup = fm.get("setup") or {}
        if not isinstance(setup, dict):
            continue
        species = setup.get("species") or []
        if not isinstance(species, list):
            continue
        for sp in species:
            if not isinstance(sp, str):
                continue
            if sp.strip().lower() not in RECOGNISED_SPECIES:
                issues.append(LintIssue(
                    "🔵", "bio-species-unknown", f"experiments/{p.name}",
                    f"Unrecognised species name {sp!r} (extend RECOGNISED_SPECIES "
                    "in tools/lint_bio.py if legitimate; otherwise correct the value)"))
    return issues


def check_md_force_field(wiki_dir: Path) -> list[LintIssue]:
    """experiments.setup.assay_type matching MD requires setup.force_field set."""
    issues: list[LintIssue] = []
    experiments_dir = wiki_dir / "experiments"
    if not experiments_dir.exists():
        return issues
    for p in sorted(experiments_dir.glob("*.md")):
        fm = _parse_frontmatter(p)
        if not fm:
            continue
        setup = fm.get("setup") or {}
        if not isinstance(setup, dict):
            continue
        assay_type = setup.get("assay_type") or ""
        if not isinstance(assay_type, str) or not MD_ASSAY_PATTERN.search(assay_type):
            continue
        force_field = setup.get("force_field") or ""
        if not isinstance(force_field, str) or not force_field.strip():
            issues.append(LintIssue(
                "🟡", "bio-md-force-field", f"experiments/{p.name}",
                f"setup.assay_type={assay_type!r} indicates MD but setup.force_field is empty",
                suggestion=(
                    "Fill setup.force_field (e.g. 'AMBER ff14SB + phosaa14SB', "
                    "'CHARMM36m', 'OPLS-AA/M'); MD reproducibility hinges on this."
                )))
    return issues


def lint(wiki_dir: Path) -> list[LintIssue]:
    issues: list[LintIssue] = []
    issues += check_pdb_ids(wiki_dir)
    issues += check_uniprot_ids(wiki_dir)
    issues += check_dataset_versions(wiki_dir)
    issues += check_species_recognised(wiki_dir)
    issues += check_md_force_field(wiki_dir)
    return issues


def main():
    parser = argparse.ArgumentParser(
        description="OmegaWiki bio-specific linter (bio-C8 minimal)")
    parser.add_argument("--wiki-dir", default="wiki/", help="Path to wiki directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"Error: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    issues = lint(wiki_dir)
    red = sum(1 for i in issues if i.level == "🔴")
    yellow = sum(1 for i in issues if i.level == "🟡")
    blue = sum(1 for i in issues if i.level == "🔵")

    if args.json:
        print(json.dumps([i.to_dict() for i in issues], indent=2, ensure_ascii=False))
    else:
        level_order = {"🔴": 0, "🟡": 1, "🔵": 2}
        print(f"Bio Lint: {red} 🔴, {yellow} 🟡, {blue} 🔵\n")
        for issue in sorted(issues, key=lambda i: (level_order.get(i.level, 9), i.file)):
            print(issue)
            if issue.suggestion:
                print(f"  💡 {issue.suggestion}")
        if not issues:
            print("No bio-specific issues found.")

    sys.exit(1 if red > 0 else 0)


if __name__ == "__main__":
    main()
