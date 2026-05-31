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

# research_wiki must be importable as a sibling before evidence.py imports it
_rw_spec = importlib.util.spec_from_file_location("research_wiki", TOOLS / "research_wiki.py")
assert _rw_spec and _rw_spec.loader
rw = importlib.util.module_from_spec(_rw_spec)
sys.modules["research_wiki"] = rw
_rw_spec.loader.exec_module(rw)

_ev_spec = importlib.util.spec_from_file_location("evidence", TOOLS / "evidence.py")
assert _ev_spec and _ev_spec.loader
ev = importlib.util.module_from_spec(_ev_spec)
sys.modules["evidence"] = ev
_ev_spec.loader.exec_module(ev)


def _wiki(with_edge: bool = False, structured: bool = False) -> Path:
    d = Path(tempfile.mkdtemp())
    for sub in ("graph", "ideas", "experiments", "manuscripts", "methods"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "ideas" / "i-val.md").write_text(
        "---\nslug: i-val\ntitle: V\nstatus: validated\norigin: x\ntags: []\norigin_gaps: []\n---\n# i-val\n",
        encoding="utf-8")
    (d / "experiments" / "e1.md").write_text(
        "---\nslug: e1\ntitle: E\nstatus: completed\noutcome: succeeded\nkey_result: r\n"
        "linked_idea: i-val\nhypothesis: h\ntags: []\n---\n# e1\n", encoding="utf-8")
    (d / "manuscripts" / "m1.md").write_text(
        "---\nslug: m1\ntitle: M\nstatus: drafting\ntags: []\n---\n# m1\n"
        "## Evidence map\nCore claim: [[i-val]] validated by [[e1]].\n"
        "## Version history\n", encoding="utf-8")
    if with_edge:
        attrs = {"metric_value": "0.9", "source_path": "r/x.json"} if structured else {}
        rw.add_edge(str(d), "ideas/i-val", "experiments/e1", "tested_by",
                    evidence="e", attrs=attrs)
    return d


class TestResolveClaims(unittest.TestCase):
    def test_resolves_evidence_map_wikilinks_filtered_to_claim_kinds(self):
        d = _wiki()
        claims = ev.resolve_claims(d, "m1")
        self.assertIn("ideas/i-val", claims)
        self.assertIn("experiments/e1", claims)
        self.assertEqual(len(claims), 2)

    def test_resolves_graph_neighbor_claims(self):
        d = _wiki()
        # A claim entity NOT named in the Evidence map, linked to the manuscript via a graph edge:
        (d / "ideas" / "i-extra.md").write_text(
            "---\nslug: i-extra\ntitle: X\nstatus: proposed\norigin: x\ntags: []\norigin_gaps: []\n---\n# i-extra\n",
            encoding="utf-8")
        rw.add_edge(str(d), "manuscripts/m1", "ideas/i-extra", "derived_from",
                    evidence="manuscript derived from this idea")
        claims = ev.resolve_claims(d, "m1")
        self.assertIn("ideas/i-extra", claims)   # resolved via graph neighbour, not Evidence map
        self.assertIn("ideas/i-val", claims)     # still resolves Evidence-map wikilinks
        self.assertIn("experiments/e1", claims)


class TestVerdict(unittest.TestCase):
    def test_high_risk_uncovered_blocks(self):
        self.assertEqual(ev.verdict_for_claim("ideas", "validated", 0, False)[0], ev.BLOCK)

    def test_high_risk_covered_no_attr_warns(self):
        self.assertEqual(ev.verdict_for_claim("ideas", "validated", 1, False)[0], ev.WARN)

    def test_high_risk_covered_structured_passes(self):
        self.assertEqual(ev.verdict_for_claim("ideas", "validated", 1, True)[0], ev.PASS)

    def test_low_risk_uncovered_info(self):
        self.assertEqual(ev.verdict_for_claim("ideas", "proposed", 0, False)[0], ev.INFO)

    def test_experiment_completed_is_high_risk(self):
        self.assertEqual(ev.classify_risk("experiments", "completed"), "high")

    def test_method_is_low_risk(self):
        self.assertEqual(ev.classify_risk("methods", ""), "low")

    def test_coverage_counts_and_structured(self):
        d = _wiki(with_edge=True, structured=True)
        edges = rw.load_edges(str(d))
        count, structured = ev._coverage(edges, "ideas/i-val")
        self.assertEqual(count, 1)
        self.assertTrue(structured)

    def test_contradicts_does_not_count_as_coverage(self):
        edges = [{"type": "contradicts", "from": "ideas/i-val", "to": "experiments/e1",
                  "metric_value": "0.5"}]
        count, structured = ev._coverage(edges, "ideas/i-val")
        self.assertEqual(count, 0)
        self.assertFalse(structured)


class TestEndToEnd(unittest.TestCase):
    def _run(self, d, *args):
        return subprocess.run(
            [sys.executable, str(TOOLS / "evidence.py"), "verify-claims", "m1",
             "--wiki-dir", str(d), *args],
            capture_output=True, text=True)

    def test_uncovered_high_risk_blocks_nonzero(self):
        d = _wiki(with_edge=False)
        r = self._run(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("BLOCK", r.stdout)

    def test_structured_covered_passes_zero(self):
        d = _wiki(with_edge=True, structured=True)
        r = self._run(d)
        self.assertEqual(r.returncode, 0)

    def test_strict_warn_nonzero(self):
        d = _wiki(with_edge=True, structured=False)
        r = self._run(d, "--strict")
        self.assertEqual(r.returncode, 1)

    def test_warn_zero_without_strict(self):
        d = _wiki(with_edge=True, structured=False)
        r = self._run(d)
        self.assertEqual(r.returncode, 0)

    def test_json_output(self):
        d = _wiki(with_edge=True, structured=True)
        r = self._run(d, "--json")
        data = json.loads(r.stdout)
        self.assertEqual(data["overall"], "PASS")
        self.assertEqual(len(data["claims"]), 2)

    def test_no_claims_reports_empty_and_exit_zero(self):
        d = _wiki(with_edge=False)
        (d / "manuscripts" / "empty.md").write_text(
            "---\nslug: empty\ntitle: E\nstatus: drafting\ntags: []\n---\n# empty\n"
            "## Evidence map\n(no claims yet)\n## Version history\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(TOOLS / "evidence.py"), "verify-claims", "empty",
             "--wiki-dir", str(d)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("no idea/experiment/method claims", r.stdout)


if __name__ == "__main__":
    unittest.main()
