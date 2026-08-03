"""Environment-backed application configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings for the private TITAN service."""

    model_config = SettingsConfigDict(
        env_prefix="TITAN_",
        env_file=".env",
        extra="forbid",
        frozen=True,
    )

    admin_telegram_ids: frozenset[int] = Field(min_length=1)
