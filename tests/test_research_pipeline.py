#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("research_pipeline", TOOLS / "research_pipeline.py")
assert spec and spec.loader
rp = importlib.util.module_from_spec(spec)
sys.modules["research_pipeline"] = rp
spec.loader.exec_module(rp)


def _exp(slug, status=None, outcome=None, tags=None):
    return rp.ExpState(slug=slug, status=status, outcome=outcome, tags=tags or [])


def _fm(**kw):
    base = {"status": "running", "current_stage": "stage1", "idea_slug": "",
            "stage3a_deployed": [], "experiment_slugs": [], "iteration_count": 0, "skip_paper": False}
    base.update(kw)
    return base


def _log(**kw):
    base = {"stage0": "skipped", "stage1": "pending", "gate1": "pending", "stage2": "pending",
            "stage3a": "pending", "stage3b": "pending", "stage3c": "pending",
            "stage4": "pending", "gate2": "pending", "stage5": "pending"}
    base.update(kw)
    return base


class IsBaselineTests(unittest.TestCase):
    def test_baseline_by_tag(self) -> None:
        self.assertTrue(rp.is_baseline(_exp("exp-x-1", tags=["baseline", "kernel"])))

    def test_baseline_by_slug(self) -> None:
        self.assertTrue(rp.is_baseline(_exp("exp-foo-baseline")))

    def test_non_baseline(self) -> None:
        self.assertFalse(rp.is_baseline(_exp("exp-foo-ablation", tags=["ablation"])))

    def test_baseline_substring_not_overmatched(self) -> None:
        self.assertFalse(rp.is_baseline(_exp("exp-baseline-free-method")))


