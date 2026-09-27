"""Gmail OAuth, retrieval, and MIME parsing."""
from __future__ import annotations

import base64
import binascii
import os
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ROOT_DIR = Path(__file__).resolve().parents[2]

def _path(env_name: str, default: str) -> Path:
    return Path(os.getenv(env_name, str(ROOT_DIR / default))).expanduser().resolve()

def get_gmail_credentials() -> Credentials:
    token_path = _path("GMAIL_TOKEN_PATH", "token.json")
    credentials_path = _path("GMAIL_CREDENTIALS_PATH", "credentials.json")
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    if not credentials or not credentials.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail OAuth credentials not found at {credentials_path}. "
                "Download an OAuth desktop client file and save it there.")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials

def get_email_service():
    return build("gmail", "v1", credentials=get_gmail_credentials(), cache_discovery=False)

def get_gmail_profile() -> dict[str, Any]:
    return get_email_service().users().getProfile(userId="me").execute()

def get_emails(limit: int = 10, days: int = 7) -> list[dict[str, Any]]:
    if limit < 1 or days < 1:
        raise ValueError("limit and days must be positive")
    service = get_email_service()
    emails: list[dict[str, Any]] = []
    page_token = None
    while len(emails) < limit:
        response = service.users().messages().list(
            userId="me", maxResults=min(100, limit - len(emails)),
            q=f"newer_than:{days}d", pageToken=page_token).execute()
        for message in response.get("messages", []):
            raw = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
            emails.append(parse_email(raw))
            if len(emails) == limit:
                break
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return emails

def decode_body(data: str | None) -> str:
    if not data:
        return ""
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except (ValueError, binascii.Error):
        return ""

def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u034f\u200b\u200c\u200f\u202a-\u202e\ufeff]", "", text)
    return " ".join(text.split())

def _extract_bodies(part: dict[str, Any], plain: list[str], html: list[str]) -> None:
    mime_type = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mime_type == "text/plain":
        plain.append(clean_text(decode_body(data)))
    elif data and mime_type == "text/html":
        soup = BeautifulSoup(decode_body(data), "html.parser")
        for element in soup(["style", "script", "noscript"]):
            element.decompose()
        html.append(clean_text(soup.get_text(separator=" ", strip=True)))
    for child in part.get("parts", []):
        _extract_bodies(child, plain, html)

def parse_email(email: dict[str, Any]) -> dict[str, Any]:
    payload = email.get("payload") or {}
    headers = {h.get("name", "").lower(): h.get("value") for h in payload.get("headers", [])}
    plain: list[str] = []
    html: list[str] = []
    _extract_bodies(payload, plain, html)
    body_parts = [part for part in plain if part] or [part for part in html if part]
    return {"id": email.get("id", ""), "sender": headers.get("from"),
            "recipient": headers.get("to"), "subject": headers.get("subject"),
            "date": headers.get("date"), "body": "\n\n".join(body_parts) or None}
