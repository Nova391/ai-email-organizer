from pathlib import Path
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_credentials():

    print("Starting OAuth...")

    if Path("token.json").exists():
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
        print("Credentials loaded.")
    else:  
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        print("Flow created. Starting browser...")

        credentials = flow.run_local_server()
        token_data = credentials.to_json()

        with open("token.json", "w") as file:
            file.write(token_data)

    print("Authorization finished.")
    return credentials

def get_email_service():
    smth = get_gmail_credentials()
    service = build("gmail", "v1", credentials=smth)
    return service

def get_gmail_profile():
    service = get_email_service()
    request = service.users().getProfile(userId="me")
    profile = request.execute()
    print(profile)

def get_emails(limit=10, days=7):
    query = f"newer_than:{days}d"
    service = get_email_service()
    request = service.users().messages().list(userId="me", maxResults=limit, q=query)
    emails_list = request.execute()
    page_token = emails_list.get("nextPageToken")
    emails = []
    for msg in emails_list["messages"]:
        request = service.users().messages().get(userId="me", id=msg["id"])
        email = request.execute()
        parsed_email = parse_email(email)
        emails.append(parsed_email)
    while page_token and len(emails) < limit:
        max_results = min(10, limit - len(emails))
        request = service.users().messages().list(userId="me", maxResults=max_results, pageToken=page_token, q=query)
        emails_list = request.execute()
        page_token = emails_list.get("nextPageToken")
        for msg in emails_list["messages"]:
            request = service.users().messages().get(userId="me", id=msg["id"])
            email = request.execute()
            parsed_email = parse_email(email)
            emails.append(parsed_email)
    return emails

def decode_body(data):
    decoded_data = base64.urlsafe_b64decode(data)
    text = decoded_data.decode("utf-8")
    return text

def clean_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u034f\u200b\u200c\u200f\u202a-\u202e\ufeff]", "", text)
    text = " ".join(text.split())
    return text

def parse_email(email):
    sender = None
    recipient = None
    subject = None
    date = None
    body = None
    plain_body = None
    html_body = None
    for header in email["payload"]["headers"]:
        if header["name"] == "From":
            sender = header["value"]
        elif header["name"] == "Subject":
            subject = header["value"]
        elif header["name"] == "To":
            recipient = header["value"]
        elif header["name"] == "Date":
            date = header["value"]
    parts = email["payload"].get("parts")
    if parts is not None:
        for part in parts:
            if part["mimeType"] == "text/html":
                data = part["body"]["data"]
                html_text = decode_body(data)
                soup = BeautifulSoup(html_text, "html.parser")
                for element in soup.find_all(["style", "script"]):
                    element.decompose()
                html_body = soup.get_text(separator=" ", strip=True)
                html_body = clean_text(html_body)
            elif part["mimeType"] == "text/plain":
                data = part["body"]["data"]
                plain_body = decode_body(data)
                plain_body = clean_text(plain_body)
    else:
        mime_type = email["payload"]["mimeType"]
        data = email["payload"]["body"].get("data")
        text = decode_body(data)
        if mime_type == "text/html":
            soup = BeautifulSoup(text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            text = clean_text(text)
            html_body = text
        elif mime_type == "text/plain":
            text = clean_text(text)
            plain_body = text
    if plain_body is not None:
        body = plain_body
    else:
        body = html_body
    return {"id": email["id"], "sender": sender, "subject": subject, "recipient": recipient, "date": date, "body": body}

result = get_emails(25)
print(result)