"""Validated, reviewable execution contract for one Hiera run."""

from __future__ import annotations

import re
import copy
from pathlib import Path
from typing import Any

from .adapter import ExperimentContext, wiki_snapshot
from .common import HieraError, atomic_write_json, canonical_digest, now_iso, read_json

CONTRACT_SCHEMA_VERSION = 2
_ALLOWED_PLACEHOLDERS = {
    "candidate_dir",
    "run_dir",
    "attempt_dir",
    "result_file",
    "config_file",
    "entrypoint",
}


def build_contract(
    context: ExperimentContext,
    *,
    environment: str = "local",
    accelerator: str = "",
    timeout_seconds: int = 3600,
    max_evaluations: int = 20,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experiment = context.experiment
    setup = experiment.get("setup") if isinstance(experiment.get("setup"), dict) else {}
    metrics = experiment.get("metrics") if isinstance(experiment.get("metrics"), list) else []
    contract: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "format": "json-compatible-yaml",
        "created_at": now_iso(),
        "source": wiki_snapshot(context),
        "experiment": {
            "title": experiment.get("title", context.experiment_slug),
            "slug": context.experiment_slug,
            "hypothesis": experiment.get("hypothesis", ""),
            "baseline": experiment.get("baseline", ""),
            "metrics": metrics,
            "setup": setup,
        },
        "candidate": {
            "entrypoint": "",
            "editable_files": [],
            "readonly_files": [],
            "config_schema": {},
        },
        "evaluation": {
            "kind": "command",
            "prepare_command": [],
            "preflight_command": [],
            "evaluate_command": [],
            "collect_command": [],
            "result_file": "results/result.json",
            "score_path": "",
            "metric": "",
            "direction": "",
        },
        "resources": {
            "environment": environment,
            "accelerator": accelerator or setup.get("hardware", ""),
            "timeout_seconds": timeout_seconds,
            "max_evaluations": max_evaluations,
            "remote_config": "config/server.yaml",
            "remote_python": "python3",
            "remote_poll_seconds": 5,
            "remote_gpu": "",
        },
        "state": {"approved": False, "contract_digest": ""},
    }
    if overrides:
        _merge_contract(contract, overrides)
    contract["readiness_errors"] = validate_contract(contract)
    return contract


