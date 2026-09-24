"""Small, deterministic helpers for the optional Hiera experiment mode."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class HieraError(RuntimeError):
    """An expected, user-actionable Hiera error."""


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def project_root(path: Path | None = None) -> Path:
    start = (path or Path.cwd()).resolve()
    if start.is_file():
        start = start.parent
    for candidate in (start, *start.parents):
        if (candidate / "wiki").is_dir() and (candidate / "tools").is_dir():
            return candidate
    raise HieraError("cannot locate AutoSci project root (expected wiki/ and tools/)")


def validate_slug(value: str, label: str = "slug") -> str:
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise HieraError(f"{label} must be lowercase kebab-case: {value!r}")
    return value


def safe_child(root: Path, *parts: str) -> Path:
    root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HieraError(f"path escapes managed root: {candidate}") from exc
    return candidate


def hiera_root(root: Path) -> Path:
    return safe_child(root, "runs", "hiera")


def run_dir(root: Path, experiment_slug: str, run_id: str) -> Path:
    validate_slug(experiment_slug, "experiment slug")
    validate_slug(run_id, "run id")
    return safe_child(hiera_root(root), experiment_slug, run_id)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def read_json(path: Path, *, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if default is not None:
            return default
        raise HieraError(f"missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        raise HieraError(f"invalid JSON in {path}: {exc}") from exc


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HieraError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise HieraError(f"JSONL record at {path}:{line_number} is not an object")
        rows.append(value)
    return rows


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256_bytes(encoded)


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value
        and value not in (float("inf"), float("-inf"))
    )


def deep_get(value: Any, dotted: str, default: Any = None) -> Any:
    current = value
    for key in dotted.split(".") if dotted else []:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


@contextmanager
def exclusive_lock(path: Path, timeout_seconds: float = 10.0) -> Iterator[None]:
    """Lock one run by atomically creating a sibling lock file."""
    import time

    lock = Path(str(path) + ".lock")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise HieraError(f"timed out waiting for run lock: {lock}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
