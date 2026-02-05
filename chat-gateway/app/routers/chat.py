import time
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from sqlalchemy import select
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import API_KEY_HEADER, get_identity_from_body, get_identity_optional, ChatIdentity
from app.config import get_settings
from app.dify_client import get_conversation_messages, get_conversations, send_chat_message
from app.models import ConversationMapping
from app.schemas import ChatRequest, ChatResponse, ConversationItem, MessageItem
from app.sync_service import record_chat_to_db, sync_all_from_mapping

router = APIRouter(prefix="/v1", tags=["chat"])

# 위젯 셸(헤더·토글) 다국어. chat-gateway가 채팅 앱 전체 다국어 담당.
CHAT_UI_STRINGS = {
    "en": {"title": "Chat", "close": "Close", "open": "Open chat", "tokenError": "Could not load chat token.", "loading": "Loading..."},
    "es": {"title": "Chat", "close": "Cerrar", "open": "Abrir chat", "tokenError": "No se pudo cargar el token del chat.", "loading": "Cargando..."},
    "ko": {"title": "채팅", "close": "닫기", "open": "채팅 열기", "tokenError": "채팅 토큰을 불러오지 못했습니다.", "loading": "로딩 중..."},
    "zh": {"title": "聊天", "close": "关闭", "open": "打开聊天", "tokenError": "无法加载聊天令牌。", "loading": "加载中..."},
    "ja": {"title": "チャット", "close": "閉じる", "open": "チャットを開く", "tokenError": "チャットトークンを読み込めませんでした。", "loading": "読み込み中..."},
}
CHAT_UI_LANGS = frozenset(CHAT_UI_STRINGS)


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
    # Use body for message/conversation_id; identity for user
    result = await send_chat_message(
        user=ident.dify_user,
        query=body.message,
        conversation_id=body.conversation_id,
        inputs=body.inputs,
        system_id=ident.system_id,
    )
    conversation_id = result.get("conversation_id") or ""
    message_id = result.get("message_id")
    answer = result.get("answer", "")
    if conversation_id:
        # 매핑 저장 (sync 대상)
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
        # 채팅 한 건을 SQLite에 바로 기록 (별도 sync 없이)
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


@router.post("/sync", response_model=dict)
async def post_sync(
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(API_KEY_HEADER),
):
    """ConversationMapping + SyncUser에 있는 사용자들의 대화를 Dify에서 가져와 SQLite에 저장. API Key 필요. cron 등으로 주기 호출."""
    settings = get_settings()
    if not api_key or (settings.api_keys_list and api_key not in settings.api_keys_list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    result = await sync_all_from_mapping(db)
    return result


@router.get("/chat-token", response_model=dict)
async def get_chat_token(
    request: Request,
    system_id: str = Query(..., description="시스템 ID (예: drillquiz)"),
    user_id: str = Query("12345", description="사용자 ID"),
    lang: str = Query("", description="위젯/채팅 UI 언어. en|es|ko|zh|ja, 없으면 응답에 ui 없음"),
    api_key: str = Security(API_KEY_HEADER),
):
    """채팅 페이지용 JWT 발급. X-API-Key 필요. lang 있으면 응답에 ui(위젯 셸 문구) 포함."""
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
    out = {"token": token}
    if lang and lang.strip().lower() in CHAT_UI_LANGS:
        out["ui"] = CHAT_UI_STRINGS[lang.strip().lower()]
    return out


@router.post("/sync/me", response_model=dict)
async def post_sync_me(
    token: str = Query(..., description="JWT (채팅 페이지 URL의 token 쿼리와 동일)"),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자(토큰 기준)의 Dify 대화만 DB로 동기화. 채팅 페이지에서 주기·종료 시 AJAX로 호출."""
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
