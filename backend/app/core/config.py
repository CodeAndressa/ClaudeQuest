from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, carregada exclusivamente de variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ClaudeQuest"
    environment: Literal["development", "staging", "production", "test"] = "development"
    port: int = 8002
    app_url: str = "http://localhost:8002"
    frontend_url: str = "http://localhost:5180"

    database_url: str = Field(
        default="postgresql+asyncpg://claudequest:claudequest@localhost:5432/claudequest"
    )
    test_database_url: str = Field(
        default="postgresql+asyncpg://claudequest:claudequest@localhost:5432/claudequest_test"
    )

    jwt_secret: str = Field(default="change-me-in-env")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    ai_provider: str = "anthropic"
    anthropic_key: str = ""
    openrouter_key: str = ""

    smtp_host: str = ""
    smtp_user: str = ""
    smtp_password: str = ""

    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
