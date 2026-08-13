import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/sendit_db")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """Create all SQLModel database tables on startup."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency injection yield for database sessions."""
    with Session(engine) as session:
        yield session