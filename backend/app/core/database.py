from typing import Generator
from fastapi import Request

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base

engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db(request: Request) -> Generator[Session, None, None]:
    guarded = getattr(request.state, "demo_db", None)
    if guarded is not None:
        yield guarded
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
