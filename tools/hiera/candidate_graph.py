"""Deterministic operation selection for repeated Hiera rounds."""

from __future__ import annotations

from .ledger import Ledger
from .semantic_space import propose
from .acquisition import coverage_scores


def choose_operation(ledger: Ledger, round_index: int) -> str:
    records = ledger.candidates()
    if not records:
        return "fresh"
    if round_index % 3 == 2 and len(records) >= 2:
        return "crossover"
    return "improve" if any(record.get("best_score") is not None for record in records.values()) else "fresh"


def parent_records(ledger: Ledger, limit: int = 4, direction: str = "minimize") -> list[dict]:
    records = [
        record for record in ledger.candidates().values() if isinstance(record.get("best_score"), (int, float))
    ]
    sign = 1 if direction == "minimize" else -1
    attempts = {}
    for item in coverage_scores(ledger):
        attempts[item["candidate_id"]] = attempts.get(item["candidate_id"], 0) + item["attempts"]
    records.sort(
        key=lambda record: (
            attempts.get(record["candidate_id"], 0),
            sign * float(record["best_score"]),
            record["candidate_id"],
        )
    )
    return records[:limit]


def build_proposals(
    space: dict,
    ledger: Ledger,
    round_index: int,
    limit: int = 8,
    direction: str = "minimize",
):
    operation = choose_operation(ledger, round_index)
    parents = [record["semantic_point"] for record in parent_records(ledger, direction=direction)]
    return operation, propose(space, operation, parents, limit)
