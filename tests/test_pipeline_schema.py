#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import loader  # noqa: E402


class PipelineSchemaTests(unittest.TestCase):
    def test_pipeline_loaded(self) -> None:
        self.assertIn("frontmatter", loader.PIPELINE)
        self.assertIn("stage_log", loader.PIPELINE)

    def test_required_fields(self) -> None:
        self.assertEqual(
            loader.pipeline_required_fields(),
            ["slug", "direction", "status", "current_stage", "started", "mode"],
        )

    def test_field_enums(self) -> None:
        enums = loader.pipeline_field_enums()
        self.assertEqual(enums["status"], {"running", "completed", "failed", "paused"})
        self.assertEqual(enums["current_stage"], {"stage0", "stage1", "stage2", "stage3", "stage4", "stage5"})
        self.assertEqual(enums["mode"], {"auto", "interactive"})

    def test_stage_log_keys_in_order(self) -> None:
        self.assertEqual(
            [line["key"] for line in loader.pipeline_stage_log_lines()],
            ["stage0", "stage1", "gate1", "stage2", "stage3a", "stage3b", "stage3c", "stage4", "gate2", "stage5"],
        )

    def test_stage_log_states(self) -> None:
        self.assertEqual(loader.pipeline_stage_log_states(),
                         {"pending", "running", "completed", "skipped", "failed"})

    def test_current_stage_map(self) -> None:
        self.assertEqual(loader.pipeline_current_stage_map()["stage3"],
                         ["stage3a", "stage3b", "stage3c"])


if __name__ == "__main__":
    unittest.main()
