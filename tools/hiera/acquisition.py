"""Coverage-oriented acquisition statistics.

The score ranks under-explored candidate/depth pairs. It deliberately does not
mix raw metric values from unrelated candidates.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .ledger import Ledger


def coverage_scores(ledger: Ledger) -> list[dict[str, Any]]:
    stats: defaultdict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"attempts": 0, "successes": 0, "failures": 0}
    )
    for receipt in ledger.evaluations():
        key = (receipt.get("candidate_id"), receipt.get("depth", "screen"))
        stats[key]["attempts"] += 1
        if receipt.get("status") == "success":
            stats[key]["successes"] += 1
        else:
            stats[key]["failures"] += 1
    result = []
    for (candidate_id, depth), values in stats.items():
        result.append(
            {
                "candidate_id": candidate_id,
                "depth": depth,
                **values,
                "priority": 1 / (1 + values["attempts"]) + 0.15 * values["failures"],
            }
        )
    return sorted(result, key=lambda item: (-item["priority"], item["candidate_id"], item["depth"]))
