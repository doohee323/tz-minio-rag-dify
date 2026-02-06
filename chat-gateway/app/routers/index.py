"""Root route: redirect to chat-admin."""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.config import get_settings

router = APIRouter()


@router.get("/")
async def index_page():
    """Redirect root to chat-admin."""
    url = get_settings().chat_admin_url.rstrip("/")
    return RedirectResponse(url=url, status_code=302)
