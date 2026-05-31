#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

SOURCES = [
    ROOT / "i18n" / "en" / "skills" / "ingest" / "SKILL.md",
    ROOT / "i18n" / "zh" / "skills" / "ingest" / "SKILL.md",
]


class IngestWiringTests(unittest.TestCase):
    def test_both_sources_invoke_trust_guard_before_log(self) -> None:
        for src in SOURCES:
            text = src.read_text(encoding="utf-8")
            self.assertIn("trust_guard.py check", text, f"{src} missing trust_guard step")
            i_guard = text.index("trust_guard.py check")
            i_log = text.index("research_wiki.py log wiki/")
            self.assertLess(i_guard, i_log, f"{src}: Trust Guard must come before the log step")
            self.assertIn(
                'tools/trust_guard.py check wiki/ "wiki/<kind>/<slug>.md" --repo-root .',
                text, f"{src} missing the documented trust_guard invocation template")

    def test_cli_blocks_missing_required_field_with_exit_2(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "wiki" / "graph").mkdir(parents=True)
        (tmp / "wiki" / "papers").mkdir(parents=True)
        (tmp / "wiki" / "papers" / "bar.md").write_text("---\nslug: bar\n---\n# Bar\n", encoding="utf-8")
        # --no-content force-skips the Review-LLM check so this test needs no live LLM
        rc = subprocess.run(
            [str(PY), str(ROOT / "tools" / "trust_guard.py"), "check",
             str(tmp / "wiki"), str(tmp / "wiki" / "papers" / "bar.md"),
             "--no-content", "--repo-root", str(tmp)],
            capture_output=True, text=True,
        ).returncode
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
