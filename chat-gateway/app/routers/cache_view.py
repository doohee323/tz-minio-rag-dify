"""Cache (conversation_cache, message_cache) query API and web page."""
from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import API_KEY_HEADER
from app.config import get_settings
from app.database import get_db
from app.models import ConversationCache, MessageCache
from app.templates import templates

router = APIRouter(tags=["cache"])


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


# ---------- API ----------

@router.get("/v1/cache/conversations")
async def list_cached_conversations(
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(API_KEY_HEADER),
    system_id: str | None = Query(None, description="System ID (e.g. cointutor)"),
    user_id: str | None = Query(None, description="User ID"),
    from_date: str | None = Query(None, description="Start date YYYY-MM-DD"),
    to_date: str | None = Query(None, description="End date YYYY-MM-DD"),
):
    """List conversations by system, user, and date range. API Key required."""
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    q = select(ConversationCache).order_by(ConversationCache.created_at.desc().nullslast())
    if system_id:
        q = q.where(ConversationCache.system_id == system_id)
    if user_id:
        q = q.where(ConversationCache.user_id == user_id)
    f = _parse_date(from_date)
    if f:
        q = q.where(ConversationCache.created_at >= f)
    t = _parse_date(to_date)
    if t:
        end = datetime.combine(t.date(), time(23, 59, 59, 999999))
        q = q.where(ConversationCache.created_at <= end)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "conversation_id": r.conversation_id,
            "system_id": r.system_id,
            "user_id": r.user_id,
            "name": r.name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "synced_at": r.synced_at.isoformat() if r.synced_at else None,
        }
        for r in rows
    ]


@router.get("/v1/cache/conversations/{conversation_id}/messages")
async def list_cached_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(API_KEY_HEADER),
):
    """List messages for a conversation. API Key required."""
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    q = select(MessageCache).where(MessageCache.conversation_id == conversation_id).order_by(MessageCache.created_at.asc().nullslast(), MessageCache.id.asc())
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "message_id": r.message_id,
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ---------- Web page ----------

@router.get("/cache", response_class=HTMLResponse)
async def cache_view_page(request: Request, api_key: str = Query("", description="API Key (for query)")):
    """Page to query cached conversations by system, user, and date range."""
    return templates.TemplateResponse(
        "cache.html",
        {
            "request": request,
            "api_key": api_key,
        },
    )
