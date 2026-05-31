#!/usr/bin/env python3
"""Read-only advisory tool for the /research pipeline (SciFlow Harness State/Orchestration).

Reports pipeline status from wiki/outputs/pipeline-progress.md + experiment pages and
recommends the next action via plan_next. It does NOT advance the pipeline (advisory only).
Stage-3 job state is derived live from experiment pages — there is no jobs.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_progress  # noqa: E402  (tools/ sibling; reuses parse_progress + validate)
import lint  # noqa: E402  (tools/ sibling; deterministic form-check at the gate)
import wiki_events  # noqa: E402  (tools/ sibling; sanctioned event writer)


@dataclass
class ExpState:
    slug: str
    status: str | None = None
    outcome: str | None = None
    started: str | None = None
    estimated_hours: int | None = None
    tags: list = field(default_factory=list)


@dataclass
class Decision:
    action: str   # done | terminate | await | resume | proceed | iterate | manual_gate
    reason: str
    detail: str


def is_baseline(exp: ExpState) -> bool:
    return "baseline" in (exp.tags or []) or exp.slug.endswith("-baseline") or exp.slug == "baseline"


def _clean_slug(value) -> str:
    s = str(value or "").strip().strip('"').strip("'")
    while s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    return s


def plan_next(frontmatter: dict, stage_log: dict, exp_states: list, idea_status) -> Decision:
    """Pure decision engine. Inputs are already-parsed; no I/O.
    Returns a Decision recommending the next action (advisory)."""
    fm = frontmatter or {}
    log = stage_log or {}
    status = str(fm.get("status") or "")
    stage = str(fm.get("current_stage") or "")
    # Prefer the actually-deployed slugs; fall back to the planned set. An empty
    # stage3a_deployed (all deploys failed) is falsy, so it correctly yields [].
    deployed = fm.get("stage3a_deployed") or fm.get("experiment_slugs") or []
    try:
        iters = int(fm.get("iteration_count") or 0)
    except (TypeError, ValueError):
        iters = 0
    skip_paper = bool(fm.get("skip_paper"))
    idea_slug = _clean_slug(fm.get("idea_slug"))

    if status == "completed":
        return Decision("done", "pipeline_completed", "Pipeline already completed.")
    if status == "failed":
        return Decision("terminate", "already_failed", "Pipeline is marked failed.")

    if stage == "stage1":
        if log.get("stage1") == "completed" and not idea_slug:
            return Decision("terminate", "all_ideas_failed",
                            "Stage 1 finished but no idea was selected — adjust the research direction.")
        if log.get("stage1") == "completed" and idea_slug and log.get("gate1") == "pending":
            return Decision("manual_gate", "gate1", "Stage 1 done — select an idea (Gate 1), then continue.")
        # gate1 already approved (or stage1 not yet complete): resuming stage1 is correct
        return Decision("resume", "stage1", "/research --start-from stage1")

    if stage == "stage2":
        if log.get("stage2") == "completed":
            return Decision("proceed", "stage3", "Stage 2 done — deploy experiments: /research --start-from stage3")
        return Decision("resume", "stage2", "/research --start-from stage2")

    if stage in ("stage3", "stage3-await"):
        stage3a = fm.get("stage3a_deployed")
        # All Stage-3a deploys failed: the deploy step ran but recorded an empty list.
        if isinstance(stage3a, list) and len(stage3a) == 0:
            return Decision("terminate", "all_deploys_failed",
                            "No experiments deployed (all deploys failed) — check GPU/SSH config.")
        if not deployed:
            return Decision("resume", "stage3", "/research --start-from stage3")
        if any(is_baseline(e) and e.outcome == "failed" for e in exp_states):
            return Decision("terminate", "baseline_collect_failed",
                            "Baseline experiment failed — baseline cannot be reproduced.")
        if exp_states and all(e.status == "completed" for e in exp_states):
            return Decision("resume", "stage3-collect",
                            "All experiments complete — collect results: /research --start-from stage3-collect")
        if not exp_states:
            return Decision("await", "experiments_running",
                            "Experiments deployed but no experiment pages loaded yet — "
                            "check wiki/experiments/ or run /exp-status.")
        running = [e.slug for e in exp_states if e.status != "completed"]
        return Decision("await", "experiments_running",
                        f"{len(running)} experiment(s) still running: {', '.join(running)}. "
                        "Check /exp-status; resume with /research --start-from stage3-collect when done.")

    if stage == "stage4":
        if not exp_states:
            return Decision("manual_gate", "no_experiment_results",
                            "Stage 4 reached but no experiment results available — check stage 3 outputs.")
        supporting = [e for e in exp_states if not is_baseline(e)]
        all_neg = all(e.outcome in ("failed", "inconclusive", None) for e in supporting)
        insufficient = (idea_status in ("proposed", "in_progress", "tested") and all_neg) or idea_status == "failed"
        if insufficient and iters < 2:
            return Decision("iterate", "verdict_insufficient",
                            f"Verdict insufficient (iteration {iters}/2) — refine idea/experiments and retry.")
        if insufficient and iters >= 2:
            return Decision("terminate", "max_iterations_reached",
                            "Verdict still insufficient after 2 iterations — stop.")
        if skip_paper:
            return Decision("done", "research_only_complete",
                            "Experiments validated; --skip-paper set, so research is complete.")
        if log.get("gate2") == "pending":
            return Decision("manual_gate", "gate2", "Verdict positive — approve paper writing (Gate 2), then continue.")
        return Decision("proceed", "stage5", "Proceed to paper writing: /research --start-from stage5")

    if stage == "stage5":
        if log.get("stage5") == "completed":
            return Decision("done", "paper_complete", "Stage 5 complete.")
        return Decision("resume", "stage5", "/research --start-from stage5")

    return Decision("resume", stage or "stage1", f"/research --start-from {stage or 'stage1'}")


def _read_frontmatter(path: Path) -> dict:
    """YAML-load a page's frontmatter. Intentionally a small standalone reader
    (generalizes pipeline_progress._read_status) to avoid importing research_wiki."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = yaml.safe_load(parts[1])
    return fm if isinstance(fm, dict) else {}


