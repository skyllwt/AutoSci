#!/usr/bin/env python3
"""Consolidation: write terminal active artifacts back into long-term memory.

`propose` scans validated/failed ideas and completed experiments and generates
candidate patches (append a line to a long-term page section). `apply` (a later
task) applies an approved patch file through Trust Guard. Patches are NOT
auto-applied.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint  # noqa: E402  (tools/ sibling: _append_to_section)
import trust_guard  # noqa: E402  (tools/ sibling: check)
import wiki_events  # noqa: E402  (tools/ sibling: append_event)

PROPOSAL_REL = "raw/tmp/consolidation/consolidation-proposal.json"


@dataclass
class Patch:
    kind: str
    target: str
    section: str
    line: str
    source: str
    rationale: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "target": self.target, "section": self.section,
                "line": self.line, "source": self.source, "rationale": self.rationale}


def _read_frontmatter(path: Path) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = yaml.safe_load(parts[1])
    return fm if isinstance(fm, dict) else {}


def _norm_slug(value) -> str:
    s = str(value).strip().strip('"').strip("'")
    while s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    return s


def _resolve(root: Path, kind: str, slugs) -> list[str]:
    out = []
    for s in slugs or []:
        s = _norm_slug(s)
        if s and (Path(root) / kind / f"{s}.md").exists():
            out.append(s)
    return out


def _iter_pages(root: Path, kind: str):
    d = Path(root) / kind
    return sorted(d.glob("*.md")) if d.exists() else []


def propose(wiki_dir: str | Path) -> list[Patch]:
    """Scan terminal active artifacts and propose long-term consolidation patches."""
    root = Path(wiki_dir)
    patches: list[Patch] = []

    for f in _iter_pages(root, "ideas"):
        fm = _read_frontmatter(f)
        slug = f.stem
        title = fm.get("title") or slug
        topics = _resolve(root, "topics", fm.get("origin_gaps"))
        status = fm.get("status")
        if status == "failed":
            reason = fm.get("failure_reason") or ""
            for t in topics:
                patches.append(Patch("topic_open_problem", f"topics/{t}", "## Open problems",
                                     f"- {title}: {reason} (failed idea {slug})",
                                     f"ideas/{slug}", "failed idea -> open problem/lesson"))
        elif status == "validated":
            for t in topics:
                patches.append(Patch("topic_synthesis", f"topics/{t}", "## Synthesis notes",
                                     f"- {title}: validated (idea {slug})",
                                     f"ideas/{slug}", "validated idea -> synthesis"))

    for f in _iter_pages(root, "experiments"):
        fm = _read_frontmatter(f)
        slug = f.stem
        if fm.get("status") != "completed":
            continue
        outcome = fm.get("outcome")
        key_result = fm.get("key_result")
        if not outcome or not key_result:
            continue
        for m in _resolve(root, "methods", fm.get("evaluates_methods")):
            patches.append(Patch("method_finding", f"methods/{m}", "## Evaluated by",
                                 f"- {key_result} — experiment {slug} (outcome={outcome})",
                                 f"experiments/{slug}", "completed experiment -> method finding"))
            mfm = _read_frontmatter(root / "methods" / f"{m}.md")
            for t in _resolve(root, "topics", mfm.get("parent_topics")):
                patches.append(Patch("topic_sota", f"topics/{t}", "## SOTA tracker",
                                     f"- {key_result} (experiment {slug})",
                                     f"experiments/{slug}", "completed experiment -> topic SOTA"))

    return patches


def cmd_propose(wiki_root: str, out: str | None, repo_root: str, as_json: bool) -> int:
    patches = propose(wiki_root)
    out_path = Path(out) if out else Path(repo_root) / PROPOSAL_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([p.to_dict() for p in patches], ensure_ascii=False, indent=2),
                        encoding="utf-8")
    wiki_events.append_event(wiki_root, "consolidation_events", {
        "kind": "consolidation_proposed",
        "count": len(patches),
        "patches": [{"kind": p.kind, "target": p.target, "source": p.source} for p in patches],
    })
    if as_json:
        print(json.dumps([p.to_dict() for p in patches], ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"status": "ok", "proposed": len(patches), "path": str(out_path)}))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="consolidate_memory")
    sub = parser.add_subparsers(dest="command", required=True)
    pp = sub.add_parser("propose")
    pp.add_argument("wiki_root")
    pp.add_argument("--out", default=None)
    pp.add_argument("--repo-root", default=".")
    pp.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "propose":
        return cmd_propose(args.wiki_root, args.out, args.repo_root, args.json)
    return 1


if __name__ == "__main__":
    sys.exit(main())