class PlanNextTests(unittest.TestCase):
    def test_completed_is_done(self) -> None:
        d = rp.plan_next(_fm(status="completed"), _log(), [], None)
        self.assertEqual(d.action, "done")

    def test_failed_is_terminate(self) -> None:
        d = rp.plan_next(_fm(status="failed"), _log(), [], None)
        self.assertEqual((d.action, d.reason), ("terminate", "already_failed"))

    def test_stage1_no_idea_terminates(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage1", idea_slug=""), _log(stage1="completed"), [], None)
        self.assertEqual((d.action, d.reason), ("terminate", "all_ideas_failed"))

    def test_stage1_gate1_manual(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage1", idea_slug="my-idea"),
                         _log(stage1="completed", gate1="pending"), [], "proposed")
        self.assertEqual((d.action, d.reason), ("manual_gate", "gate1"))

    def test_stage3_await_no_deploys_terminates(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=[]),
                         _log(stage1="completed", gate1="completed", stage2="completed", stage3a="completed"),
                         [], "in_progress")
        self.assertEqual((d.action, d.reason), ("terminate", "all_deploys_failed"))

    def test_stage3_await_baseline_failed_terminates(self) -> None:
        exps = [_exp("exp-foo-baseline", status="completed", outcome="failed"),
                _exp("exp-foo-val", status="completed", outcome="succeeded")]
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=["exp-foo-baseline", "exp-foo-val"]),
                         _log(), exps, "in_progress")
        self.assertEqual((d.action, d.reason), ("terminate", "baseline_collect_failed"))

    def test_stage3_await_all_complete_resume_collect(self) -> None:
        exps = [_exp("exp-foo-baseline", status="completed", outcome="succeeded"),
                _exp("exp-foo-val", status="completed", outcome="succeeded")]
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=["exp-foo-baseline", "exp-foo-val"]),
                         _log(), exps, "in_progress")
        self.assertEqual((d.action, d.reason), ("resume", "stage3-collect"))
        self.assertIn("stage3-collect", d.detail)

    def test_stage3_await_running_awaits(self) -> None:
        exps = [_exp("exp-foo-baseline", status="completed", outcome="succeeded"),
                _exp("exp-foo-val", status="running")]
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=["exp-foo-baseline", "exp-foo-val"]),
                         _log(), exps, "in_progress")
        self.assertEqual(d.action, "await")
        self.assertIn("exp-foo-val", d.detail)

    def test_stage4_insufficient_iterates(self) -> None:
        exps = [_exp("exp-foo-val", status="completed", outcome="failed")]
        d = rp.plan_next(_fm(current_stage="stage4", iteration_count=0), _log(stage4="completed"), exps, "tested")
        self.assertEqual((d.action, d.reason), ("iterate", "verdict_insufficient"))

    def test_stage4_insufficient_max_iters_terminates(self) -> None:
        exps = [_exp("exp-foo-val", status="completed", outcome="failed")]
        d = rp.plan_next(_fm(current_stage="stage4", iteration_count=2), _log(stage4="completed"), exps, "tested")
        self.assertEqual((d.action, d.reason), ("terminate", "max_iterations_reached"))

    def test_stage4_ok_skip_paper_done(self) -> None:
        exps = [_exp("exp-foo-val", status="completed", outcome="succeeded")]
        d = rp.plan_next(_fm(current_stage="stage4", skip_paper=True), _log(stage4="completed"), exps, "validated")
        self.assertEqual((d.action, d.reason), ("done", "research_only_complete"))

    def test_stage4_ok_gate2_manual(self) -> None:
        exps = [_exp("exp-foo-val", status="completed", outcome="succeeded")]
        d = rp.plan_next(_fm(current_stage="stage4"), _log(stage4="completed", gate2="pending"), exps, "validated")
        self.assertEqual((d.action, d.reason), ("manual_gate", "gate2"))

    def test_stage4_ok_proceeds_to_stage5(self) -> None:
        exps = [_exp("exp-foo-val", status="completed", outcome="succeeded")]
        d = rp.plan_next(_fm(current_stage="stage4"), _log(stage4="completed", gate2="completed"), exps, "validated")
        self.assertEqual((d.action, d.reason), ("proceed", "stage5"))

    def test_stage2_completed_proceeds(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage2"), _log(stage2="completed"), [], "in_progress")
        self.assertEqual((d.action, d.reason), ("proceed", "stage3"))

    def test_stage2_resume(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage2"), _log(), [], "in_progress")
        self.assertEqual((d.action, d.reason), ("resume", "stage2"))

    def test_stage5_completed_done(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage5"), _log(stage5="completed"), [], "validated")
        self.assertEqual((d.action, d.reason), ("done", "paper_complete"))

    def test_stage0_fallthrough_resume(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage0"), _log(), [], None)
        self.assertEqual(d.action, "resume")

    def test_stage3_await_no_exp_pages_awaits(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=["e1"]), _log(), [], "in_progress")
        self.assertEqual(d.action, "await")
        self.assertIn("no experiment pages", d.detail.lower())

    def test_stage4_no_exps_manual_gate(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage4"), _log(stage4="completed"), [], "tested")
        self.assertEqual((d.action, d.reason), ("manual_gate", "no_experiment_results"))

    def test_all_deploys_failed_with_planned_slugs(self) -> None:
        d = rp.plan_next(_fm(current_stage="stage3-await", stage3a_deployed=[], experiment_slugs=["e1", "e2"]),
                         _log(stage1="completed", gate1="completed", stage2="completed"), [], "in_progress")
        self.assertEqual((d.action, d.reason), ("terminate", "all_deploys_failed"))

    def test_stage4_baseline_ok_but_supporting_failed_iterates(self) -> None:
        exps = [_exp("exp-foo-baseline", status="completed", outcome="succeeded"),
                _exp("exp-foo-val", status="completed", outcome="failed")]
        d = rp.plan_next(_fm(current_stage="stage4", iteration_count=0), _log(stage4="completed"), exps, "tested")
        self.assertEqual((d.action, d.reason), ("iterate", "verdict_insufficient"))


_PROGRESS = """---
slug: p1
direction: kernel opt
status: running
current_stage: stage3-await
started: 2026-05-31
mode: auto
skip_paper: false
idea_slug: i1
experiment_slugs: [e-baseline, e-val]
stage3a_deployed: [e-baseline, e-val]
linked_idea_slugs: []
iteration_count: 0
---
## Stage Log
- Stage 0 (Bootstrap): skipped
- Stage 1: completed
- Gate 1: completed
- Stage 2: completed
- Stage 3a (Deploy): completed
- Stage 3b (Await): running
- Stage 3c (Collect): pending
- Stage 4: pending
- Gate 2: pending
- Stage 5: pending
"""


def _wiki(progress=_PROGRESS, exps=None, idea_status="in_progress") -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    (d / "experiments").mkdir(parents=True, exist_ok=True)
    (d / "ideas").mkdir(parents=True, exist_ok=True)
    if progress is not None:
        (d / "outputs" / "pipeline-progress.md").write_text(progress, encoding="utf-8")
    for slug, fields in (exps or {}).items():
        fm = "\n".join(f"{k}: {v}" for k, v in fields.items())
        (d / "experiments" / f"{slug}.md").write_text(f"---\nslug: {slug}\n{fm}\n---\n# {slug}\n", encoding="utf-8")
    if idea_status is not None:
        (d / "ideas" / "i1.md").write_text(f"---\nslug: i1\nstatus: {idea_status}\n---\n# i1\n", encoding="utf-8")
    return d


class ToolTests(unittest.TestCase):
    def test_derive_exp_states_reads_pages(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded", "tags": "[baseline]"},
                        "e-val": {"status": "running"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        states = rp.derive_exp_states(d, ["e-baseline", "e-val"])
        by = {e.slug: e for e in states}
        self.assertEqual(by["e-baseline"].status, "completed")
        self.assertEqual(by["e-baseline"].outcome, "succeeded")
        self.assertTrue(rp.is_baseline(by["e-baseline"]))
        self.assertEqual(by["e-val"].status, "running")

    def test_resume_plan_awaits_when_running(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"},
                        "e-val": {"status": "running"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        decision = rp.resume_plan(d)
        self.assertEqual(decision.action, "await")

    def test_resume_plan_collect_when_all_done(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"},
                        "e-val": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        decision = rp.resume_plan(d)
        self.assertEqual((decision.action, decision.reason), ("resume", "stage3-collect"))

    def test_resume_plan_baseline_failed_terminates(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"},
                        "e-val": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        decision = rp.resume_plan(d)
        self.assertEqual((decision.action, decision.reason), ("terminate", "baseline_collect_failed"))

    def test_status_no_pipeline(self) -> None:
        d = _wiki(progress=None)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        text = rp.status(d)
        self.assertIn("no active pipeline", text.lower())


class CliTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / "research_pipeline.py"), *args],
                              capture_output=True, text=True)

    def test_cli_resume_plan_runs(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"},
                        "e-val": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run("resume-plan", str(d))
        self.assertEqual(r.returncode, 0)
        self.assertIn("stage3-collect", r.stdout)

    def test_cli_status_json(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"},
                        "e-val": {"status": "running"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run("status", str(d), "--json")
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["current_stage"], "stage3-await")
        self.assertEqual(payload["decision"]["action"], "await")

    def test_cli_status_json_handles_date_started(self) -> None:
        # /exp-run writes `started: YYYY-MM-DD`; yaml loads it as datetime.date.
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded", "started": "2026-05-31"},
                        "e-val": {"status": "running", "started": "2026-05-31"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run("status", str(d), "--json")
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["experiments"][0]["started"], "2026-05-31")

    def test_cli_validate_block_exits_1(self) -> None:
        prog = _PROGRESS.replace("idea_slug: i1", "idea_slug: ghost")
        d = _wiki(progress=prog, idea_status=None,
                  exps={"e-baseline": {"status": "completed"}, "e-val": {"status": "completed"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run("validate", str(d))
        self.assertEqual(r.returncode, 1)


class GateTests(unittest.TestCase):
    def _no_generic(self):
        # patch out the generic checks (real lint flags 🔴 on minimal pages; real validate
        # flags dangling refs) so each test isolates the gate-specific logic
        return (mock.patch.object(rp.lint, "lint", return_value=[]),
                mock.patch.object(rp.pipeline_progress, "validate", return_value=[]))

    def test_gate_evidence_pass(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"},
                        "e-val": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage4", "stage5")
        self.assertEqual(v.decision, "PASS")

    def test_gate_evidence_block(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"},
                        "e-val": {"status": "completed", "outcome": "inconclusive"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage4", "stage5")
        self.assertEqual(v.decision, "BLOCK")
        self.assertTrue(any(c.name == "evidence:experiment" and c.status == "BLOCK" for c in v.checks))

    def test_gate_evidence_override(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"},
                        "e-val": {"status": "completed", "outcome": "failed"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage4", "stage5", override=True)
        self.assertEqual(v.decision, "WARN")
        self.assertTrue(v.overridden)

    def test_gate_lint_red_blocks(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        red = rp.lint.LintIssue("🔴", "demo", "papers/x.md", "missing field")
        with mock.patch.object(rp.lint, "lint", return_value=[red]), \
             mock.patch.object(rp.pipeline_progress, "validate", return_value=[]):
            v = rp.gate_handoff(d, "stage4", "stage5")
        self.assertEqual(v.decision, "BLOCK")
        self.assertTrue(any(c.name == "form:lint" and c.status == "BLOCK" for c in v.checks))

    def test_gate_validate_block(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "succeeded"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with mock.patch.object(rp.lint, "lint", return_value=[]), \
             mock.patch.object(rp.pipeline_progress, "validate", return_value=[("BLOCK", "dangling idea")]):
            v = rp.gate_handoff(d, "stage4", "stage5")
        self.assertEqual(v.decision, "BLOCK")
        self.assertTrue(any(c.name == "pipeline:validate" for c in v.checks))

    def test_gate_manuscript_pass(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "manuscripts").mkdir(parents=True, exist_ok=True)
        (d / "manuscripts" / "m1.md").write_text("---\nslug: m1\nstatus: submitted\n---\n# m1\n", encoding="utf-8")
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage5", "rebuttal", manuscript="m1")
        self.assertEqual(v.decision, "PASS")

    def test_gate_manuscript_block(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "manuscripts").mkdir(parents=True, exist_ok=True)
        (d / "manuscripts" / "m1.md").write_text("---\nslug: m1\nstatus: drafting\n---\n# m1\n", encoding="utf-8")
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage5", "rebuttal", manuscript="m1")
        self.assertEqual(v.decision, "BLOCK")

    def test_gate_manuscript_no_arg_warns(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage5", "rebuttal")
        self.assertEqual(v.decision, "WARN")
        self.assertTrue(any(c.name == "manuscript:status" and c.status == "WARN" for c in v.checks))

    def test_gate_override_does_not_bypass_lint_block(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        red = rp.lint.LintIssue("🔴", "demo", "papers/x.md", "missing field")
        with mock.patch.object(rp.lint, "lint", return_value=[red]), \
             mock.patch.object(rp.pipeline_progress, "validate", return_value=[]):
            v = rp.gate_handoff(d, "stage4", "stage5", override=True)
        self.assertEqual(v.decision, "BLOCK")  # --override softens evidence only, NOT lint

    def test_gate_generic_only_for_other_handoff(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        m1, m2 = self._no_generic()
        with m1, m2:
            v = rp.gate_handoff(d, "stage2", "stage3")
        names = {c.name for c in v.checks}
        self.assertNotIn("evidence:experiment", names)
        self.assertNotIn("manuscript:status", names)
        self.assertEqual(v.decision, "PASS")


class GateCliTests(unittest.TestCase):
    def test_cli_gate_blocks_and_writes_event(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"},
                        "e-val": {"status": "completed", "outcome": "failed"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = subprocess.run([sys.executable, str(TOOLS / "research_pipeline.py"), "gate",
                            str(d), "--from", "stage4", "--to", "stage5"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)  # no succeeded experiment (and/or lint) -> BLOCK
        events = d / "graph" / "pipeline_events.jsonl"
        self.assertTrue(events.exists())
        rows = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(any(row.get("kind") == "gate" for row in rows))

    def test_cli_gate_json(self) -> None:
        d = _wiki(exps={"e-baseline": {"status": "completed", "outcome": "failed"},
                        "e-val": {"status": "completed", "outcome": "failed"}})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = subprocess.run([sys.executable, str(TOOLS / "research_pipeline.py"), "gate",
                            str(d), "--from", "stage4", "--to", "stage5", "--json"],
                           capture_output=True, text=True)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["kind"], "gate")
        self.assertEqual(payload["to"], "stage5")


class FeedbackTests(unittest.TestCase):
    def test_route_known(self) -> None:
        self.assertEqual(rp.route_feedback("schema_error"), "refine")
        self.assertEqual(rp.route_feedback("evidence_gap"), "manual_gate")
        self.assertEqual(rp.route_feedback("experiment_failed"), "rerun")
        self.assertEqual(rp.route_feedback("review_concern"), "refine")
        self.assertEqual(rp.route_feedback("compile_failed"), "refine")

    def test_route_unknown_manual_gate(self) -> None:
        self.assertEqual(rp.route_feedback("???"), "manual_gate")
        self.assertEqual(rp.route_feedback(None), "manual_gate")

    def test_classify_known(self) -> None:
        self.assertEqual(rp.classify_signal("baseline_collect_failed"), "experiment_failed")
        self.assertEqual(rp.classify_signal("evidence:experiment"), "evidence_gap")
        self.assertEqual(rp.classify_signal("form:lint"), "schema_error")
        self.assertEqual(rp.classify_signal("manuscript:status"), "compile_failed")

    def test_classify_unknown_none(self) -> None:
        self.assertIsNone(rp.classify_signal("totally_unknown"))
        self.assertIsNone(rp.classify_signal(None))

    def test_feedback_from_reason(self) -> None:
        v = rp.feedback(reason="baseline_collect_failed")
        self.assertEqual((v.category, v.action), ("experiment_failed", "rerun"))

    def test_feedback_from_category(self) -> None:
        v = rp.feedback(category="schema_error")
        self.assertEqual(v.action, "refine")

    def test_feedback_unknown_reason(self) -> None:
        v = rp.feedback(reason="unknown_xyz")
        self.assertEqual((v.category, v.action), ("unknown", "manual_gate"))

    def test_feedback_to_event(self) -> None:
        ev = rp.feedback(reason="evidence:experiment", source="gate", detail="d").to_event()
        self.assertEqual(ev["kind"], "feedback")
        self.assertEqual(ev["category"], "evidence_gap")
        self.assertEqual(ev["action"], "manual_gate")
        self.assertEqual(ev["source"], "gate")

    def test_feedback_category_wins_over_reason(self) -> None:
        v = rp.feedback(category="schema_error", reason="baseline_collect_failed")
        self.assertEqual((v.category, v.action), ("schema_error", "refine"))

    def test_feedback_empty_category_not_classified_from_reason(self) -> None:
        v = rp.feedback(category="", reason="baseline_collect_failed")
        self.assertEqual(v.category, "unknown")  # explicit "" != reason-derived category

    def test_classify_all_ideas_failed(self) -> None:
        self.assertEqual(rp.classify_signal("all_ideas_failed"), "terminal_failure")


class FeedbackCliTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / "research_pipeline.py"), "feedback", *args],
                              capture_output=True, text=True)

    def test_cli_feedback_emits_event_exit_0(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run(str(d), "--reason", "evidence:experiment", "--source", "gate", "--json")
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["category"], "evidence_gap")
        self.assertEqual(payload["action"], "manual_gate")
        rows = [json.loads(line) for line in (d / "graph" / "pipeline_feedback.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(any(row.get("kind") == "feedback" for row in rows))

    def test_cli_feedback_category_exit_0(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run(str(d), "--category", "schema_error")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "[schema_error] -> refine")

    def test_cli_feedback_reason_plain_text(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run(str(d), "--reason", "evidence:experiment")  # no --json -> plain text
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "[evidence_gap] -> manual_gate (evidence:experiment)")

    def test_cli_feedback_no_args_exit_2(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = self._run(str(d))
        self.assertEqual(r.returncode, 2)
        self.assertIn("--category or --reason", r.stderr)


class TestTerminalFailureRouting(unittest.TestCase):
    def test_terminal_failure_routes_to_stop(self):
        self.assertEqual(rp.route_feedback("terminal_failure"), "stop")

    def test_max_iterations_classifies_terminal(self):
        self.assertEqual(rp.classify_signal("max_iterations_reached"), "terminal_failure")
        self.assertEqual(rp.route_feedback(rp.classify_signal("max_iterations_reached")), "stop")

    def test_all_ideas_failed_classifies_terminal(self):
        self.assertEqual(rp.classify_signal("all_ideas_failed"), "terminal_failure")
        self.assertEqual(rp.route_feedback(rp.classify_signal("all_ideas_failed")), "stop")

    def test_baseline_failed_still_reruns(self):
        self.assertEqual(rp.classify_signal("baseline_collect_failed"), "experiment_failed")
        self.assertEqual(rp.route_feedback("experiment_failed"), "rerun")


if __name__ == "__main__":
    unittest.main()
