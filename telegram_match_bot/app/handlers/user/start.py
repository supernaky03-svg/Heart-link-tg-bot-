from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import language_keyboard, username_recheck_keyboard
from app.services.app_context import AppContext
from app.handlers.user.profile import begin_profile_setup


router = Router(name="user_start")


@router.message(CommandStart())
async def command_start(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    user = db_user
    if not user.get("language_chosen"):
        await message.answer(app.i18n.t("en", "choose_language"), reply_markup=language_keyboard(app.i18n))
        return

    await message.answer(app.i18n.t(user["language"], "welcome"))
    if not await ensure_allowed_message(message, app, user):
        return
    if not await ensure_username_or_prompt(message, app, user):
        return
    if not user.get("is_profile_complete"):
        await message.answer(app.i18n.t(user["language"], "start_profile"))
        await begin_profile_setup(message, app, user, state, restart=True)
        return
    await send_main_menu(message, app, user)


@router.message(Command("language"))
async def command_language(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    await message.answer(app.i18n.t(db_user.get("language"), "choose_language"), reply_markup=language_keyboard(app.i18n))


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in {"en", "my"}:
        await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
        return
    await app.users.update_language(callback.from_user.id, language)
    user = await app.users.get_by_telegram_id(callback.from_user.id)
    await callback.answer(app.i18n.t(language, "language_updated"))
    if user is None:
        return
    if not await ensure_allowed_callback(callback, app, user):
        return
    await callback.message.answer(app.i18n.t(language, "welcome"))
    if not await ensure_username_or_prompt(callback.message, app, user):
        return
    if not user.get("is_profile_complete"):
        await callback.message.answer(app.i18n.t(language, "start_profile"))
        await begin_profile_setup(callback.message, app, user, state, restart=True)
        return
    await send_main_menu(callback.message, app, user)


@router.callback_query(F.data == "recheck_username")
async def recheck_username(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    user = await app.users.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language=db_user.get("language", app.settings.default_language),
        is_admin=callback.from_user.id in app.settings.admin_ids,
    )
    language = user.get("language")
    if not user.get("username"):
        await callback.answer(app.i18n.t(language, "username_still_missing"), show_alert=True)
        return
    await callback.answer()
    if not user.get("is_profile_complete"):
        await callback.message.answer(app.i18n.t(language, "start_profile"))
        await begin_profile_setup(callback.message, app, user, state, restart=True)
        return
    await send_main_menu(callback.message, app, user)


@router.message(Command("help"))
async def command_help(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    await message.answer(app.i18n.t(db_user.get("language"), "help_text"))
