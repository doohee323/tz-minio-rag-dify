"""Dify 대화 목록·메시지를 가져와 SQLite에 저장하는 동기화."""
import logging
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.dify_client import get_conversation_messages, get_conversations
from app.models import ConversationCache, ConversationMapping, MessageCache, SyncUser

logger = logging.getLogger("chat_gateway")


async def _upsert_message(
    db: AsyncSession,
    conversation_id: str,
    message_id: str,
    role: str,
    content: str,
    created_at: datetime | None,
) -> None:
    stmt = sqlite_insert(MessageCache).values(
        conversation_id=conversation_id,
        message_id=message_id,
        role=role,
        content=content,
        created_at=created_at,
        synced_at=datetime.utcnow(),
    ).on_conflict_do_update(
        index_elements=["message_id"],
        set_={
            "content": content,
            "created_at": created_at,
            "synced_at": datetime.utcnow(),
        },
    )
    await db.execute(stmt)


def _ts_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(ts)
    except Exception:
        return None


async def record_chat_to_db(
    db: AsyncSession,
    system_id: str,
    user_id: str,
    dify_user: str,
    conversation_id: str,
    message_id: str | None,
    user_query: str,
    assistant_answer: str,
) -> None:
    """채팅 한 건을 Dify 응답 직후 SQLite에 바로 기록. (별도 sync 불필요)."""
    now = datetime.utcnow()
    stmt_conv = sqlite_insert(ConversationCache).values(
        system_id=system_id,
        user_id=user_id,
        dify_user=dify_user,
        conversation_id=conversation_id,
        name=None,
        created_at=now,
        synced_at=now,
    ).on_conflict_do_update(
        index_elements=["conversation_id"],
        set_={"synced_at": now},
    )
    await db.execute(stmt_conv)
    mid = message_id or f"local-{uuid.uuid4().hex[:12]}"
    await _upsert_message(db, conversation_id, f"{mid}_user", "user", user_query or "", now)
    await _upsert_message(db, conversation_id, f"{mid}_assistant", "assistant", assistant_answer or "", now)


async def register_sync_user(
    db: AsyncSession,
    system_id: str,
    user_id: str,
    dify_user: str,
) -> None:
    """채팅 페이지 접속 시 (system_id, user_id)를 동기화 대상으로 등록. Embed 전용 사용자도 sync 대상에 포함."""
    stmt = sqlite_insert(SyncUser).values(
        system_id=system_id,
        user_id=user_id,
        dify_user=dify_user,
        updated_at=datetime.utcnow(),
    ).on_conflict_do_update(
        index_elements=["system_id", "user_id"],
        set_={"dify_user": dify_user, "updated_at": datetime.utcnow()},
    )
    await db.execute(stmt)


async def sync_user_conversations(
    db: AsyncSession,
    system_id: str,
    user_id: str,
    dify_user: str,
) -> tuple[int, int]:
    """한 사용자의 대화 목록과 메시지를 Dify에서 가져와 캐시 테이블에 upsert. (conversations 수, messages 수) 반환."""
    convs = await get_conversations(dify_user, system_id=system_id)
    conv_count = 0
    msg_count = 0
    for c in convs:
        cid = c.get("id")
        if not cid:
            continue
        conv_count += 1
        name = c.get("name")
        created_at = _ts_to_datetime(c.get("created_at"))
        stmt = sqlite_insert(ConversationCache).values(
            system_id=system_id,
            user_id=user_id,
            dify_user=dify_user,
            conversation_id=cid,
            name=name,
            created_at=created_at,
            synced_at=datetime.utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["conversation_id"],
            set_={
                "name": name,
                "created_at": created_at,
                "synced_at": datetime.utcnow(),
            },
        )
        await db.execute(stmt)

        messages = await get_conversation_messages(cid, dify_user, system_id=system_id)
        for m in messages:
            mid = m.get("id")
            if not mid:
                continue
            created_at = _ts_to_datetime(m.get("created_at"))
            # Dify 한 건에 query(user)+answer(assistant)가 같이 있을 수 있음 → 각각 한 행씩 저장
            if m.get("query") is not None:
                await _upsert_message(db, cid, f"{mid}_user", "user", m.get("query") or "", created_at)
                msg_count += 1
            if m.get("answer") is not None:
                await _upsert_message(db, cid, f"{mid}_assistant", "assistant", m.get("answer") or "", created_at)
                msg_count += 1
    return conv_count, msg_count


async def sync_all_from_mapping(db: AsyncSession) -> dict:
    """ConversationMapping + SyncUser에 있는 (system_id, user_id) 기준으로 Dify에서 전부 동기화."""
    q_mapping = select(
        ConversationMapping.system_id,
        ConversationMapping.user_id,
        ConversationMapping.dify_user,
    ).distinct()
    q_sync_users = select(
        SyncUser.system_id,
        SyncUser.user_id,
        SyncUser.dify_user,
    )
    r1 = await db.execute(q_mapping)
    r2 = await db.execute(q_sync_users)
    seen: set[tuple[str, str, str]] = set()
    rows: list[tuple[str, str, str]] = []
    for row in (*r1.all(), *r2.all()):
        key = (row[0], row[1], row[2])
        if key not in seen:
            seen.add(key)
            rows.append(row)
    total_conv = 0
    total_msg = 0
    errors = []
    for system_id, user_id, dify_user in rows:
        try:
            nc, nm = await sync_user_conversations(db, system_id, user_id, dify_user)
            total_conv += nc
            total_msg += nm
        except Exception as e:
            logger.exception("sync %s/%s: %s", system_id, user_id, e)
            errors.append(f"{system_id}/{user_id}: {e}")
    return {"conversations_synced": total_conv, "messages_synced": total_msg, "errors": errors}
