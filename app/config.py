from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    telegram_api_id: int = Field(alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(alias="TELEGRAM_API_HASH")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    private_db_channel_id: int = Field(alias="PRIVATE_DB_CHANNEL_ID")
    log_channel_id: Optional[int] = Field(default=None, alias="LOG_CHANNEL_ID")
    render_external_url: Optional[str] = Field(default=None, alias="RENDER_EXTERNAL_URL")
    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")
    debug: bool = Field(default=False, alias="DEBUG")
    bot_username: Optional[str] = Field(default=None, alias="BOT_USERNAME")
    discover_pass_ttl_hours: int = Field(default=48, alias="DISCOVER_PASS_TTL_HOURS")
    broadcast_delay_ms: int = Field(default=50, alias="BROADCAST_DELAY_MS")
    max_bio_length: int = Field(default=400, alias="MAX_BIO_LENGTH")
    max_name_length: int = Field(default=40, alias="MAX_NAME_LENGTH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return [int(p) for p in parts]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
