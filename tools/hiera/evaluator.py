"""Safe local command evaluator for immutable Hiera candidate snapshots."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from .adapter import source_snapshot_unchanged
from .common import (
    HieraError,
    canonical_digest,
    deep_get,
    finite_number,
    now_iso,
    project_root,
    read_json,
    sha256_file,
    validate_slug,
)
from .contract import verify_frozen
from .ledger import Ledger
from .remote_adapter import RemoteCommandAdapter


class CommandEvaluator:
    def __init__(self, run_dir: Path, contract: dict[str, Any], ledger: Ledger):
        self.run_dir = run_dir
        self.contract = contract
        self.ledger = ledger

    def _format(self, argv: list[str], values: dict[str, str]) -> list[str]:
        rendered: list[str] = []
        for item in argv:
            item_value = item
            for key, value in values.items():
                item_value = item_value.replace("{" + key + "}", value)
            rendered.append(item_value)
        return rendered

    def _run(self, argv: list[str], cwd: Path, log_dir: Path, timeout: int) -> dict[str, Any]:
        log_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = log_dir / "stdout.log"
        stderr_path = log_dir / "stderr.log"
        started = time.monotonic()
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=str(cwd),
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                    creationflags=creation_flags,
                )
            except OSError as exc:
                raise HieraError(f"could not start evaluator {argv[0]!r}: {exc}") from exc
            try:
                return_code = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
                try:
                    return_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    return_code = process.wait()
                timed_out = True
        return {
            "returncode": return_code,
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        }

    def _values(
        self, candidate_dir: Path, attempt_dir: Path, result_file: Path, config_file: Path
    ) -> dict[str, str]:
        return {
            "candidate_dir": str(candidate_dir),
            "run_dir": str(self.run_dir),
            "attempt_dir": str(attempt_dir),
            "result_file": str(result_file),
            "config_file": str(config_file),
            "entrypoint": self.contract["candidate"]["entrypoint"],
        }

    def _ensure_local_environment(self) -> None:
        if self.contract["resources"].get("environment") != "local":
            raise HieraError(
                "this evaluator is for local execution; remote dispatch is handled by "
                "RemoteCommandAdapter"
            )

    def _ensure_source_snapshot(self) -> None:
        manifest_path = self.run_dir / "manifest.json"
        if not manifest_path.is_file():
            return
        manifest = read_json(manifest_path)
        if manifest.get("wiki_snapshot") != self.contract.get("source"):
            raise HieraError(
                "Hiera manifest source snapshot does not match the approved contract"
            )
        if not source_snapshot_unchanged(project_root(self.run_dir), manifest):
            raise HieraError(
                "linked wiki source changed after Hiera run initialization; "
                "start a new sidecar run"
            )

    def _verify_candidate_snapshot(self, candidate: dict[str, Any], candidate_dir: Path) -> None:
        expected = candidate.get("file_digests")
        if not isinstance(expected, dict):
            raise HieraError("candidate has no immutable file digest manifest")
        actual: dict[str, str] = {}
        for relative in expected:
            path = candidate_dir / relative
            try:
                path.resolve().relative_to(candidate_dir.resolve())
            except ValueError as exc:
                raise HieraError(f"candidate file outside snapshot: {relative}") from exc
            if not path.is_file():
                raise HieraError(f"candidate file missing or outside snapshot: {relative}")
            actual[relative] = sha256_file(path)
        if actual != expected or canonical_digest(actual) != candidate.get("code_digest"):
            raise HieraError("candidate snapshot changed after admission")

    def preflight(self, candidate_id: str) -> dict[str, Any]:
        verify_frozen(self.contract)
        self._ensure_source_snapshot()
        validate_slug(candidate_id, "candidate_id")
        candidate = self.ledger.candidate(candidate_id)
        candidate_dir = self.run_dir / "candidates" / candidate_id
        if not candidate_dir.is_dir():
            raise HieraError(f"candidate snapshot missing: {candidate_dir}")
        self._verify_candidate_snapshot(candidate, candidate_dir)
        entrypoint = candidate_dir / self.contract["candidate"]["entrypoint"]
        if not entrypoint.is_file():
            raise HieraError(f"candidate entrypoint missing: {entrypoint}")
        if self.contract["resources"].get("environment") == "remote":
            return {
                "status": "passed",
                "candidate_id": candidate_id,
                "remote": "preflight command runs on remote submit",
                "checked_at": now_iso(),
            }
        self._ensure_local_environment()
        command = self.contract["evaluation"].get("preflight_command", [])
        if not command:
            return {"status": "passed", "candidate_id": candidate_id, "checked_at": now_iso()}
        attempt_dir = self.run_dir / "preflight" / candidate_id
        values = self._values(candidate_dir, attempt_dir, attempt_dir / "preflight.json", candidate_dir / "config.json")
        execution = self._run(
            self._format(command, values),
            candidate_dir,
            attempt_dir,
            int(self.contract["resources"]["timeout_seconds"]),
        )
        return {
            "status": "passed" if execution["returncode"] == 0 and not execution["timed_out"] else "failed",
            "candidate_id": candidate_id,
            "command_result": execution,
            "checked_at": now_iso(),
        }

    def evaluate(self, candidate_id: str, depth: str = "screen") -> dict[str, Any]:
        verify_frozen(self.contract)
        self._ensure_source_snapshot()
        if depth not in {"screen", "deep"}:
            raise HieraError("depth must be screen or deep")
        validate_slug(candidate_id, "candidate_id")
        candidate = self.ledger.candidate(candidate_id)
        candidate_dir = self.run_dir / "candidates" / candidate_id
        if not candidate_dir.is_dir():
            raise HieraError(f"candidate snapshot missing: {candidate_dir}")
        self._verify_candidate_snapshot(candidate, candidate_dir)
        if self.contract["resources"].get("environment") == "remote":
            return RemoteCommandAdapter(self.run_dir, self.contract, self.ledger).evaluate(
                candidate_id, depth
            )
        self._ensure_local_environment()
        attempt_id = self.ledger.reserve(
            candidate_id, depth, int(self.contract["resources"]["max_evaluations"])
        )
        attempt_dir = self.run_dir / "attempts" / attempt_id
        receipt_recorded = False
        try:
            attempt_dir.mkdir(parents=True, exist_ok=False)
            result_relative = Path(self.contract["evaluation"]["result_file"])
            result_file = (attempt_dir / result_relative).resolve()
            try:
                result_file.relative_to(attempt_dir.resolve())
            except ValueError as exc:
                raise HieraError("result_file escaped attempt directory") from exc
            result_file.parent.mkdir(parents=True, exist_ok=True)
            config_file = candidate_dir / "config.json"
            values = self._values(candidate_dir, attempt_dir, result_file, config_file)
            command = self._format(self.contract["evaluation"]["evaluate_command"], values)
            try:
                execution = self._run(
                    command,
                    candidate_dir,
                    attempt_dir,
                    int(self.contract["resources"]["timeout_seconds"]),
                )
            except HieraError as exc:
                execution = {"returncode": -1, "timed_out": False, "error": str(exc)}
            receipt: dict[str, Any] = {
                "depth": depth,
                "status": "failed",
                "direction": self.contract["evaluation"]["direction"],
                "attempt_id": attempt_id,
                "started_at": now_iso(),
                "execution": execution,
            }
            if execution.get("returncode") == 0 and not execution.get("timed_out") and result_file.is_file():
                try:
                    data = json.loads(result_file.read_text(encoding="utf-8"))
                    score = deep_get(data, self.contract["evaluation"]["score_path"])
                except (OSError, json.JSONDecodeError) as exc:
                    data, score = None, None
                    receipt["parse_error"] = str(exc)
                if finite_number(score):
                    receipt.update(
                        {
                            "status": "success",
                            "score": float(score),
                            "result": data,
                            "result_digest": sha256_file(result_file),
                        }
                    )
                else:
                    receipt["parse_error"] = "score_path did not resolve to a finite number"
            self.ledger.record_evaluation(
                attempt_id,
                candidate_id,
                {key: value for key, value in receipt.items() if key not in {"attempt_id", "candidate_id"}},
            )
            receipt_recorded = True
            self.ledger.set_status(candidate_id, "evaluated", last_attempt_id=attempt_id, last_depth=depth)
            return receipt
        except Exception as exc:
            if receipt_recorded:
                raise
            receipt = {
                "depth": depth,
                "status": "failed",
                "direction": self.contract["evaluation"]["direction"],
                "attempt_id": attempt_id,
                "started_at": now_iso(),
                "execution": {"returncode": -1, "timed_out": False, "error": str(exc)},
            }
            self.ledger.record_evaluation(
                attempt_id,
                candidate_id,
                {key: value for key, value in receipt.items() if key not in {"attempt_id", "candidate_id"}},
            )
            return receipt
