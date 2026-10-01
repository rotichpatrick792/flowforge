"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values are read from environment variables or a .env file at the
    project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "FlowForge"
    app_env: Literal["dev", "test", "prod"] = "dev"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- Observability ---
    otel_enabled: bool = True
    otel_service_name: str = "flowforge-api"
    otel_exporter: Literal["console", "none"] = "console"

    # --- Placeholders for later phases ---
    database_url: str = Field(
        default="postgresql+asyncpg://flowforge:flowforge@localhost:5432/flowforge"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()
