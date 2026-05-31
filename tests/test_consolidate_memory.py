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

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("consolidate_memory", TOOLS / "consolidate_memory.py")
assert spec and spec.loader
cm = importlib.util.module_from_spec(spec)
sys.modules["consolidate_memory"] = cm
spec.loader.exec_module(cm)


def _wiki() -> Path:
    d = Path(tempfile.mkdtemp())
    for sub in ("graph", "ideas", "experiments", "methods", "topics"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "ideas" / "i-fail.md").write_text(
        "---\nslug: i-fail\ntitle: Failed Idea\nstatus: failed\norigin: x\ntags: []\n"
        "origin_gaps: [t1]\nfailure_reason: did not work\n---\n# i-fail\n", encoding="utf-8")
    (d / "ideas" / "i-val.md").write_text(
        "---\nslug: i-val\ntitle: Valid Idea\nstatus: validated\norigin: x\ntags: []\n"
        "origin_gaps: [t1]\n---\n# i-val\n", encoding="utf-8")
    (d / "ideas" / "i-skip.md").write_text(
        "---\nslug: i-skip\ntitle: Skip Idea\nstatus: failed\norigin: x\ntags: []\n"
        "origin_gaps: [no-such-topic]\nfailure_reason: x\n---\n# i-skip\n", encoding="utf-8")
    (d / "experiments" / "e1.md").write_text(
        "---\nslug: e1\ntitle: Exp One\nstatus: completed\noutcome: succeeded\nkey_result: 1.5x speedup\n"
        "linked_idea: i-val\nhypothesis: h\ntags: []\nevaluates_methods: [m1]\n---\n# e1\n", encoding="utf-8")
    (d / "methods" / "m1.md").write_text(
        "---\nslug: m1\nname: Method One\ntype: other\ntags: []\nparent_topics: [t1]\n---\n"
        "# m1\n## Evaluated by\n", encoding="utf-8")
    (d / "topics" / "t1.md").write_text(
        "---\nslug: t1\ntitle: Topic One\ntags: []\n---\n# t1\n## Open problems\n## Synthesis notes\n## SOTA tracker\n",
        encoding="utf-8")
    return d


class ProposeTests(unittest.TestCase):
    def test_propose_generates_four_patch_kinds(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        patches = cm.propose(d)
        kinds = {p.kind for p in patches}
        self.assertEqual(kinds, {"topic_open_problem", "topic_synthesis", "method_finding", "topic_sota"})

    def test_propose_open_problem_has_failure_reason(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        op = [p for p in cm.propose(d) if p.kind == "topic_open_problem"]
        self.assertEqual(len(op), 1)
        self.assertEqual(op[0].target, "topics/t1")
        self.assertIn("did not work", op[0].line)
        self.assertEqual(op[0].source, "ideas/i-fail")

    def test_propose_skips_unresolved_targets(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertFalse(any(p.source == "ideas/i-skip" for p in cm.propose(d)))

    def test_propose_method_finding_and_topic_sota(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        patches = cm.propose(d)
        mf = [p for p in patches if p.kind == "method_finding"]
        sota = [p for p in patches if p.kind == "topic_sota"]
        self.assertEqual(mf[0].target, "methods/m1")
        self.assertIn("1.5x speedup", mf[0].line)
        self.assertEqual(sota[0].target, "topics/t1")

    def test_experiment_without_key_result_no_patch(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "experiments" / "e-nokr.md").write_text(
            "---\nslug: e-nokr\ntitle: E\nstatus: completed\noutcome: succeeded\n"
            "linked_idea: i-val\nhypothesis: h\ntags: []\nevaluates_methods: [m1]\n---\n# e-nokr\n", encoding="utf-8")
        # completed but no key_result -> no consolidation patch from it
        self.assertFalse(any(p.source == "experiments/e-nokr" for p in cm.propose(d)))

    def test_non_completed_experiment_ignored(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "experiments" / "e-aband.md").write_text(
            "---\nslug: e-aband\ntitle: E\nstatus: abandoned\noutcome: inconclusive\nkey_result: x\n"
            "linked_idea: i-val\nhypothesis: h\ntags: []\nevaluates_methods: [m1]\n---\n# e-aband\n", encoding="utf-8")
        self.assertFalse(any(p.source == "experiments/e-aband" for p in cm.propose(d)))


class ProposeCliTests(unittest.TestCase):
    def test_cli_propose_writes_file_and_event(self) -> None:
        d = _wiki()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        r = subprocess.run([sys.executable, str(TOOLS / "consolidate_memory.py"), "propose",
                            str(d), "--repo-root", str(d)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        patch_file = d / "raw" / "tmp" / "consolidation" / "consolidation-proposal.json"
        self.assertTrue(patch_file.exists())
        patches = json.loads(patch_file.read_text(encoding="utf-8"))
        self.assertEqual(len(patches), 4)
        events = d / "graph" / "consolidation_events.jsonl"
        rows = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(any(row.get("kind") == "consolidation_proposed" for row in rows))


if __name__ == "__main__":
    unittest.main()
