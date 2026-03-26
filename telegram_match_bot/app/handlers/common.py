from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import username_recheck_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.app_context import AppContext
from app.services.guards import can_use_bot, has_username


async def send_main_menu(message: Message, app: AppContext, user: dict[str, Any]) -> None:
    language = user.get("language", app.settings.default_language)
    await message.answer(
        app.i18n.t(language, "main_menu_hint"),
        reply_markup=main_menu_keyboard(app.i18n, language),
    )


async def ensure_allowed_message(message: Message, app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> bool:
    allowed, reason_key = await can_use_bot(app, user, admin_bypass=admin_bypass)
    if not allowed and reason_key:
        await message.answer(app.i18n.t(user.get("language"), reason_key))
        return False
    return True


async def ensure_allowed_callback(callback: CallbackQuery, app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> bool:
    allowed, reason_key = await can_use_bot(app, user, admin_bypass=admin_bypass)
    if not allowed and reason_key:
        await callback.answer(app.i18n.t(user.get("language"), reason_key), show_alert=True)
        return False
    return True


async def ensure_username_or_prompt(message: Message, app: AppContext, user: dict[str, Any]) -> bool:
    language = user.get("language")
    if has_username(user):
        return True
    await message.answer(
        app.i18n.t(language, "username_required"),
        reply_markup=username_recheck_keyboard(app.i18n, language),
    )
    return False
