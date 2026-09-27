from fastapi import APIRouter, HTTPException, Query

from apps.models.schemas import (EmailPage, EmailRecord, OrganizeRequest, OrganizeResponse,
    PredictionRequest, PredictionResponse, StatsResponse, SyncRequest, SyncResponse)
from apps.services.classifier import predict_email
from apps.services.email_service import sync_emails
from apps.services.organizer import organize_unprocessed
from apps.storage.database import get_email, get_stats, list_emails

router = APIRouter(prefix="/api", tags=["email-organizer"])

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/emails", response_model=EmailPage)
def emails(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
           processed: bool | None = None, category: str | None = None,
           priority: str | None = None, search: str | None = Query(None, max_length=200)):
    items, total = list_emails(offset=offset, limit=limit, processed=processed,
        category=category, priority=priority, search=search)
    return {"items": items, "total": total, "offset": offset, "limit": limit}

@router.get("/emails/{email_id}", response_model=EmailRecord)
def email(email_id: int):
    item = get_email(email_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return item

@router.get("/stats", response_model=StatsResponse)
def stats():
    return get_stats()

@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        return predict_email(request.subject, request.body, request.sender)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.post("/sync", response_model=SyncResponse)
def sync(request: SyncRequest):
    try:
        return sync_emails(request.limit, request.days)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail sync failed: {exc}") from exc

@router.post("/organize", response_model=OrganizeResponse)
def organize(request: OrganizeRequest):
    return organize_unprocessed(request.limit, reprocess=request.reprocess)
