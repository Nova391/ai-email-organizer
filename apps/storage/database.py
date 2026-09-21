from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.integrations.gmail import get_emails
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

emails = get_emails(25, 7)

connection = sqlite3.connect("emails.db")
cursor = connection.cursor()
for email in emails:
    cursor.execute("""
        INSERT INTO emails (gmail_id, sender, recipient, subject, date, body)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email["id"], email["sender"], email["recipient"], email["subject"], email["date"], email["body"]))
connection.commit()
connection.close()