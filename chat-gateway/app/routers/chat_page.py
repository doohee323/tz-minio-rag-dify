import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_jwt
from app.database import get_db
from app.sync_service import register_sync_user
from app.templates import templates

router = APIRouter(tags=["chat-page"])
logger = logging.getLogger("chat_gateway")

CHAT_ALLOWED_LANGS = frozenset({"en", "es", "ko", "zh", "ja"})


def _normalize_lang(lang: str | None) -> str | None:
    if not lang or not isinstance(lang, str):
        return None
    v = lang.strip().lower()[:5]
    return v if v in CHAT_ALLOWED_LANGS else None


def _render_chat_page(
    request: Request, token: str, identity, embed: bool = False, lang: str | None = None
) -> HTMLResponse:
    return templates.TemplateResponse(
        "chat_api.html",
        {
            "request": request,
            "token": token,
            "system_id": identity.system_id,
            "user_id": identity.user_id,
            "embed": embed,
            "lang": _normalize_lang(lang) or "",
        },
    )


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    token: str = "",
    embed: str = "",
    lang: str = "",
    db: AsyncSession = Depends(get_db),
):
    """채팅 페이지. embed=1 위젯용. lang= en|es|ko|zh|ja 넘기면 해당 언어, 없으면 브라우저 언어 폴백."""
    if not token:
        logger.warning("GET /chat: missing token")
        return HTMLResponse(
            content="<html><body><p>Missing <code>token</code> query parameter (JWT).</p></body></html>",
            status_code=400,
        )
    try:
        identity = decode_jwt(token)
    except HTTPException as e:
        return HTMLResponse(content=f"<html><body><p>{e.detail}</p></body></html>", status_code=e.status_code)
    await register_sync_user(db, identity.system_id, identity.user_id, identity.dify_user)
    logger.info("GET /chat: system_id=%s user_id=%s", identity.system_id, identity.user_id)
    return _render_chat_page(request, token, identity, embed=(embed == "1"), lang=lang or None)


@router.get("/chat-api", response_class=HTMLResponse)
async def chat_api_page(
    request: Request,
    token: str = "",
    embed: str = "",
    lang: str = "",
    db: AsyncSession = Depends(get_db),
):
    """채팅 페이지 (동일). embed=1 위젯용. lang= en|es|ko|zh|ja."""
    if not token:
        return HTMLResponse(
            content="<html><body><p>Missing <code>token</code> query parameter (JWT).</p></body></html>",
            status_code=400,
        )
    try:
        identity = decode_jwt(token)
    except HTTPException as e:
        return HTMLResponse(content=f"<html><body><p>{e.detail}</p></body></html>", status_code=e.status_code)
    await register_sync_user(db, identity.system_id, identity.user_id, identity.dify_user)
    logger.info("GET /chat-api: system_id=%s user_id=%s", identity.system_id, identity.user_id)
    return _render_chat_page(request, token, identity, embed=(embed == "1"), lang=lang or None)
