import logging
import time
import jwt
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from sqlalchemy import select
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import API_KEY_HEADER, get_identity_from_body, get_identity_optional, ChatIdentity
from app.config import get_settings
from app.dify_client import delete_conversation, get_conversation_messages, get_conversations, send_chat_message
from app.models import ConversationMapping
from app.schemas import ChatRequest, ChatResponse, ConversationItem, MessageItem
from app.sync_service import record_chat_to_db, sync_all_from_mapping

router = APIRouter(prefix="/v1", tags=["chat"])
logger = logging.getLogger("chat_gateway")


@router.get("/status")
async def get_status():
    """Returns only whether Dify integration is configured (no key/URL exposure). For 502 troubleshooting."""
    settings = get_settings()
    systems = {}
    for sid in ("drillquiz", "cointutor"):
        base = (settings.get_dify_base_url(sid) or "").strip()
        key = (settings.get_dify_api_key(sid) or "").strip()
        systems[sid] = {"configured": bool(base and key), "has_base_url": bool(base), "has_api_key": bool(key)}
    return {"systems": systems}


def _resolve_identity(
    identity: ChatIdentity | None,
    body: ChatRequest | None,
    api_key: str | None,
    system_id: str | None = None,
    user_id: str | None = None,
) -> ChatIdentity:
    if identity is not None:
        if system_id and user_id and (identity.system_id != system_id or identity.user_id != user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="system_id/user_id must match token")
        return identity
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key or Bearer token required")
    if body and body.system_id and body.user_id:
        return get_identity_from_body(body.system_id, body.user_id)
    if system_id and user_id:
        return get_identity_from_body(system_id, user_id)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="system_id and user_id required in body or query when using API key")


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    identity: ChatIdentity | None = Depends(get_identity_optional),
    api_key: str = Security(API_KEY_HEADER),
):
    sid = body.system_id or (identity.system_id if identity else None)
    uid = body.user_id or (identity.user_id if identity else None)
    ident = _resolve_identity(identity, body, api_key, system_id=sid, user_id=uid)

    settings = get_settings()
    dify_key = settings.get_dify_api_key(ident.system_id)
    dify_base = settings.get_dify_base_url(ident.system_id)
    if not dify_key or not dify_base:
        logger.warning(
            "Chat not configured for system_id=%s (missing Dify API key or base URL)",
            ident.system_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is not configured for this app.",
        )

    try:
        result = await send_chat_message(
            user=ident.dify_user,
            query=body.message,
            conversation_id=body.conversation_id,
            inputs=body.inputs,
            system_id=ident.system_id,
        )
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Dify API error for system_id=%s: %s %s",
            ident.system_id,
            e.response.status_code,
            (e.response.text or "")[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat service temporarily unavailable. Please try again.",
        )
    except httpx.RequestError as e:
        logger.warning(
            "Dify request error for system_id=%s: %s",
            ident.system_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat service temporarily unavailable. Please try again.",
        )

    conversation_id = result.get("conversation_id") or ""
    message_id = result.get("message_id")
    answer = result.get("answer", "")

    try:
        if conversation_id:
            stmt = select(ConversationMapping).where(
                ConversationMapping.system_id == ident.system_id,
                ConversationMapping.user_id == ident.user_id,
                ConversationMapping.conversation_id == conversation_id,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                row = ConversationMapping(
                    system_id=ident.system_id,
                    user_id=ident.user_id,
                    dify_user=ident.dify_user,
                    conversation_id=conversation_id,
                )
                db.add(row)
            await record_chat_to_db(
                db,
                ident.system_id,
                ident.user_id,
                ident.dify_user,
                conversation_id,
                message_id,
                body.message,
                answer,
            )
    except Exception as e:
        logger.warning(
            "Failed to record chat for system_id=%s conversation_id=%s: %s",
            ident.system_id,
            conversation_id,
            e,
            exc_info=True,
        )
        await db.rollback()
        # Still return the chat response; recording is best-effort.

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=message_id,
        answer=answer,
        metadata=result.get("metadata"),
    )


