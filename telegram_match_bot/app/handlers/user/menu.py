from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.common import ensure_allowed_message
from app.filters.admin import AdminFilter
from app.handlers.user.browse import command_browse
from app.handlers.user.matches import command_matches
from app.handlers.user.profile import command_profile
from app.handlers.user.settings import command_settings
from app.handlers.user.start import command_help
from app.services.app_context import AppContext


router = Router(name="user_menu")


@router.message(Command("admin"), ~AdminFilter())
async def admin_denied(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if db_user.get("is_admin"):
        return
    await message.answer(app.i18n.t(db_user.get("language"), "admin_only"))


@router.message()
async def menu_router(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    text = (message.text or "").strip()
    labels = app.i18n.localized_menu_labels()
    if text in labels["browse_profiles"]:
        await command_browse(message, app, db_user)
        return
    if text in labels["my_profile"]:
        await command_profile(message, app, db_user)
        return
    if text in labels["my_matches"]:
        await command_matches(message, app, db_user)
        return
    if text in labels["settings"]:
        await command_settings(message, app, db_user)
        return
    if text in labels["help"]:
        await command_help(message, app, db_user)
        return
    await message.answer(app.i18n.t(db_user.get("language"), "unsupported_message"))


@router.callback_query()
async def fallback_callback(callback, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
