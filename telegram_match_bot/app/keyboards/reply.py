from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.services.i18n import I18n


def main_menu_keyboard(i18n: I18n, language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.t(language, "browse_profiles"))],
            [
                KeyboardButton(text=i18n.t(language, "my_profile")),
                KeyboardButton(text=i18n.t(language, "my_matches")),
            ],
            [
                KeyboardButton(text=i18n.t(language, "settings")),
                KeyboardButton(text=i18n.t(language, "help")),
            ],
        ],
        resize_keyboard=True,
    )
