import base64
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from apps.api.routes import email, emails, health
from apps.integrations.gmail import parse_email
from apps.services.classifier import NaiveBayesClassifier
from apps.services.summarizer import summarize
from apps.storage import database


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["EMAIL_ORGANIZER_DB"] = str(Path(self.temp_dir.name) / "test.db")
        database.init_db()
        database.save_email({"id": "g1", "sender": "boss@example.com", "recipient": "me@example.com",
            "subject": "Meeting", "date": "Mon, 1 Jan 2026", "body": "Please attend the meeting tomorrow."})

    def tearDown(self):
        os.environ.pop("EMAIL_ORGANIZER_DB", None)
        self.temp_dir.cleanup()

    def test_database_and_api(self):
        self.assertEqual(health(), {"status": "ok"})
        response = emails(offset=0, limit=50, processed=None, category=None,
                          priority=None, search="Meeting")
        self.assertEqual(response["total"], 1)
        with self.assertRaises(HTTPException) as caught:
            email(999)
        self.assertEqual(caught.exception.status_code, 404)

    def test_classifier_validation_and_prediction(self):
        model = NaiveBayesClassifier()
        with self.assertRaises(ValueError):
            model.fit([], [])
        model.fit(["urgent invoice", "summer sale"], ["work", "promotion"])
        label, confidence, probabilities = model.predict_one("urgent work")
        self.assertEqual(label, "work")
        self.assertGreater(confidence, 0)
        self.assertAlmostEqual(sum(probabilities.values()), 1.0, places=3)

    def test_nested_mime_parsing(self):
        encoded = base64.urlsafe_b64encode(b"Hello from a nested part").decode()
        raw = {"id": "abc", "payload": {"headers": [{"name": "Subject", "value": "Hi"}],
            "mimeType": "multipart/mixed", "parts": [{"mimeType": "multipart/alternative", "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded}}]}]}}
        parsed = parse_email(raw)
        self.assertEqual(parsed["body"], "Hello from a nested part")
        self.assertEqual(parsed["subject"], "Hi")

    def test_summary_is_bounded(self):
        result = summarize("First sentence. Second sentence is much longer.", max_chars=20)
        self.assertLessEqual(len(result), 20)

    def test_summary_prefers_relevant_action_and_removes_reply(self):
        body = """Hi Jordan,

        I hope you are doing well. The project report must be reviewed by Friday at 3:00 PM.
        Please approve the final budget before the deadline. Thanks!

        On Tue, Alex wrote:
        > This old reply must never appear in the summary.
        """
        result = summarize(body, subject="Project report deadline")
        self.assertIn("reviewed by Friday", result)
        self.assertIn("approve the final budget", result)
        self.assertNotIn("old reply", result)

    def test_summary_removes_marketing_boilerplate(self):
        body = "Your order 4821 ships tomorrow. Track it in your account. Unsubscribe from these emails."
        result = summarize(body, subject="Order 4821 update")
        self.assertIn("ships tomorrow", result)
        self.assertNotIn("Unsubscribe", result)

    def test_summary_uses_subject_when_body_is_empty(self):
        self.assertEqual(summarize(None, subject="Your receipt is ready"), "Your receipt is ready")


if __name__ == "__main__":
    unittest.main()
