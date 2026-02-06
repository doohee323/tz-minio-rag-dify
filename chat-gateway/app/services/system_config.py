"""Allowed system_ids from DB (chat_systems). Loaded on startup. Fallback to env."""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_allowed_system_ids_cache: list[str] = []


async def refresh_allowed_systems() -> None:
    """Load enabled system_ids from chat_systems into cache. Called on startup."""
    global _allowed_system_ids_cache
    try:
        async with AsyncSessionLocal() as session:
            # ChatSystem table (same as chat-admin). Use raw SQL to avoid model dependency if table missing.
            result = await session.execute(
                text("SELECT system_id FROM chat_systems WHERE enabled")
            )
            rows = result.fetchall()
            _allowed_system_ids_cache = [r[0].strip().lower() for r in rows if r[0]]
            logger.info("Loaded allowed_system_ids from DB: %s", _allowed_system_ids_cache)
    except Exception as e:
        logger.warning("Could not load chat_systems from DB: %s. Using env fallback.", e)
        _allowed_system_ids_cache = []


def get_allowed_system_ids_list() -> list[str]:
    """Allowed system_ids. DB first, then env (ALLOWED_SYSTEM_IDS) fallback. Empty = allow all."""
    if _allowed_system_ids_cache:
        return _allowed_system_ids_cache
    return get_settings().allowed_system_ids_list
