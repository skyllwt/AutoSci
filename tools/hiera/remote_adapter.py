"""Remote candidate deployment adapter for the optional Hiera workflow.

The adapter transfers one immutable candidate snapshot to a per-attempt
directory. It reuses connection fields from config/server.yaml through the
low-level helpers in tools.remote, but never calls the project-wide sync or
launch commands used by formal exp-run.
"""

from __future__ import annotations

import base64
import json
import posixpath
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    HieraError,
    atomic_write_json,
    canonical_digest,
    deep_get,
    finite_number,
    project_root,
    read_json,
    safe_child,
    sha256_file,
    sha256_bytes,
    validate_slug,
)
from .ledger import Ledger


class RemoteAdapterError(HieraError):
    """A remote transport or remote worker failure."""


class RemoteCommandAdapter:
    """Submit, poll, and collect one Hiera candidate on a remote host."""

    def __init__(self, run_dir: Path, contract: dict[str, Any], ledger: Ledger):
        self.run_dir = run_dir.resolve()
        self.contract = contract
        self.ledger = ledger
        self.project = project_root(self.run_dir)
        self.manifest = read_json(self.run_dir / "manifest.json")
        self.experiment = validate_slug(self.manifest.get("experiment"), "experiment slug")
        self.run_id = validate_slug(self.manifest.get("run_id"), "run id")
        resources = contract.get("resources", {})
        config_relative = resources.get("remote_config", "config/server.yaml")
        config_path = safe_child(self.project, *Path(config_relative).parts)
        try:
            from tools.remote import build_ssh_cmd, load_config
        except Exception as exc:  # pragma: no cover - import boundary
            raise RemoteAdapterError(f"could not load AutoSci remote helpers: {exc}") from exc
        self._build_ssh_cmd = build_ssh_cmd
        try:
            self.config = load_config(str(config_path))
        except SystemExit as exc:  # tools.remote uses _error for user-facing errors
            raise RemoteAdapterError(f"invalid remote config: {config_path}") from exc
        self.config_digest = canonical_digest(self.config)
        work_dir = self.config.get("work_dir")
        if (
            not isinstance(work_dir, str)
            or not work_dir.startswith("/")
            or work_dir.rstrip("/") == ""
            or "\\" in work_dir
            or "\x00" in work_dir
            or ".." in PurePosixPath(work_dir).parts
        ):
            raise RemoteAdapterError("remote work_dir must be an absolute POSIX path without '..'")
        self.remote_python = resources.get("remote_python", "python3")
        self.poll_seconds = float(resources.get("remote_poll_seconds", 5.0))
        if self.poll_seconds <= 0:
            raise RemoteAdapterError("resources.remote_poll_seconds must be positive")
        if shutil.which("ssh") is None:
            raise RemoteAdapterError("ssh executable is required for remote Hiera execution")
        self.worker_source = (
            Path(__file__).with_name("remote_worker.py").read_text(encoding="utf-8")
        )
        self.worker_digest = sha256_bytes(self.worker_source.encode("utf-8"))

    def _select_gpu(self) -> str | None:
        requested = self.contract.get("resources", {}).get("remote_gpu", "")
        if requested:
            if not re.fullmatch(r"[0-9]+(?:,[0-9]+)*", requested):
                raise RemoteAdapterError("resources.remote_gpu contains an invalid GPU index")
            return requested
        accelerator = str(self.contract.get("resources", {}).get("accelerator", "")).lower()
        if accelerator in {"", "cpu", "none"}:
            return None
        try:
            from tools.remote import parse_nvidia_smi, run_ssh
        except Exception as exc:  # pragma: no cover - import boundary
            raise RemoteAdapterError(f"could not load GPU helpers: {exc}") from exc
        rc, stdout, stderr = run_ssh(
            self.config,
            "nvidia-smi --query-gpu=index,name,memory.used,memory.total,"
            "utilization.gpu,temperature.gpu --format=csv,noheader,nounits",
            timeout=15,
        )
        if rc != 0:
            raise RemoteAdapterError(
                "remote GPU query failed: " + (stderr.strip() or f"exit {rc}")
            )
        gpus = parse_nvidia_smi(
            stdout, self.config.get("free_gpu_threshold_mib", 500)
        )
        free = [str(item["index"]) for item in gpus if item.get("free")]
        if not free:
            raise RemoteAdapterError("no free remote GPU is available")
        return free[0]

    @property
    def _remote_run_prefix(self) -> str:
        return posixpath.join("runs", "hiera", self.experiment, self.run_id)

    def _remote_attempt_rel(self, attempt_id: str) -> str:
        validate_slug(attempt_id, "attempt id")
        return posixpath.join(self._remote_run_prefix, attempt_id)

    @property
    def _remote_root(self) -> str:
        return str(self.config["work_dir"]).rstrip("/")

    def _rpc(self, request: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
        bootstrap = (
            "import base64,json,sys; "
            "payload=json.load(sys.stdin); source=base64.b64decode(payload['source']).decode('utf-8'); "
            "ns={'__name__':'hiera_remote_worker'}; "
            "exec(compile(source, 'hiera_remote_worker.py', 'exec'), ns); "
            "request=payload['request']; request['worker_source']=source if request.get('action')=='deploy' else request.get('worker_source'); "
            "result=ns['dispatch'](request); "
            "print(json.dumps(result, ensure_ascii=False))"
        )
        try:
            from tools.remote import conda_prefix
        except Exception as exc:  # pragma: no cover - import boundary
            raise RemoteAdapterError(f"could not load remote runtime helper: {exc}") from exc
        prefix = conda_prefix(self.config)
        runtime_command = f"{shlex.quote(str(self.remote_python))} -c {shlex.quote(bootstrap)}"
        command = f"bash -lc {shlex.quote((prefix + ' && ' if prefix else '') + 'exec ' + runtime_command)}"
        try:
            completed = subprocess.run(
                self._build_ssh_cmd(self.config) + [command],
                input=json.dumps({
                    "source": base64.b64encode(self.worker_source.encode("utf-8")).decode("ascii"),
                    "request": request,
                }, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RemoteAdapterError(f"remote RPC timed out after {timeout}s") from exc
        except OSError as exc:
            raise RemoteAdapterError(f"could not start SSH: {exc}") from exc
        if completed.returncode != 0:
            raise RemoteAdapterError(
                "remote RPC failed: "
                + (completed.stderr.strip() or f"exit {completed.returncode}")
            )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RemoteAdapterError("remote RPC returned no JSON response")
        try:
            response = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise RemoteAdapterError(
                f"remote RPC returned invalid JSON: {lines[-1][:200]}"
            ) from exc
        if not isinstance(response, dict):
            raise RemoteAdapterError("remote RPC response must be an object")
        if response.get("status") == "error":
            raise RemoteAdapterError(str(response.get("error", "remote worker failed")))
        return response

    @staticmethod
    def _format(argv: list[str], values: dict[str, str]) -> list[str]:
        output = []
        for item in argv:
            rendered = item
            for key, value in values.items():
                rendered = rendered.replace("{" + key + "}", value)
            output.append(rendered)
        return output

    def _candidate_files(
        self, candidate: dict[str, Any], candidate_dir: Path
    ) -> dict[str, dict[str, str]]:
        files: dict[str, dict[str, str]] = {}
        for relative, expected_digest in candidate.get("file_digests", {}).items():
            relative = str(PurePosixPath(relative.replace("\\", "/")))
            path = safe_child(candidate_dir, *Path(relative).parts)
            if not path.is_file() or sha256_file(path) != expected_digest:
                raise RemoteAdapterError(
                    f"candidate snapshot changed before remote upload: {relative}"
                )
            files[relative] = {
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                "sha256": expected_digest,
            }
        return files

    def _job(self, candidate_id: str, depth: str, attempt_id: str) -> dict[str, Any]:
        candidate = self.ledger.candidate(candidate_id)
        candidate_dir = safe_child(self.run_dir, "candidates", candidate_id)
        remote_attempt = self._remote_attempt_rel(attempt_id)
        remote_attempt_abs = posixpath.join(self._remote_root, remote_attempt)
        remote_candidate = posixpath.join(remote_attempt_abs, "candidate")
        result_relative = str(
            PurePosixPath(self.contract["evaluation"]["result_file"].replace("\\", "/"))
        )
        values = {
            "candidate_dir": remote_candidate,
            "run_dir": remote_attempt_abs,
            "attempt_dir": remote_attempt_abs,
            "result_file": posixpath.join(remote_attempt_abs, result_relative),
            "config_file": posixpath.join(remote_candidate, "config.json"),
            "entrypoint": self.contract["candidate"]["entrypoint"],
        }
        immutable = {
            "contract_digest": self.contract["state"]["contract_digest"],
            "candidate_digest": candidate["code_digest"],
            "attempt_id": attempt_id,
            "remote_attempt": remote_attempt,
            "remote_root": self._remote_root,
            "config_digest": self.config_digest,
            "worker_digest": self.worker_digest,
        }
        gpu = self._select_gpu()
        runtime = {
            "python": self.remote_python,
            "conda": self.config.get("conda"),
            "env_setup": self.config.get("env_setup", ""),
        }
        job = {
            **immutable,
            "attempt_id": attempt_id,
            "remote_attempt": remote_attempt,
            "candidate_id": candidate_id,
            "depth": depth,
            "argv": self._format(self.contract["evaluation"]["evaluate_command"], values),
            "preflight_argv": self._format(
                self.contract["evaluation"].get("preflight_command", []), values
            ),
            "result_file": result_relative,
            "score_path": self.contract["evaluation"]["score_path"],
            "timeout_seconds": int(self.contract["resources"]["timeout_seconds"]),
            "runtime": runtime,
            "gpu": gpu,
            "files": self._candidate_files(candidate, candidate_dir),
        }
        job["token"] = canonical_digest(job)
        return job

    def submit(self, candidate_id: str, depth: str, attempt_id: str) -> dict[str, Any]:
        attempt_dir = safe_child(self.run_dir, "attempts", attempt_id)
        existing = attempt_dir / "remote.json"
        if existing.exists():
            try:
                stored = read_json(existing)
            except (HieraError, OSError) as exc:
                raise RemoteAdapterError(f"local remote attempt metadata is unreadable: {exc}") from exc
            if (
                stored.get("attempt_id") != attempt_id
                or stored.get("candidate_id") != candidate_id
                or stored.get("depth") != depth
            ):
                raise RemoteAdapterError("local remote attempt metadata belongs to another evaluation")
            if stored.get("remote_root") != self._remote_root or stored.get("config_digest") != self.config_digest:
                raise RemoteAdapterError("local remote attempt metadata uses another server configuration")
            return stored
        job = self._job(candidate_id, depth, attempt_id)
        if attempt_dir.exists():
            raise RemoteAdapterError(
                f"attempt directory already exists without a recoverable remote handle: {attempt_dir}"
            )
        try:
            attempt_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise RemoteAdapterError(f"could not create local remote attempt directory: {exc}") from exc
        pending = {
            "status": "deploying",
            "token": job["token"],
            "attempt_id": attempt_id,
            "candidate_id": candidate_id,
            "candidate_digest": job["candidate_digest"],
            "contract_digest": job["contract_digest"],
            "depth": depth,
            "remote_attempt": job["remote_attempt"],
            "host": self.config["host"],
            "remote_work_dir": self.config["work_dir"],
            "remote_root": self._remote_root,
            "config_digest": self.config_digest,
            "worker_digest": self.worker_digest,
            "gpu": job.get("gpu"),
            "submitted_at": None,
        }
        # Persist the handle before the first SSH side effect.  If the client
        # disconnects during deployment, recover can inspect this exact token
        # and never start a second remote process.
        try:
            atomic_write_json(existing, pending)
        except OSError as exc:
            raise RemoteAdapterError(f"could not persist remote attempt handle: {exc}") from exc
        try:
            from tools.remote import run_ssh
        except Exception as exc:  # pragma: no cover - import boundary
            raise RemoteAdapterError(f"could not load SSH helper: {exc}") from exc
        managed_root = posixpath.join(self._remote_root, "runs", "hiera")
        rc, _stdout, stderr = run_ssh(
            self.config, f"mkdir -p {shlex.quote(managed_root)}", timeout=15
        )
        if rc != 0:
            raise RemoteAdapterError(
                "could not prepare remote Hiera root: "
                + (stderr.strip() or f"exit {rc}")
            )
        response = self._rpc(
            {
                "action": "deploy",
                "root": self._remote_root,
                "remote_attempt_rel": job["remote_attempt"],
                "attempt_id": attempt_id,
                "token": job["token"],
                "job": job,
            }
        )
        handle = {
            "status": response.get("status", "submitted"),
            "token": job["token"],
            "attempt_id": attempt_id,
            "candidate_id": candidate_id,
            "candidate_digest": job["candidate_digest"],
            "contract_digest": job["contract_digest"],
            "depth": depth,
            "remote_attempt": job["remote_attempt"],
            "host": self.config["host"],
            "remote_work_dir": self.config["work_dir"],
            "remote_root": self._remote_root,
            "config_digest": self.config_digest,
            "worker_digest": self.worker_digest,
            "gpu": job.get("gpu"),
            "submitted_at": response.get("submitted_at"),
        }
        atomic_write_json(existing, handle)
        return handle

    def _load_handle(self, attempt_id: str) -> dict[str, Any]:
        validate_slug(attempt_id, "attempt id")
        path = safe_child(self.run_dir, "attempts", attempt_id, "remote.json")
        if not path.is_file():
            raise RemoteAdapterError(f"remote handle is missing for {attempt_id}")
        try:
            handle = read_json(path)
        except (HieraError, OSError) as exc:
            raise RemoteAdapterError(f"remote handle is unreadable: {exc}") from exc
        if not isinstance(handle, dict) or handle.get("attempt_id") != attempt_id:
            raise RemoteAdapterError("remote handle is malformed")
        for key in ("token", "remote_attempt", "candidate_id", "candidate_digest", "contract_digest", "worker_digest", "depth", "host"):
            if not isinstance(handle.get(key), str) or not handle[key]:
                raise RemoteAdapterError(f"remote handle is missing {key}")
        if handle.get("remote_root") != self._remote_root:
            raise RemoteAdapterError("remote handle root differs from current server configuration")
        if handle.get("config_digest") != self.config_digest:
            raise RemoteAdapterError("remote handle server configuration has changed")
        if handle.get("worker_digest") != self.worker_digest:
            raise RemoteAdapterError("remote worker source changed; inspect the attempt before recovery")
        if handle.get("host") != self.config.get("host"):
            raise RemoteAdapterError("remote handle host differs from current server configuration")
        if handle.get("remote_attempt") != self._remote_attempt_rel(attempt_id):
            raise RemoteAdapterError("remote handle path is not the canonical attempt path")
        if handle.get("contract_digest") != self.contract.get("state", {}).get("contract_digest"):
            raise RemoteAdapterError("remote handle contract digest differs from the approved contract")
        reservation = [
            item for item in self.ledger.reservations() if item.get("attempt_id") == attempt_id
        ]
        if len(reservation) != 1 or reservation[0].get("candidate_id") != handle.get("candidate_id") or reservation[0].get("depth") != handle.get("depth"):
            raise RemoteAdapterError("remote handle does not match the ledger reservation")
        candidate = self.ledger.candidate(handle["candidate_id"])
        if candidate.get("code_digest") != handle.get("candidate_digest"):
            raise RemoteAdapterError("remote handle candidate digest differs from the ledger")
        return handle

    def _record_receipt(self, handle: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
        attempt_id = handle["attempt_id"]
        candidate_id = handle["candidate_id"]
        self.ledger.record_evaluation(
            attempt_id,
            candidate_id,
            {key: value for key, value in receipt.items() if key not in {"attempt_id", "candidate_id"}},
        )
        self.ledger.set_status(
            candidate_id,
            "evaluated",
            last_attempt_id=attempt_id,
            last_depth=handle["depth"],
        )
        return receipt

    def _wait_for_handle(self, handle: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + int(self.contract["resources"]["timeout_seconds"]) + 30
        while True:
            state = self.poll(handle)
            if state.get("status") in {"completed", "failed"}:
                return self._record_receipt(handle, self.collect(handle))
            if state.get("status") in {"missing", "unknown", "lost"}:
                raise RemoteAdapterError(f"remote attempt {state.get('status')}")
            if time.monotonic() >= deadline:
                raise RemoteAdapterError(
                    "remote attempt did not finish within timeout; use recover to inspect the same attempt"
                )
            time.sleep(self.poll_seconds)

    def recover(self, attempt_id: str) -> dict[str, Any]:
        """Resume polling an existing reserved remote attempt without resubmission."""
        handle = self._load_handle(attempt_id)
        candidate = self.ledger.candidate(handle["candidate_id"])
        candidate_dir = safe_child(self.run_dir, "candidates", handle["candidate_id"])
        expected = candidate.get("file_digests")
        if not isinstance(expected, dict):
            raise HieraError("candidate has no immutable file digest manifest")
        actual: dict[str, str] = {}
        for relative in expected:
            path = safe_child(candidate_dir, *Path(relative).parts)
            if not path.is_file():
                raise HieraError(f"candidate snapshot file is missing: {relative}")
            actual[relative] = sha256_file(path)
        if actual != expected or canonical_digest(actual) != candidate.get("code_digest"):
            raise HieraError("candidate snapshot changed; start a new sidecar run")
        for receipt in self.ledger.evaluations():
            if receipt.get("attempt_id") == attempt_id:
                return {
                    key: value for key, value in receipt.items()
                    if key != "candidate_id"
                }
        try:
            return self._wait_for_handle(handle)
        except RemoteAdapterError as exc:
            message = str(exc)
            state = self.poll(handle)
            if state.get("status") not in {"missing", "unknown", "lost"}:
                raise HieraError(
                    f"remote attempt remains reserved; retry recover later: {message}"
                ) from exc
            receipt = {
                "depth": handle["depth"],
                "status": "failed",
                "direction": self.contract["evaluation"]["direction"],
                "attempt_id": attempt_id,
                "started_at": state.get("started_at"),
                "execution": state.get("execution", {"error": message}),
                "remote": {
                    "host": handle["host"],
                    "remote_attempt": handle["remote_attempt"],
                    "status": state.get("status"),
                },
                "parse_error": f"remote attempt was not recoverable: {state.get('status')}",
            }
            return self._record_receipt(handle, receipt)

    def inspect(self, attempt_id: str, *, collect_terminal: bool = True) -> dict[str, Any]:
        """Poll one existing attempt once, optionally collecting a terminal job.

        This is the non-blocking counterpart to :meth:`recover`, used by the
        Hiera sidecar status command.  It never submits or reserves work.  A
        terminal attempt is collected and recorded exactly once when requested;
        a running attempt is returned immediately for a later status check.
        """

        handle = self._load_handle(attempt_id)
        for receipt in self.ledger.evaluations():
            if receipt.get("attempt_id") == attempt_id:
                return {
                    "attempt_id": attempt_id,
                    "status": "collected",
                    "receipt": receipt,
                }
        state = self.poll(handle)
        status = state.get("status")
        if collect_terminal and status in {"completed", "failed"}:
            receipt = self._record_receipt(handle, self.collect(handle))
            return {"attempt_id": attempt_id, "status": "collected", "receipt": receipt}
        return {
            "attempt_id": attempt_id,
            "status": status or "unknown",
            "remote": {
                "host": handle.get("host"),
                "remote_attempt": handle.get("remote_attempt"),
            },
            "execution": state.get("execution"),
            "last_lines": state.get("last_lines", []),
            "anomalies": state.get("anomalies", []),
            "reason": state.get("reason"),
        }

    def poll(self, handle: dict[str, Any]) -> dict[str, Any]:
        return self._rpc(
            {
                "action": "check",
                "root": self._remote_root,
                "remote_attempt_rel": handle["remote_attempt"],
                "token": handle["token"],
                "attempt_id": handle["attempt_id"],
            },
            timeout=30,
        )

    def collect(self, handle: dict[str, Any]) -> dict[str, Any]:
        response = self._rpc(
            {
                "action": "collect",
                "root": self._remote_root,
                "remote_attempt_rel": handle["remote_attempt"],
                "token": handle["token"],
                "attempt_id": handle["attempt_id"],
            },
            timeout=30,
        )
        if response.get("status") not in {"completed", "failed"}:
            raise RemoteAdapterError(
                f"remote attempt is not complete: {response.get('status')}"
            )
        attempt_dir = safe_child(self.run_dir, "attempts", handle["attempt_id"])
        for relative, encoded in (response.get("files") or {}).items():
            target = safe_child(attempt_dir, *Path(relative).parts)
            if not isinstance(encoded, str):
                raise RemoteAdapterError(f"remote file payload is not base64: {relative}")
            try:
                data = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise RemoteAdapterError(f"remote file payload is invalid: {relative}") from exc
            if len(data) > 16 * 1024 * 1024:
                raise RemoteAdapterError(f"remote file is too large to collect: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        result_file = safe_child(
            attempt_dir,
            *Path(self.contract["evaluation"]["result_file"].replace("\\", "/")).parts,
        )
        receipt: dict[str, Any] = {
            "depth": handle["depth"],
            "status": "failed",
            "direction": self.contract["evaluation"]["direction"],
            "attempt_id": handle["attempt_id"],
            "started_at": response.get("started_at"),
            "execution": response.get("execution", {}),
            "remote": {
                "host": handle["host"],
                "remote_attempt": handle["remote_attempt"],
                "status": response.get("status"),
            },
        }
        execution = receipt["execution"]
        execution_success = (
            isinstance(execution, dict)
            and execution.get("outcome") == "success"
            and execution.get("evaluation", {}).get("returncode") == 0
        )
        if result_file.is_file() and execution_success:
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
        else:
            receipt["parse_error"] = "remote result file was not collected"
        return receipt

    def evaluate(self, candidate_id: str, depth: str = "screen") -> dict[str, Any]:
        attempt_id = self.ledger.reserve(
            candidate_id, depth, int(self.contract["resources"]["max_evaluations"])
        )
        handle: dict[str, Any] | None = None
        try:
            handle = self.submit(candidate_id, depth, attempt_id)
            return self._wait_for_handle(handle)
        except RemoteAdapterError as exc:
            if handle is None:
                try:
                    handle = self._load_handle(attempt_id)
                except RemoteAdapterError:
                    handle = None
            if handle is not None:
                raise HieraError(
                    f"{exc}; evaluation reservation remains active; run `hiera ... recover --attempt {attempt_id}`"
                ) from exc
            remote_attempt = (
                handle.get("remote_attempt")
                if handle is not None
                else self._remote_attempt_rel(attempt_id)
            )
            receipt = {
                "depth": depth,
                "status": "failed",
                "direction": self.contract["evaluation"]["direction"],
                "attempt_id": attempt_id,
                "execution": {"error": str(exc)},
                "remote": {
                    "host": self.config.get("host"),
                    "remote_attempt": remote_attempt,
                    "status": "unknown",
                },
            }
            self.ledger.record_evaluation(
                attempt_id,
                candidate_id,
                {key: value for key, value in receipt.items() if key not in {"attempt_id", "candidate_id"}},
            )
            return receipt
