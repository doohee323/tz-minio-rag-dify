import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import cache_view, chat, chat_page, debug, index

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
    logger.info("Chat Gateway ready")
    yield


app = FastAPI(title="Chat Gateway", description="Chat gateway in front of Dify", lifespan=lifespan)

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
    "http://localhost:8088",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8088",
]
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]
CORS_ALLOW_HEADERS = ["X-API-Key", "Content-Type", "Authorization", "Accept"]

# Merge default domains with env extra list so all are allowed (env-only would omit us-dev etc.)
_origins_extra = get_settings().allowed_chat_token_origins_list
cors_origins = list(CORS_ORIGINS_DEFAULT)
for o in _origins_extra:
    if o and o not in cors_origins:
        cors_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=[],
)
app.add_middleware(RequestLogMiddleware)
app.include_router(index.router)
app.include_router(chat.router)
app.include_router(chat_page.router)
app.include_router(cache_view.router)
app.include_router(debug.router)
