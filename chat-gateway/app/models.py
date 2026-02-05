from sqlalchemy import String, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class SyncUser(Base):
    """User who accessed the chat page (/chat). Registered so embed-only users are included in sync targets."""
    __tablename__ = "sync_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    dify_user: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("system_id", "user_id", name="uq_sync_users_system_user"),)


class ConversationMapping(Base):
    __tablename__ = "conversation_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    dify_user: Mapped[str] = mapped_column(String(320), nullable=False, index=True)  # system_id_user_id
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_system_user", "system_id", "user_id"),)


class ConversationCache(Base):
    """Cache of Dify conversation list fetched and stored periodically."""
    __tablename__ = "conversation_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    dify_user: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # from Dify
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MessageCache(Base):
    """Cache of Dify conversation messages fetched and stored periodically."""
    __tablename__ = "message_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user, assistant
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # from Dify
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
