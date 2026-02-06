from typing import Annotated
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field, AliasChoices, BeforeValidator
from functools import lru_cache


def _parse_minio_port(v: str | int) -> int:
    """Handle K8s env: MINIO_PORT can be 'tcp://10.233.50.97:9000' or '9000'."""
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return 9000
    if ":" in s:
        return int(s.rsplit(":", 1)[-1])
    return int(s)


class Settings(BaseSettings):
    # Shared Dify (can leave empty if using only per-system)
    dify_base_url: str = ""
    dify_api_key: str = ""
    jwt_secret: str = Field(..., validation_alias="CHAT_GATEWAY_JWT_SECRET")
    api_keys: str = Field("", validation_alias=AliasChoices("CHAT_GATEWAY_API_KEYS", "CHAT_GATEWAY_API_KEY"))
    allowed_system_ids: str = ""
    # Allowed origins for /v1/chat-token (comma-separated). Empty = no check.
    allowed_chat_token_origins: str = ""
    # Origins allowed for /v1/chat-token-guest (no API key). Empty = localhost defaults.
    allow_guest_token_origins: str = Field("", validation_alias="ALLOW_GUEST_TOKEN_ORIGINS")
    # Explicit DATABASE_URL overrides. Otherwise: SQLite locally, PostgreSQL when POSTGRES_HOST is set (K8s).
    database_url: str = Field("", validation_alias="DATABASE_URL")
    postgres_host: str = Field("", validation_alias="POSTGRES_HOST")
    postgres_port: str = Field("5432", validation_alias="POSTGRES_PORT")
    postgres_db: str = Field("chat_gateway", validation_alias="POSTGRES_DB")
    postgres_user: str = Field("postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field("", validation_alias="POSTGRES_PASSWORD")

    @computed_field
    @property
    def effective_database_url(self) -> str:
        """SQLite locally, PostgreSQL on K8s (when POSTGRES_HOST is set)."""
        if self.database_url.strip():
            return self.database_url.strip()
        if self.postgres_host.strip():
            from urllib.parse import quote_plus
            pw = quote_plus(self.postgres_password) if self.postgres_password else ""
            return f"postgresql+asyncpg://{self.postgres_user}:{pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        return "sqlite+aiosqlite:///./chat_gateway.db"
    # Per-system Dify (empty = use shared dify_base_url / dify_api_key)
    dify_drillquiz_base_url: str = ""
    dify_drillquiz_api_key: str = ""
    dify_drillquiz_chatbot_token: str = ""
    dify_cointutor_base_url: str = ""
    dify_cointutor_api_key: str = ""
    dify_cointutor_chatbot_token: str = ""

    # MinIO for file upload: rag-docs/raw/{system_id}/filename
    minio_endpoint: str = Field("localhost", validation_alias="MINIO_ENDPOINT")
    minio_port: Annotated[int, BeforeValidator(_parse_minio_port)] = Field(
        9000, validation_alias="MINIO_PORT"
    )
    minio_bucket: str = Field("rag-docs", validation_alias="MINIO_BUCKET")
    minio_access_key: str = Field("", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("", validation_alias="MINIO_SECRET_KEY")
    minio_use_ssl: bool = Field(False, validation_alias="MINIO_USE_SSL")

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

    def get_dify_chatbot_token(self, system_id: str | None) -> str:
        """Dify Publish → 임베드 token (embed용). API 키와 다름."""
        if system_id:
            key = f"dify_{system_id.lower()}_chatbot_token"
            token = getattr(self, key, None) or ""
            if token.strip():
                return token.strip()
        return ""

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

    @property
    def allow_guest_token_origins_list(self) -> list[str]:
        if not self.allow_guest_token_origins.strip():
            return [
                "http://localhost:8080",
                "http://localhost:8000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8000",
            ]
        return [s.strip() for s in self.allow_guest_token_origins.split(",") if s.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
