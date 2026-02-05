"""Root route: project introduction page for chat.drillquiz.com."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Serve the project introduction page at the root URL."""
    return templates.TemplateResponse("index.html", {"request": request})
