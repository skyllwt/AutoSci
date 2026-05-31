#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("trust_content_review", TOOLS / "trust_content_review.py")
assert spec and spec.loader
tcr = importlib.util.module_from_spec(spec)
sys.modules["trust_content_review"] = tcr
spec.loader.exec_module(tcr)


class ContentReviewTests(unittest.TestCase):
    def test_returns_none_when_env_unconfigured(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "", "base_url": "", "model": "", "fallback_model": ""}):
            self.assertIsNone(tcr.review_artifact("some text", context={}))

    def test_parses_block_verdict_from_llm(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "k", "base_url": "http://x/v1", "model": "m", "fallback_model": ""}), \
             mock.patch.object(tcr, "_post_chat", return_value='{"verdict": "block", "reason": "claim unsupported by evidence"}'):
            v = tcr.review_artifact("artifact", context={"neighbors": []})
            self.assertEqual(v.status, "BLOCK")
            self.assertIn("unsupported", v.message)

    def test_unknown_verdict_degrades_to_warn(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "k", "base_url": "http://x/v1", "model": "m", "fallback_model": ""}), \
             mock.patch.object(tcr, "_post_chat", return_value='{"verdict": "weird", "reason": "?"}'):
            v = tcr.review_artifact("artifact", context={})
            self.assertEqual(v.status, "WARN")

    def test_pass_verdict(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "k", "base_url": "http://x/v1", "model": "m", "fallback_model": ""}), \
             mock.patch.object(tcr, "_post_chat", return_value='here is json {"verdict":"pass","reason":"ok"} trailing'):
            v = tcr.review_artifact("artifact", context={})
            self.assertEqual(v.status, "PASS")

    def test_returns_none_when_post_chat_raises(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "k", "base_url": "http://x/v1", "model": "m", "fallback_model": ""}), \
             mock.patch.object(tcr, "_post_chat", side_effect=RuntimeError("boom")):
            self.assertIsNone(tcr.review_artifact("artifact", context={}))

    def test_parses_reason_with_braces(self) -> None:
        with mock.patch.object(tcr, "_llm_env", return_value={"api_key": "k", "base_url": "http://x/v1", "model": "m", "fallback_model": ""}), \
             mock.patch.object(tcr, "_post_chat", return_value='prefix {"verdict": "warn", "reason": "ratio {3/5} unclear"} suffix'):
            v = tcr.review_artifact("artifact", context={})
            self.assertEqual(v.status, "WARN")
            self.assertIn("{3/5}", v.message)


if __name__ == "__main__":
    unittest.main()
