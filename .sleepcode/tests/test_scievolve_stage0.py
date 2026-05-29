#!/usr/bin/env python3
"""Smoke tests for the Stage 0 SciEvolve spine."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "research_wiki.py"


class SciEvolveStage0Tests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_empty_report_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            result = self.run_tool(
                "scievolve-report",
                str(wiki),
                "--json",
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["signal_count"], 0)
            self.assertEqual(data["proposal_count"], 0)
            self.assertTrue(Path(data["report_path"]).exists())

    def test_signal_to_proposal_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.run_tool("scievolve-init", str(wiki))
            signal_result = self.run_tool(
                "scievolve-record-signal",
                str(wiki),
                "--source",
                "user",
                "--dimension",
                "memory",
                "--target",
                "concepts/test-memory",
                "--kind",
                "correction",
                "--summary",
                "Reviewer-visible test signal.",
            )
            signal = json.loads(signal_result.stdout)
            self.assertEqual(signal["status"], "ok")
            self.assertTrue(signal["signal_id"].startswith("sig-"))

            report_result = self.run_tool(
                "scievolve-report",
                str(wiki),
                "--dimension",
                "memory",
                "--propose",
                "--json",
            )
            report = json.loads(report_result.stdout)
            self.assertEqual(report["signal_count"], 1)
            self.assertEqual(report["proposal_count"], 1)
            proposal = report["proposals"][0]
            self.assertEqual(proposal["dimension"], "memory")
            self.assertEqual(proposal["skill"], "/dream")
            self.assertEqual(proposal["status"], "proposed")
            self.assertTrue((wiki / proposal["output_path"]).exists())
            self.assertTrue((wiki / proposal["json_path"]).exists())


if __name__ == "__main__":
    unittest.main()
