#!/usr/bin/env python3
"""Tests for the /forge Stage 2 workflow evolution."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "research_wiki.py"
RECORD_TOOL = REPO / "tools" / "scievolve_record.py"


class SciEvolveForgeTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )

    def run_record(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RECORD_TOOL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_forge_empty_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            result = self.run_tool("forge", str(wiki), "--json")
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["signal_count"], 0)
            self.assertEqual(data["proposal_count"], 0)
            self.assertTrue(Path(data["report_path"]).exists())

    def test_forge_signal_to_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "workflow",
                "--target", "discover",
                "--kind", "failure",
                "--summary", "S2 timeout causes empty shortlist",
                "--severity", "medium",
                "--confidence", "high",
            )
            response_path = wiki / "forge_response.json"
            response_path.write_text(json.dumps({
                "proposals": [
                    {
                        "operation": "add-recovery",
                        "target": "discover",
                        "title": "Add S2 timeout recovery",
                        "proposed_action": "Add timeout check and DeepXiv fallback in Step 2.",
                        "rationale": "Task signals show S2 timeout causes empty shortlists.",
                        "confidence": "high",
                        "skill_path": "i18n/en/skills/discover/SKILL.md",
                        "evidence": [
                            {"source": "sig-placeholder", "summary": "S2 timeout"}
                        ],
                    }
                ]
            }), encoding="utf-8")

            result = self.run_tool(
                "forge", str(wiki),
                "--agent-response", str(response_path),
                "--json",
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["signal_count"], 1)
            self.assertEqual(data["accepted_agent_proposals"], 1)
            self.assertEqual(data["proposal_count"], 1)
            self.assertEqual(data["safe_application_count"], 0)

            # Proposal artifact exists
            proposals = data.get("proposals", [])
            self.assertEqual(len(proposals), 1)
            proposal = proposals[0]
            self.assertEqual(proposal["dimension"], "workflow")
            self.assertEqual(proposal["skill"], "/forge")
            self.assertEqual(proposal["status"], "proposed")
            self.assertTrue((wiki / proposal["output_path"]).exists())
            self.assertTrue((wiki / proposal["json_path"]).exists())

    def test_forge_rejects_fabricated_skill_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "workflow",
                "--target", "discover",
                "--kind", "failure",
                "--summary", "Test signal",
            )
            response_path = wiki / "forge_response.json"
            response_path.write_text(json.dumps({
                "proposals": [
                    {
                        "operation": "add-check",
                        "target": "nonexistent-skill",
                        "title": "Fake",
                        "proposed_action": "Add check.",
                        "rationale": "Signal shows issue.",
                        "confidence": "high",
                    }
                ]
            }), encoding="utf-8")

            result = self.run_tool(
                "forge", str(wiki),
                "--agent-response", str(response_path),
                "--json",
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["accepted_agent_proposals"], 0)
            self.assertEqual(data["rejected_agent_items"], 1)
            self.assertEqual(data["proposal_count"], 0)

    def test_forge_no_auto_apply_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "workflow",
                "--target", "discover",
                "--kind", "failure",
                "--summary", "Test signal",
            )
            response_path = wiki / "forge_response.json"
            response_path.write_text(json.dumps({
                "proposals": [
                    {
                        "operation": "add-recovery",
                        "target": "discover",
                        "title": "Recovery",
                        "proposed_action": "Add recovery.",
                        "rationale": "Signal.",
                        "confidence": "high",
                    }
                ]
            }), encoding="utf-8")

            result = self.run_tool(
                "forge", str(wiki),
                "--agent-response", str(response_path),
                "--json",
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["safe_application_count"], 0)
            self.assertEqual(len(data.get("safe_applications", [])), 0)

    def test_forge_target_skill_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "workflow",
                "--target", "discover",
                "--kind", "failure",
                "--summary", "Discover issue",
            )
            self.run_record(
                "--wiki-root", str(wiki),
                "--source", "task",
                "--dimension", "workflow",
                "--target", "ideate",
                "--kind", "failure",
                "--summary", "Ideate issue",
            )
            result = self.run_tool(
                "forge", str(wiki),
                "--target-skill", "discover",
                "--json",
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["signal_count"], 1)


if __name__ == "__main__":
    unittest.main()
