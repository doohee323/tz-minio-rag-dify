from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class ChatSystem(Base):
    """Target system (e.g. drillquiz, cointutor) - Dify + API config per system."""
    __tablename__ = "chat_systems"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    dify_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    dify_api_key: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    dify_chatbot_token: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    allowed_origins: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # admin username who created
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminUser(Base):
    """Admin user for chat gateway management (login/register)."""
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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
