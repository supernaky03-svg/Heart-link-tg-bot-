from __future__ import annotations

from app.locales.translations import t
from app.models.enums import Language
from app.services.storage import TelegramChannelStorage


def get_user_language(storage: TelegramChannelStorage, user_id: int) -> str:
    settings = storage.get_user_settings(user_id)
    if settings:
        return settings.language.value
    profile = storage.get_user_profile(user_id)
    if profile:
        return profile.language.value
    return storage.settings.default_language


def translate(storage: TelegramChannelStorage, user_id: int, key: str, **kwargs) -> str:
    return t(get_user_language(storage, user_id), key, **kwargs)
