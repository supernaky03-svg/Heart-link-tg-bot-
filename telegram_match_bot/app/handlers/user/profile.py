from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import (
    photo_skip_keyboard,
    profile_confirm_keyboard,
    profile_gender_keyboard,
    profile_interest_keyboard,
)
from app.services.app_context import AppContext
from app.utils.formatters import profile_card
from app.utils.states import ProfileSetup
from app.utils.validators import parse_interests, validate_age, validate_bio, validate_nickname, validate_region


router = Router(name="user_profile")


async def begin_profile_setup(message: Message, app: AppContext, user: dict[str, Any], state: FSMContext, restart: bool = False) -> None:
    if restart:
        await state.clear()
    await state.set_state(ProfileSetup.nickname)
    await message.answer(app.i18n.t(user.get("language"), "ask_nickname"))


@router.message(Command("profile"))
async def command_profile(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not db_user.get("is_profile_complete"):
        await message.answer(app.i18n.t(db_user.get("language"), "profile_incomplete"))
        return
    await message.answer(profile_card(db_user))


@router.message(Command("editprofile"))
async def command_edit_profile(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not await ensure_username_or_prompt(message, app, db_user):
        return
    await begin_profile_setup(message, app, db_user, state, restart=True)


@router.message(ProfileSetup.nickname)
async def profile_nickname(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    nickname = (message.text or "").strip()
    if not validate_nickname(nickname, max_len=app.settings.max_nickname_length):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_nickname"))
        return
    await state.update_data(nickname=nickname)
    await state.set_state(ProfileSetup.age)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_age"))


@router.message(ProfileSetup.age)
async def profile_age(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    age = validate_age(message.text or "")
    if age is None:
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_age"))
        return
    await state.update_data(age=age)
    await state.set_state(ProfileSetup.gender)
    await message.answer(
        app.i18n.t(db_user.get("language"), "ask_gender"),
        reply_markup=profile_gender_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.gender, F.data.startswith("profile_gender:"))
async def profile_gender(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    await state.set_state(ProfileSetup.interested_in)
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "ask_interested_in"),
        reply_markup=profile_interest_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.interested_in, F.data.startswith("profile_interest:"))
async def profile_interest(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    interested_in = callback.data.split(":", 1)[1]
    await state.update_data(interested_in=interested_in)
    await state.set_state(ProfileSetup.region)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "ask_region"))


@router.message(ProfileSetup.region)
async def profile_region(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    region = (message.text or "").strip()
    if not validate_region(region):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_region"))
        return
    await state.update_data(region=region)
    await state.set_state(ProfileSetup.bio)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_bio"))


@router.message(ProfileSetup.bio)
async def profile_bio(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    bio = (message.text or "").strip()
    if not validate_bio(bio, max_len=app.settings.max_bio_length):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_bio"))
        return
    await state.update_data(bio=bio)
    await state.set_state(ProfileSetup.interests)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_interests"))


@router.message(ProfileSetup.interests)
async def profile_interests(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    interests = parse_interests(message.text or "")
    if not interests:
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_interests"))
        return
    await state.update_data(interests=interests)
    await state.set_state(ProfileSetup.photo)
    await message.answer(
        app.i18n.t(db_user.get("language"), "ask_photo"),
        reply_markup=photo_skip_keyboard(app.i18n, db_user.get("language")),
    )


@router.message(ProfileSetup.photo, F.photo)
async def profile_photo(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(profile_photo_file_id=photo.file_id)
    await show_profile_confirmation(message, app, db_user, state)


@router.callback_query(ProfileSetup.photo, F.data == "profile_skip_photo")
async def profile_skip_photo(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(profile_photo_file_id=None)
    await show_profile_confirmation(callback.message, app, db_user, state)


async def show_profile_confirmation(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    preview = {
        **db_user,
        **data,
    }
    await state.set_state(ProfileSetup.confirm)
    await message.answer(app.i18n.t(db_user.get("language"), "confirm_profile_text"))
    await message.answer(
        profile_card(preview),
        reply_markup=profile_confirm_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.confirm, F.data == "profile_confirm")
async def profile_confirm(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    saved = await app.users.set_profile(
        callback.from_user.id,
        nickname=data["nickname"],
        age=int(data["age"]),
        gender=data["gender"],
        interested_in=data["interested_in"],
        region=data["region"],
        bio=data["bio"],
        interests=data["interests"],
        profile_photo_file_id=data.get("profile_photo_file_id"),
    )
    await state.clear()
    await callback.answer()
    if saved:
        await callback.message.answer(app.i18n.t(saved.get("language"), "profile_saved"))
        await send_main_menu(callback.message, app, saved)


@router.callback_query(F.data == "profile_restart")
async def profile_restart(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await begin_profile_setup(callback.message, app, db_user, state, restart=True)


@router.callback_query(F.data == "profile_cancel")
async def profile_cancel(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "profile_edit_cancelled"))
    await send_main_menu(callback.message, app, db_user)
