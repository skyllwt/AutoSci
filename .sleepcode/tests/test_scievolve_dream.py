#!/usr/bin/env python3
"""Smoke tests for the agent-first /dream SciEvolve stage."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "research_wiki.py"


class SciEvolveDreamTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )

    def write_page(self, wiki: Path, rel: str, content: str) -> None:
        path = wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def seed_wiki(self, wiki: Path) -> str:
        self.run_tool("init", str(wiki))
        self.write_page(
            wiki,
            "concepts/neural-cache.md",
            """---
title: Neural Cache
tags: [memory, cache]
maturity: active
key_papers: []
date_updated: 2024-01-01T12:00:00Z
---

## Definition

Reusable memory cache for agent context.
""",
        )
        self.write_page(
            wiki,
            "concepts/neural-cache-memory.md",
            """---
title: Neural Cache Memory
tags: [memory, cache]
maturity: emerging
key_papers: []
date_updated: 2024-01-02
---

## Definition

Another note about reusable memory cache behavior.
""",
        )
        self.write_page(
            wiki,
            "methods/cache-tuning.md",
            """---
name: Cache Tuning
slug: cache-tuning
type: system
tags: [memory, cache]
source_papers: []
realizes_concepts: []
date_updated: 2026-01-01
---

## Mechanism

