import os
import tempfile
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to SQLite if no DATABASE_URL is set
if not DATABASE_URL or DATABASE_URL.strip() == "":
    db_path = os.path.join(tempfile.gettempdir(), "sendit.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# Fix Render's postgres:// prefix for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Apply threading fix for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        echo=True, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    """Create all SQLModel database tables on startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency injection yield for database sessions."""
    with Session(engine) as session:
        yield session
