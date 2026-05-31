#!/usr/bin/env python3
"""verify-claims — read-only claim/evidence coverage check for SciMem-3.

Resolves the entities a manuscript asserts (claims) from its `## Evidence map`
wikilinks + graph neighbours, classifies each by risk (status-driven), and
checks whether high-risk claims carry >=1 structured supports/tested_by edge.
Read-only: never writes the wiki. Verdict is PASS/WARN/BLOCK/INFO with an exit
code (BLOCK -> nonzero; WARN nonzero only under --strict; INFO never).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_wiki  # noqa: E402  (tools/ sibling: load_edges, graph_neighbors, add_edge)

PASS, WARN, BLOCK, INFO = "PASS", "WARN", "BLOCK", "INFO"
EMOJI = {PASS: "🔵", WARN: "🟡", BLOCK: "🔴", INFO: "ℹ️"}
_RANK = {INFO: 0, PASS: 0, WARN: 1, BLOCK: 2}

CLAIM_KINDS = ("ideas", "experiments", "methods")
COVERAGE_EDGES = ("supports", "tested_by")
HIGH_RISK_IDEA = {"validated", "tested"}
HIGH_RISK_EXPERIMENT = {"completed"}


@dataclass
class ClaimVerdict:
    node_id: str
    kind: str
    status: str
    risk: str           # "high" | "low"
    verdict: str        # PASS / WARN / BLOCK / INFO
    covering_edges: int
    has_structured: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "claim": self.node_id, "kind": self.kind, "status": self.status,
            "risk": self.risk, "verdict": self.verdict,
            "covering_edges": self.covering_edges,
            "has_structured": self.has_structured, "reason": self.reason,
        }


def _read_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = yaml.safe_load(parts[1])
    return fm if isinstance(fm, dict) else {}


def _section_body(text: str, heading: str) -> str:
    """Return the body of a `## <heading>` markdown section (until the next `## `)."""
    out, capturing = [], False
    for ln in text.splitlines():
        if ln.strip().startswith("## "):
            if capturing:
                break
            capturing = ln.strip() == f"## {heading}"
            continue
        if capturing:
            out.append(ln)
    return "\n".join(out)


def _resolve_link(wiki_dir: Path, target: str) -> str | None:
    """Resolve a wikilink target to a 'kind/slug' node id among CLAIM_KINDS."""
    target = target.strip().split("|", 1)[0].strip()  # drop display alias if any
    if "/" in target:
        kind, slug = target.split("/", 1)
        if kind in CLAIM_KINDS and (wiki_dir / kind / f"{slug}.md").exists():
            return f"{kind}/{slug}"
        return None
    for kind in CLAIM_KINDS:
        if (wiki_dir / kind / f"{target}.md").exists():
            return f"{kind}/{target}"
    return None


def resolve_claims(wiki_dir: Path, manuscript_slug: str) -> list[str]:
    """Claim set = Evidence-map wikilinks ∪ manuscript graph neighbours, kept to CLAIM_KINDS."""
    wiki_dir = Path(wiki_dir)
    claims: set[str] = set()
    man_path = wiki_dir / "manuscripts" / f"{manuscript_slug}.md"
    if man_path.exists():
        body = _section_body(man_path.read_text(encoding="utf-8"), "Evidence map")
        for raw in re.findall(r"\[\[([^\]]+)\]\]", body):
            nid = _resolve_link(wiki_dir, raw)
            if nid:
                claims.add(nid)
    for nb in research_wiki.graph_neighbors(
            str(wiki_dir), f"manuscripts/{manuscript_slug}", depth=1):
        nid = nb.get("id", "")
        kind = nid.split("/", 1)[0] if "/" in nid else ""
        if kind in CLAIM_KINDS and (wiki_dir / f"{nid}.md").exists():
            claims.add(nid)
    return sorted(claims)


def classify_risk(kind: str, status: str) -> str:
    if kind == "ideas" and status in HIGH_RISK_IDEA:
        return "high"
    if kind == "experiments" and status in HIGH_RISK_EXPERIMENT:
        return "high"
    return "low"


def _coverage(edges: list[dict], node_id: str) -> tuple[int, bool]:
    """Count supports/tested_by edges incident to node_id; structured if any
    covering edge carries a non-empty metric_value or source_path."""
    count, structured = 0, False
    for e in edges:
        if e.get("type") not in COVERAGE_EDGES:
            continue
        if node_id not in (e.get("from"), e.get("to")):
            continue
        count += 1
        if e.get("metric_value") or e.get("source_path"):
            structured = True
    return count, structured


def verdict_for_claim(kind: str, status: str, covering: int,
                      structured: bool) -> tuple[str, str]:
    """Return (verdict, reason) for one claim. See design spec section 3.4(c)."""
    if classify_risk(kind, status) == "high":
        if covering == 0:
            return BLOCK, "high-risk claim has no supports/tested_by evidence edge"
        if not structured:
            return WARN, "covered but no structured attribute (metric_value/source_path)"
        return PASS, "covered with structured evidence"
    if covering == 0:
        return INFO, "low-risk claim, no evidence edge (informational)"
    return PASS, "low-risk claim, covered"


def verify_claims(wiki_dir: Path, manuscript_slug: str) -> list[ClaimVerdict]:
    wiki_dir = Path(wiki_dir)
    edges = research_wiki.load_edges(str(wiki_dir))
    results: list[ClaimVerdict] = []
    for nid in resolve_claims(wiki_dir, manuscript_slug):
        kind = nid.split("/", 1)[0]
        status = str(_read_frontmatter(wiki_dir / f"{nid}.md").get("status", ""))
        covering, structured = _coverage(edges, nid)
        verdict, reason = verdict_for_claim(kind, status, covering, structured)
        results.append(ClaimVerdict(nid, kind, status,
                                    classify_risk(kind, status), verdict,
                                    covering, structured, reason))
    return results
