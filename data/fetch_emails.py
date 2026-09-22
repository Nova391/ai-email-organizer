import sqlite3
import sys
import ssl
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from apps.integrations.gmail import get_emails

def fetch_and_save(limit=100, days=60):
    print(f"Fetching up to {limit} emails from the last {days} days...")
    new_emails = get_emails(limit=limit, days=days)
    print(f"Fetched {len(new_emails)} emails from Gmail. Saving to database...")
    
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    saved = 0
    for email in new_emails:
        cursor.execute("""
            INSERT OR IGNORE INTO emails (gmail_id, sender, recipient, subject, date, body)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email["id"], email["sender"], email["recipient"], email["subject"], email["date"], email["body"]))
        if cursor.rowcount > 0:
            saved += 1
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM emails")
    total = cursor.fetchone()[0]
    conn.close()
    
    print(f"Added {saved} new emails to database.")
    print(f"Total emails in database: {total}")

if __name__ == "__main__":
    fetch_and_save(100, 60)
