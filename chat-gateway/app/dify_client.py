import logging

import httpx
from app.config import get_settings

logger = logging.getLogger("chat_gateway")


def _base_url(system_id: str | None = None) -> str:
    url = get_settings().get_dify_base_url(system_id)
    return f"{url}/v1"


def _headers(system_id: str | None = None) -> dict:
    return {
        "Authorization": f"Bearer {get_settings().get_dify_api_key(system_id)}",
        "Content-Type": "application/json",
    }


def _log_dify_error(method: str, url: str, status: int, body: str | bytes) -> None:
    try:
        text = body.decode("utf-8") if isinstance(body, bytes) else body
    except Exception:
        text = str(body)[:500]
    logger.warning(
        "Dify API error: %s %s -> %s | body: %s",
        method,
        url,
        status,
        text[:300] if text else "",
    )


async def send_chat_message(
    user: str,
    query: str,
    conversation_id: str | None = None,
    inputs: dict | None = None,
    response_mode: str = "blocking",
    system_id: str | None = None,
) -> dict:
    body = {
        "inputs": inputs or {},
        "query": query,
        "response_mode": response_mode,
        "user": user,
    }
    if conversation_id:
        body["conversation_id"] = conversation_id
    url = f"{_base_url(system_id)}/chat-messages"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=body, headers=_headers(system_id))
        if r.status_code >= 400:
            _log_dify_error("POST", url, r.status_code, r.content)
        r.raise_for_status()
        return r.json()


async def get_conversations(user: str, system_id: str | None = None) -> list[dict]:
    url = f"{_base_url(system_id)}/conversations"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params={"user": user}, headers=_headers(system_id))
        if r.status_code >= 400:
            _log_dify_error("GET", url, r.status_code, r.content)
        r.raise_for_status()
        data = r.json()
        return data.get("data", []) or []


async def delete_conversation(
    conversation_id: str, user: str, system_id: str | None = None
) -> None:
    url = f"{_base_url(system_id)}/conversations/{conversation_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.request(
            "DELETE",
            url,
            json={"user": user},
            headers=_headers(system_id),
        )
        if r.status_code >= 400:
            _log_dify_error("DELETE", url, r.status_code, r.content)
        r.raise_for_status()


async def get_conversation_messages(
    conversation_id: str, user: str, system_id: str | None = None
) -> list[dict]:
    url = f"{_base_url(system_id)}/messages"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            params={"conversation_id": conversation_id, "user": user},
            headers=_headers(system_id),
        )
        if r.status_code >= 400:
            _log_dify_error("GET", url, r.status_code, r.content)
        r.raise_for_status()
        data = r.json()
        return data.get("data", []) or []
