"""CLI for the optional, sidecar-only Hiera experiment mode."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .adapter import load_experiment_context, source_snapshot_unchanged, wiki_snapshot
from .candidate_graph import build_proposals
from .acquisition import coverage_scores
from .common import (
    HieraError,
    atomic_write_json,
    canonical_digest,
    now_iso,
    project_root,
    read_json,
    run_dir,
    safe_child,
    sha256_file,
    validate_slug,
)
from .contract import (
    freeze_contract,
    load_contract,
    require_ready,
    verify_frozen,
    write_contract,
    build_contract,
)
from .evaluator import CommandEvaluator
from .ledger import Ledger
from .remote_adapter import RemoteCommandAdapter
from .scheduler import choose_deep_candidate, reconcile_deep_bouts, record_bout
from .semantic_space import (
    default_space,
    load_space,
    point_id,
    validate_point,
    write_space,
)
from .tuner import propose_configs, validate_config
from .experience import build_snapshot


def _run_path(args: argparse.Namespace) -> Path:
    root = project_root(Path(args.project))
    return run_dir(root, args.experiment, args.run_id)


def _json_object(path: str) -> dict[str, Any]:
    value = read_json(Path(path))
    if not isinstance(value, dict):
        raise HieraError(f"JSON file must contain an object: {path}")
    return value


def cmd_init(args: argparse.Namespace) -> None:
    root = project_root(Path(args.project))
    validate_slug(args.experiment, "experiment slug")
    validate_slug(args.run_id, "run id")
    context = load_experiment_context(root, args.experiment)
    destination = run_dir(root, args.experiment, args.run_id)
    if destination.exists() and any(destination.iterdir()):
        raise HieraError(f"run already exists and is non-empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("candidates", "attempts", "preflight", "drafts"):
        (destination / name).mkdir()
    atomic_write_json(
        destination / "manifest.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "experiment": args.experiment,
            "created_at": now_iso(),
            "wiki_snapshot": wiki_snapshot(context),
            "state": "initialized",
        },
    )
    space = _json_object(args.space) if args.space else default_space(args.experiment, {})
    write_space(destination / "semantic_space.json", space)
    overrides = _json_object(args.contract) if args.contract else None
    contract = build_contract(context, overrides=overrides)
    write_contract(destination / "task_contract.yaml", contract)
    print(
        json.dumps(
            {
                "run_dir": str(destination),
                "contract_ready": not contract["readiness_errors"],
                "contract_errors": contract["readiness_errors"],
                "space": str(destination / "semantic_space.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_propose(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    space = load_space(destination / "semantic_space.json")
    ledger = Ledger(destination)
    contract = load_contract(destination / "task_contract.yaml")
    direction = contract.get("evaluation", {}).get("direction", "minimize")
    operation, proposals = build_proposals(space, ledger, args.round, args.limit, direction)
    coverage = coverage_scores(ledger)
    ledger.record_decision(
        {"action": "PROPOSE", "round": args.round, "operation": operation, "proposal_ids": [item["point_id"] for item in proposals]}
    )
    print(json.dumps({"operation": operation, "proposals": proposals, "coverage": coverage}, ensure_ascii=False, indent=2))


def _safe_relative(value: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not value or ".." in path.parts:
        raise HieraError(f"{label} must be relative and remain inside candidate")
    return path


def _file_key(
    value: str,
    label: str = "candidate file",
    *,
    allow_generated_config: bool = False,
) -> tuple[str, Path]:
    """Return a canonical slash-separated key and its safe relative path."""
    relative = _safe_relative(value, label)
    key = relative.as_posix()
    if key in {"", "."} or (key == "config.json" and not allow_generated_config):
        raise HieraError(f"{label} uses a reserved or empty path: {value!r}")
    return key, relative


def _load_source_files(
    project: Path,
    destination: Path,
    source_dir: str,
    editable: list[str],
) -> dict[str, str]:
    """Load a reviewed modular source tree from this run's drafts directory."""
    source_arg = Path(source_dir)
    if source_arg.is_absolute():
        raise HieraError("--source-dir must be relative to the project root")
    raw_source = project.joinpath(*source_arg.parts)
    if raw_source.is_symlink():
        raise HieraError(f"source directory is a symlink: {raw_source}")
    source = safe_child(project, *source_arg.parts)
    drafts = safe_child(destination, "drafts")
    try:
        source.relative_to(drafts)
    except ValueError as exc:
        raise HieraError("--source-dir must be inside this run's drafts/ directory") from exc
    if source.is_symlink() or not source.is_dir():
        raise HieraError(f"source directory is missing or is a symlink: {source}")
    if not isinstance(editable, list) or not editable:
        raise HieraError("candidate.editable_files must whitelist the modular source tree")
    allowed: dict[str, Path] = {}
    for item in editable:
        key, relative = _file_key(item, "candidate.editable_files")
        path = safe_child(source, *relative.parts)
        if path.is_symlink() or not path.is_file():
            raise HieraError(f"source tree is missing a whitelisted file: {key}")
        allowed[key] = path
    discovered: set[str] = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise HieraError(f"source tree cannot contain symlinks: {path}")
        if path.is_file():
            key = path.relative_to(source).as_posix()
            if key == "config.json":
                raise HieraError("config.json is generated from candidate.config and must not be in --source-dir")
            discovered.add(key)
            if key not in allowed:
                raise HieraError(f"source file is not listed in candidate.editable_files: {key}")
    if discovered != set(allowed):
        missing = sorted(set(allowed) - discovered)
        raise HieraError("source tree contains no file for: " + ", ".join(missing))
    output: dict[str, str] = {}
    for key in sorted(allowed):
        try:
            output[key] = allowed[key].read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HieraError(f"candidate source must be UTF-8 text: {key}") from exc
    return output


