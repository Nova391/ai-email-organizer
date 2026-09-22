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

def save_email(email):
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO emails (gmail_id, sender, recipient, subject, date, body)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email["id"], email["sender"], email["recipient"], email["subject"], email["date"], email["body"]))
    connection.commit()
    connection.close()

def show_emails_count():
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM emails
        """)
    result = cursor.fetchone()
    connection.close()
    return result

def show_emails():
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM emails
        """)
    rows = cursor.fetchall()
    connection.close()
    return rows

def get_unprocessed_emails():
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM emails WHERE processed = 0
        """)
    rows = cursor.fetchall()
    connection.close()
    return rows

def mark_email_processed(gmail_id):
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE emails
        SET processed = 1 
        WHERE gmail_id = ?
    """, (gmail_id,))
    connection.commit()
    connection.close()