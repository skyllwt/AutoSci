#!/usr/bin/env python3
"""One-shot backfill: populate wiki/graph/citations.jsonl for all already-ingested
papers.

The bootstrap `/init` workflow skips `fetch_s2.py references` in parallel mode
for safety and never reinstates it at fan-in. As a result, freshly-bootstrapped
wikis have an empty `citations.jsonl`. This script walks every paper in
`wiki/papers/`, fetches references from Semantic Scholar, and uses
`research_wiki.py add-citations-batch` to append all matching `cites` rows.

Idempotent: re-runs only add newly-discovered references; existing ones are
skipped via the `skipped_existing` counter.

Usage:
    .venv/bin/python tools/backfill_citations.py [--wiki-dir wiki/]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Resolve project root so relative paths work from any CWD
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

import tools._env  # noqa: F401, E402  side-effect: load .env files

# Use the current interpreter (handles .venv automatically when invoked via
# .venv/bin/python). Fall back to "python3" only if frozen-ish environment.
PYTHON_BIN = sys.executable or "python3"


def _parse_arxiv_id(md_path: Path) -> str | None:
    """Return the arxiv field from frontmatter, stripped of quotes."""
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm_text = text[4:end]
    for line in fm_text.splitlines():
        if not line.strip().startswith("arxiv:"):
            continue
        v = line.split(":", 1)[1].strip()
        # strip surrounding quotes
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        return v or None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-dir", default="wiki",
                        help="Wiki root directory (default: wiki)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without writing")
    args = parser.parse_args()

    wiki_root = (REPO_ROOT / args.wiki_dir).resolve()
    papers_dir = wiki_root / "papers"
    if not papers_dir.is_dir():
        print(f"ERROR: {papers_dir} not found", file=sys.stderr)
        return 1

    paper_files = sorted(papers_dir.glob("*.md"))
    print(f"Found {len(paper_files)} papers in {papers_dir}")

    totals = {"received": 0, "matched": 0, "added": 0,
              "skipped_existing": 0, "unmatched": 0}
    failed: list[str] = []

    for md in paper_files:
        slug = md.stem
        arxiv = _parse_arxiv_id(md)
        if not arxiv:
            print(f"  [skip] {slug}: no arxiv ID in frontmatter")
            continue

        print(f"  [fetch] {slug} (arxiv:{arxiv})...", end=" ", flush=True)
        try:
            refs_proc = subprocess.run(
                [PYTHON_BIN, str(SCRIPT_DIR / "fetch_s2.py"), "references", arxiv],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            failed.append(slug)
            continue

        if refs_proc.returncode != 0:
            print(f"FETCH FAILED (rc={refs_proc.returncode})")
            print(refs_proc.stderr[:500], file=sys.stderr)
            failed.append(slug)
            continue

        refs_json = refs_proc.stdout.strip()
        if not refs_json:
            print("empty result")
            continue

        # Quick count for display
        try:
            ref_count = len(json.loads(refs_json))
        except json.JSONDecodeError:
            print("invalid JSON from fetch_s2")
            failed.append(slug)
            continue

        if args.dry_run:
            print(f"would attempt {ref_count} refs (dry-run)")
            continue

        batch_proc = subprocess.run(
            [PYTHON_BIN, str(SCRIPT_DIR / "research_wiki.py"),
             "add-citations-batch", str(wiki_root),
             "--citer", f"papers/{slug}"],
            cwd=REPO_ROOT,
            input=refs_json,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if batch_proc.returncode != 0:
            print(f"BATCH FAILED (rc={batch_proc.returncode})")
            print(batch_proc.stderr[:500], file=sys.stderr)
            failed.append(slug)
            continue

        try:
            result = json.loads(batch_proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            print("unparseable batch output")
            failed.append(slug)
            continue

        for k in totals:
            totals[k] += result.get(k, 0)
        print(f"refs={result['received']} matched={result['matched']} "
              f"added={result['added']} skipped={result['skipped_existing']}")

    if not args.dry_run:
        # Final dedup pass (cheap insurance against any duplicate slips)
        subprocess.run(
            [PYTHON_BIN, str(SCRIPT_DIR / "research_wiki.py"),
             "dedup-citations", str(wiki_root)],
            cwd=REPO_ROOT,
        )

    print()
    print(f"Totals: {totals}")
    if failed:
        print(f"Failed papers ({len(failed)}): {failed}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
