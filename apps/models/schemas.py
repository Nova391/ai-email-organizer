from pydantic import BaseModel, ConfigDict, Field

class EmailRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gmail_id: str
    sender: str | None = None
    recipient: str | None = None
    subject: str | None = None
    date: str | None = None
    body: str | None = None
    processed: bool = False
    category: str | None = None
    category_confidence: float | None = None
    priority: str | None = None
    priority_confidence: float | None = None
    summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

class EmailPage(BaseModel):
    items: list[EmailRecord]
    total: int
    offset: int
    limit: int

class PredictionRequest(BaseModel):
    subject: str = ""
    body: str = ""
    sender: str = ""

class PredictionResponse(BaseModel):
    category: str
    category_confidence: float
    category_probabilities: dict[str, float]
    priority: str
    priority_confidence: float
    priority_probabilities: dict[str, float]

class SyncRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=500)
    days: int = Field(default=7, ge=1, le=3650)

class SyncResponse(BaseModel):
    fetched: int
    added: int
    updated: int

class OrganizeRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=1000)

class OrganizeResponse(BaseModel):
    processed: int
    failed: int
    errors: list[str] = Field(default_factory=list)

class StatsResponse(BaseModel):
    total: int
    processed: int
    unprocessed: int
    categories: dict[str, int]
    priorities: dict[str, int]
