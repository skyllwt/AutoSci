#!/usr/bin/env python3
"""Trust Guard — gate SciMem writes with a PASS/WARN/BLOCK verdict.

Form validity is deterministic and reuses tools/lint.py. Content validity is an
independent Review-LLM check (tools/trust_content_review.py), injectable for tests.
BLOCKed artifacts are quarantined to raw/tmp/quarantine/; every verdict is logged
to wiki/graph/trust_events.jsonl via research_wiki.append_event.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import lint
import research_wiki
import trust_content_review

PASS, WARN, BLOCK = "PASS", "WARN", "BLOCK"
_RANK = {PASS: 0, WARN: 1, BLOCK: 2}
_LEVEL_TO_STATUS = {"🔴": BLOCK, "🟡": WARN, "🔵": PASS}


@dataclass
class TrustCheck:
    name: str
    status: str
    message: str


@dataclass
class TrustVerdict:
    artifact: str
    status: str
    checks: list[TrustCheck] = field(default_factory=list)

    def to_event(self) -> dict:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "checks": [{"name": c.name, "status": c.status, "message": c.message} for c in self.checks],
        }


def overall_status(checks: list[TrustCheck]) -> str:
    worst = PASS
    for c in checks:
        if _RANK[c.status] > _RANK[worst]:
            worst = c.status
    return worst


def _mk_content_verdict(status: str, message: str):
    """Thin factory for trust_content_review.ContentVerdict (test convenience)."""
    return trust_content_review.ContentVerdict(status=status, message=message, raw=None)


def run_form_checks(wiki_dir: Path, artifact_rel: str) -> list[TrustCheck]:
    """Run deterministic lint over the wiki and keep only issues for `artifact_rel`."""
    issues = [i for i in lint.lint(Path(wiki_dir)) if i.file == artifact_rel]
    if not issues:
        return [TrustCheck("form:pass", PASS, "no deterministic form issues")]
    checks: list[TrustCheck] = []
    for i in issues:
        status = _LEVEL_TO_STATUS.get(i.level, WARN)
        checks.append(TrustCheck(f"form:{i.category}", status, i.message))
    return checks


def _artifact_rel(wiki_dir: Path, artifact_path: Path) -> str:
    try:
        return str(Path(artifact_path).resolve().relative_to(Path(wiki_dir).resolve()))
    except ValueError:
        return str(artifact_path)


def check(wiki_dir: Path, artifact_path: Path, *,
          content_reviewer: Callable[[str, dict], trust_content_review.ContentVerdict | None] | None = None,
          repo_root: Path | None = None, emit_event: bool = True) -> TrustVerdict:
    """Produce a TrustVerdict, quarantine on BLOCK (file-exists path), and log a trust_event.
    `content_reviewer` is a callable (text, context) -> ContentVerdict|None."""
    if content_reviewer is None:
        content_reviewer = lambda text, context: trust_content_review.review_artifact(text, context=context)

    wiki_dir = Path(wiki_dir)
    artifact_path = Path(artifact_path)
    rel = _artifact_rel(wiki_dir, artifact_path)

    if not artifact_path.exists():
        verdict = TrustVerdict(artifact=rel, status=BLOCK,
                               checks=[TrustCheck("form:missing-file", BLOCK, f"{rel} does not exist")])
    else:
        checks = run_form_checks(wiki_dir, rel)
        text = artifact_path.read_text(encoding="utf-8")
        cv = content_reviewer(text, {"neighbors": []})
        if cv is None:
            checks.append(TrustCheck("content:review", PASS, "content-check skipped (Review LLM not configured)"))
        else:
            checks.append(TrustCheck("content:review", cv.status, cv.message))
        verdict = TrustVerdict(artifact=rel, status=overall_status(checks), checks=checks)
        if verdict.status == BLOCK:
            _quarantine(repo_root or Path("."), artifact_path, text, verdict)

    if emit_event:
        research_wiki.append_event(str(wiki_dir), "trust_events", verdict.to_event())

    return verdict


def _quarantine(repo_root: Path, artifact_path: Path, text: str, verdict: TrustVerdict) -> Path:
    """Copy a BLOCKed artifact + its verdict into raw/tmp/quarantine/ (skill-writable
    zone per hard-rule 1). Returns the quarantined .md path."""
    qdir = Path(repo_root) / "raw" / "tmp" / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    stem = verdict.artifact.replace("/", "__").removesuffix(".md")
    md_path = qdir / f"{stem}.md"
    # Re-checking the same artifact overwrites its prior quarantine entry (latest verdict wins).
    md_path.write_text(text, encoding="utf-8")
    (qdir / f"{stem}.verdict.json").write_text(
        json.dumps(verdict.to_event(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trust_guard")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="Trust-guard a single artifact")
    p.add_argument("wiki_root")
    p.add_argument("artifact_path")
    p.add_argument("--no-content", action="store_true", help="skip the Review-LLM content check")
    p.add_argument("--repo-root", default=".", help="repo root for quarantine path (default: .)")
    p.add_argument("--json", action="store_true", help="print the verdict as JSON")
    args = parser.parse_args(argv)

    if args.command == "check":
        reviewer = (lambda text, context: None) if args.no_content else None
        verdict = check(Path(args.wiki_root), Path(args.artifact_path),
                        content_reviewer=reviewer, repo_root=Path(args.repo_root))
        if args.json:
            print(json.dumps(verdict.to_event(), ensure_ascii=False, indent=2))
        else:
            print(f"{verdict.status}  {verdict.artifact}")
            for c in verdict.checks:
                print(f"  [{c.status}] {c.name}: {c.message}")
        return 2 if verdict.status == BLOCK else 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
