"""Small, fail-closed worker used by the optional Hiera remote adapter.

The module deliberately has no dependency on AutoSci's package imports.  A
transport may copy this file to a remote host and invoke ``dispatch`` through
an ordinary Python bootstrap, or start it directly with ``--execute``.  The
worker only operates inside one managed Hiera attempt directory; it never
syncs a repository and never removes files.

The public protocol is intentionally narrow:

``deploy``
    Verify and materialise a job and candidate files, then start one detached
    worker process.  Repeating the request with the same token is idempotent;
    a different token is a conflict and is never allowed to overwrite an
    attempt.

``check`` / ``collect``
    Verify the request token against the persisted job before reading state.
    ``collect`` returns bounded tails of the four logs and the bounded JSON
    result file after completion.

The code uses only the Python standard library so it can be bootstrapped on a
remote machine without installing the AutoSci environment.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import os
import re
import signal
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
MAX_LOG_BYTES = 1024 * 1024
MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 256 * 1024 * 1024
ATTEMPT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ANOMALY_PATTERNS = (
    (re.compile(r"\bnan\b"), "NaN detected"),
    (re.compile(r"\binf\b"), "Inf detected"),
    (re.compile(r"out of memory"), "out of memory"),
    (re.compile(r"traceback"), "traceback"),
)


class RemoteWorkerError(RuntimeError):
    """An invalid request or a fail-closed worker state."""


def _now() -> float:
    return time.time()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _finite_timeout(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RemoteWorkerError("timeout_seconds must be a positive integer")
    # A very large timeout can overflow platform APIs or make a malformed
    # request effectively unbounded.  The parent contract normally imposes a
    # much smaller limit; this cap is only a worker-side sanity bound.
    if value > 7 * 24 * 60 * 60:
        raise RemoteWorkerError("timeout_seconds exceeds the worker limit")
    return value


def _token(value: Any) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise RemoteWorkerError("token must be a sha256:<64 lowercase hex> digest")
    return value


def _attempt_id(value: Any) -> str:
    if not isinstance(value, str) or not ATTEMPT_RE.fullmatch(value):
        raise RemoteWorkerError("attempt_id must be lowercase kebab-case")
    return value


def _portable_rel(value: Any, label: str = "path") -> str:
    """Validate a canonical POSIX relative path and return it unchanged."""

    if not isinstance(value, str) or not value:
        raise RemoteWorkerError(f"{label} must be a non-empty relative path")
    if "\x00" in value or "\\" in value:
        raise RemoteWorkerError(f"{label} must use portable POSIX separators")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise RemoteWorkerError(f"{label} must be relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RemoteWorkerError(f"{label} contains an unsafe path component")
    if any(":" in part for part in parts):
        raise RemoteWorkerError(f"{label} contains a drive-like component")
    # Reject alternate spellings such as ``a//b`` and ``a/./b``.  This keeps
    # token binding and collect keys deterministic across platforms.
    if "/".join(parts) != value:
        raise RemoteWorkerError(f"{label} is not canonical")
    return value


def _parts(path: Path) -> list[str]:
    return [part.lower() for part in path.parts if part not in {"/", "\\"}]


def _has_runs_hiera(path: Path) -> bool:
    names = _parts(path)
    return any(names[index : index + 2] == ["runs", "hiera"] for index in range(len(names) - 1))


def _absolute_without_resolving(path: Path) -> Path:
    """Return an absolute lexical path while preserving every symlink hop."""

    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_ancestors(path: Path) -> None:
    """Reject symlink components from an absolute path up to its anchor."""

    current = _absolute_without_resolving(path)
    while True:
        if current.exists() and current.is_symlink():
            raise RemoteWorkerError(f"symlinks are not allowed in managed paths: {current}")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _managed_root(value: Any, *, allow_repo_root: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise RemoteWorkerError("root must be an absolute managed path")
    raw = Path(value)
    if not raw.is_absolute():
        raise RemoteWorkerError("root must be absolute")
    _reject_symlink_ancestors(raw)
    root = raw.resolve(strict=False)
    has_pair = _has_runs_hiera(root)
    if not has_pair and allow_repo_root:
        # A repository/work directory is accepted with remote_attempt_rel.
        # The relative attempt itself must begin with runs/hiera (checked by
        # _resolve_attempt), and the directory may legitimately be created by
        # this first deployment on a fresh remote checkout.
        if root.exists() and not root.is_dir():
            raise RemoteWorkerError("repository root is not a directory")
    elif not has_pair:
        raise RemoteWorkerError("root must be below a runs/hiera directory")
    if root.exists() and not root.is_dir():
        raise RemoteWorkerError("root is not a directory")
    return root


def _inside(root: Path, candidate: Path) -> Path:
    root = root.resolve(strict=False)
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RemoteWorkerError("path escapes the managed root") from exc
    return candidate


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    """Reject an existing symlink anywhere between ``stop`` and ``path``."""

    # Do not resolve either side before walking.  Resolving first would hide
    # precisely the intermediate symlink this guard is meant to reject.
    stop = _absolute_without_resolving(stop)
    current = _absolute_without_resolving(path)
    try:
        current.relative_to(stop)
    except ValueError as exc:
        raise RemoteWorkerError("managed path does not descend from its root") from exc
    while True:
        if current.exists() and current.is_symlink():
            raise RemoteWorkerError(f"symlinks are not allowed in managed paths: {current}")
        if current == stop:
            return
        parent = current.parent
        if parent == current:
            raise RemoteWorkerError("managed path does not descend from its root")
        current = parent


def _validate_execution_paths(
    attempt_arg: str, root_arg: str | None = None
) -> tuple[Path, Path, str]:
    """Authenticate the filesystem boundary before a detached worker writes.

    Validation starts from lexical, unresolved paths so symlink components
    remain visible.  Only after the complete root-to-attempt chain is clean do
    we resolve paths and prove containment a second time.
    """

    if not isinstance(attempt_arg, str) or not attempt_arg:
        raise RemoteWorkerError("execute path is required")
    raw_attempt = Path(attempt_arg)
    if not raw_attempt.is_absolute():
        raise RemoteWorkerError("execute path must be absolute")
    lexical_attempt = _absolute_without_resolving(raw_attempt)

    if root_arg is not None:
        if not isinstance(root_arg, str) or not root_arg:
            raise RemoteWorkerError("managed root must be an absolute path")
        raw_root = Path(root_arg)
        if not raw_root.is_absolute():
            raise RemoteWorkerError("managed root must be absolute")
        lexical_root = _absolute_without_resolving(raw_root)
        _reject_symlink_ancestors(lexical_root)
        # A caller-supplied root may be the repository/work directory even if
        # one of its ancestors happens to be named "runs".  Layout validation
        # below, rather than that incidental component, establishes authority.
        root = _managed_root(str(lexical_root), allow_repo_root=True)
    else:
        if lexical_attempt.parent.name.lower() != "attempts":
            raise RemoteWorkerError("--root is required outside a run-root attempts directory")
        lexical_root = lexical_attempt.parent.parent
        root = _managed_root(str(lexical_root), allow_repo_root=False)

    _reject_symlink_chain(lexical_attempt, lexical_root)
    attempt = _inside(root, lexical_attempt)
    if not attempt.is_dir():
        raise RemoteWorkerError("execute path must be an existing attempt directory")
    attempt_id = _attempt_id(attempt.name)

    try:
        relative = attempt.relative_to(root)
    except ValueError as exc:  # defensive: _inside already performs this check
        raise RemoteWorkerError("execute path escaped the managed root") from exc
    relative_parts = [part.lower() for part in relative.parts]
    relative_has_hiera = any(
        relative_parts[index : index + 2] == ["runs", "hiera"]
        for index in range(len(relative_parts) - 1)
    )
    if not (relative_parts[:1] == ["attempts"] or relative_has_hiera):
        raise RemoteWorkerError("execute path is outside the Hiera attempt layout")
    return root, attempt, attempt_id


def _mkdir_chain(path: Path, root: Path) -> None:
    """Create directories one component at a time without following links."""

    root = root.resolve(strict=False)
    path = _inside(root, path)
    relative = path.relative_to(root)
    current = root
    if current.exists() and (current.is_symlink() or not current.is_dir()):
        raise RemoteWorkerError(f"managed root is not a real directory: {current}")
    for component in relative.parts:
        current = current / component
        if current.exists():
            if current.is_symlink() or not current.is_dir():
                raise RemoteWorkerError(f"managed directory is not a real directory: {current}")
        else:
            current.mkdir()


def _atomic_bytes(path: Path, data: bytes, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_chain(path, path.parent)
    if not replace and path.exists():
        raise RemoteWorkerError(f"refusing to overwrite existing file: {path}")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    if os.name != "nt":
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # Directory fsync is not available on every mounted filesystem;
            # the file itself has already been fsynced and atomically renamed.
            pass


def _atomic_json(path: Path, value: Any, *, replace: bool = True) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        replace=replace,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RemoteWorkerError(f"missing JSON file: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RemoteWorkerError(f"invalid JSON file: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RemoteWorkerError(f"JSON file must contain an object: {path}")
    return value


def _read_source() -> str:
    try:
        source_path = Path(__file__).resolve()
        source = source_path.read_text(encoding="utf-8")
    except (NameError, OSError) as exc:
        raise RemoteWorkerError("worker_source is required when __file__ is unavailable") from exc
    if not source or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise RemoteWorkerError("worker source is empty or too large")
    return source


def _resolve_attempt(root: Path, request: dict[str, Any]) -> tuple[Path, str]:
    requested_id = request.get("attempt_id")
    relative = request.get("remote_attempt_rel")
    if requested_id is not None:
        requested_id = _attempt_id(requested_id)
    if relative is not None:
        relative = _portable_rel(relative, "remote_attempt_rel")
        relative_path = PurePosixPath(relative)
        if relative_path.parts[-1] != (requested_id or relative_path.parts[-1]):
            raise RemoteWorkerError("remote_attempt_rel and attempt_id disagree")
        lexical_attempt = root.joinpath(*relative_path.parts)
        _reject_symlink_chain(lexical_attempt, root)
        attempt = _inside(root, lexical_attempt)
        attempt_id = requested_id or _attempt_id(relative_path.parts[-1])
    else:
        if requested_id is None:
            raise RemoteWorkerError("attempt_id or remote_attempt_rel is required")
        attempt_id = requested_id
        lexical_attempt = root / "attempts" / attempt_id
        _reject_symlink_chain(lexical_attempt, root)
        attempt = _inside(root, lexical_attempt)
    # A remote path must still be recognisably an attempt path.  Accept both
    # a run-root ``attempts/<id>`` and a repository-root
    # ``runs/hiera/<exp>/<run>/<attempt>`` form.
    rel_parts = [part.lower() for part in attempt.relative_to(root).parts]
    has_hiera_prefix = any(
        rel_parts[i : i + 2] == ["runs", "hiera"] for i in range(len(rel_parts) - 1)
    )
    if not (rel_parts[:1] == ["attempts"] or has_hiera_prefix):
        raise RemoteWorkerError("remote attempt path is outside the Hiera attempt layout")
    return attempt, attempt_id


def _request_context(request: dict[str, Any], *, action: str) -> tuple[Path, Path, str, str]:
    if not isinstance(request, dict):
        raise RemoteWorkerError("request must be an object")
    if request.get("action") != action:
        raise RemoteWorkerError(f"request action must be {action!r}")
    token = _token(request.get("token"))
    # A supplied remote_attempt_rel may describe a repository-root path.  In
    # that form allow the repository root only after checking the relative
    # path itself contains runs/hiera; _resolve_attempt performs the layout
    # check below.
    relative = request.get("remote_attempt_rel")
    root = _managed_root(request.get("root"), allow_repo_root=relative is not None)
    attempt, attempt_id = _resolve_attempt(root, request)
    return root, attempt, attempt_id, token


def _job_token(job: dict[str, Any]) -> str:
    value = job.get("token", job.get("token_binding"))
    return _token(value)


def _load_bound_job(attempt: Path, token: str) -> dict[str, Any]:
    job = _read_json(attempt / "job.json")
    persisted = _job_token(job)
    if persisted != token:
        raise RemoteWorkerError("request token does not match the persisted job")
    binding = job.get("_job_binding_digest")
    if not isinstance(binding, str) or not SHA256_RE.fullmatch(binding):
        raise RemoteWorkerError("persisted job has no valid binding digest")
    unsigned = {key: value for key, value in job.items() if key != "_job_binding_digest"}
    if _digest(unsigned) != binding:
        raise RemoteWorkerError("persisted job binding digest does not match")
    return job


def _validate_argv(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RemoteWorkerError(f"{label} must be a list of non-empty strings")
    return list(value)


def _validate_job(raw: Any, token: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RemoteWorkerError("job must be an object")
    job = copy.deepcopy(raw)
    if _job_token(job) != token:
        raise RemoteWorkerError("job token does not match request token")
    job["token"] = token
    _validate_argv(job.get("argv"), "job.argv")
    _validate_argv(job.get("preflight_argv", []), "job.preflight_argv")
    _finite_timeout(job.get("timeout_seconds"))
    gpu = job.get("gpu")
    if gpu is not None and (not isinstance(gpu, str) or "\x00" in gpu or "\n" in gpu or "\r" in gpu):
        raise RemoteWorkerError("job.gpu must be null or a single-line string")
    result_file = _portable_rel(job.get("result_file"), "job.result_file")
    job["result_file"] = result_file
    files = job.get("files")
    if not isinstance(files, dict):
        raise RemoteWorkerError("job.files must be an object")
    # Validate and normalize every file before creating the attempt.  The
    # returned job retains the base64 payload so job.json is a complete,
    # inspectable deployment receipt.
    file_digests: dict[str, str] = {}
    total_bytes = 0
    for name, record in files.items():
        _portable_rel(name, "candidate file")
        if not isinstance(record, dict):
            raise RemoteWorkerError(f"candidate file record must be an object: {name}")
        data = record.get("data")
        digest = record.get("sha256")
        if not isinstance(data, str):
            raise RemoteWorkerError(f"candidate file data must be base64 text: {name}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise RemoteWorkerError(f"candidate file sha256 is invalid: {name}")
        try:
            decoded = base64.b64decode(data.encode("ascii"), validate=True)
        except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
            raise RemoteWorkerError(f"candidate file data is not valid base64: {name}") from exc
        if len(decoded) > MAX_FILE_BYTES:
            raise RemoteWorkerError(f"candidate file is too large: {name}")
        total_bytes += len(decoded)
        actual = "sha256:" + hashlib.sha256(decoded).hexdigest()
        if actual != digest:
            raise RemoteWorkerError(f"candidate file digest mismatch: {name}")
        file_digests[name] = digest
    if total_bytes > MAX_TOTAL_FILE_BYTES:
        raise RemoteWorkerError(f"candidate snapshot exceeds {MAX_TOTAL_FILE_BYTES} bytes")
    candidate_digest = job.get("candidate_digest")
    if not isinstance(candidate_digest, str) or _digest(file_digests) != candidate_digest:
        raise RemoteWorkerError("candidate snapshot digest does not match the job")
    return job


def _candidate_file_path(candidate: Path, relative: str) -> Path:
    path = _inside(candidate, candidate.joinpath(*PurePosixPath(relative).parts))
    _reject_symlink_chain(path, candidate)
    return path


def _materialize_files(attempt: Path, files: dict[str, Any]) -> None:
    candidate = attempt / "candidate"
    candidate.mkdir(parents=True, exist_ok=False)
    for name in sorted(files):
        relative = _portable_rel(name, "candidate file")
        target = _candidate_file_path(candidate, relative)
        record = files[name]
        decoded = base64.b64decode(record["data"].encode("ascii"), validate=True)
        _mkdir_chain(target.parent, candidate)
        _reject_symlink_chain(target, candidate)
        # O_EXCL prevents a late race from replacing a file that was already
        # materialised.  The enclosing attempt is fresh and is never removed
        # on error, leaving an inspectable failed deployment.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        fd = os.open(str(target), flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(decoded)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            try:
                os.close(fd)
            except OSError:
                pass


def _pid_alive(pid: Any) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _execution(attempt: Path) -> dict[str, Any] | None:
    path = attempt / "execution.json"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return _read_json(path)
    except RemoteWorkerError:
        return None


def _monitor_snapshot(attempt: Path) -> dict[str, Any]:
    """Return bounded live log tails and exp-status-style anomaly hints."""

    lines: list[str] = []
    for path in _log_paths(attempt):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data, _truncated = _tail(path, min(MAX_LOG_BYTES, 64 * 1024))
        except OSError:
            # A log can appear between the existence check and the read while
            # the detached worker is opening it.  A status poll must remain
            # non-blocking and should simply omit that tail.
            continue
        text = data.decode("utf-8", errors="replace")
        lines.extend(text.splitlines())
    recent = lines[-20:]
    lowered = "\n".join(lines).lower()
    anomalies = [label for pattern, label in _ANOMALY_PATTERNS if pattern.search(lowered)]
    return {"last_lines": recent, "anomalies": anomalies}
def _status(attempt: Path, token: str) -> dict[str, Any]:
    if not attempt.exists():
        return {"status": "missing"}
    if attempt.is_symlink() or not attempt.is_dir():
        raise RemoteWorkerError("attempt path is not a directory")
    job = _load_bound_job(attempt, token)
    execution = _execution(attempt)
    monitor = _monitor_snapshot(attempt)
    if execution is not None:
        if execution.get("status") == "completed":
            # Keep the transport-level status useful to schedulers while the
            # detailed, immutable outcome remains in execution.json.
            status = "completed" if execution.get("outcome") == "success" else "failed"
            return {
                "status": status,
                "execution": execution,
                "started_at": execution.get("started_at"),
                "finished_at": execution.get("finished_at"),
                "outcome": execution.get("outcome"),
                **monitor,
            }
        if execution.get("status") == "running":
            pid = execution.get("pid")
            if not _pid_alive(pid):
                pid_path = attempt / "worker.pid"
                if pid_path.is_file() and not pid_path.is_symlink():
                    try:
                        pid = int(pid_path.read_text(encoding="ascii").strip())
                    except (OSError, ValueError):
                        pid = None
            if _pid_alive(pid):
                return {
                    "status": "running",
                    "execution": execution,
                    "started_at": execution.get("started_at"),
                    **monitor,
                }
            # Detached processes on Windows can take a short moment to become
            # visible to os.kill(pid, 0).  Honour the durable running marker
            # during that startup window; after it expires, expose an
            # interrupted worker as unknown for explicit recovery.
            started = execution.get("started_at")
            if isinstance(started, (int, float)) and not isinstance(started, bool):
                if 0 <= _now() - float(started) <= 2.0:
                    return {
                        "status": "running",
                        "execution": execution,
                        "started_at": execution.get("started_at"),
                        **monitor,
                    }
            # A stale running marker with no live process is an interrupted
            # worker.  It is intentionally reported as unknown so a caller
            # can inspect/recover it instead of silently claiming completion.
            return {"status": "unknown", "reason": "worker stopped without a terminal execution receipt", **monitor}
        return {"status": "unknown", "reason": "execution receipt has an unknown status", **monitor}
    pid_path = attempt / "worker.pid"
    if pid_path.is_file() and not pid_path.is_symlink():
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            pid = None
        if _pid_alive(pid):
            return {"status": "running"}
    # Reading the job above is intentional: even an unknown/partial attempt
    # has to prove token ownership before its state is exposed.
    del job
    return {"status": "unknown", "reason": "attempt has no execution receipt", **monitor}


def _log_paths(attempt: Path) -> tuple[Path, ...]:
    return (
        attempt / "preflight_stdout.log",
        attempt / "preflight_stderr.log",
        attempt / "stdout.log",
        attempt / "stderr.log",
    )


def _write_pid(attempt: Path, pid: int) -> None:
    _atomic_bytes(attempt / "worker.pid", str(pid).encode("ascii"), replace=True)


def _spawn_worker(attempt: Path, root: Path) -> int:
    worker = attempt / "worker.py"
    if not worker.is_file() or worker.is_symlink():
        raise RemoteWorkerError("worker source was not materialised")
    argv = [sys.executable, str(worker), "--execute", str(attempt), "--root", str(root)]
    kwargs: dict[str, Any] = {
        "cwd": str(attempt),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        flags = 0
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(argv, **kwargs)
    except OSError as exc:
        raise RemoteWorkerError(f"could not start detached worker: {exc}") from exc
    pid = process.pid
    # This process is intentionally detached; the durable execution marker is
    # the ownership record. Prevent the short-lived RPC process from warning
    # while the detached child continues independently.
    process._child_created = False  # type: ignore[attr-defined]
    _write_pid(attempt, pid)
    return pid


def _deploy(request: dict[str, Any]) -> dict[str, Any]:
    root, attempt, attempt_id, token = _request_context(request, action="deploy")
    job = _validate_job(request.get("job"), token)
    job_attempt = job.get("attempt_id")
    if job_attempt is not None and _attempt_id(job_attempt) != attempt_id:
        raise RemoteWorkerError("job.attempt_id does not match the request")
    job["attempt_id"] = attempt_id
    if attempt.exists():
        if attempt.is_symlink() or not attempt.is_dir():
            raise RemoteWorkerError("attempt path already exists and is not a directory")
        existing = _load_bound_job(attempt, token)
        # Same token is a replay.  Never launch a second process, even if the
        # previous worker stopped without a terminal receipt.
        if _job_token(existing) != token:
            raise RemoteWorkerError("attempt already belongs to another token")
        result = _status(attempt, token)
        result.update({"attempt_id": attempt_id, "idempotent": True})
        return result

    # For the usual run-root form this is ``root/attempts``.  A transport may
    # instead supply a repository root plus ``remote_attempt_rel``; in that
    # form the parent is derived from the already validated absolute attempt
    # path and remains confined to the managed root.
    attempts = attempt.parent
    _mkdir_chain(attempts, root)
    _reject_symlink_chain(attempts, root)
    if attempts.is_symlink():
        raise RemoteWorkerError("attempts directory cannot be a symlink")
    try:
        attempt.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise RemoteWorkerError("attempt appeared during deployment; retry with the same token") from exc
    _reject_symlink_chain(attempt, root)

    try:
        _materialize_files(attempt, job["files"])
        source = request.get("worker_source")
        if source is None:
            source = _read_source()
        if not isinstance(source, str) or not source:
            raise RemoteWorkerError("worker_source must be non-empty text")
        if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise RemoteWorkerError("worker_source is too large")
        _atomic_bytes(attempt / "worker.py", source.encode("utf-8"), replace=False)
        persisted = copy.deepcopy(job)
        persisted["_job_binding_digest"] = _digest(job)
        _atomic_json(attempt / "job.json", persisted, replace=False)
        started = _now()
        _atomic_json(
            attempt / "execution.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "running",
                "outcome": "starting",
                "token": token,
                "attempt_id": attempt_id,
                "started_at": started,
            },
            replace=False,
        )
        pid = _spawn_worker(attempt, root)
        return {
            "status": "running",
            "attempt_id": attempt_id,
            "pid": pid,
            "idempotent": False,
        }
    except Exception as exc:
        # Do not remove the partially materialised attempt.  Write a terminal
        # receipt when possible so callers can inspect a deterministic failure.
        try:
            _atomic_json(
                attempt / "execution.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "completed",
                    "outcome": "deploy_failed",
                    "error": str(exc),
                    "finished_at": _now(),
                },
                replace=True,
            )
        except Exception:
            pass
        if isinstance(exc, RemoteWorkerError):
            raise
        raise RemoteWorkerError(f"deployment failed: {exc}") from exc


def _check_or_collect(request: dict[str, Any], *, collect: bool) -> dict[str, Any]:
    root, attempt, attempt_id, token = _request_context(request, action="collect" if collect else "check")
    result = _status(attempt, token)
    result["attempt_id"] = attempt_id
    if not collect or result.get("status") not in {"completed", "failed"}:
        return result
    execution = result.get("execution")
    files: dict[str, str] = {}
    truncation: dict[str, bool] = {}
    for path in _log_paths(attempt):
        if not path.is_file() or path.is_symlink():
            continue
        data, truncated = _tail(path, MAX_LOG_BYTES)
        key = path.name
        files[key] = base64.b64encode(data).decode("ascii")
        truncation[key] = truncated
    job = _load_bound_job(attempt, token)
    result_path = _inside(attempt, attempt.joinpath(*PurePosixPath(job["result_file"]).parts))
    _reject_symlink_chain(result_path, attempt)
    if result_path.is_file() and not result_path.is_symlink():
        size = result_path.stat().st_size
        if size <= MAX_RESULT_BYTES:
            files[job["result_file"]] = base64.b64encode(result_path.read_bytes()).decode("ascii")
        else:
            result["result_error"] = f"result file exceeds {MAX_RESULT_BYTES} bytes"
    # A command that runs with the candidate directory as cwd may write a
    # relative result there.  The normal adapter renders an attempt-relative
    # absolute path, but accepting this deterministic fallback keeps the
    # worker interoperable with simple remote jobs without changing the
    # persisted contract.
    if job["result_file"] not in files:
        candidate_result = _inside(attempt / "candidate", attempt.joinpath("candidate", *PurePosixPath(job["result_file"]).parts))
        _reject_symlink_chain(candidate_result, attempt / "candidate")
        if candidate_result.is_file() and not candidate_result.is_symlink():
            size = candidate_result.stat().st_size
            if size <= MAX_RESULT_BYTES:
                files[job["result_file"]] = base64.b64encode(candidate_result.read_bytes()).decode("ascii")
            else:
                result["result_error"] = f"result file exceeds {MAX_RESULT_BYTES} bytes"
    result["files"] = files
    result["truncated"] = truncation
    if execution is not None:
        result["execution"] = execution
    del root
    return result


def _tail(path: Path, limit: int) -> tuple[bytes, bool]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > limit:
            handle.seek(-limit, os.SEEK_END)
            return handle.read(limit), True
        return handle.read(), False


def _kill_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
    else:
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        process.wait()


def _run_command(argv: list[str], cwd: Path, env: dict[str, str], deadline: float, stdout: Path, stderr: Path) -> dict[str, Any]:
    stdout.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    if not argv:
        stdout.write_bytes(b"")
        stderr.write_bytes(b"")
        return {"argv": [], "returncode": 0, "timed_out": False, "duration_seconds": 0.0}
    with stdout.open("wb") as out, stderr.open("wb") as err:
        try:
            process = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=env,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                close_fds=True,
                **({"start_new_session": True} if os.name != "nt" else {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}),
            )
        except OSError as exc:
            err.write(str(exc).encode("utf-8", errors="replace"))
            err.flush()
            return {"argv": argv, "returncode": None, "timed_out": False, "error": str(exc), "duration_seconds": round(time.monotonic() - start, 3)}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _kill_process(process)
            return {"argv": argv, "returncode": process.returncode, "timed_out": True, "duration_seconds": round(time.monotonic() - start, 3)}
        try:
            code = process.wait(timeout=remaining)
            timed_out = False
        except subprocess.TimeoutExpired:
            _kill_process(process)
            code = process.returncode
            timed_out = True
    return {"argv": argv, "returncode": code, "timed_out": timed_out, "duration_seconds": round(time.monotonic() - start, 3)}


def _runtime_argv(argv: list[str], runtime: Any) -> list[str]:
    """Apply the reviewed remote environment without changing user argv semantics."""
    if not argv:
        return []
    if not isinstance(runtime, dict):
        return list(argv)
    result = list(argv)
    python_bin = runtime.get("python")
    if isinstance(python_bin, str) and python_bin and result and result[0] in {"python", "python3"}:
        result[0] = python_bin
    conda = runtime.get("conda")
    if isinstance(conda, dict) and conda.get("path") and conda.get("env"):
        conda_bin = str(conda["path"]).rstrip("/") + "/bin/conda"
        return [conda_bin, "run", "--no-capture-output", "-n", str(conda["env"]), *result]
    env_setup = runtime.get("env_setup")
    if isinstance(env_setup, str) and env_setup.strip():
        return ["bash", "-lc", env_setup + " && " + shlex.join(result)]
    return result


def _execute(attempt_arg: str, root_arg: str | None = None) -> int:
    root, attempt, attempt_id = _validate_execution_paths(attempt_arg, root_arg)
    job = _read_json(attempt / "job.json")
    token = _job_token(job)
    binding = job.get("_job_binding_digest")
    if not isinstance(binding, str) or _digest({key: value for key, value in job.items() if key != "_job_binding_digest"}) != binding:
        raise RemoteWorkerError("job binding digest mismatch")
    candidate = attempt / "candidate"
    if candidate.is_symlink() or not candidate.is_dir():
        raise RemoteWorkerError("candidate directory is missing or is a symlink")
    timeout = _finite_timeout(job.get("timeout_seconds"))
    result_file = _portable_rel(job.get("result_file"), "job.result_file")
    result_path = _inside(attempt, attempt.joinpath(*PurePosixPath(result_file).parts))
    _reject_symlink_chain(result_path, attempt)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    preflight = _validate_argv(job.get("preflight_argv", []), "job.preflight_argv")
    argv = _validate_argv(job.get("argv"), "job.argv")
    gpu = job.get("gpu")
    env = os.environ.copy()
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = gpu
    started = _now()
    _atomic_json(
        attempt / "execution.json",
        {"schema_version": SCHEMA_VERSION, "status": "running", "outcome": "running", "token": token, "attempt_id": attempt_id, "pid": os.getpid(), "started_at": started},
        replace=True,
    )
    deadline = time.monotonic() + timeout
    preflight_result = _run_command(_runtime_argv(preflight, job.get("runtime")), candidate, env, deadline, attempt / "preflight_stdout.log", attempt / "preflight_stderr.log")
    if preflight_result.get("timed_out"):
        outcome = "preflight_timeout"
        evaluation_result = None
    elif preflight_result.get("returncode") != 0:
        outcome = "preflight_failed"
        evaluation_result = None
    else:
        evaluation_result = _run_command(_runtime_argv(argv, job.get("runtime")), candidate, env, deadline, attempt / "stdout.log", attempt / "stderr.log")
        if evaluation_result.get("timed_out"):
            outcome = "timeout"
        elif evaluation_result.get("returncode") == 0:
            outcome = "success"
        else:
            outcome = "failed"
    finished = _now()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "outcome": outcome,
        "token": token,
        "attempt_id": attempt_id,
        "pid": os.getpid(),
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(finished - started, 3),
        "preflight": preflight_result,
        "evaluation": evaluation_result,
        "result_file": result_file,
    }
    _atomic_json(attempt / "execution.json", receipt, replace=True)
    return 0


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one validated RPC request.

    Invalid requests raise :class:`RemoteWorkerError`; transports should turn
    that exception into their normal structured RPC error.  Valid requests
    always return a JSON-serialisable dictionary.
    """

    if not isinstance(request, dict):
        raise RemoteWorkerError("request must be an object")
    action = request.get("action")
    if action == "deploy":
        return _deploy(request)
    if action == "check":
        return _check_or_collect(request, collect=False)
    if action == "collect":
        return _check_or_collect(request, collect=True)
    raise RemoteWorkerError("action must be deploy, check, or collect")


def _main() -> int:
    parser = argparse.ArgumentParser(prog="hiera-remote-worker")
    parser.add_argument("--execute", metavar="ATTEMPT_DIR")
    parser.add_argument("--root", metavar="MANAGED_ROOT")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required for a detached worker")
    try:
        return _execute(args.execute, args.root)
    except Exception as exc:
        # The detached process has no caller to receive an exception.  Write a
        # terminal receipt only after re-authenticating the lexical path and
        # the persisted job binding.  In particular, never write an error
        # receipt to an arbitrary path rejected by _execute.
        try:
            _, attempt, _ = _validate_execution_paths(args.execute, args.root)
            job = _read_json(attempt / "job.json")
            token = _job_token(job)
            _load_bound_job(attempt, token)
            marker = _execution(attempt)
            if marker is None or marker.get("token") != token:
                raise RemoteWorkerError("attempt has no matching deployment execution marker")
            _atomic_json(
                attempt / "execution.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "completed",
                    "outcome": "worker_failed",
                    "error": str(exc),
                    "token": token,
                    "finished_at": _now(),
                },
                replace=True,
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
