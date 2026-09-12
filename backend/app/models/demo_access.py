"""DIP owns authentication and trial records; no shared provider database."""
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import BaseModel


class DemoChallenge(BaseModel):
    __tablename__ = "demo_challenges"
    reference: Mapped[str] = mapped_column(String(64), unique=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    proof_hash: Mapped[str] = mapped_column(String(256))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DemoSession(BaseModel):
    __tablename__ = "demo_sessions"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DemoRateEvent(BaseModel):
    __tablename__ = "demo_rate_events"
    key_hash: Mapped[str] = mapped_column(String(64), index=True)
