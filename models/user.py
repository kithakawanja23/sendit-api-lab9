from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.document import Document

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str = Field(min_length=2, max_length=100)
    role: str = Field(default="staff")  # "admin", "manager", "staff"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_login: Optional[datetime] = None

    documents: List["Document"] = Relationship(back_populates="uploader")

class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=100)
    role: str = Field(default="staff")

class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"