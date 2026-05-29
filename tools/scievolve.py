#!/usr/bin/env python3
"""Shared SciEvolve signal/proposal spine.

This module is intentionally small and file-based.  Stage-specific skills
(`/dream`, `/forge`, `/morph`) should extend this same substrate instead of
creating private stores.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCIEVOLVE_DIR = Path("outputs") / "evolution"
SCIEVOLVE_SIGNALS = "signals.jsonl"
SCIEVOLVE_PROPOSALS = "proposals.jsonl"

SCIEVOLVE_SOURCE_VALUES = ("user", "task", "open")
SCIEVOLVE_DIMENSION_VALUES = ("memory", "workflow", "orchestration")
SCIEVOLVE_CONFIDENCE_VALUES = ("low", "medium", "high")
SCIEVOLVE_SEVERITY_VALUES = ("info", "low", "medium", "high", "critical")
SCIEVOLVE_STATUS_VALUES = (
    "proposed",
    "approved",
    "applied",
    "rejected",
    "superseded",
)

DIMENSION_SKILL = {
    "memory": "/dream",
    "workflow": "/forge",
    "orchestration": "/morph",
}

DIMENSION_ACTION = {
    "memory": (
        "Run the memory-evolution view over the target neighborhood, then "
        "draft proposal-first updates for forgetting low-signal material, "
        "consolidating related memories, or adding justified associations."
    ),
    "workflow": (
        "Run the workflow-evolution view over the target skill/protocol, then "
        "draft proposal-first updates to handoffs, checks, prompts, or recovery "
        "steps."
    ),
    "orchestration": (
        "Run the orchestration-evolution view over the target DAG/template, "
        "then draft proposal-first updates to operators, branches, roles, "
        "verification nodes, or tool configuration."
    ),
}


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _compact_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _json_digest(payload: object, length: int = 8) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:length]


def _slug_part(value: str, fallback: str = "general", max_len: int = 48) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not text:
        text = fallback
    return text[:max_len].strip("-") or fallback


def _relative_to_wiki(path: Path, wiki_root: Path) -> str:
    try:
        return str(path.relative_to(wiki_root))
    except ValueError:
        return str(path)


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _store_readme() -> str:
    return """# SciEvolve Store

This directory is managed by `tools/research_wiki.py scievolve-*` commands.

- `signals.jsonl` records user/task/open-environment signals.
- `proposals.jsonl` indexes proposal artifacts.
- `proposals/` stores proposal Markdown/JSON pairs.
- `reports/` stores dry-run evolution reports.

Stage-specific skills extend this same substrate:

- `/dream` uses `dimension: memory`.
- `/forge` uses `dimension: workflow`.
- `/morph` uses `dimension: orchestration`.

