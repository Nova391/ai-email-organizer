from apps.services.classifier import predict_email
from apps.services.summarizer import summarize
from apps.storage.database import get_emails_for_processing, mark_email_processed

def organize_unprocessed(limit: int | None = None, *, reprocess: bool = False) -> dict[str, object]:
    processed = 0
    errors: list[str] = []
    for email in get_emails_for_processing(limit, reprocess=reprocess):
        try:
            prediction = predict_email(email.get("subject") or "", email.get("body") or "",
                                       email.get("sender") or "")
            mark_email_processed(email["gmail_id"], category=prediction["category"],
                category_confidence=prediction["category_confidence"], priority=prediction["priority"],
                priority_confidence=prediction["priority_confidence"],
                summary=summarize(email.get("body"), subject=email.get("subject") or ""))
            processed += 1
        except Exception as exc:
            errors.append(f"{email['gmail_id']}: {exc}")
    return {"processed": processed, "failed": len(errors), "errors": errors}
