from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.locales.translations import t
from app.models.enums import Language


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="English")],
            [KeyboardButton(text="မြန်မာ")],
            [KeyboardButton(text="Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def gender_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_male"))],
            [KeyboardButton(text=t(lang, "btn_female"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def looking_for_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_men"))],
            [KeyboardButton(text=t(lang, "btn_women"))],
            [KeyboardButton(text=t(lang, "btn_everyone"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_location"), request_location=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def media_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_add_more")), KeyboardButton(text=t(lang, "btn_done_save"))],
            [KeyboardButton(text=t(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
    )


def yes_edit_cancel_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_yes")), KeyboardButton(text=t(lang, "btn_edit"))],
            [KeyboardButton(text=t(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "menu_discover")), KeyboardButton(text=t(lang, "menu_profile"))],
            [KeyboardButton(text=t(lang, "menu_premium")), KeyboardButton(text=t(lang, "menu_language"))],
            [KeyboardButton(text=t(lang, "menu_complain")), KeyboardButton(text=t(lang, "menu_help"))],
        ],
        resize_keyboard=True,
    )


def skip_keyboard(lang: str | Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_skip"))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
