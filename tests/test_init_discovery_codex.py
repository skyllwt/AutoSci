#!/usr/bin/env python3
"""Codex serial-mode regression tests for init discovery handoff."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import init_discovery  # noqa: E402


class InitDiscoveryCodexTests(unittest.TestCase):
    def test_codex_init_docs_do_not_regress_to_parallel_default(self) -> None:
        docs = {
            "README.md": ROOT / "README.md",
            ".agents/skills/init/SKILL.md": ROOT / ".agents/skills/init/SKILL.md",
            ".agents/skills/ingest/SKILL.md": ROOT / ".agents/skills/ingest/SKILL.md",
            "AGENTS.md": ROOT / "AGENTS.md",
        }
        combined = "\n".join(path.read_text(encoding="utf-8") for path in docs.values())

        self.assertIn("$init", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("serially by default", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Codex default", (ROOT / ".agents/skills/init/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("INIT MODE SERIAL", combined)
        self.assertIn("init-handoff.json", combined)
        self.assertIn("tools/backfill_citations.py", combined)
        self.assertIn("tools/backfill_citations.py", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))

        stale_phrases = [
            "ingest the final paper set in parallel",
            "parallel `/ingest` subagents",
            "all paper ingest must run through parallel",
            "Canvas + HTML",
            "--canvas --html",
        ]
        for phrase in stale_phrases:
            self.assertNotIn(phrase, combined)

    def test_local_help_paths_without_network_gate(self) -> None:
        for tool_name, args in [
            ("init_discovery.py", ["handoff", "--help"]),
            ("prepare_paper_source.py", ["--help"]),
            ("backfill_citations.py", ["--help"]),
        ]:
            proc = subprocess.run(
                [sys.executable, str(TOOLS / tool_name), *args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_local_tex_serial_handoff_without_network_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-init-test.") as tmp:
            project = Path(tmp)
            raw_root = project / "raw"
            wiki_root = project / "wiki"
            checkpoint_root = project / ".checkpoints"
            (raw_root / "papers").mkdir(parents=True)
            (raw_root / "notes").mkdir(parents=True)
            wiki_root.mkdir()
            checkpoint_root.mkdir()

            (raw_root / "papers" / "codex-local-test.tex").write_text(
                "\n".join(
                    [
                        r"\title{Codex Local Test Paper}",
                        r"\begin{document}",
                        r"\maketitle",
                        r"\begin{abstract}",
                        "This paper studies deterministic Codex migration for init handoff.",
                        r"\end{abstract}",
                        r"\section{Introduction}",
                        "Serial ingest should consume local tex without network access.",
                        r"\end{document}",
                    ]
                ),
                encoding="utf-8",
            )
            (raw_root / "notes" / "context.md").write_text(
                "Codex init migration should default to serial ingest.",
                encoding="utf-8",
            )

            prepare_manifest = init_discovery.prepare_inputs(raw_root)
            paper_entries = [
                entry for entry in prepare_manifest["entries"]
                if entry.get("source_kind") == "paper"
            ]
            self.assertEqual(len(paper_entries), 1)
            self.assertTrue(paper_entries[0]["usable"])
            self.assertEqual(paper_entries[0]["ingest_format"], "tex")

            plan = init_discovery.build_plan(
                "codex init migration",
                raw_root,
                wiki_root,
                allow_introduction=False,
                prepared_manifest=prepare_manifest,
            )
            self.assertEqual(plan["mode"], "seeded")
            self.assertFalse(plan["allow_introduction"])
            self.assertEqual(plan["errors"], [])
            self.assertEqual(len(plan["shortlist"]), 1)

            plan_path = checkpoint_root / "init-plan.json"
            prepare_path = checkpoint_root / "init-prepare.json"
            source_path = checkpoint_root / "init-sources.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            prepare_path.write_text(json.dumps(prepare_manifest), encoding="utf-8")

            fetch_result = init_discovery.fetch_from_plan(
                raw_root,
                plan_path,
                [],
                prepared_manifest_json=prepare_path,
                output_sources=source_path,
            )
            source_manifest = fetch_result["source_manifest"]
            self.assertEqual(source_manifest["status"], "ok")
            self.assertEqual(len(source_manifest["sources"]), 1)
            self.assertEqual(source_manifest["sources"][0]["origin"], "user_local")

            handoff = init_discovery.build_ingest_handoff(source_manifest, mode="serial")
            self.assertEqual(handoff["status"], "ok")
            self.assertEqual(handoff["init_mode"], "INIT MODE SERIAL")
            self.assertEqual(handoff["task_count"], 1)
            self.assertFalse(handoff["tasks"][0]["commit_after_ingest"])
            self.assertEqual(
                handoff["tasks"][0]["canonical_ingest_path"],
                "raw/papers/codex-local-test.tex",
            )

    def test_handoff_skips_invalid_sources_with_contiguous_order(self) -> None:
        source_manifest = {
            "sources": [
                {
                    "candidate_id": "rank2",
                    "origin": "introduced",
                    "canonical_ingest_path": "raw/discovered/rank2/main.tex",
                    "ingest_format": "tex",
                    "shortlist_rank": 2,
                },
                {
                    "candidate_id": "missing",
                    "shortlist_rank": 1,
                },
                {
                    "candidate_id": "rank1",
                    "origin": "user_local",
                    "canonical_ingest_path": "raw/papers/rank1.pdf",
                    "ingest_format": "pdf",
                    "shortlist_rank": 1,
                },
            ],
        }

        handoff = init_discovery.build_ingest_handoff(source_manifest, mode="serial")

        self.assertEqual([task["order"] for task in handoff["tasks"]], [1, 2])
        self.assertEqual(
            [task["candidate_id"] for task in handoff["tasks"]],
            ["rank1", "rank2"],
        )
        self.assertEqual(handoff["warnings"][0]["candidate_id"], "missing")

    def test_backfill_citations_local_paths_without_network_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autosci-backfill-test.") as tmp:
            wiki_root = Path(tmp) / "wiki"
            papers_dir = wiki_root / "papers"
            graph_dir = wiki_root / "graph"
            papers_dir.mkdir(parents=True)
            graph_dir.mkdir()
            (graph_dir / "citations.jsonl").write_text("", encoding="utf-8")
            (papers_dir / "no-arxiv.md").write_text(
                "---\n"
                "title: No Arxiv Paper\n"
                "arxiv: \"\"\n"
                "---\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOLS / "backfill_citations.py"),
                    "--wiki-dir",
                    str(wiki_root),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[skip] no-arxiv", proc.stdout)


if __name__ == "__main__":
    unittest.main()
