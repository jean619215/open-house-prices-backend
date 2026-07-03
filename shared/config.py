"""Application configuration using pydantic-settings.

All settings are loaded from environment variables (via .env file).
No secrets or connection strings may be hardcoded here.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields are required unless a default is provided. Missing required
    fields cause a ValidationError at startup, giving a clear error message.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # Redis
    redis_url: str

    # Security
    secret_key: str

    # Application
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings: The application settings instance.

    Raises:
        ValidationError: If required environment variables are missing.
    """
    settings = Settings()  # type: ignore[call-arg]
    logger.info("Settings loaded, environment=%s", settings.environment)
    return settings
