"""Application settings — loaded once from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "LMS Backend"
    environment: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://lms:lms@localhost:5432/lms"
    database_sync_url: str | None = None
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ── Redis (optional — disabled when unset) ────────────────────────────
    redis_url: str | None = None

    # ── Security / JWT ────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-please-32-bytes-minimum-secret"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    password_reset_ttl_seconds: int = 3_600

    # ── Rate limiting ─────────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"

    # ── Tenancy ───────────────────────────────────────────────────────────
    tenant_header: str = "X-Tenant-ID"
    enable_row_level_security: bool = True

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://lms-mf-es-shell.vercel.app"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic. Derive from async URL when not set."""
        if self.database_sync_url:
            return self.database_sync_url
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