@router.get("/conversations", response_model=list[ConversationItem])
async def list_conversations(
    system_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    identity: ChatIdentity | None = Depends(get_identity_optional),
    api_key: str = Security(API_KEY_HEADER),
):
    ident = _resolve_identity(identity, None, api_key, system_id=system_id, user_id=user_id)
    # Prefer Dify as source of truth for list
    convs = await get_conversations(ident.dify_user, system_id=ident.system_id)
    return [
        ConversationItem(
            id=c.get("id", ""),
            name=c.get("name"),
            created_at=c.get("created_at"),
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageItem])
async def list_messages(
    conversation_id: str,
    system_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    identity: ChatIdentity | None = Depends(get_identity_optional),
    api_key: str = Security(API_KEY_HEADER),
):
    ident = _resolve_identity(identity, None, api_key, system_id=system_id, user_id=user_id)
    messages = await get_conversation_messages(
        conversation_id, ident.dify_user, system_id=ident.system_id
    )
    return [
        MessageItem(
            id=m.get("id", ""),
            role=m.get("role", "user"),
            content=m.get("content") or (m.get("message") or ""),
            created_at=m.get("created_at"),
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_route(
    conversation_id: str,
    system_id: str = Query(..., description="System ID"),
    user_id: str = Query(..., description="User ID"),
    identity: ChatIdentity | None = Depends(get_identity_optional),
    api_key: str = Security(API_KEY_HEADER),
):
    ident = _resolve_identity(identity, None, api_key, system_id=system_id, user_id=user_id)
    try:
        await delete_conversation(
            conversation_id, ident.dify_user, system_id=ident.system_id
        )
    except httpx.HTTPStatusError as e:
        logger.warning("Dify delete conversation error: %s %s", e.response.status_code, conversation_id)
        raise HTTPException(
            status_code=min(e.response.status_code, 599),
            detail="Failed to delete conversation",
        )
    except httpx.RequestError as e:
        logger.warning("Dify delete request error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat service temporarily unavailable.",
        )


@router.post("/sync", response_model=dict)
async def post_sync(
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(API_KEY_HEADER),
):
    """Fetch conversations from Dify for users in ConversationMapping + SyncUser and store in SQLite. API Key required. Call periodically via cron etc."""
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    result = await sync_all_from_mapping(db)
    return result


@router.get("/chat-token", response_model=dict)
async def get_chat_token(
    request: Request,
    system_id: str = Query(..., description="System ID (e.g. drillquiz)"),
    user_id: str = Query("12345", description="User ID"),
    api_key: str = Security(API_KEY_HEADER),
):
    """Issue JWT for chat page. X-API-Key required."""
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    origins = settings.allowed_chat_token_origins_list
    if origins:
        origin = request.headers.get("origin") or request.headers.get("referer") or ""
        origin_base = origin.split("?")[0].rstrip("/")
        if not any(origin_base == o or origin_base.startswith(o + "/") for o in origins):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    get_identity_from_body(system_id, user_id)
    payload = {"system_id": system_id, "user_id": user_id, "exp": int(time.time()) + 86400}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    if hasattr(token, "decode"):
        token = token.decode("utf-8")
    return {"token": token}


@router.post("/sync/me", response_model=dict)
async def post_sync_me(
    token: str = Query(..., description="JWT (same as token query on chat page URL)"),
    db: AsyncSession = Depends(get_db),
):
    """Sync only the current user's (by token) Dify conversations to DB. Called via AJAX from chat page periodically or on close."""
    import logging
    from app.auth import decode_jwt
    from app.sync_service import sync_user_conversations
    ident = decode_jwt(token)
    logging.getLogger("chat_gateway").info("sync/me: system_id=%s user_id=%s", ident.system_id, ident.user_id)
    try:
        nc, nm = await sync_user_conversations(db, ident.system_id, ident.user_id, ident.dify_user)
        return {"conversations_synced": nc, "messages_synced": nm}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
