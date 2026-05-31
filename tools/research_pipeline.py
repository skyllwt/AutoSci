#!/usr/bin/env python3
"""Read-only advisory tool for the /research pipeline (SciFlow Harness State/Orchestration).

Reports pipeline status from wiki/outputs/pipeline-progress.md + experiment pages and
recommends the next action via plan_next. It does NOT advance the pipeline (advisory only).
Stage-3 job state is derived live from experiment pages — there is no jobs.jsonl.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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
    return "baseline" in (exp.tags or []) or "baseline" in exp.slug


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
        if not deployed:
            return Decision("terminate", "all_deploys_failed",
                            "No experiments deployed (all deploys failed) — check GPU/SSH config.")
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
        all_neg = all(e.outcome in ("failed", "inconclusive", None) for e in exp_states)
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
