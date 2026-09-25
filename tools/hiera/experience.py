"""Bounded experience summaries derived from the append-only ledger."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .common import canonical_digest, now_iso
from .ledger import Ledger


def build_snapshot(ledger: Ledger) -> dict[str, Any]:
    by_point: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"attempts": 0, "successes": 0, "failures": 0}
    )
    for receipt in ledger.evaluations():
        point_id = ledger.candidate(receipt["candidate_id"]).get("point_id")
        if not isinstance(point_id, str):
            continue
        row = by_point[point_id]
        row["attempts"] += 1
        row["successes" if receipt.get("status") == "success" else "failures"] += 1
    payload = {
        "schema_version": 1,
        "updated_at": now_iso(),
        "points": dict(sorted(by_point.items())),
    }
    payload["revision"] = canonical_digest(payload)
    return payload
