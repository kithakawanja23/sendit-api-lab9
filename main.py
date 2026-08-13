from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select, col, or_
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime, timezone
from typing import Optional, List
import os
import aiofiles
import json
import hmac
import hashlib
import httpx

from database.session import init_db, get_session
from models.user import User, UserCreate, UserResponse, TokenResponse
from models.document import Document
from models.webhook import WebhookSubscription
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_admin, get_current_manager
)
from services.weather import get_weather

app = FastAPI(
    title="SendIt Document Management & Enrichment API",
    version="1.0.0",
    description="Lab 9 API for digitizing waybills, managing uploads, and external weather enrichment."
)

@app.on_event("startup")
def on_startup():
    init_db()

# Rate Limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 5 * 1024 * 1024))
ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".docx"]

async def dispatch_webhook(event_type: str, payload: dict, session: Session):
    subscriptions = session.exec(
        select(WebhookSubscription)
        .where(WebhookSubscription.event_type == event_type)
        .where(WebhookSubscription.is_active == True)
    ).all()

    if not subscriptions:
        return

    async with httpx.AsyncClient() as client:
        for sub in subscriptions:
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = hmac.new(sub.secret_token.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
            headers = {"Content-Type": "application/json", "X-SendIt-Signature": signature, "X-SendIt-Event": event_type}
            try:
                await client.post(sub.target_url, content=payload_bytes, headers=headers, timeout=5.0)
            except Exception as e:
                print(f"Webhook delivery failed for {sub.target_url}: {e}")

# AUTHENTICATION
@app.post("/auth/register", response_model=UserResponse, status_code=201, tags=["Authentication"])
def register(user_data: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(or_(User.username == user_data.username, User.email == user_data.email))).first()
    if existing:
        raise HTTPException(400, "Username or email is already registered")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")

    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    session.commit()

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# FILE UPLOADS
@app.post("/documents/upload", status_code=201, tags=["Documents"])
@limiter.limit("10/hour")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    city: str = Form(...),
    description: Optional[str] = Form(None),
    country: str = Form("Kenya"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)} MB")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(contents)

    document = Document(
        filename=safe_filename,
        original_filename=file.filename,
        file_size=file_size,
        file_type=file.content_type or "application/octet-stream",
        city=city,
        country=country,
        description=description,
        uploader_id=current_user.id,
        file_path=file_path,
        status="processing"
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        weather_data = await get_weather(city, country)
        if weather_data and "error" not in weather_data:
            document.weather_data = json.dumps(weather_data)
            document.weather_fetched_at = datetime.now(timezone.utc)
            document.status = "enriched"
        else:
            document.status = "uploaded"
        session.commit()
    except Exception:
        document.status = "uploaded"
        session.commit()

    await dispatch_webhook("document.uploaded", {"document_id": document.id, "status": document.status}, session)
    return {"message": "Upload complete", "document_id": document.id, "status": document.status}

# EXERCISE 1: SEARCH
@app.get("/documents/search", tags=["Exercise 1 - Search"])
@limiter.limit("20/minute")
def search_documents(
    request: Request,
    q: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    query = select(Document)
    if current_user.role not in ["admin", "manager"]:
        query = query.where(Document.uploader_id == current_user.id)

    if q:
        query = query.where(or_(col(Document.original_filename).ilike(f"%{q}%"), col(Document.description).ilike(f"%{q}%")))
    if city:
        query = query.where(col(Document.city).ilike(city))
    if status:
        query = query.where(Document.status == status)
    if date_from:
        query = query.where(Document.uploaded_at >= date_from)
    if date_to:
        query = query.where(Document.uploaded_at <= date_to)

    return session.exec(query).all()

# EXERCISE 2: VERSIONING
@app.post("/documents/upload/versioned", tags=["Exercise 2 - Versioning"])
async def upload_document_versioned(
    request: Request,
    file: UploadFile = File(...),
    city: str = Form(...),
    description: Optional[str] = Form(None),
    country: str = Form("Kenya"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    contents = await file.read()
    existing_docs = session.exec(
        select(Document)
        .where(Document.original_filename == file.filename)
        .where(Document.uploader_id == current_user.id)
        .order_by(Document.version.desc())
    ).all()

    new_version = 1
    if existing_docs:
        for doc in existing_docs:
            doc.is_latest = False
            session.add(doc)
        new_version = existing_docs[0].version + 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"v{new_version}_{timestamp}_{current_user.id}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(contents)

    document = Document(
        filename=safe_filename,
        original_filename=file.filename,
        file_size=len(contents),
        file_type=file.content_type or "application/octet-stream",
        version=new_version,
        is_latest=True,
        city=city,
        country=country,
        description=description,
        uploader_id=current_user.id,
        file_path=file_path,
        status="uploaded"
    )
    session.add(document)
    session.commit()
    return {"message": "Version uploaded", "version": new_version, "document_id": document.id}

# EXERCISE 3: WEBHOOKS
@app.post("/webhooks/register", tags=["Exercise 3 - Webhooks"])
def register_webhook(
    webhook_url: str,
    event_type: str,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    subscription = WebhookSubscription(target_url=webhook_url, event_type=event_type)
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return {"message": "Webhook registered successfully", "subscription": subscription}

# MANUAL ENRICHMENT
@app.post("/documents/{document_id}/enrich", tags=["Enrichment"])
async def enrich_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(get_current_manager),
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")

    weather_data = await get_weather(document.city, document.country)
    if weather_data and "error" not in weather_data:
        document.weather_data = json.dumps(weather_data)
        document.weather_fetched_at = datetime.now(timezone.utc)
        document.status = "enriched"
        session.commit()
        await dispatch_webhook("document.enriched", {"document_id": document.id, "status": "enriched"}, session)
        return {"message": "Enriched successfully", "weather": weather_data}

    document.status = "failed"
    session.commit()
    raise HTTPException(500, "Failed to resolve external weather enrichment")