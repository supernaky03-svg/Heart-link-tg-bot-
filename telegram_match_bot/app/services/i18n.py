from __future__ import annotations

from typing import Any

from app.locales.en import MESSAGES as EN_MESSAGES
from app.locales.my import MESSAGES as MY_MESSAGES

SUPPORTED_LANGUAGES = {"en", "my"}

TRANSLATIONS = {
    "en": EN_MESSAGES,
    "my": MY_MESSAGES,
}


class I18n:
    def __init__(self, default_language: str = "en") -> None:
        self.default_language = default_language if default_language in SUPPORTED_LANGUAGES else "en"

    def t(self, language: str | None, key: str, **kwargs: Any) -> str:
        lang = language if language in SUPPORTED_LANGUAGES else self.default_language
        template = TRANSLATIONS.get(lang, TRANSLATIONS[self.default_language]).get(key)
        if template is None:
            template = TRANSLATIONS[self.default_language].get(key, key)
        return template.format(**kwargs)

    def available_languages(self) -> list[tuple[str, str]]:
        return [(code, TRANSLATIONS[code]["lang_name"]) for code in ["en", "my"]]

    def localized_menu_labels(self) -> dict[str, set[str]]:
        keys = ["browse_profiles", "my_profile", "my_matches", "settings", "help"]
        result: dict[str, set[str]] = {key: set() for key in keys}
        for _, messages in TRANSLATIONS.items():
            for key in keys:
                result[key].add(messages[key])
        return result
