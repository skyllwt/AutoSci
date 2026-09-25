"""Anchor/challenger scheduling for repeated deep-tuning bouts."""

from __future__ import annotations

from typing import Any

from .common import HieraError, finite_number
from .ledger import Ledger


def choose_deep_candidate(
    ledger: Ledger,
    max_bouts_per_candidate: int = 3,
    direction: str = "minimize",
) -> dict[str, Any]:
    eligible = []
    for record in ledger.candidates().values():
        if not finite_number(record.get("best_score")):
            continue
        if len(record.get("tuning_bouts", [])) < max_bouts_per_candidate:
            eligible.append(record)
    if not eligible:
        return {"action": "STOP", "reason": "no-deep-eligible-candidate", "candidate_id": None}
    sign = 1 if direction == "minimize" else -1
    eligible.sort(
        key=lambda record: (
            sign * float(record["best_score"]),
            len(record.get("tuning_bouts", [])),
            record["candidate_id"],
        )
    )
    chosen = eligible[0]
    decision = {
        "action": "TUNE",
        "candidate_id": chosen["candidate_id"],
        "reason": "anchor" if chosen.get("tuning_bouts") else "challenger",
        "bout_index": len(chosen.get("tuning_bouts", [])) + 1,
    }
    ledger.record_decision(decision)
    return decision


def record_bout(
    ledger: Ledger,
    candidate_id: str,
    *,
    score: float | None,
    status: str = "tuned",
    trials: int = 0,
    regime: str = "deep",
    attempt_id: str | None = None,
    reconciled: bool = False,
) -> None:
    if trials < 0:
        raise HieraError("trials cannot be negative")
    if score is not None and not finite_number(score):
        raise HieraError("tuning score must be finite or null")
    receipt: dict[str, Any] = {
        "score": score,
        "status": status,
        "trials": trials,
        "regime": regime,
        "evaluation_depth": "deep",
    }
    if attempt_id is not None:
        receipt["attempt_id"] = attempt_id
    if reconciled:
        receipt["reconciled"] = True
    ledger.record_tuning(candidate_id, receipt)


def reconcile_deep_bouts(ledger: Ledger) -> list[str]:
    """Repair orchestration state for completed deep attempts.

    A remote client can disconnect after the evaluator records an evaluation
    but before ``loop`` or ``tune`` records its tuning bout.  The evaluation
    remains authoritative; this function adds the missing, attempt-bound bout
    exactly once so resuming the workflow cannot spend a duplicate bout.
    """

    existing_attempts = {
        bout.get("attempt_id")
        for record in ledger.candidates().values()
        for bout in record.get("tuning_bouts", [])
        if isinstance(bout.get("attempt_id"), str)
    }
    repaired: list[str] = []
    for evaluation in ledger.evaluations():
        attempt_id = evaluation.get("attempt_id")
        if (
            evaluation.get("depth") != "deep"
            or not isinstance(attempt_id, str)
            or attempt_id in existing_attempts
        ):
            continue
        candidate_id = evaluation.get("candidate_id")
        if not isinstance(candidate_id, str):
            continue
        candidate = ledger.candidate(candidate_id)
        # ``tune`` evaluates a newly materialized child but records the bout
        # on its parent.  ``loop`` records it on the evaluated candidate.
        target = candidate_id
        if candidate.get("operation") == "tune":
            parents = candidate.get("parents", [])
            if isinstance(parents, list) and parents and isinstance(parents[0], str):
                target = parents[0]
        record_bout(
            ledger,
            target,
            score=evaluation.get("score"),
            status="tuned" if evaluation.get("status") == "success" else "failed",
            attempt_id=attempt_id,
            reconciled=True,
        )
        existing_attempts.add(attempt_id)
        repaired.append(attempt_id)
    return repaired
