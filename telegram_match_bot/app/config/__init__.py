from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet

from dotenv import load_dotenv


load_dotenv()


TRUE_VALUES = {"1", "true", "yes", "on"}


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


@dataclass(slots=True, frozen=True)
class Settings:
    bot_token: str
    database_url: str
    admin_ids: FrozenSet[int]
    bot_username: str
    port: int
    host: str
    use_webhook: bool
    webhook_base_url: str
    webhook_path: str
    default_language: str
    log_level: str
    max_bio_length: int
    max_nickname_length: int
    max_interests_length: int

    @property
    def webhook_url(self) -> str:
        base = self.webhook_base_url.rstrip("/")
        if not base:
            return ""
        return f"{base}{self.webhook_path}"



def load_settings() -> Settings:
    admin_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = frozenset(
        int(chunk.strip())
        for chunk in admin_raw.split(",")
        if chunk.strip().isdigit()
    )

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        admin_ids=admin_ids,
        bot_username=os.getenv("BOT_USERNAME", "").strip(),
        port=int(os.getenv("PORT", "10000")),
        host=os.getenv("HOST", "0.0.0.0"),
        use_webhook=_to_bool(os.getenv("USE_WEBHOOK"), False),
        webhook_base_url=os.getenv("WEBHOOK_BASE_URL", "").strip(),
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook",
        default_language=os.getenv("DEFAULT_LANGUAGE", "en").strip() or "en",
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_bio_length=int(os.getenv("MAX_BIO_LENGTH", "280")),
        max_nickname_length=int(os.getenv("MAX_NICKNAME_LENGTH", "32")),
        max_interests_length=int(os.getenv("MAX_INTERESTS_LENGTH", "120")),
    )
