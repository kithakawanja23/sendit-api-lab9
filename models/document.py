from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str = Field(default="uploaded")  # "uploaded", "processing", "enriched", "failed"
    version: int = Field(default=1)
    is_latest: bool = Field(default=True)

    city: str = Field(index=True)
    country: str = Field(default="Kenya")

    weather_data: Optional[str] = Field(default=None)
    weather_fetched_at: Optional[datetime] = None

    description: Optional[str] = None
    uploader_id: int = Field(foreign_key="user.id")
    uploader: Optional["User"] = Relationship(back_populates="documents")
    uploaded_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    file_path: str