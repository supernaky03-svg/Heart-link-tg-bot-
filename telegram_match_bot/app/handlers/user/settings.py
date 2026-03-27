from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt
from app.handlers.user.profile import begin_profile_setup
from app.keyboards.inline import language_keyboard, settings_keyboard, username_recheck_keyboard
from app.services.app_context import AppContext


router = Router(name="user_settings")


@router.message(Command("settings"))
async def command_settings(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    await message.answer(
        app.i18n.t(db_user.get("language"), "settings_title"),
        reply_markup=settings_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(F.data == "settings:language")
async def settings_language(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    await callback.answer()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "choose_language"), reply_markup=language_keyboard(app.i18n))


@router.callback_query(F.data == "settings:edit_profile")
async def settings_edit_profile(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    if not await ensure_username_or_prompt(callback.message, app, db_user):
        return
    await callback.answer()
    await begin_profile_setup(callback.message, app, db_user, state, restart=True)


@router.callback_query(F.data == "settings:recheck_username")
async def settings_recheck_username(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    refreshed = await app.users.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language=db_user.get("language", app.settings.default_language),
        is_admin=callback.from_user.id in app.settings.admin_ids,
    )
    await callback.answer()
    if refreshed.get("username"):
        await callback.message.answer(app.i18n.t(refreshed.get("language"), "welcome"))
        return
    await callback.message.answer(
        app.i18n.t(refreshed.get("language"), "username_required"),
        reply_markup=username_recheck_keyboard(app.i18n, refreshed.get("language")),
    )


@router.callback_query(F.data == "settings:toggle_notifications")
async def settings_toggle_notifications(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    enabled = not bool(db_user.get("notification_matches"))
    await app.users.set_notification_matches(callback.from_user.id, enabled)
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "notifications_on" if enabled else "notifications_off")
    )
