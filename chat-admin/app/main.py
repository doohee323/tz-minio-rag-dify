import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import admin_auth, cache_view, debug, sample, systems
from app.services.system_config import get_allowed_origins_extra, refresh_systems_cache

# Ensure app logs appear in terminal even with uvicorn --reload (force=True overrides existing config)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger("chat_gateway")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        client = request.client.host if request.client else "-"
        line = f"{request.method} {request.url.path} {response.status_code} {client}"
        logger.info("%s %s %s %s", request.method, request.url.path, response.status_code, client)
        print(f"[request] {line}", file=sys.stderr, flush=True)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await refresh_systems_cache()
    logger.info("TZ-Chat Admin ready")
    yield


app = FastAPI(title="TZ-Chat Gateway", description="TZ-Chat Gateway in front of Dify", lifespan=lifespan)

# CORS: required for frontends (e.g. DrillQuiz) calling /v1/chat-token. OPTIONS preflight + X-API-Key allowed.
CORS_ORIGINS_DEFAULT = [
    "https://us-dev.drillquiz.com",
    "https://us.drillquiz.com",
    "https://us-qa.drillquiz.com",
    "https://devops.drillquiz.com",
    "https://leetcode.drillquiz.com",
    "https://cointutor.net",
    "https://www.cointutor.net",
    "https://dev.cointutor.net",
    "https://qa.cointutor.net",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_METHODS = ["GET", "POST", "DELETE", "OPTIONS", "PATCH"]
CORS_ALLOW_HEADERS = ["X-API-Key", "Content-Type", "Authorization", "Accept"]

def _build_cors_origins() -> list[str]:
    cors = list(CORS_ORIGINS_DEFAULT)
    for o in get_settings().allowed_chat_token_origins_list:
        if o and o not in cors:
            cors.append(o)
    for o in get_allowed_origins_extra():
        if o and o not in cors:
            cors.append(o)
    return cors


app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=[],
)
app.add_middleware(RequestLogMiddleware)

# API routers first (before static mount)
app.include_router(admin_auth.router)
app.include_router(sample.router)
app.include_router(systems.router)
app.include_router(cache_view.router)
app.include_router(debug.router)

# Vue SPA: static files (html=True serves 404.html for 404; copy index.html to 404.html at build time for SPA fallback)
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    # Ensure 404.html exists for SPA fallback (StaticFiles html=True serves it on 404)
    _index = _static_dir / "index.html"
    _404 = _static_dir / "404.html"
    if _index.exists() and not _404.exists():
        import shutil
        shutil.copy(_index, _404)
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
