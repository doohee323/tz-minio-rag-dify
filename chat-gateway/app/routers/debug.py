"""Dify 연동 디버그용. 배포 환경에서는 비활성화 권장."""
import httpx
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/dify-test")
async def dify_test():
    """Dify API를 직접 호출해 요청 URL·상태·응답 본문을 그대로 반환."""
    s = get_settings()
    base = s.dify_base_url.rstrip("/")
    url = f"{base}/v1/conversations"
    headers = {
        "Authorization": f"Bearer {s.dify_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params={"user": "debug_test_user"}, headers=headers)
        body = r.text
        try:
            body = r.json()
        except Exception:
            pass
        return {
            "request_url": url,
            "request_headers": {k: ("***" if k.lower() == "authorization" else v) for k, v in headers.items()},
            "status_code": r.status_code,
            "response_body": body,
        }
    except Exception as e:
        return {
            "request_url": url,
            "error": str(e),
            "status_code": None,
            "response_body": None,
        }