The default mode is proposal-first. Recording signals and generating reports
does not mutate wiki entity pages, skills, templates, or DAGs.
"""


def ensure_scievolve_store(wiki_root: str | Path) -> Path:
    root = Path(wiki_root)
    store = root / SCIEVOLVE_DIR
    (store / "proposals").mkdir(parents=True, exist_ok=True)
    (store / "reports").mkdir(parents=True, exist_ok=True)
    _write_if_missing(store / "README.md", _store_readme())
    _write_if_missing(store / SCIEVOLVE_SIGNALS, "")
    _write_if_missing(store / SCIEVOLVE_PROPOSALS, "")
    return store


def _validate_choice(field: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        print(json.dumps({
            "status": "error",
            "message": f"Invalid {field} '{value}'. Valid: {list(choices)}",
        }), file=sys.stderr)
        sys.exit(1)


def _load_jsonl(path: Path) -> tuple[list[dict], int]:
    records: list[dict] = []
    malformed = 0
    if not path.exists():
        return records, malformed
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(obj, dict):
            records.append(obj)
        else:
            malformed += 1
    return records, malformed


def load_scievolve_signals(wiki_root: str | Path) -> tuple[list[dict], int]:
    store = ensure_scievolve_store(wiki_root)
    return _load_jsonl(store / SCIEVOLVE_SIGNALS)


def load_scievolve_proposals(wiki_root: str | Path) -> tuple[list[dict], int]:
    store = ensure_scievolve_store(wiki_root)
    return _load_jsonl(store / SCIEVOLVE_PROPOSALS)


def scievolve_init(wiki_root: str) -> None:
    store = ensure_scievolve_store(wiki_root)
    print(json.dumps({
        "status": "ok",
        "store": str(store),
        "signals": str(store / SCIEVOLVE_SIGNALS),
        "proposals": str(store / SCIEVOLVE_PROPOSALS),
    }, ensure_ascii=False))


def scievolve_record_signal(
    wiki_root: str,
    source: str,
    dimension: str,
    target: str,
    kind: str,
    summary: str,
    evidence_path: str = "",
    evidence_text: str = "",
    confidence: str = "medium",
    severity: str = "info",
) -> None:
    _validate_choice("source", source, SCIEVOLVE_SOURCE_VALUES)
    _validate_choice("dimension", dimension, SCIEVOLVE_DIMENSION_VALUES)
    _validate_choice("confidence", confidence, SCIEVOLVE_CONFIDENCE_VALUES)
    _validate_choice("severity", severity, SCIEVOLVE_SEVERITY_VALUES)

    if not kind.strip():
        print(json.dumps({"status": "error", "message": "--kind is required"}),
              file=sys.stderr)
        sys.exit(1)
    if not summary.strip():
        print(json.dumps({"status": "error", "message": "--summary is required"}),
              file=sys.stderr)
        sys.exit(1)

    store = ensure_scievolve_store(wiki_root)
    timestamp = _now_iso()
    base_record = {
        "timestamp": timestamp,
        "source": source,
        "dimension": dimension,
        "skill": DIMENSION_SKILL[dimension],
        "target": target,
        "kind": kind,
        "summary": summary,
        "evidence_path": evidence_path,
        "evidence_text": evidence_text,
        "confidence": confidence,
        "severity": severity,
        "status": "recorded",
    }
    record = {
        "id": f"sig-{_compact_timestamp()}-{_json_digest(base_record)}",
        **base_record,
    }

    with open(store / SCIEVOLVE_SIGNALS, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(json.dumps({
        "status": "ok",
        "signal_id": record["id"],
        "path": str(store / SCIEVOLVE_SIGNALS),
        "signal": record,
    }, ensure_ascii=False))


def _filter_signals(
    signals: list[dict],
    dimension: str = "",
    target: str = "",
    limit: int = 20,
) -> list[dict]:
    filtered = []
    for signal in signals:
        if dimension and signal.get("dimension") != dimension:
            continue
        if target and signal.get("target") != target:
            continue
        filtered.append(signal)
    if limit > 0:
        filtered = filtered[-limit:]
    return filtered


def _proposal_id(dimension: str, target: str, signals: list[dict]) -> str:
    signal_ids = [str(s.get("id", "")) for s in signals]
    digest = _json_digest({"dimension": dimension, "target": target,
                           "signals": sorted(signal_ids)}, length=10)
    return f"prop-{dimension}-{_slug_part(target)}-{digest}"


def _proposal_rationale(signals: list[dict]) -> str:
    sources = Counter(str(s.get("source", "unknown")) for s in signals)
    kinds = Counter(str(s.get("kind", "unknown")) for s in signals)
    source_text = ", ".join(f"{k}:{v}" for k, v in sorted(sources.items()))
    kind_text = ", ".join(f"{k}:{v}" for k, v in sorted(kinds.items()))
    return (
        f"{len(signals)} recorded signal(s) point at the same evolution target. "
        f"Sources: {source_text or 'none'}. Kinds: {kind_text or 'none'}."
    )


def _proposal_risk(signals: list[dict]) -> str:
    severities = {str(s.get("severity", "")) for s in signals}
    if "critical" in severities or "high" in severities:
        return (
            "High-salience signal group. Keep this proposal human-reviewed; "
            "do not apply edits automatically."
        )
    return (
        "Proposal-only dry run. No core file is mutated until a human approves "
        "and applies a later-stage update explicitly."
    )


def _build_proposal_record(
    wiki_root: Path,
    dimension: str,
    target: str,
    signals: list[dict],
) -> dict:
    store = ensure_scievolve_store(wiki_root)
    proposal_id = _proposal_id(dimension, target, signals)
    md_path = store / "proposals" / f"{proposal_id}.md"
    json_path = store / "proposals" / f"{proposal_id}.json"
    return {
        "id": proposal_id,
        "created_at": _now_iso(),
        "dimension": dimension,
        "skill": DIMENSION_SKILL[dimension],
        "target": target,
        "triggering_signals": [s.get("id", "") for s in signals],
        "proposed_action": DIMENSION_ACTION[dimension],
        "rationale": _proposal_rationale(signals),
        "risk": _proposal_risk(signals),
        "status": "proposed",
        "output_path": _relative_to_wiki(md_path, wiki_root),
        "json_path": _relative_to_wiki(json_path, wiki_root),
        "evidence": [
            {
                "signal_id": s.get("id", ""),
                "source": s.get("source", ""),
                "kind": s.get("kind", ""),
                "summary": s.get("summary", ""),
                "evidence_path": s.get("evidence_path", ""),
                "evidence_text": s.get("evidence_text", ""),
            }
            for s in signals
        ],
    }


def _proposal_markdown(record: dict, signals: list[dict]) -> str:
    lines = [
        f"# SciEvolve Proposal: {record['id']}",
        "",
        f"- Status: {record['status']}",
        f"- Dimension: {record['dimension']}",
        f"- Skill view: {record['skill']}",
        f"- Target: {record['target'] or '(general)'}",
        f"- Created: {record['created_at']}",
        "",
        "## Triggering Signals",
        "",
    ]
    for signal in signals:
        lines.append(
            "- {id} ({source}/{kind}, severity={severity}, confidence={confidence}): "
            "{summary}".format(
                id=signal.get("id", ""),
                source=signal.get("source", ""),
                kind=signal.get("kind", ""),
                severity=signal.get("severity", ""),
                confidence=signal.get("confidence", ""),
                summary=signal.get("summary", ""),
            )
        )
        evidence_path = signal.get("evidence_path") or ""
        evidence_text = signal.get("evidence_text") or ""
        if evidence_path:
            lines.append(f"  - Evidence path: `{evidence_path}`")
        if evidence_text:
            lines.append(f"  - Evidence text: {evidence_text}")

    lines.extend([
        "",
        "## Proposed Action",
        "",
        record["proposed_action"],
        "",
        "## Rationale",
        "",
        record["rationale"],
        "",
        "## Risk",
        "",
        record["risk"],
        "",
        "## Apply Semantics",
        "",
        (
            "This artifact is a proposal. It does not mutate wiki pages, skills, "
            "runtime schemas, or DAG templates."
        ),
        "",
    ])
    return "\n".join(lines)


def _existing_proposal_ids(index_path: Path) -> set[str]:
    records, _ = _load_jsonl(index_path)
    return {str(r.get("id", "")) for r in records}


def _write_proposal(wiki_root: Path, record: dict, signals: list[dict]) -> dict:
    store = ensure_scievolve_store(wiki_root)
    index_path = store / SCIEVOLVE_PROPOSALS
    md_path = wiki_root / record["output_path"]
    json_path = wiki_root / record["json_path"]

    created = record["id"] not in _existing_proposal_ids(index_path)
    if created:
        md_path.write_text(_proposal_markdown(record, signals), encoding="utf-8")
        json_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    elif json_path.exists():
        try:
            record = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return {"created": created, **record}


def _group_for_proposals(signals: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for signal in signals:
        dimension = str(signal.get("dimension", ""))
        target = str(signal.get("target", ""))
        if dimension not in SCIEVOLVE_DIMENSION_VALUES:
            continue
        groups[(dimension, target)].append(signal)
    return dict(groups)


def _report_markdown(
    generated_at: str,
    all_signals: list[dict],
    included_signals: list[dict],
    proposals: list[dict],
    malformed_signals: int,
    dimension: str,
    target: str,
    propose: bool,
) -> str:
    by_dimension = Counter(str(s.get("dimension", "unknown"))
                           for s in included_signals)
    by_source = Counter(str(s.get("source", "unknown"))
                        for s in included_signals)
    lines = [
        "# SciEvolve Evolution Report",
        "",
        f"- Generated: {generated_at}",
        f"- Mode: {'proposal generation' if propose else 'dry-run summary'}",
        f"- Scope dimension: {dimension or '(all)'}",
        f"- Scope target: {target or '(all)'}",
        f"- Signals loaded: {len(all_signals)}",
        f"- Signals included: {len(included_signals)}",
        f"- Malformed signal rows ignored: {malformed_signals}",
        "",
        "## Signal Summary",
        "",
    ]
    if included_signals:
        lines.append("By dimension:")
        for key, count in sorted(by_dimension.items()):
            lines.append(f"- {key}: {count}")
        lines.append("")
        lines.append("By source:")
        for key, count in sorted(by_source.items()):
            lines.append(f"- {key}: {count}")
    else:
        lines.append("No signals matched this scope yet.")

    lines.extend(["", "## Included Signals", ""])
    if included_signals:
        for signal in included_signals:
            lines.append(
                "- {id} [{dimension} -> {target}] {summary}".format(
                    id=signal.get("id", ""),
                    dimension=signal.get("dimension", ""),
                    target=signal.get("target", "") or "(general)",
                    summary=signal.get("summary", ""),
                )
            )
    else:
        lines.append("_No signals to report._")

    lines.extend(["", "## Proposal Artifacts", ""])
    if proposals:
        for proposal in proposals:
            state = "created" if proposal.get("created") else "existing"
            lines.append(
                f"- {proposal['id']} ({state}, {proposal['status']}): "
                f"`{proposal['output_path']}`"
            )
    elif propose:
        lines.append("_No proposal artifacts were generated because no signals matched._")
    else:
        lines.append("_Run with `--propose` to create proposal artifacts._")

    lines.extend([
        "",
        "## Skill Views",
        "",
        "- `memory` -> `/dream`",
        "- `workflow` -> `/forge`",
        "- `orchestration` -> `/morph`",
        "",
        (
            "This report is proposal-first. It records evidence and candidate "
            "updates without applying them."
        ),
        "",
    ])
    return "\n".join(lines)


def scievolve_report(
    wiki_root: str,
    dimension: str = "",
    target: str = "",
    limit: int = 20,
    propose: bool = False,
    as_json: bool = False,
) -> None:
    if dimension:
        _validate_choice("dimension", dimension, SCIEVOLVE_DIMENSION_VALUES)

    root = Path(wiki_root)
    store = ensure_scievolve_store(root)
    signals, malformed = load_scievolve_signals(root)
    included = _filter_signals(signals, dimension, target, limit)

    proposals = []
    if propose:
        for (proposal_dimension, proposal_target), group in sorted(
            _group_for_proposals(included).items()
        ):
            record = _build_proposal_record(
                root, proposal_dimension, proposal_target, group
            )
            proposals.append(_write_proposal(root, record, group))

    generated_at = _now_iso()
    report_path = (
        store / "reports" /
        f"{_compact_timestamp()}-scievolve-report.md"
    )
    report_path.write_text(
        _report_markdown(
            generated_at,
            signals,
            included,
            proposals,
            malformed,
            dimension,
            target,
            propose,
        ),
        encoding="utf-8",
    )

    result = {
        "status": "ok",
        "report_path": str(report_path),
        "signal_count": len(included),
        "total_signal_count": len(signals),
        "malformed_signal_rows": malformed,
        "proposal_count": len(proposals),
        "proposals": proposals,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"SciEvolve report: {report_path}")
        print(f"Signals included: {len(included)}")
        print(f"Proposals: {len(proposals)}")
