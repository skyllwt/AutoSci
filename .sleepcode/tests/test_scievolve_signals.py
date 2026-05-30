#!/usr/bin/env python3
"""Tests for skill-explicit signal recording via tools/scievolve_record.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
RECORD_TOOL = REPO / "tools" / "scievolve_record.py"


class SciEvolveSignalTests(unittest.TestCase):
    def run_record(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RECORD_TOOL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
        )

    def test_record_signal_via_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            result = self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "memory",
                "--target", "discover",
                "--kind", "success",
                "--summary", "Test signal via helper.",
                "--severity", "low",
                "--confidence", "high",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "ok")
            self.assertTrue(data["signal_id"].startswith("sig-"))

            signals_path = wiki / "outputs" / "evolution" / "signals.jsonl"
            self.assertTrue(signals_path.exists())
            lines = signals_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["source"], "task")
            self.assertEqual(record["dimension"], "memory")
            self.assertEqual(record["target"], "discover")
            self.assertEqual(record["kind"], "success")
            self.assertEqual(record["severity"], "low")
            self.assertEqual(record["confidence"], "high")

    def test_helper_rejects_invalid_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            result = self.run_record(
                "--wiki-root", str(wiki),
                "--source", "invalid",
                "--dimension", "memory",
                "--target", "x",
                "--kind", "test",
                "--summary", "x",
            )
            self.assertNotEqual(result.returncode, 0)
            err_text = result.stderr.strip()
            self.assertTrue(
                err_text and ("error" in err_text.lower() or "invalid" in err_text.lower()),
                f"Expected error in stderr, got: {err_text!r}"
            )
            signals_path = wiki / "outputs" / "evolution" / "signals.jsonl"
            if signals_path.exists():
                self.assertFalse(signals_path.read_text().strip())
            # If file does not exist, no signal was written — that's also correct

    def test_helper_rejects_empty_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            result = self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "memory",
                "--target", "x",
                "--kind", "test",
                "--summary", "   ",
            )
            self.assertEqual(result.returncode, 1)
            data = json.loads(result.stderr)
            self.assertEqual(data["status"], "error")
            self.assertIn("summary", data["message"].lower())

    def test_multiple_signals_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            for i in range(3):
                result = self.run_record(
                    "--wiki-root", str(wiki),
                    "--source", "task",
                    "--dimension", "workflow",
                    "--target", "discover",
                    "--kind", "failure",
                    "--summary", f"Failure {i}",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            signals_path = wiki / "outputs" / "evolution" / "signals.jsonl"
            lines = [l for l in signals_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