def cmd_admit(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    spec = _json_object(args.spec)
    candidate_id = spec.get("candidate_id")
    validate_slug(candidate_id, "candidate_id")
    ledger = Ledger(destination)
    space = load_space(destination / "semantic_space.json")
    point = spec.get("semantic_point")
    if not isinstance(point, dict):
        raise HieraError("semantic_point must be an object")
    validate_point(space, point)
    contract = load_contract(destination / "task_contract.yaml")
    source_dir = getattr(args, "source_dir", None)
    inline_files = spec.get("files")
    if source_dir and inline_files is not None:
        raise HieraError("--source-dir and spec.files are mutually exclusive")
    editable = contract.get("candidate", {}).get("editable_files", [])
    if source_dir:
        files = _load_source_files(project_root(Path(args.project)), destination, source_dir, editable)
    else:
        files = inline_files
        if not isinstance(files, dict) or not files:
            raise HieraError("candidate spec files must be a non-empty object")
    canonical_files: dict[str, str] = {}
    for name, content in files.items():
        key, _relative = _file_key(name, allow_generated_config=True)
        if key in canonical_files:
            raise HieraError(f"candidate contains duplicate file paths: {key}")
        canonical_files[key] = content
    files = canonical_files
    editable_keys = {
        _file_key(item, "candidate.editable_files", allow_generated_config=True)[0]
        for item in editable
    } if isinstance(editable, list) else set()
    if editable_keys and any(path not in editable_keys for path in files):
        raise HieraError("candidate includes a file outside candidate.editable_files")
    candidate_directory = destination / "candidates" / candidate_id
    if candidate_directory.exists():
        raise HieraError(f"candidate snapshot already exists: {candidate_id}")
    validated_files: list[tuple[str, Path, str]] = []
    for name, content in files.items():
        relative = _safe_relative(name, "candidate file")
        if not isinstance(content, str):
            raise HieraError(f"candidate file content must be text: {name}")
        validated_files.append((name, relative, content))
    config = spec.get("config", {})
    if not isinstance(config, dict):
        raise HieraError("candidate config must be an object")
    config_schema = contract.get("candidate", {}).get("config_schema", {})
    if config_schema:
        validate_config(config_schema, config)
    entrypoint = contract.get("candidate", {}).get("entrypoint")
    entrypoint_key = _file_key(entrypoint, "candidate.entrypoint")[0] if isinstance(entrypoint, str) else ""
    if not entrypoint_key or entrypoint_key not in files:
        raise HieraError("candidate must include the contract entrypoint")
    parents = spec.get("parents", [])
    if not isinstance(parents, list) or any(not isinstance(parent, str) for parent in parents):
        raise HieraError("parents must be a list of candidate ids")
    for parent in parents:
        ledger.candidate(parent)
    operation = spec.get("operation", "fresh")
    if operation not in {"fresh", "improve", "crossover"}:
        raise HieraError("operation must be fresh, improve, or crossover")

    candidate_directory.mkdir(parents=True)
    file_digests: dict[str, str] = {}
    for name, relative, content in validated_files:
        target = safe_child(candidate_directory, *relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        file_digests[name] = sha256_file(target)
    atomic_write_json(candidate_directory / "config.json", config)
    file_digests["config.json"] = sha256_file(candidate_directory / "config.json")
    record = {
        "candidate_id": candidate_id,
        "operation": operation,
        "parents": parents,
        "point_id": point_id(point, space.get("space_revision", "")),
        "semantic_point": point,
        "config": config,
        "code_digest": canonical_digest(file_digests),
        "file_digests": file_digests,
        "status": "admitted",
        "direction": contract.get("evaluation", {}).get("direction"),
    }
    ledger.add_candidate(record)
    print(json.dumps({"candidate_id": candidate_id, "code_digest": record["code_digest"], "status": "admitted"}, indent=2))


def cmd_tune(args: argparse.Namespace) -> None:
    """Materialize and evaluate bounded config variants of one candidate."""
    if args.depth != "deep":
        raise HieraError("tune only supports --depth deep; use run for screen evaluations")
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    verify_frozen(contract)
    schema = contract.get("candidate", {}).get("config_schema", {})
    if not schema:
        raise HieraError("candidate.config_schema is empty; define and review a tuning space first")
    ledger = Ledger(destination)
    # A previous remote client may have disconnected after recording an
    # evaluation but before recording the parent tuning bout.  Reconcile that
    # append-only state before selecting or materialising more variants.
    reconcile_deep_bouts(ledger)
    parent_id = args.candidate
    parent = ledger.candidate(parent_id)
    parent_directory = destination / "candidates" / parent_id
    evaluator = CommandEvaluator(destination, contract, ledger)
    evaluator._verify_candidate_snapshot(parent, parent_directory)
    tried = [record.get("config", {}) for record in ledger.candidates().values() if record.get("point_id") == parent.get("point_id")]
    configs = propose_configs(schema, parent.get("config", {}), tried, args.limit)
    space = load_space(destination / "semantic_space.json")
    results = []
    for config in configs:
        suffix = canonical_digest(config)[7:15]
        candidate_id = f"{parent_id}-tune-{suffix}"
        candidate_directory = destination / "candidates" / candidate_id
        if candidate_directory.exists():
            continue
        candidate_directory.mkdir(parents=True)
        file_digests: dict[str, str] = {}
        for relative in parent.get("file_digests", {}):
            source = parent_directory / relative
            target = candidate_directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == "config.json":
                atomic_write_json(target, config)
            else:
                shutil.copy2(source, target)
            file_digests[relative] = sha256_file(target)
        record = {
            "candidate_id": candidate_id,
            "operation": "tune",
            "parents": [parent_id],
            "point_id": parent["point_id"],
            "semantic_point": parent["semantic_point"],
            "config": config,
            "code_digest": canonical_digest(file_digests),
            "file_digests": file_digests,
            "status": "admitted",
            "direction": contract["evaluation"]["direction"],
        }
        ledger.add_candidate(record)
        receipt = evaluator.evaluate(candidate_id, args.depth)
        record_bout(
            ledger,
            parent_id,
            score=receipt.get("score"),
            status="tuned" if receipt.get("status") == "success" else "failed",
            attempt_id=receipt.get("attempt_id"),
        )
        results.append({"candidate_id": candidate_id, "config": config, "receipt": receipt})
    print(json.dumps({"parent": parent_id, "variants": results}, ensure_ascii=False, indent=2))


def cmd_approve(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    require_ready(contract)
    frozen = freeze_contract(contract)
    write_contract(destination / "task_contract.yaml", frozen)
    manifest = read_json(destination / "manifest.json")
    manifest["state"] = "approved"
    manifest["contract_digest"] = frozen["state"]["contract_digest"]
    atomic_write_json(destination / "manifest.json", manifest)
    print(json.dumps({"approved": True, "contract_digest": frozen["state"]["contract_digest"]}, indent=2))


def cmd_preflight(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    verify_frozen(contract)
    ledger = Ledger(destination)
    result = CommandEvaluator(destination, contract, ledger).preflight(args.candidate)
    ledger.record_decision({"action": "PREFLIGHT", "candidate_id": args.candidate, "status": result["status"]})
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    verify_frozen(contract)
    result = CommandEvaluator(destination, contract, Ledger(destination)).evaluate(args.candidate, args.depth)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_recover(args: argparse.Namespace) -> None:
    """Poll and collect an already-reserved remote attempt; never resubmit it."""
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    verify_frozen(contract)
    if contract.get("resources", {}).get("environment") != "remote":
        raise HieraError("recover is only available for resources.environment=remote")
    ledger = Ledger(destination)
    existing = next(
        (item for item in ledger.evaluations() if item.get("attempt_id") == args.attempt),
        None,
    )
    if existing is not None:
        reconcile_deep_bouts(ledger)
        print(json.dumps({key: value for key, value in existing.items() if key != "candidate_id"}, ensure_ascii=False, indent=2))
        return
    evaluator = CommandEvaluator(destination, contract, ledger)
    evaluator._ensure_source_snapshot()
    result = RemoteCommandAdapter(destination, contract, ledger).recover(args.attempt)
    reconcile_deep_bouts(ledger)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_loop(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    verify_frozen(contract)
    ledger = Ledger(destination)
    reconcile_deep_bouts(ledger)
    evaluator = CommandEvaluator(destination, contract, ledger)
    reports = []
    for _ in range(args.rounds):
        summary = ledger.summary(contract["resources"]["max_evaluations"], contract["evaluation"]["direction"])
        if summary["remaining_evaluations"] <= 0:
            break
        decision = choose_deep_candidate(
            ledger, args.max_bouts, contract["evaluation"]["direction"]
        )
        if decision["action"] == "STOP":
            break
        receipt = evaluator.evaluate(decision["candidate_id"], "deep")
        record_bout(
            ledger,
            decision["candidate_id"],
            score=receipt.get("score"),
            status="tuned" if receipt.get("status") == "success" else "failed",
            attempt_id=receipt.get("attempt_id"),
        )
        reports.append(receipt)
    print(json.dumps({"rounds_completed": len(reports), "reports": reports, "summary": ledger.summary(contract["resources"]["max_evaluations"], contract["evaluation"]["direction"])}, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    ledger = Ledger(destination)
    repaired = reconcile_deep_bouts(ledger)
    summary = ledger.summary(
        contract.get("resources", {}).get("max_evaluations"),
        contract.get("evaluation", {}).get("direction", "minimize"),
    )
    summary["wiki_source_unchanged"] = source_snapshot_unchanged(
        project_root(Path(args.project)), read_json(destination / "manifest.json")
    )
    summary["coverage"] = coverage_scores(ledger)
    summary["experience_revision"] = build_snapshot(ledger)["revision"]
    summary["reconciled_deep_attempts"] = repaired
    summary["remote_attempts"] = []
    if contract.get("resources", {}).get("environment") == "remote":
        adapter = RemoteCommandAdapter(destination, contract, ledger)
        for handle_path in sorted((destination / "attempts").glob("*/remote.json")):
            attempt_id = handle_path.parent.name
            if any(item.get("attempt_id") == attempt_id for item in ledger.evaluations()):
                continue
            try:
                summary["remote_attempts"].append(adapter.inspect(attempt_id))
            except HieraError as exc:
                summary["remote_attempts"].append(
                    {"attempt_id": attempt_id, "status": "error", "error": str(exc)}
                )
        repaired.extend(reconcile_deep_bouts(ledger))
        # A terminal status poll may have written a receipt that was not part
        # of the initial summary; expose the current counts in the same report.
        summary.update(
            {
                "evaluation_count": ledger.budget_used(),
                "remaining_evaluations": max(
                    0,
                    contract["resources"]["max_evaluations"] - ledger.budget_used(),
                ),
                "coverage": coverage_scores(ledger),
                "experience_revision": build_snapshot(ledger)["revision"],
                "reconciled_deep_attempts": repaired,
            }
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_finalize(args: argparse.Namespace) -> None:
    destination = _run_path(args)
    contract = load_contract(destination / "task_contract.yaml")
    summary = Ledger(destination).summary(
        contract.get("resources", {}).get("max_evaluations"),
        contract.get("evaluation", {}).get("direction", "minimize"),
    )
    report = {
        "schema_version": 1,
        "run_id": args.run_id,
        "experiment": args.experiment,
        "contract_digest": (contract.get("state") or {}).get("contract_digest"),
        "summary": summary,
        "coverage": coverage_scores(Ledger(destination)),
        "experience_revision": build_snapshot(Ledger(destination))["revision"],
        "wiki_source_unchanged": source_snapshot_unchanged(
            project_root(Path(args.project)), read_json(destination / "manifest.json")
        ),
        "wiki_writeback": "none",
        "note": "Exploratory search output; use the existing formal experiment workflow for confirmatory validation.",
    }
    atomic_write_json(destination / "FINAL_REPORT.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.hiera.cli")
    parser.add_argument("--project", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_run_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("experiment")
        command.add_argument("--run-id", required=True)

    command = subparsers.add_parser("init")
    add_run_arguments(command)
    command.add_argument("--contract")
    command.add_argument("--space")
    command.set_defaults(func=cmd_init)
    command = subparsers.add_parser("propose")
    add_run_arguments(command)
    command.add_argument("--round", type=int, default=0)
    command.add_argument("--limit", type=int, default=8)
    command.set_defaults(func=cmd_propose)
    command = subparsers.add_parser("admit")
    add_run_arguments(command)
    command.add_argument("--spec", required=True)
    command.add_argument(
        "--source-dir",
        help="optional modular source tree under runs/hiera/<experiment>/<run-id>/drafts/; mutually exclusive with spec.files",
    )
    command.set_defaults(func=cmd_admit)
    for name, function in (("approve", cmd_approve), ("status", cmd_status), ("finalize", cmd_finalize)):
        command = subparsers.add_parser(name)
        add_run_arguments(command)
        command.set_defaults(func=function)
    command = subparsers.add_parser("preflight")
    add_run_arguments(command)
    command.add_argument("--candidate", required=True)
    command.set_defaults(func=cmd_preflight)
    command = subparsers.add_parser("run")
    add_run_arguments(command)
    command.add_argument("--candidate", required=True)
    command.add_argument("--depth", choices=("screen", "deep"), default="screen")
    command.set_defaults(func=cmd_run)
    command = subparsers.add_parser("recover")
    add_run_arguments(command)
    command.add_argument("--attempt", required=True)
    command.set_defaults(func=cmd_recover)
    command = subparsers.add_parser("tune")
    add_run_arguments(command)
    command.add_argument("--candidate", required=True)
    command.add_argument("--limit", type=int, default=8)
    command.add_argument("--depth", choices=("deep",), default="deep")
    command.set_defaults(func=cmd_tune)
    command = subparsers.add_parser("loop")
    add_run_arguments(command)
    command.add_argument("--rounds", type=int, default=3)
    command.add_argument("--max-bouts", type=int, default=3)
    command.set_defaults(func=cmd_loop)
    return parser


def main() -> None:
    try:
        arguments = build_parser().parse_args()
        arguments.func(arguments)
    except HieraError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
