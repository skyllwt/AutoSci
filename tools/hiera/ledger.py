"""Append-only event ledger with pre-execution budget reservation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import HieraError, append_jsonl, exclusive_lock, finite_number, now_iso, read_jsonl, validate_slug

LEDGER_SCHEMA_VERSION = 2
_EVENT_KINDS = {
    "candidate_created",
    "candidate_status",
    "evaluation_reserved",
    "evaluation_released",
    "evaluation",
    "tuning_bout",
    "scheduler_decision",
}


class Ledger:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "ledger.jsonl"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def events(self) -> list[dict[str, Any]]:
        rows = read_jsonl(self.path)
        for index, event in enumerate(rows, 1):
            if event.get("schema_version") != LEDGER_SCHEMA_VERSION:
                raise HieraError(f"unsupported ledger schema at event {index}")
            if event.get("event_id") != f"evt-{index:08d}":
                raise HieraError(f"ledger event sequence is corrupt at event {index}")
            if not isinstance(event.get("kind"), str) or not isinstance(event.get("payload"), dict):
                raise HieraError(f"ledger event {index} is malformed")
            if event["kind"] not in _EVENT_KINDS:
                raise HieraError(f"unknown ledger event kind at event {index}: {event['kind']}")
        return rows

    def _append_locked(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.events()
        event = {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "event_id": f"evt-{len(rows) + 1:08d}",
            "kind": kind,
            "created_at": now_iso(),
            "payload": payload,
        }
        append_jsonl(self.path, event)
        return event

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(kind, str) or not kind or not isinstance(payload, dict):
            raise HieraError("ledger event requires kind and object payload")
        with exclusive_lock(self.path):
            return self._append_locked(kind, payload)

    def candidates(self) -> dict[str, dict[str, Any]]:
        state: dict[str, dict[str, Any]] = {}
        for event in self.events():
            payload = event["payload"]
            candidate_id = payload.get("candidate_id")
            kind = event["kind"]
            if kind == "candidate_created":
                if not isinstance(candidate_id, str) or candidate_id in state:
                    raise HieraError(f"duplicate or invalid candidate: {candidate_id!r}")
                state[candidate_id] = dict(payload, evaluations=[], tuning_bouts=[])
            elif candidate_id in state:
                if kind == "candidate_status":
                    state[candidate_id].update(
                        {key: value for key, value in payload.items() if key != "candidate_id"}
                    )
                elif kind == "evaluation":
                    state[candidate_id]["evaluations"].append(dict(payload))
                    _update_best(state[candidate_id], payload)
                elif kind == "tuning_bout":
                    state[candidate_id]["tuning_bouts"].append(dict(payload))
        return state

    def candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.candidates().get(candidate_id)
        if candidate is None:
            raise HieraError(f"candidate not found: {candidate_id}")
        return candidate

    def reservations(self) -> list[dict[str, Any]]:
        return [event["payload"] for event in self.events() if event["kind"] == "evaluation_reserved"]

    def evaluations(self) -> list[dict[str, Any]]:
        return [event["payload"] for event in self.events() if event["kind"] == "evaluation"]

    def budget_used(self) -> int:
        released = {
            event["payload"].get("attempt_id")
            for event in self.events()
            if event["kind"] == "evaluation_released"
        }
        return sum(
            reservation.get("attempt_id") not in released for reservation in self.reservations()
        )

    def reserve(self, candidate_id: str, depth: str, budget: int) -> str:
        self.candidate(candidate_id)
        with exclusive_lock(self.path):
            rows = self.events()
            released = {
                event["payload"].get("attempt_id")
                for event in rows
                if event["kind"] == "evaluation_released"
            }
            used = sum(
                event["payload"].get("attempt_id") not in released
                for event in rows
                if event["kind"] == "evaluation_reserved"
            )
            if used >= budget:
                raise HieraError(f"evaluation budget exhausted ({budget})")
            reserved_count = sum(event["kind"] == "evaluation_reserved" for event in rows)
            attempt_id = f"att-{reserved_count + 1:08d}"
            self._append_locked(
                "evaluation_reserved",
                {
                    "attempt_id": attempt_id,
                    "candidate_id": candidate_id,
                    "depth": depth,
                    "reserved_at": now_iso(),
                },
            )
            return attempt_id

    def release(self, attempt_id: str, reason: str) -> None:
        if not any(item.get("attempt_id") == attempt_id for item in self.reservations()):
            raise HieraError(f"unknown attempt: {attempt_id}")
        if any(
            event["payload"].get("attempt_id") == attempt_id
            for event in self.events()
            if event["kind"] == "evaluation_released"
        ):
            return
        self.append("evaluation_released", {"attempt_id": attempt_id, "reason": reason})

    def add_candidate(self, record: dict[str, Any]) -> None:
        candidate_id = record.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise HieraError("candidate_id is required")
        validate_slug(candidate_id, "candidate_id")
        if candidate_id in self.candidates():
            raise HieraError(f"candidate already exists: {candidate_id}")
        required = {"operation", "point_id", "semantic_point", "code_digest", "status"}
        missing = sorted(required - record.keys())
        if missing:
            raise HieraError("candidate record missing: " + ", ".join(missing))
        self.append("candidate_created", dict(record))

    def set_status(self, candidate_id: str, status: str, **extra: Any) -> None:
        self.candidate(candidate_id)
        if "candidate_id" in extra:
            raise HieraError("candidate status cannot override candidate_id")
        self.append("candidate_status", {"candidate_id": candidate_id, "status": status, **extra})

    def record_evaluation(self, attempt_id: str, candidate_id: str, receipt: dict[str, Any]) -> None:
        if not isinstance(receipt, dict):
            raise HieraError("evaluation receipt must be an object")
        if "attempt_id" in receipt or "candidate_id" in receipt:
            raise HieraError("evaluation receipt cannot override attempt_id or candidate_id")
        with exclusive_lock(self.path):
            rows = self.events()
            reservations = [
                event["payload"]
                for event in rows
                if event["kind"] == "evaluation_reserved"
                and event["payload"].get("attempt_id") == attempt_id
            ]
            if not reservations or reservations[0].get("candidate_id") != candidate_id:
                raise HieraError("evaluation must reference a reserved attempt")
            if any(
                event["payload"].get("attempt_id") == attempt_id
                for event in rows
                if event["kind"] == "evaluation_released"
            ):
                raise HieraError("released evaluation attempt cannot receive a receipt")
            existing = [
                event["payload"]
                for event in rows
                if event["kind"] == "evaluation"
                and event["payload"].get("attempt_id") == attempt_id
            ]
            expected = {"attempt_id": attempt_id, "candidate_id": candidate_id, **receipt}
            if existing:
                if existing[0] != expected:
                    raise HieraError("duplicate evaluation attempt has a different receipt")
                return
            self._append_locked("evaluation", expected)

    def record_tuning(self, candidate_id: str, receipt: dict[str, Any]) -> None:
        self.candidate(candidate_id)
        if not isinstance(receipt, dict) or "candidate_id" in receipt:
            raise HieraError("tuning receipt cannot override candidate_id")
        # Deep evaluations are reconciled after a client interruption.  Bind
        # their tuning record to the attempt so recovery is idempotent rather
        # than appending a second bout when the CLI is resumed.
        attempt_id = receipt.get("attempt_id")
        if attempt_id is not None and (
            not isinstance(attempt_id, str) or not attempt_id
        ):
            raise HieraError("tuning attempt_id must be a non-empty string")
        with exclusive_lock(self.path):
            rows = self.events()
            if attempt_id is not None:
                expected = {"candidate_id": candidate_id, **receipt}
                existing = [
                    event["payload"]
                    for event in rows
                    if event["kind"] == "tuning_bout"
                    and event["payload"].get("candidate_id") == candidate_id
                    and event["payload"].get("attempt_id") == attempt_id
                ]
                if existing:
                    if existing[0] != expected:
                        raise HieraError("duplicate tuning attempt has a different receipt")
                    return
            self._append_locked("tuning_bout", {"candidate_id": candidate_id, **receipt})

    def record_decision(self, receipt: dict[str, Any]) -> None:
        self.append("scheduler_decision", dict(receipt))

    def summary(self, budget: int | None = None, direction: str = "minimize") -> dict[str, Any]:
        records = list(self.candidates().values())
        scored = [record for record in records if finite_number(record.get("best_score"))]
        best = None
        if scored:
            chooser = min if direction == "minimize" else max
            best = chooser(scored, key=lambda record: float(record["best_score"]))
        used = self.budget_used()
        return {
            "candidate_count": len(records),
            "evaluation_count": used,
            "max_evaluations": budget,
            "remaining_evaluations": None if budget is None else max(0, budget - used),
            "best_candidate": best,
            "scheduler_decisions": sum(event["kind"] == "scheduler_decision" for event in self.events()),
            "event_count": len(self.events()),
        }


def _update_best(candidate: dict[str, Any], receipt: dict[str, Any]) -> None:
    if receipt.get("status") != "success" or not finite_number(receipt.get("score")):
        return
    score = float(receipt["score"])
    current = candidate.get("best_score")
    direction = receipt.get("direction", candidate.get("direction", "minimize"))
    if current is None or (direction == "maximize" and score > float(current)) or (
        direction != "maximize" and score < float(current)
    ):
        candidate["best_score"] = score
        candidate["best_attempt_id"] = receipt.get("attempt_id")
