from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class WebhookSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_url: str
    event_type: str  # "document.enriched", "document.uploaded"
    secret_token: str = Field(default="whsec_default_secret")
    created_at: datetime = Field(default_factory=utc_now)
    is_active: bool = Field(default=True)