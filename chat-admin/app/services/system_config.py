"""In-memory cache of ChatSystem config. Refreshed at startup and on write."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import ChatSystem

# Cache: list of dicts with system_id, display_name, dify_base_url, dify_api_key, dify_chatbot_token, allowed_origins, enabled
_systems_cache: list[dict] = []


async def refresh_systems_cache() -> None:
    """Load ChatSystems from DB into cache."""
    global _systems_cache
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ChatSystem).where(ChatSystem.enabled == True))
        rows = result.scalars().all()
        _systems_cache = [
            {
                "system_id": r.system_id,
                "display_name": r.display_name,
                "dify_base_url": (r.dify_base_url or "").strip().rstrip("/"),
                "dify_api_key": (r.dify_api_key or "").strip(),
                "dify_chatbot_token": (r.dify_chatbot_token or "").strip(),
                "allowed_origins": (r.allowed_origins or "").strip(),
                "enabled": r.enabled,
            }
            for r in rows
        ]


def _get_system(system_id: str | None) -> dict | None:
    if not system_id:
        return None
    sid = system_id.lower().strip()
    for s in _systems_cache:
        if s["system_id"].lower() == sid:
            return s
    return None


def get_dify_base_url(system_id: str | None) -> str:
    """Dify base URL for system. DB first, then env fallback."""
    s = _get_system(system_id)
    if s and s["dify_base_url"]:
        return s["dify_base_url"]
    return (get_settings().get_dify_base_url(system_id) or "").strip().rstrip("/")


def get_dify_api_key(system_id: str | None) -> str:
    """Dify API key for system. DB first, then env fallback."""
    s = _get_system(system_id)
    if s and s["dify_api_key"]:
        return s["dify_api_key"]
    return (get_settings().get_dify_api_key(system_id) or "").strip()


def get_api_keys_list() -> list[str]:
    """All valid API keys. From .env only (CHAT_GATEWAY_API_KEYS) - shared across systems."""
    return get_settings().api_keys_list


def get_dify_chatbot_token(system_id: str | None) -> str:
    """Dify embed token for chat page. DB first, then env (DIFY_<system>_CHATBOT_TOKEN)."""
    s = _get_system(system_id)
    if s and s.get("dify_chatbot_token"):
        return s["dify_chatbot_token"]
    return get_settings().get_dify_chatbot_token(system_id) or ""


def get_allowed_system_ids_list() -> list[str]:
    """Allowed system_ids. Empty = allow all. DB systems first."""
    ids = [s["system_id"] for s in _systems_cache if s["system_id"]]
    if ids:
        return ids
    return get_settings().allowed_system_ids_list


def get_systems_for_status() -> dict[str, dict]:
    """Return {system_id: {configured, has_base_url, has_api_key}} for status endpoint."""
    result = {}
    for s in _systems_cache:
        sid = s["system_id"]
        base = s.get("dify_base_url") or ""
        key = s.get("dify_api_key") or ""
        result[sid] = {"configured": bool(base and key), "has_base_url": bool(base), "has_api_key": bool(key)}
    if not result:
        settings = get_settings()
        for sid in ("drillquiz", "cointutor"):
            base = (settings.get_dify_base_url(sid) or "").strip()
            key = (settings.get_dify_api_key(sid) or "").strip()
            result[sid] = {"configured": bool(base and key), "has_base_url": bool(base), "has_api_key": bool(key)}
    return result


def get_allowed_origins_extra() -> list[str]:
    """Extra CORS origins from ChatSystems (allowed_origins, comma-separated)."""
    extra: list[str] = []
    for s in _systems_cache:
        for o in (s.get("allowed_origins") or "").split(","):
            o = o.strip()
            if o and o not in extra:
                extra.append(o)
    return extra
