import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from apps.services.email_service import sync_emails
from apps.storage.database import get_stats, init_db

def fetch_and_save(limit=100, days=60):
    print(f"Fetching up to {limit} emails from the last {days} days...")
    init_db()
    result = sync_emails(limit=limit, days=days)
    print(f"Fetched {result['fetched']} emails; added {result['added']}, updated {result['updated']}.")
    print(f"Total emails in database: {get_stats()['total']}")

if __name__ == "__main__":
    fetch_and_save(100, 60)