def derive_exp_states(wiki_dir, slugs) -> list:
    """Build ExpState list from experiment pages (no jobs registry)."""
    states = []
    for slug in slugs or []:
        slug = _clean_slug(slug)
        fm = _read_frontmatter(Path(wiki_dir) / "experiments" / f"{slug}.md")
        started = fm.get("started")
        states.append(ExpState(
            slug=slug,
            status=fm.get("status"),
            outcome=fm.get("outcome"),
            started=str(started) if started is not None else None,
            estimated_hours=fm.get("estimated_hours"),
            tags=fm.get("tags") or [],
        ))
    return states


def _read_idea_status(wiki_dir, idea_slug):
    idea_slug = _clean_slug(idea_slug)
    if not idea_slug:
        return None
    return _read_frontmatter(Path(wiki_dir) / "ideas" / f"{idea_slug}.md").get("status")


def gather(wiki_dir):
    """Return (frontmatter, stage_log, exp_states, idea_status) or None if no pipeline file."""
    progress = Path(wiki_dir) / pipeline_progress.PROGRESS_REL
    if not progress.exists():
        return None
    fm, stage_log = pipeline_progress.parse_progress(progress)
    deployed = fm.get("stage3a_deployed") or fm.get("experiment_slugs") or []
    exp_states = derive_exp_states(wiki_dir, deployed)
    idea_status = _read_idea_status(wiki_dir, fm.get("idea_slug"))
    return fm, stage_log, exp_states, idea_status


def resume_plan(wiki_dir) -> Decision:
    g = gather(wiki_dir)
    if g is None:
        return Decision("done", "no_pipeline", "No active pipeline (outputs/pipeline-progress.md not found).")
    fm, stage_log, exp_states, idea_status = g
    return plan_next(fm, stage_log, exp_states, idea_status)


def _status_payload(wiki_dir):
    """Return the status dict, or None when there is no active pipeline."""
    g = gather(wiki_dir)
    if g is None:
        return None
    fm, stage_log, exp_states, idea_status = g
    decision = plan_next(fm, stage_log, exp_states, idea_status)
    return {
        "slug": fm.get("slug"),
        "status": fm.get("status"),
        "current_stage": fm.get("current_stage"),
        "idea_slug": _clean_slug(fm.get("idea_slug")),
        "idea_status": idea_status,
        "stage_log": stage_log,
        "experiments": [asdict(e) for e in exp_states],
        "counts": {
            "running": sum(1 for e in exp_states if e.status == "running"),
            "completed": sum(1 for e in exp_states if e.status == "completed"),
            "failed": sum(1 for e in exp_states if e.outcome == "failed"),
            "inconclusive": sum(1 for e in exp_states if e.outcome == "inconclusive"),
        },
        "decision": asdict(decision),
    }


def status(wiki_dir, as_json: bool = False) -> str:
    payload = _status_payload(wiki_dir)
    if payload is None:
        if as_json:
            return json.dumps({"pipeline": None}, ensure_ascii=False, indent=2)
        return "No active pipeline (outputs/pipeline-progress.md not found)."
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines = [
        f"pipeline: {payload['slug']}  status={payload['status']}  current_stage={payload['current_stage']}",
        f"idea: {payload['idea_slug'] or '(none)'} ({payload['idea_status']})",
        "experiments:",
    ]
    for e in payload["experiments"]:
        lines.append(f"  - {e['slug']}: status={e['status']} outcome={e['outcome']}")
    c = payload["counts"]
    lines.append(f"counts: running={c['running']} completed={c['completed']} failed={c['failed']} inconclusive={c['inconclusive']}")
    d = payload["decision"]
    lines.append(f"next: [{d['action']}] {d['reason']} — {d['detail']}")
    return "\n".join(lines)


# ── Stage handoff verification gate (S1.2) ──────────────────────────────────

_GATE_RANK = {"PASS": 0, "WARN": 1, "BLOCK": 2}


@dataclass
class GateCheck:
    name: str
    status: str   # PASS | WARN | BLOCK
    message: str


