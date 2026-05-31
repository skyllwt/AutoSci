#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("pipeline_progress", TOOLS / "pipeline_progress.py")
assert spec and spec.loader
pp = importlib.util.module_from_spec(spec)
sys.modules["pipeline_progress"] = pp
spec.loader.exec_module(pp)

lint_spec = importlib.util.spec_from_file_location("lint", TOOLS / "lint.py")
assert lint_spec and lint_spec.loader
lint = importlib.util.module_from_spec(lint_spec)
sys.modules["lint"] = lint
lint_spec.loader.exec_module(lint)

_GOOD = """---
slug: p1
direction: kernel opt
status: running
current_stage: stage1
started: 2026-05-31
mode: interactive
skip_paper: false
idea_slug: ""
experiment_slugs: []
linked_idea_slugs: []
iteration_count: 0
---
## Stage Log
- Stage 0 (Bootstrap): skipped
- Stage 1: pending
- Gate 1: pending
- Stage 2: pending
- Stage 3a (Deploy): pending
- Stage 3b (Await): pending
- Stage 3c (Collect): pending
- Stage 4: pending
- Gate 2: pending
- Stage 5: pending
"""


def _wiki(progress_text=None, pages=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    if progress_text is not None:
        (d / "outputs" / "pipeline-progress.md").write_text(progress_text, encoding="utf-8")
    for rel, status in (pages or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nslug: {p.stem}\nstatus: {status}\n---\n# x\n", encoding="utf-8")
    return d


class PipelineProgressToolTests(unittest.TestCase):
    def test_parse_progress_frontmatter_and_log(self) -> None:
        d = _wiki(_GOOD)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fm, log = pp.parse_progress(d / "outputs" / "pipeline-progress.md")
        self.assertEqual(fm["current_stage"], "stage1")
        self.assertEqual(fm["experiment_slugs"], [])
        self.assertEqual(log["stage0"], "skipped")
        self.assertEqual(log["stage1"], "pending")
        self.assertEqual(log["stage3a"], "pending")

    def test_validate_clean_snapshot_is_empty(self) -> None:
        d = _wiki(_GOOD)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertEqual(pp.validate(d), [])

    def test_validate_absent_file_is_empty(self) -> None:
        d = _wiki(None)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertEqual(pp.validate(d), [])

    def test_validate_dangling_idea_blocks(self) -> None:
        text = _GOOD.replace('idea_slug: ""', "idea_slug: ghost")
        d = _wiki(text)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        issues = pp.validate(d)
        self.assertTrue(any(s == "BLOCK" and "ghost" in m for s, m in issues))

    def test_validate_resolves_real_entity_status(self) -> None:
        text = _GOOD.replace("current_stage: stage1", "current_stage: stage4")
        text = text.replace("experiment_slugs: []", "experiment_slugs: [e1]")
        text = text.replace('idea_slug: ""', "idea_slug: i1")
        text = text.replace("- Stage 1: pending", "- Stage 1: completed")
        text = text.replace("- Gate 1: pending", "- Gate 1: completed")
        text = text.replace("- Stage 2: pending", "- Stage 2: completed")
        text = text.replace("- Stage 3a (Deploy): pending", "- Stage 3a (Deploy): completed")
        text = text.replace("- Stage 3b (Await): pending", "- Stage 3b (Await): completed")
        text = text.replace("- Stage 3c (Collect): pending", "- Stage 3c (Collect): completed")
        text = text.replace("- Stage 4: pending", "- Stage 4: running")
        d = _wiki(text, pages={"experiments/e1.md": "running", "ideas/i1.md": "tested"})
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        issues = pp.validate(d)
        self.assertTrue(any(s == "BLOCK" and "e1" in m for s, m in issues))


class LintHookTests(unittest.TestCase):
    def test_lint_surfaces_pipeline_block(self) -> None:
        text = _GOOD.replace('idea_slug: ""', "idea_slug: ghost")
        d = _wiki(text)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        issues = lint.check_pipeline_progress(d)
        self.assertTrue(any(i.category == "pipeline" and i.level == "🔴" for i in issues))
        self.assertTrue(any("ghost" in i.message for i in issues))

    def test_lint_clean_snapshot_no_pipeline_issue(self) -> None:
        d = _wiki(_GOOD)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertEqual(lint.check_pipeline_progress(d), [])

    def test_lint_aggregate_includes_pipeline(self) -> None:
        text = _GOOD.replace("current_stage: stage1", "current_stage: stage9")
        d = _wiki(text)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        cats = {i.category for i in lint.lint(d)}
        self.assertIn("pipeline", cats)


class ValidatePipelineCliTests(unittest.TestCase):
    def _run(self, wiki: Path) -> int:
        return subprocess.run(
            [sys.executable, str(TOOLS / "research_wiki.py"), "validate-pipeline", str(wiki)],
            capture_output=True, text=True,
        ).returncode

    def test_cli_clean_exits_0(self) -> None:
        d = _wiki(_GOOD)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertEqual(self._run(d), 0)

    def test_cli_absent_file_exits_0(self) -> None:
        d = _wiki(None)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertEqual(self._run(d), 0)

    def test_cli_block_exits_nonzero(self) -> None:
        text = _GOOD.replace('idea_slug: ""', "idea_slug: ghost")
        d = _wiki(text)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertNotEqual(self._run(d), 0)

    def test_cli_warn_only_exits_0(self) -> None:
        # status running + all non-skippable stages completed -> a WARN, no BLOCK
        text = _GOOD.replace("current_stage: stage1", "current_stage: stage5")
        for label in ("- Stage 1: pending", "- Gate 1: pending", "- Stage 2: pending",
                      "- Stage 3a (Deploy): pending", "- Stage 3b (Await): pending",
                      "- Stage 3c (Collect): pending", "- Stage 4: pending", "- Gate 2: pending"):
            text = text.replace(label, label.replace("pending", "completed"))
        d = _wiki(text)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "research_wiki.py"), "validate-pipeline", str(d)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN", result.stdout)


if __name__ == "__main__":
    unittest.main()
