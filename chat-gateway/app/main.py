import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import cache_view, chat, chat_page, debug

# uvicorn --reload 시에도 앱 로그가 터미널에 보이도록 설정 (force=True로 기존 설정 덮음)
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
        # 호출 후 터미널에 반드시 보이도록 flush
        print(f"[요청] {line}", file=sys.stderr, flush=True)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Chat Gateway ready")
    yield


app = FastAPI(title="Chat Gateway", description="Dify 앞단 채팅 게이트웨이", lifespan=lifespan)
origins = get_settings().allowed_chat_token_origins_list
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
app.add_middleware(RequestLogMiddleware)
app.include_router(chat.router)
app.include_router(chat_page.router)
app.include_router(cache_view.router)
app.include_router(debug.router)
