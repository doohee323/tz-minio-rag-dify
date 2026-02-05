from sqlalchemy import String, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class SyncUser(Base):
    """채팅 페이지(/chat) 접속 사용자. Embed 전용 사용자도 sync 대상에 포함시키기 위해 등록."""
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
    """Dify 대화 목록을 주기적으로 가져와 저장한 캐시."""
    __tablename__ = "conversation_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    dify_user: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Dify에서 온 값
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MessageCache(Base):
    """Dify 대화 메시지를 주기적으로 가져와 저장한 캐시."""
    __tablename__ = "message_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user, assistant
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Dify에서 온 값
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
