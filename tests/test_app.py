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
        self.assertLessEqual(len(result), 21)


if __name__ == "__main__":
    unittest.main()
