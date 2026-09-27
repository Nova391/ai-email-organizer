from apps.integrations.gmail import get_emails
from apps.storage.database import upsert_email

def sync_emails(limit: int = 25, days: int = 7) -> dict[str, int]:
    emails = get_emails(limit=limit, days=days)
    added = 0
    for email in emails:
        _, created = upsert_email(email)
        added += int(created)
    return {"fetched": len(emails), "added": added, "updated": len(emails) - added}
