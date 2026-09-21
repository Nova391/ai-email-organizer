from pathlib import Path
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

def get_emails():
    service = get_email_service()
    request = service.users().messages().list(userId="me", maxResults=10)
    emails_list = request.execute()
    request2 = service.users().messages().get(userId="me", id=emails_list["messages"][0]["id"])
    email = request2.execute()
    parsed_email = parse_email(email)
    return parsed_email

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
                decoded_data = base64.urlsafe_b64decode(data)
                html_text = decoded_data.decode("utf-8")
                soup = BeautifulSoup(html_text, "html.parser")
                html_body = soup.get_text(separator=" ", strip=True)
                html_body = html_body.replace("\xa0", " ")
                html_body = html_body.replace("\u034f", "")
                html_body = " ".join(html_body.split())
            elif part["mimeType"] == "text/plain":
                data = part["body"]["data"]
                decoded_data = base64.urlsafe_b64decode(data)
                plain_body = decoded_data.decode("utf-8")
                plain_body = plain_body.replace("\xa0", " ")
                plain_body = plain_body.replace("\u034f", "")
                plain_body = " ".join(plain_body.split())
    else:
        mime_type = email["payload"]["mimeType"]
        data = email["payload"]["body"].get("data")
        decoded_data = base64.urlsafe_b64decode(data)
        text = decoded_data.decode("utf-8")
        if mime_type == "text/html":
            soup = BeautifulSoup(text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            text = text.replace("\xa0", " ")
            text = text.replace("\u034f", "")
            text = " ".join(text.split())
            html_body = text
        elif mime_type == "text/plain":
            text = text.replace("\xa0", " ")
            text = text.replace("\u034f", "")
            text = " ".join(text.split())
            plain_body = text
    if plain_body is not None:
        body = plain_body
    else:
        body = html_body
    return {"sender": sender, "subject": subject, "recipient": recipient, "date": date, "body": body}

result = get_emails()
print(result)