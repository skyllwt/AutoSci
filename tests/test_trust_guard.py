#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


lint = _load("lint")
trust_guard = _load("trust_guard")


def _issue(level: str, file: str, msg: str):
    return lint.LintIssue(level, "demo", file, msg)


class FormCheckMappingTests(unittest.TestCase):
    def test_red_issue_maps_to_block(self) -> None:
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🔴", "papers/foo.md", "missing title")]):
            checks = trust_guard.run_form_checks(Path("/wiki"), "papers/foo.md")
        self.assertTrue(any(c.status == "BLOCK" for c in checks))

    def test_yellow_issue_maps_to_warn(self) -> None:
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🟡", "papers/foo.md", "broken link")]):
            checks = trust_guard.run_form_checks(Path("/wiki"), "papers/foo.md")
        self.assertEqual({c.status for c in checks}, {"WARN"})

    def test_issue_for_other_file_is_ignored(self) -> None:
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🔴", "papers/other.md", "x")]):
            checks = trust_guard.run_form_checks(Path("/wiki"), "papers/foo.md")
        self.assertEqual([c.status for c in checks], ["PASS"])

    def test_no_issues_returns_single_pass(self) -> None:
        with mock.patch.object(trust_guard.lint, "lint", return_value=[]):
            checks = trust_guard.run_form_checks(Path("/wiki"), "papers/foo.md")
        self.assertEqual([c.status for c in checks], ["PASS"])


class VerdictCombineTests(unittest.TestCase):
    def test_overall_is_worst_severity(self) -> None:
        checks = [trust_guard.TrustCheck("a", "PASS", ""), trust_guard.TrustCheck("b", "WARN", ""), trust_guard.TrustCheck("c", "BLOCK", "")]
        self.assertEqual(trust_guard.overall_status(checks), "BLOCK")

    def test_overall_warn_when_no_block(self) -> None:
        checks = [trust_guard.TrustCheck("a", "PASS", ""), trust_guard.TrustCheck("b", "WARN", "")]
        self.assertEqual(trust_guard.overall_status(checks), "WARN")

    def test_overall_pass_when_all_pass(self) -> None:
        self.assertEqual(trust_guard.overall_status([trust_guard.TrustCheck("a", "PASS", "")]), "PASS")


class CheckIntegrationTests(unittest.TestCase):
    def _wiki_with_page(self) -> tuple[Path, str]:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "graph").mkdir(parents=True, exist_ok=True)
        (d / "papers").mkdir(parents=True, exist_ok=True)
        rel = "papers/foo.md"
        (d / rel).write_text("---\ntitle: Foo\nslug: foo\n---\n# Foo\n", encoding="utf-8")
        return d, rel

    def _repo(self) -> Path:
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        return repo

    def test_form_block_makes_overall_block_and_records_checks(self) -> None:
        wiki, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🔴", rel, "missing required field")]):
            verdict = trust_guard.check(wiki, wiki / rel, content_reviewer=lambda text, context: None, repo_root=self._repo())
        self.assertEqual(verdict.status, "BLOCK")
        self.assertTrue(any(c.name.startswith("form:") and c.status == "BLOCK" for c in verdict.checks))

    def test_injected_content_block_overrides_form_pass(self) -> None:
        wiki, rel = self._wiki_with_page()
        fake = lambda text, context: trust_guard._mk_content_verdict("BLOCK", "evidence missing")
        with mock.patch.object(trust_guard.lint, "lint", return_value=[]):
            verdict = trust_guard.check(wiki, wiki / rel, content_reviewer=fake, repo_root=self._repo())
        self.assertEqual(verdict.status, "BLOCK")
        self.assertTrue(any(c.name == "content:review" and c.status == "BLOCK" for c in verdict.checks))

    def test_content_skipped_records_pass_note(self) -> None:
        wiki, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[]):
            verdict = trust_guard.check(wiki, wiki / rel, content_reviewer=lambda text, context: None)
        self.assertEqual(verdict.status, "PASS")
        self.assertTrue(any(c.name == "content:review" and "skipped" in c.message for c in verdict.checks))

    def test_missing_file_is_block(self) -> None:
        wiki, _ = self._wiki_with_page()
        missing = wiki / "papers" / "nope.md"
        verdict = trust_guard.check(wiki, missing, content_reviewer=lambda text, context: None)
        self.assertEqual(verdict.status, "BLOCK")
        self.assertTrue(any(c.name == "form:missing-file" for c in verdict.checks))


class QuarantineAndEventTests(unittest.TestCase):
    def _wiki_with_page(self) -> tuple[Path, Path, str]:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "graph").mkdir(parents=True, exist_ok=True)
        (d / "papers").mkdir(parents=True, exist_ok=True)
        rel = "papers/foo.md"
        (d / rel).write_text("---\ntitle: Foo\nslug: foo\n---\n# Foo\n", encoding="utf-8")
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        return d, repo, rel

    def test_block_quarantines_artifact_and_writes_verdict(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🔴", rel, "bad")]), \
             mock.patch.object(trust_guard.research_wiki, "append_event"):
            verdict = trust_guard.check(wiki, wiki / rel, content_reviewer=lambda t, c: None, repo_root=repo)
        qfiles = list((repo / "raw" / "tmp" / "quarantine").glob("*.md"))
        vfiles = list((repo / "raw" / "tmp" / "quarantine").glob("*.verdict.json"))
        self.assertEqual(len(qfiles), 1)
        self.assertEqual(len(vfiles), 1)
        self.assertIn("Foo", qfiles[0].read_text(encoding="utf-8"))

    def test_warn_does_not_quarantine(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🟡", rel, "soft")]), \
             mock.patch.object(trust_guard.research_wiki, "append_event"):
            verdict = trust_guard.check(wiki, wiki / rel, content_reviewer=lambda t, c: None, repo_root=repo)
        self.assertEqual(verdict.status, "WARN")
        self.assertFalse((repo / "raw" / "tmp" / "quarantine").exists())

    def test_pass_does_not_quarantine(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[]):
            trust_guard.check(wiki, wiki / rel, content_reviewer=lambda t, c: None, repo_root=repo)
        self.assertFalse((repo / "raw" / "tmp" / "quarantine").exists())

    def test_event_is_appended(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        captured = {}

        def fake_append(wiki_root, stream, record):
            captured["stream"] = stream
            captured["record"] = record

        with mock.patch.object(trust_guard.lint, "lint", return_value=[]), \
             mock.patch.object(trust_guard.research_wiki, "append_event", side_effect=fake_append):
            trust_guard.check(wiki, wiki / rel, content_reviewer=lambda t, c: None, repo_root=repo)
        self.assertEqual(captured["stream"], "trust_events")
        self.assertEqual(captured["record"]["status"], "PASS")
        self.assertEqual(captured["record"]["artifact"], rel)

    def test_cli_exits_2_on_block(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[_issue("🔴", rel, "bad")]), \
             mock.patch.object(trust_guard.research_wiki, "append_event"):
            rc = trust_guard.main(["check", str(wiki), str(wiki / rel), "--no-content", "--repo-root", str(repo)])
        self.assertEqual(rc, 2)

    def test_cli_exits_0_on_pass(self) -> None:
        wiki, repo, rel = self._wiki_with_page()
        with mock.patch.object(trust_guard.lint, "lint", return_value=[]), \
             mock.patch.object(trust_guard.research_wiki, "append_event"):
            rc = trust_guard.main(["check", str(wiki), str(wiki / rel), "--no-content", "--repo-root", str(repo)])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
