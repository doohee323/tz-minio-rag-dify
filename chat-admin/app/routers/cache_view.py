"""Admin Dify-direct API (conversations, messages)."""
import logging
from datetime import datetime, time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.auth import get_admin_required
from app.database import get_db
from app.dify_client import delete_conversation, get_conversation_messages, get_conversations
from app.models import ChatSystem, ConversationCache, MessageCache

router = APIRouter(tags=["admin"])
logger = logging.getLogger("chat_admin")


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


# ---------- API ----------

async def _check_system_owner(db: AsyncSession, system_id: str, admin_username: str) -> bool:
    """Return True if admin can access this system (owner or legacy)."""
    result = await db.execute(
        select(ChatSystem).where(ChatSystem.system_id == system_id.strip().lower())
    )
    row = result.scalar_one_or_none()
    if not row:
        return False
    return row.created_by is None or row.created_by == admin_username


@router.get("/v1/admin/conversations")
async def admin_list_conversations(
    system_id: str = Query("", description="System ID (e.g. drillquiz)"),
    user_id: str = Query("", description="User ID"),
    from_date: str | None = Query(None, description="Start date YYYY-MM-DD"),
    to_date: str | None = Query(None, description="End date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """List conversations from Dify (no cache). Admin can only view systems they created."""
    if not system_id.strip() or not user_id.strip():
        return []
    if not await _check_system_owner(db, system_id, admin_username):
        return []
    dify_user = f"{system_id.strip()}_{user_id.strip()}"
    try:
        convs = await get_conversations(dify_user, system_id=system_id.strip())
    except httpx.HTTPStatusError as e:
        try:
            body = e.response.json()
            detail = body.get("message") or body.get("detail") or e.response.text[:500]
        except Exception:
            detail = (e.response.text or str(e))[:500]
        raise HTTPException(status_code=min(e.response.status_code, 599), detail=detail or "Failed to fetch conversations")
    except httpx.RequestError as e:
        logger.warning("Dify get_conversations error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Chat service temporarily unavailable.")
    result = [
        {"conversation_id": c.get("id", ""), "system_id": system_id.strip(), "user_id": user_id.strip(), "name": c.get("name"), "created_at": c.get("created_at")}
        for c in convs
    ]
    f = _parse_date(from_date)
    t = _parse_date(to_date)
    if f or t:
        def in_range(created_str):
            if not created_str:
                return True
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if f and dt.replace(tzinfo=None) < f:
                    return False
                if t:
                    end = datetime.combine(t.date(), time(23, 59, 59, 999999))
                    if dt.replace(tzinfo=None) > end:
                        return False
                return True
            except Exception:
                return True
        result = [r for r in result if in_range(r.get("created_at"))]
    return result


@router.get("/v1/admin/conversations/{conversation_id}/messages")
async def admin_list_messages(
    conversation_id: str,
    system_id: str = Query(..., description="System ID"),
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """List messages from Dify (no cache). Admin can only view systems they created."""
    if not await _check_system_owner(db, system_id, admin_username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this system")
    dify_user = f"{system_id}_{user_id}"
    try:
        msgs = await get_conversation_messages(conversation_id, dify_user, system_id=system_id)
    except httpx.HTTPStatusError as e:
        try:
            body = e.response.json()
            detail = body.get("message") or body.get("detail") or e.response.text[:500]
        except Exception:
            detail = (e.response.text or str(e))[:500]
        raise HTTPException(status_code=min(e.response.status_code, 599), detail=detail or "Failed to fetch messages")
    except httpx.RequestError as e:
        logger.warning("Dify get_conversation_messages error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Chat service temporarily unavailable.")
    return [
        {
            "message_id": m.get("id", ""),
            "role": m.get("role", "user"),
            "content": m.get("content") or (m.get("message") or ""),
            "created_at": m.get("created_at"),
        }
        for m in msgs
    ]


@router.delete("/v1/admin/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_conversation(
    conversation_id: str,
    system_id: str = Query(..., description="System ID"),
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    admin_username: str = Depends(get_admin_required),
):
    """Delete a conversation from Dify and local cache. Admin can only delete in systems they created."""
    if not await _check_system_owner(db, system_id, admin_username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this system")
    dify_user = f"{system_id}_{user_id}"
    try:
        await delete_conversation(conversation_id, dify_user, system_id=system_id)
    except httpx.HTTPStatusError as e:
        try:
            body = e.response.json()
            detail = body.get("message") or body.get("detail") or e.response.text[:500]
        except Exception:
            detail = (e.response.text or str(e))[:500]
        logger.warning("Dify delete conversation error: %s %s | %s", e.response.status_code, conversation_id, detail[:200])
        raise HTTPException(
            status_code=min(e.response.status_code, 599),
            detail=detail or "Failed to delete conversation",
        )
    except httpx.RequestError as e:
        logger.warning("Dify delete request error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Chat service temporarily unavailable.")

    await db.execute(delete(MessageCache).where(MessageCache.conversation_id == conversation_id))
    await db.execute(delete(ConversationCache).where(ConversationCache.conversation_id == conversation_id))
    await db.commit()