Adjusts retrieval memory cache parameters.
""",
        )
        signal = self.run_tool(
            "scievolve-record-signal",
            str(wiki),
            "--source",
            "user",
            "--dimension",
            "memory",
            "--target",
            "concepts/neural-cache",
            "--kind",
            "review",
            "--summary",
            "Consolidate duplicate neural cache memory notes.",
        )
        return json.loads(signal.stdout)["signal_id"]

    def test_dream_prepare_writes_agent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)

            result = self.run_tool("dream", str(wiki), "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["proposal_count"], 0)
            self.assertGreater(data["candidate_count"], 0)
            self.assertTrue(Path(data["context_path"]).exists())
            self.assertTrue(Path(data["context_markdown_path"]).exists())
            self.assertTrue(Path(data["prompt_path"]).exists())
            prompt = Path(data["prompt_path"]).read_text(encoding="utf-8")
            self.assertIn("You are AutoSci's /dream agent", prompt)
            self.assertIn("candidate_memory_cues", prompt)

    def test_dream_agent_response_writes_scievolve_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)

            prepare = json.loads(self.run_tool("dream", str(wiki), "--json").stdout)
            context = json.loads(Path(prepare["context_path"]).read_text(encoding="utf-8"))
            consolidation = next(
                candidate
                for candidate in context["candidate_memory_cues"]
                if candidate["operation"] == "consolidation"
            )
            response_path = Path(tmp) / "dream_agent_response.json"
            response_path.write_text(
                json.dumps({
                    "proposals": [
                        {
                            "operation": "consolidation",
                            "target": "concepts/neural-cache",
                            "title": "Cluster duplicate neural cache memories",
                            "proposed_action": (
                                "Create a review proposal to merge or cluster the two "
                                "neural cache concept pages."
                            ),
                            "rationale": (
                                "The pages share a near-identical name and repeated "
                                "memory/cache tags, so retrieval will benefit from one "
                                "organized concept neighborhood."
                            ),
                            "confidence": "medium",
                            "related_entities": [
                                "concepts/neural-cache",
                                "concepts/neural-cache-memory",
                            ],
                            "candidate_ids": [consolidation["id"]],
                            "evidence": [
                                {
                                    "source": consolidation["id"],
                                    "summary": "Agent cited the consolidation cue.",
                                }
                            ],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            finalized = self.run_tool(
                "dream",
                str(wiki),
                "--agent-response",
                str(response_path),
                "--propose-only",
                "--json",
            )
            data = json.loads(finalized.stdout)

            self.assertEqual(data["accepted_agent_proposals"], 1)
            self.assertEqual(data["proposal_count"], 1)
            proposal = data["proposals"][0]
            self.assertEqual(proposal["dimension"], "memory")
            self.assertEqual(proposal["skill"], "/dream")
            self.assertEqual(proposal["proposal_kind"], "consolidation")
            self.assertEqual(proposal["confidence"], "medium")
            self.assertTrue((wiki / proposal["output_path"]).exists())
            proposal_json = json.loads((wiki / proposal["json_path"]).read_text(encoding="utf-8"))
            self.assertIn("agent_trace", proposal_json)
            self.assertEqual(proposal_json["agent_trace"]["provider"], "supplied-policy-response")
            self.assertEqual(proposal_json["agent_trace"]["policy_runtime"], "caller-supplied")

    def test_dream_rejects_fabricated_context_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)
            response_path = Path(tmp) / "bad_dream_response.json"
            response_path.write_text(
                json.dumps({
                    "proposals": [
                        {
                            "operation": "association",
                            "target": "concepts/not-real",
                            "title": "Invented link",
                            "proposed_action": "Connect unsupported pages.",
                            "rationale": "No real evidence.",
                            "confidence": "high",
                            "related_entities": ["concepts/not-real"],
                            "evidence": [{"source": "concepts/not-real"}],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            result = self.run_tool(
                "dream",
                str(wiki),
                "--agent-response",
                str(response_path),
                "--propose-only",
                "--json",
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["accepted_agent_proposals"], 0)
            self.assertEqual(data["proposal_count"], 0)
            self.assertEqual(data["rejected_agent_items"], 1)

    def test_dream_apply_safe_updates_memory_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)

            prepare = json.loads(self.run_tool("dream", str(wiki), "--json").stdout)
            context = json.loads(Path(prepare["context_path"]).read_text(encoding="utf-8"))
            consolidation = next(
                candidate
                for candidate in context["candidate_memory_cues"]
                if candidate["operation"] == "consolidation"
            )
            response_path = Path(tmp) / "dream_agent_response.json"
            response_path.write_text(
                json.dumps({
                    "proposals": [
                        {
                            "operation": "consolidation",
                            "target": "concepts/neural-cache",
                            "title": "Cluster duplicate neural cache memories",
                            "proposed_action": (
                                "Record neural-cache-memory as a consolidation "
                                "neighbor for the neural-cache concept."
                            ),
                            "rationale": (
                                "The pages share a memory-cache mechanism; adding "
                                "safe SciEvolve metadata makes later retrieval see "
                                "the neighborhood instead of two isolated notes."
                            ),
                            "confidence": "medium",
                            "related_entities": [
                                "concepts/neural-cache",
                                "concepts/neural-cache-memory",
                            ],
                            "candidate_ids": [consolidation["id"]],
                            "evidence": [
                                {
                                    "source": consolidation["id"],
                                    "summary": "Agent cited the consolidation cue.",
                                }
                            ],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            finalized = self.run_tool(
                "dream",
                str(wiki),
                "--agent-response",
                str(response_path),
                "--json",
            )
            data = json.loads(finalized.stdout)

            self.assertEqual(data["proposal_count"], 1)
            self.assertEqual(data["safe_application_count"], 1)
            self.assertTrue(Path(data["apply_report_path"]).exists())
            page = (wiki / "concepts/neural-cache.md").read_text(encoding="utf-8")
            self.assertIn("scievolve_consolidates_with", page)
            self.assertIn("concepts/neural-cache-memory", page)
            self.assertIn("scievolve_last_dream", page)
            context_brief = (wiki / "graph" / "context_brief.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("## SciEvolve Memory Guidance", context_brief)
            self.assertIn("concepts/neural-cache-memory", context_brief)

            proposal = data["proposals"][0]
            proposal_json = json.loads((wiki / proposal["json_path"]).read_text(encoding="utf-8"))
            self.assertEqual(proposal_json["status"], "applied")
            applications = (wiki / "outputs" / "evolution" / "applications.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn(proposal["id"], applications)


    def test_dream_yolo_consolidation_merges_and_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)

            response_path = Path(tmp) / "yolo_response.json"
            response_path.write_text(
                json.dumps({
                    "proposals": [
                        {
                            "operation": "consolidation",
                            "target": "concepts/neural-cache",
                            "title": "Merge duplicate neural cache memories",
                            "proposed_action": (
                                "Merge neural-cache-memory body into neural-cache "
                                "and archive the source."
                            ),
                            "rationale": "Duplicate concepts should be merged.",
                            "confidence": "high",
                            "related_entities": ["concepts/neural-cache-memory"],
                            "candidate_ids": [],
                            "evidence": [],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            result = self.run_tool(
                "dream",
                str(wiki),
                "--agent-response",
                str(response_path),
                "--yolo",
                "--json",
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["proposal_count"], 1)
            self.assertEqual(data["safe_application_count"], 1)

            target = (wiki / "concepts" / "neural-cache.md").read_text(encoding="utf-8")
            self.assertIn("Consolidated Content from", target)
            self.assertIn("<!-- /dream merge:", target)
            self.assertIn("Another note about reusable memory cache behavior", target)

            archive = wiki / "archive" / "concepts" / "neural-cache-memory.md"
            self.assertTrue(archive.exists())
            self.assertFalse((wiki / "concepts" / "neural-cache-memory.md").exists())

    def test_dream_yolo_forgetting_archives_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            self.seed_wiki(wiki)

            response_path = Path(tmp) / "yolo_forget.json"
            response_path.write_text(
                json.dumps({
                    "proposals": [
                        {
                            "operation": "forgetting",
                            "target": "concepts/neural-cache-memory",
                            "title": "Archive obsolete neural cache memory",
                            "proposed_action": "Archive this page as it is superseded.",
                            "rationale": "The main neural-cache page covers this.",
                            "confidence": "high",
                            "related_entities": [],
                            "candidate_ids": [],
                            "evidence": [],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            result = self.run_tool(
                "dream",
                str(wiki),
                "--agent-response",
                str(response_path),
                "--yolo",
                "--json",
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["proposal_count"], 1)
            self.assertEqual(data["safe_application_count"], 1)

            archive = wiki / "archive" / "concepts" / "neural-cache-memory.md"
            self.assertTrue(archive.exists())
            self.assertFalse((wiki / "concepts" / "neural-cache-memory.md").exists())

            archived_content = archive.read_text(encoding="utf-8")
            self.assertIn("maturity: deprecated", archived_content)
            self.assertIn("SciEvolve Memory Evolution Note", archived_content)


if __name__ == "__main__":
    unittest.main()
