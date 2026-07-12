from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import daily_arxiv, send_email


class DailyArxivRecommendationTests(unittest.TestCase):
    def test_config_has_no_runtime_or_ingest_state(self):
        cfg, _ = daily_arxiv.load_config(None)
        self.assertNotIn("mode", cfg)
        self.assertNotIn("runtime", cfg)
        self.assertNotIn("max_auto_ingest", cfg)

    def test_finalize_without_llm_is_deterministic_fallback(self):
        context = {
            "generated_at": "2026-01-01T00:00:00Z",
            "config": {"max_recommendations": 3},
            "counts": {"feed_total": 1, "already_in_wiki": 0, "new_candidates": 1, "listed": 1},
            "category_counts": {"cs.AI": 1},
            "candidates": [{"arxiv_id": "2601.00001", "title": "A", "is_known": False, "tool_rank_score": .5, "signals": {}}],
            "notes": [],
        }
        payload = daily_arxiv.finalize_payload(context)
        self.assertFalse(payload["llm_decision_available"])
        self.assertEqual(payload["listed_candidates"][0]["decision"], "maybe")
        self.assertNotIn("auto_ingest", payload)

    def test_full_recommendation_decisions_are_merged(self):
        context = {
            "generated_at": "2026-01-01T00:00:00Z",
            "config": {"max_recommendations": 2},
            "counts": {"feed_total": 1, "already_in_wiki": 0, "new_candidates": 1, "listed": 1},
            "category_counts": {"cs.AI": 1},
            "candidates": [{"arxiv_id": "2601.00001", "title": "A", "is_known": False, "tool_rank_score": .5, "signals": {}}],
            "notes": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            decisions = Path(tmp) / "decisions.json"
            decisions.write_text(json.dumps({"decisions": [{"arxiv_id": "2601.00001", "decision": "strong_recommend", "confidence": "high", "rationale": "matches profile"}]}), encoding="utf-8")
            payload = daily_arxiv.finalize_payload(context, decisions)
        self.assertTrue(payload["llm_decision_available"])
        self.assertEqual(payload["listed_candidates"][0]["decision"], "strong_recommend")

    def test_prepare_records_external_degradation(self):
        cfg, _ = daily_arxiv.load_config(None)
        payload = daily_arxiv.build_recommendation_context(
            feed=[], feed_path=None, wiki_root=Path("missing-wiki"), cfg=cfg,
            config_notes=[], enrich=False,
        )
        self.assertIn("External enrichment skipped by command-line option.", payload["notes"])

    def test_no_new_papers_produces_empty_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = Path(tmp) / "feed.json"
            feed.write_text("[]", encoding="utf-8")
            payload = daily_arxiv.build_digest(feed, Path(tmp) / "wiki", 10)
            self.assertEqual(payload["counts"]["new_candidates"], 0)


class EmailFailureTests(unittest.TestCase):
    def _args(self, body: Path):
        return type("Args", (), {"subject": "x", "body_file": body, "to": None, "from_addr": None, "check_config": False})()

    @mock.patch.dict("os.environ", {"SMTP_HOST":"smtp.test", "SMTP_PORT":"587", "SMTP_USER":"u", "SMTP_PASSWORD":"p", "SMTP_FROM":"a@test", "DAILY_ARXIV_EMAIL_TO":"b@test"}, clear=True)
    @mock.patch("smtplib.SMTP")
    def test_smtp_success_and_auth_failure_are_exposed(self, smtp):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "digest.md"
            body.write_text("digest", encoding="utf-8")
            send_email.send_message(self._args(body))
            smtp.return_value.__enter__.return_value.login.side_effect = OSError("auth")
            with self.assertRaises(OSError):
                send_email.send_message(self._args(body))

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_missing_smtp_configuration_is_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "digest.md"
            body.write_text("digest", encoding="utf-8")
            with self.assertRaises(send_email.ConfigError):
                send_email.send_message(self._args(body))

    @mock.patch.dict("os.environ", {"SMTP_HOST":"smtp.test", "SMTP_PORT":"587", "SMTP_USER":"u", "SMTP_PASSWORD":"p", "SMTP_FROM":"a@test", "DAILY_ARXIV_EMAIL_TO":"b@test"}, clear=True)
    @mock.patch("smtplib.SMTP", side_effect=TimeoutError("timeout"))
    def test_connection_timeout_is_exposed(self, _smtp):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "digest.md"
            body.write_text("digest", encoding="utf-8")
            with self.assertRaises(TimeoutError):
                send_email.send_message(self._args(body))

    def test_workflow_keeps_artifact_after_mail_failure(self):
        workflow = (Path(__file__).parents[1] / ".github/workflows/daily-arxiv.yml").read_text(encoding="utf-8")
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("name: Upload digest artifact", workflow)
        self.assertIn("if: always()", workflow)


if __name__ == "__main__":
    unittest.main()