def _merge_contract(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if key in {"schema_version", "source", "created_at", "state"}:
            continue
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_contract(target[key], value)
        else:
            target[key] = value


def _validate_argv(value: Any, label: str, required: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        return [f"{label} must be a non-empty string list"]
    if required and not value:
        return [f"{label} is required"]
    for item in value:
        placeholders = set(re.findall(r"\{([a-z_][a-z0-9_]*)\}", item))
        if not placeholders <= _ALLOWED_PLACEHOLDERS:
            return [f"{label} uses an unsupported placeholder"]
    return []


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(contract, dict) or contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CONTRACT_SCHEMA_VERSION}")
    candidate = contract.get("candidate") if isinstance(contract, dict) else None
    evaluation = contract.get("evaluation") if isinstance(contract, dict) else None
    resources = contract.get("resources") if isinstance(contract, dict) else None
    if not isinstance(candidate, dict):
        errors.append("candidate must be an object")
    else:
        entrypoint = candidate.get("entrypoint")
        if not isinstance(entrypoint, str) or not entrypoint.strip():
            errors.append("candidate.entrypoint is required")
        editable = candidate.get("editable_files")
        if (
            not isinstance(editable, list)
            or not editable
            or any(
                not isinstance(item, str)
                or Path(item).is_absolute()
                or ".." in Path(item).parts
                for item in editable
            )
        ):
            errors.append("candidate.editable_files must contain relative paths")
        elif entrypoint not in editable:
            errors.append("candidate.entrypoint must be listed in candidate.editable_files")
        readonly = candidate.get("readonly_files")
        if not isinstance(readonly, list) or any(
            not isinstance(item, str) or Path(item).is_absolute() or ".." in Path(item).parts
            for item in readonly or []
        ):
            errors.append("candidate.readonly_files must be a list")
    if not isinstance(evaluation, dict):
        errors.append("evaluation must be an object")
    else:
        if evaluation.get("kind") != "command":
            errors.append("only evaluation.kind=command is supported")
        errors.extend(_validate_argv(evaluation.get("evaluate_command"), "evaluation.evaluate_command", True))
        for key in ("prepare_command", "preflight_command", "collect_command"):
            errors.extend(_validate_argv(evaluation.get(key), f"evaluation.{key}"))
        if evaluation.get("prepare_command") or evaluation.get("collect_command"):
            errors.append(
                "evaluation.prepare_command and evaluation.collect_command are reserved; "
                "Hiera adapters deploy candidate snapshots and collect result files directly"
            )
        result_file = evaluation.get("result_file")
        if (
            not isinstance(result_file, str)
            or not result_file
            or Path(result_file).is_absolute()
            or ".." in Path(result_file).parts
        ):
            errors.append("evaluation.result_file must be a relative path")
        if not isinstance(evaluation.get("score_path"), str) or not evaluation["score_path"]:
            errors.append("evaluation.score_path is required")
        if evaluation.get("direction") not in {"minimize", "maximize"}:
            errors.append("evaluation.direction must be explicitly minimize or maximize")
        if not isinstance(evaluation.get("metric"), str) or not evaluation["metric"].strip():
            errors.append("evaluation.metric is required")
    if not isinstance(resources, dict):
        errors.append("resources must be an object")
    else:
        for key in ("timeout_seconds", "max_evaluations"):
            value = resources.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"resources.{key} must be a positive integer")
        if resources.get("environment") not in {"local", "remote"}:
            errors.append("resources.environment must be local or remote")
        remote_config = resources.get("remote_config", "config/server.yaml")
        if (
            not isinstance(remote_config, str)
            or not remote_config
            or Path(remote_config).is_absolute()
            or ".." in Path(remote_config).parts
        ):
            errors.append("resources.remote_config must be a relative path")
        remote_python = resources.get("remote_python", "python3")
        if (
            not isinstance(remote_python, str)
            or not remote_python.strip()
            or any(char.isspace() or ord(char) < 32 for char in remote_python)
        ):
            errors.append("resources.remote_python must be one executable path/name without whitespace")
        poll_seconds = resources.get("remote_poll_seconds", 5)
        if (
            isinstance(poll_seconds, bool)
            or not isinstance(poll_seconds, (int, float))
            or poll_seconds <= 0
        ):
            errors.append("resources.remote_poll_seconds must be positive")
        remote_gpu = resources.get("remote_gpu", "")
        if not isinstance(remote_gpu, str) or (
            remote_gpu and not re.fullmatch(r"[0-9]+(?:,[0-9]+)*", remote_gpu)
        ):
            errors.append("resources.remote_gpu must be empty or comma-separated GPU indices")
    return errors


def write_contract(path: Path, contract: dict[str, Any]) -> None:
    output = copy.deepcopy(contract)
    output["readiness_errors"] = validate_contract(output)
    atomic_write_json(path, output)


def load_contract(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise HieraError(f"contract must be an object: {path}")
    value["readiness_errors"] = validate_contract(value)
    return value


def require_ready(contract: dict[str, Any]) -> None:
    errors = validate_contract(contract)
    if errors:
        raise HieraError("task contract is not executable: " + "; ".join(errors))


def freeze_contract(contract: dict[str, Any]) -> dict[str, Any]:
    require_ready(contract)
    immutable = {
        key: value for key, value in contract.items() if key not in {"readiness_errors", "state"}
    }
    state = dict(contract.get("state") or {})
    state.update({"approved": True, "contract_digest": canonical_digest(immutable), "approved_at": now_iso()})
    output = copy.deepcopy(contract)
    output["state"] = state
    output["readiness_errors"] = []
    return output


def verify_frozen(contract: dict[str, Any]) -> None:
    require_ready(contract)
    state = contract.get("state") or {}
    expected = state.get("contract_digest")
    if not state.get("approved") or not isinstance(expected, str):
        raise HieraError("run has no approved contract; inspect and approve before execution")
    immutable = {
        key: value for key, value in contract.items() if key not in {"readiness_errors", "state"}
    }
    if canonical_digest(immutable) != expected:
        raise HieraError("approved contract changed after approval")
