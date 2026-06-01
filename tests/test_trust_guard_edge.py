#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tg = _load("trust_guard")


def _wiki() -> Path:
    d = Path(tempfile.mkdtemp())
    for sub in ("graph", "ideas", "experiments"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "ideas" / "i.md").write_text(
        "---\nslug: i\ntitle: I\nstatus: validated\norigin: x\ntags: []\norigin_gaps: []\n---\n# i\n", encoding="utf-8")
    (d / "experiments" / "e.md").write_text(
        "---\nslug: e\ntitle: E\nstatus: completed\noutcome: succeeded\nkey_result: r\n"
        "linked_idea: i\nhypothesis: h\ntags: []\n---\n# e\n", encoding="utf-8")
    return d


class TestCheckEdge(unittest.TestCase):
    def test_valid_edge_between_existing_nodes_passes(self):
        d = _wiki()
        v = tg.check_edge(d, "ideas/i", "experiments/e", "tested_by", evidence="exp tested it", emit_event=False)
        self.assertEqual(v.status, "PASS")

    def test_unknown_edge_type_blocks(self):
        d = _wiki()
        v = tg.check_edge(d, "ideas/i", "experiments/e", "bogus_type", emit_event=False)
        self.assertEqual(v.status, "BLOCK")

    def test_unknown_attr_key_blocks(self):
        d = _wiki()
        v = tg.check_edge(d, "ideas/i", "experiments/e", "tested_by", attrs={"bogus": "x"}, emit_event=False)
        self.assertEqual(v.status, "BLOCK")

    def test_dangling_node_warns(self):
        d = _wiki()
        v = tg.check_edge(d, "ideas/i", "experiments/does-not-exist", "tested_by", evidence="e", emit_event=False)
        self.assertEqual(v.status, "WARN")

    def test_block_writes_quarantine_record(self):
        d = _wiki()
        repo = Path(tempfile.mkdtemp())
        v = tg.check_edge(d, "ideas/i", "experiments/e", "bogus_type", repo_root=repo, emit_event=False)
        self.assertEqual(v.status, "BLOCK")
        files = list((repo / "raw" / "tmp" / "quarantine").glob("edge__*.json"))
        self.assertEqual(len(files), 1)
        rec = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(rec["edge"]["type"], "bogus_type")
        self.assertIn("verdict", rec)

    def test_emit_event_logs_trust_event(self):
        d = _wiki()
        tg.check_edge(d, "ideas/i", "experiments/e", "tested_by", evidence="e", emit_event=True)
        events = (d / "graph" / "trust_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertTrue(any("tested_by" in line for line in events))


class TestCheckEdgeCLI(unittest.TestCase):
    def _run(self, d, *args):
        return subprocess.run(
            [sys.executable, str(TOOLS / "trust_guard.py"), "check-edge", str(d), *args],
            capture_output=True, text=True)

    def test_cli_pass_returns_0(self):
        d = _wiki()
        r = self._run(d, "--from", "ideas/i", "--to", "experiments/e", "--type", "tested_by", "--attr", "evidence=ok")
        self.assertEqual(r.returncode, 0)

    def test_cli_block_returns_2(self):
        d = _wiki()
        r = self._run(d, "--from", "ideas/i", "--to", "experiments/e", "--type", "bogus_type",
                      "--repo-root", str(Path(tempfile.mkdtemp())))
        self.assertEqual(r.returncode, 2)

    def test_cli_json(self):
        d = _wiki()
        r = self._run(d, "--from", "ideas/i", "--to", "experiments/e", "--type", "tested_by", "--attr", "evidence=ok", "--json")
        data = json.loads(r.stdout)
        self.assertEqual(data["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
