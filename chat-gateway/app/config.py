from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Shared Dify (can leave empty if using only per-system)
    dify_base_url: str = ""
    dify_api_key: str = ""
    jwt_secret: str = Field(..., validation_alias="CHAT_GATEWAY_JWT_SECRET")
    api_keys: str = Field("", validation_alias="CHAT_GATEWAY_API_KEY")
    allowed_system_ids: str = ""
    # Allowed origins for /v1/chat-token (comma-separated). Empty = no check.
    allowed_chat_token_origins: str = ""
    database_url: str = "sqlite+aiosqlite:///./chat_gateway.db"
    dify_chatbot_token: str = ""
    # Per-system Dify (empty = use shared dify_base_url / dify_api_key)
    dify_drillquiz_base_url: str = ""
    dify_drillquiz_api_key: str = ""
    dify_cointutor_base_url: str = ""
    dify_cointutor_api_key: str = ""
    # Redirect root URL to chat-admin (default: http://localhost:8080)
    chat_admin_url: str = Field("http://localhost:8080", validation_alias="CHAT_ADMIN_URL")

    def get_dify_base_url(self, system_id: str | None) -> str:
        if system_id:
            key = f"dify_{system_id.lower()}_base_url"
            url = getattr(self, key, None) or ""
            if url.strip():
                return url.rstrip("/")
        return self.dify_base_url.rstrip("/")

    def get_dify_api_key(self, system_id: str | None) -> str:
        if system_id:
            key = f"dify_{system_id.lower()}_api_key"
            api_key = getattr(self, key, None) or ""
            if api_key.strip():
                return api_key.strip()
        return self.dify_api_key or ""

    @property
    def api_keys_list(self) -> list[str]:
        if not self.api_keys.strip():
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def allowed_system_ids_list(self) -> list[str]:
        if not self.allowed_system_ids.strip():
            return []
        return [s.strip() for s in self.allowed_system_ids.split(",") if s.strip()]

    @property
    def allowed_chat_token_origins_list(self) -> list[str]:
        if not self.allowed_chat_token_origins.strip():
            return []
        return [s.strip() for s in self.allowed_chat_token_origins.split(",") if s.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
