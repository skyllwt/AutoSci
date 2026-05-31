#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
