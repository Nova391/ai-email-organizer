import sqlite3

connection = sqlite3.connect("emails.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS 
    emails (
    id INTEGER PRIMARY KEY,
    gmail_id TEXT UNIQUE NOT NULL,
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    date TEXT,
    body TEXT,
    processed INTEGER DEFAULT 0
)
""")

connection.commit()
connection.close()