@dataclass
class GateVerdict:
    decision: str
    from_stage: str
    to_stage: str
    overridden: bool
    checks: list[GateCheck] = field(default_factory=list)

    def to_event(self) -> dict:
        return {
            "kind": "gate",
            "from": self.from_stage,
            "to": self.to_stage,
            "decision": self.decision,
            "overridden": self.overridden,
            "checks": [{"name": c.name, "status": c.status, "message": c.message} for c in self.checks],
        }


def _gate_overall(checks: list[GateCheck]) -> str:
    worst = "PASS"
    for c in checks:
        if _GATE_RANK[c.status] > _GATE_RANK[worst]:
            worst = c.status
    return worst


def gate_handoff(wiki_dir, from_stage: str, to_stage: str, *, manuscript=None, override: bool = False) -> GateVerdict:
    """Verify a stage handoff. Generic checks (pipeline-validate + lint form) run
    every time; evidence (→stage5) and manuscript (→rebuttal) gates are handoff-
    specific. `override` only softens the evidence gate. No event I/O (caller emits)."""
    checks = []
    overridden = False

    # Generic: pipeline-progress validation
    for severity, message in pipeline_progress.validate(wiki_dir):
        checks.append(GateCheck("pipeline:validate", severity, message))

    # Generic: deterministic form-check (lint)
    issues = lint.lint(Path(wiki_dir))
    reds = [i for i in issues if i.level == "🔴"]
    yellows = [i for i in issues if i.level == "🟡"]
    if reds:
        checks.append(GateCheck("form:lint", "BLOCK", f"{len(reds)} structural lint error(s)"))
    elif yellows:
        checks.append(GateCheck("form:lint", "WARN", f"{len(yellows)} lint warning(s)"))
    else:
        checks.append(GateCheck("form:lint", "PASS", "no lint errors"))

    # Evidence gate (Experiment -> Writing)
    if to_stage == "stage5":
        g = gather(wiki_dir)
        exp_states = g[2] if g else []  # gather() resolves stage3a_deployed -> experiment_slugs
        succeeded = [e for e in exp_states if e.outcome == "succeeded"]
        if succeeded:
            checks.append(GateCheck("evidence:experiment", "PASS", f"{len(succeeded)} succeeded experiment(s)"))
        elif override:
            overridden = True
            checks.append(GateCheck("evidence:experiment", "WARN", "no succeeded experiment; overridden"))
        else:
            checks.append(GateCheck("evidence:experiment", "BLOCK",
                                    "no succeeded experiment — paper writing blocked (use --override to proceed)"))

    # Manuscript gate (Writing -> Rebuttal)
    if to_stage == "rebuttal":
        if manuscript:
            ms = _read_frontmatter(Path(wiki_dir) / "manuscripts" / f"{_clean_slug(manuscript)}.md")
            st = ms.get("status")
            if st in ("submitted", "final_version"):
                checks.append(GateCheck("manuscript:status", "PASS", f"manuscript status={st}"))
            else:
                checks.append(GateCheck("manuscript:status", "BLOCK", f"manuscript not submitted (status={st})"))
        else:
            checks.append(GateCheck("manuscript:status", "WARN",
                                    "no --manuscript specified; cannot verify manuscript status"))

    return GateVerdict(decision=_gate_overall(checks), from_stage=from_stage,
                       to_stage=to_stage, overridden=overridden, checks=checks)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="research_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "resume-plan", "validate"):
        p = sub.add_parser(name)
        p.add_argument("wiki_root")
        if name in ("status", "resume-plan"):
            p.add_argument("--json", action="store_true")
    pg = sub.add_parser("gate")
    pg.add_argument("wiki_root")
    pg.add_argument("--from", dest="from_stage", required=True)
    pg.add_argument("--to", dest="to_stage", required=True)
    pg.add_argument("--manuscript", default=None)
    pg.add_argument("--override", action="store_true")
    pg.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "status":
        print(status(args.wiki_root, as_json=args.json))
        return 0
    if args.command == "resume-plan":
        d = resume_plan(args.wiki_root)
        if args.json:
            print(json.dumps(asdict(d), ensure_ascii=False, indent=2))
        else:
            print(f"[{d.action}] {d.reason} — {d.detail}")
        return 0
    if args.command == "validate":
        issues = pipeline_progress.validate(args.wiki_root)
        for severity, message in issues:
            print(f"{severity}: {message}")
        return 1 if any(sev == "BLOCK" for sev, _ in issues) else 0
    if args.command == "gate":
        verdict = gate_handoff(args.wiki_root, args.from_stage, args.to_stage,
                               manuscript=args.manuscript, override=args.override)
        wiki_events.append_event(args.wiki_root, "pipeline_events", verdict.to_event())
        if args.json:
            print(json.dumps(verdict.to_event(), ensure_ascii=False, indent=2))
        else:
            tag = " (overridden)" if verdict.overridden else ""
            print(f"[{verdict.decision}] {args.from_stage} -> {args.to_stage}{tag}")
            for c in verdict.checks:
                print(f"  [{c.status}] {c.name}: {c.message}")
        return 1 if verdict.decision == "BLOCK" else 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
