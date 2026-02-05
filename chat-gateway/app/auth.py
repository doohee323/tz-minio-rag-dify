import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER = HTTPBearer(auto_error=False)


class ChatIdentity:
    def __init__(self, system_id: str, user_id: str):
        self.system_id = system_id
        self.user_id = user_id

    @property
    def dify_user(self) -> str:
        return f"{self.system_id}_{self.user_id}"


def _check_system_id(system_id: str) -> None:
    settings = get_settings()
    if not settings.allowed_system_ids_list:
        return
    if system_id not in settings.allowed_system_ids_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="system_id not allowed")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> ChatIdentity | None:
    if not api_key:
        return None
    settings = get_settings()
    if not settings.api_keys_list:
        return None
    if api_key not in settings.api_keys_list:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    # API key alone doesn't carry system_id/user_id; they must come from body/query. Return None and let route require body.
    return None


def decode_jwt(token: str) -> ChatIdentity:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature. Ensure server CHAT_GATEWAY_JWT_SECRET matches the value used when issuing the token. Try issuing a new token after restarting the server.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    system_id = payload.get("system_id")
    user_id = payload.get("user_id")
    if not system_id or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token must contain system_id and user_id")
    _check_system_id(system_id)
    return ChatIdentity(system_id=system_id, user_id=str(user_id))


async def get_identity_optional(
    api_key: str = Security(API_KEY_HEADER),
    bearer: HTTPAuthorizationCredentials | None = Security(BEARER),
) -> ChatIdentity | None:
    """If JWT: return identity. If API Key: None (use system_id/user_id from body)."""
    if bearer:
        return decode_jwt(bearer.credentials)
    if api_key:
        settings = get_settings()
        if settings.api_keys_list and api_key in settings.api_keys_list:
            return None
        if settings.api_keys_list:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return None


def get_identity_from_body(system_id: str, user_id: str) -> ChatIdentity:
    _check_system_id(system_id)
    return ChatIdentity(system_id=system_id, user_id=user_id)
