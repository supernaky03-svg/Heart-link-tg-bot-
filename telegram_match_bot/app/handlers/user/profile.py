from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.common import (
    ensure_allowed_callback,
    ensure_allowed_message,
    ensure_username_or_prompt,
    send_main_menu,
)
from app.keyboards.inline import (
    profile_confirm_keyboard,
    profile_gender_keyboard,
    profile_interest_keyboard,
)
from app.keyboards.reply import location_request_keyboard, remove_reply_keyboard
from app.services.app_context import AppContext
from app.utils.formatters import profile_card
from app.utils.states import ProfileSetup
from app.utils.validators import (
    parse_interests,
    validate_age,
    validate_bio,
    validate_nickname,
)

router = Router(name="user_profile")


async def _safe_delete_message(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        pass


async def _delete_prompt_if_exists(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("_prompt_message_id")
    if not prompt_message_id:
        return

    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
    except Exception:
        pass

    await state.update_data(_prompt_message_id=None)


async def _send_prompt(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    await _delete_prompt_if_exists(message, state)
    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(_prompt_message_id=sent.message_id)


async def _consume_answer(message: Message, state: FSMContext) -> None:
    await _delete_prompt_if_exists(message, state)
    await _safe_delete_message(message)


async def begin_profile_setup(
    message: Message,
    app: AppContext,
    user: dict[str, Any],
    state: FSMContext,
    restart: bool = False,
) -> None:
    if restart:
        await state.clear()

    await state.set_state(ProfileSetup.nickname)
    await _send_prompt(
        message,
        state,
        app.i18n.t(user.get("language"), "ask_nickname"),
    )


@router.message(Command("profile"))
async def command_profile(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return

    if not db_user.get("is_profile_complete"):
        await message.answer(app.i18n.t(db_user.get("language"), "profile_incomplete"))
        return

    await message.answer(profile_card(db_user))


@router.message(Command("editprofile"))
async def command_edit_profile(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not await ensure_username_or_prompt(message, app, db_user):
        return

    await begin_profile_setup(message, app, db_user, state, restart=True)


@router.message(ProfileSetup.nickname)
async def profile_nickname(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    nickname = (message.text or "").strip()
    if not validate_nickname(nickname, max_len=app.settings.max_nickname_length):
        await _consume_answer(message, state)
        await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "invalid_nickname"))
        return

    await _consume_answer(message, state)
    await state.update_data(nickname=nickname)
    await state.set_state(ProfileSetup.age)
    await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "ask_age"))

@router.message(ProfileSetup.age)
async def profile_age(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    age = validate_age(message.text or "")
    if age is None:
        await _consume_answer(message, state)
        await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "invalid_age"))
        return

    await _consume_answer(message, state)
    await state.update_data(age=age)
    await state.set_state(ProfileSetup.gender)
    await _send_prompt(
        message,
        state,
        app.i18n.t(db_user.get("language"), "ask_gender"),
        reply_markup=profile_gender_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.gender, F.data.startswith("profile_gender:"))
async def profile_gender(
    callback: CallbackQuery,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return

    await callback.answer()
    if callback.message:
        await _safe_delete_message(callback.message)

    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender, _prompt_message_id=None)
    await state.set_state(ProfileSetup.interested_in)

    if callback.message:
        await _send_prompt(
            callback.message,
            state,
            app.i18n.t(db_user.get("language"), "ask_interested_in"),
            reply_markup=profile_interest_keyboard(app.i18n, db_user.get("language")),
        )


@router.callback_query(ProfileSetup.interested_in, F.data.startswith("profile_interest:"))
async def profile_interest(
    callback: CallbackQuery,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return

    await callback.answer()
    if callback.message:
        await _safe_delete_message(callback.message)

    interested_in = callback.data.split(":", 1)[1]
    await state.update_data(interested_in=interested_in, _prompt_message_id=None)
    await state.set_state(ProfileSetup.bio)

    if callback.message:
        await _send_prompt(
            callback.message,
            state,
            app.i18n.t(db_user.get("language"), "ask_bio"),
        )


@router.message(ProfileSetup.bio)
async def profile_bio(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    bio = (message.text or "").strip()
    if not validate_bio(bio, max_len=app.settings.max_bio_length):
        await _consume_answer(message, state)
        await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "invalid_bio"))
        return

    await _consume_answer(message, state)
    await state.update_data(bio=bio)
    await state.set_state(ProfileSetup.interests)
    await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "ask_interests"))


@router.message(ProfileSetup.interests)
async def profile_interests(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    interests = parse_interests(message.text or "")
    if not interests:
        await _consume_answer(message, state)
        await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "invalid_interests"))
        return

    await _consume_answer(message, state)
    await state.update_data(interests=interests)
    await state.set_state(ProfileSetup.photo)
    await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "ask_photo"))


@router.message(ProfileSetup.photo, F.photo)
async def profile_photo(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    photo = message.photo[-1]
    await _consume_answer(message, state)
    await state.update_data(profile_photo_file_id=photo.file_id)
    await state.set_state(ProfileSetup.location)
    await _send_prompt(
        message,
        state,
        app.i18n.t(db_user.get("language"), "ask_location"),
        reply_markup=location_request_keyboard(app.i18n, db_user.get("language")),
    )


@router.message(ProfileSetup.photo)
async def profile_photo_invalid(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    await _consume_answer(message, state)
    await _send_prompt(message, state, app.i18n.t(db_user.get("language"), "invalid_photo"))


@router.message(ProfileSetup.location, F.location)
async def profile_location(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    await _consume_answer(message, state)
    await state.update_data(
        latitude=round(message.location.latitude, 6),
        longitude=round(message.location.longitude, 6),
    )
    await show_profile_confirmation(message, app, db_user, state)


@router.message(ProfileSetup.location)
async def profile_location_invalid(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    await _consume_answer(message, state)
    await _send_prompt(
        message,
        state,
        app.i18n.t(db_user.get("language"), "invalid_location"),
        reply_markup=location_request_keyboard(app.i18n, db_user.get("language")),
    )


async def show_profile_confirmation(
    message: Message,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    data = await state.get_data()
    preview = {**db_user, **data}

    await state.set_state(ProfileSetup.confirm)
    await _delete_prompt_if_exists(message, state)

    preview_intro = await message.answer(
        app.i18n.t(db_user.get("language"), "confirm_profile_text"),
        reply_markup=remove_reply_keyboard(),
    )
    await _safe_delete_message(preview_intro)

    if preview.get("profile_photo_file_id"):
        sent = await message.answer_photo(
            preview["profile_photo_file_id"],
            caption=profile_card(preview),
            reply_markup=profile_confirm_keyboard(app.i18n, db_user.get("language")),
        )
    else:
        sent = await message.answer(
            profile_card(preview),
            reply_markup=profile_confirm_keyboard(app.i18n, db_user.get("language")),
        )

    await state.update_data(_prompt_message_id=sent.message_id)


@router.callback_query(ProfileSetup.confirm, F.data == "profile_confirm")
async def profile_confirm(
    callback: CallbackQuery,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return

    data = await state.get_data()
    saved = await app.users.set_profile(
        callback.from_user.id,
        nickname=data["nickname"],
        age=int(data["age"]),
        gender=data["gender"],
        interested_in=data["interested_in"],
        bio=data["bio"],
        interests=data["interests"],
        profile_photo_file_id=data["profile_photo_file_id"],
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
    )

    await state.clear()
    await callback.answer()

    if callback.message:
        await _safe_delete_message(callback.message)

    if saved and callback.message:
        await callback.message.answer(
            app.i18n.t(saved.get("language"), "profile_saved"),
            reply_markup=remove_reply_keyboard(),
        )
        await send_main_menu(callback.message, app, saved)


@router.callback_query(F.data == "profile_restart")
async def profile_restart(
    callback: CallbackQuery,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
        await callback.answer()
    if callback.message:
        await _safe_delete_message(callback.message)
        await begin_profile_setup(callback.message, app, db_user, state, restart=True)


@router.callback_query(F.data == "profile_cancel")
async def profile_cancel(
    callback: CallbackQuery,
    app: AppContext,
    db_user: dict[str, Any],
    state: FSMContext,
) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return

    await callback.answer()
    await state.clear()

    if callback.message:
        await _safe_delete_message(callback.message)
        await callback.message.answer(
            app.i18n.t(db_user.get("language"), "profile_edit_cancelled"),
            reply_markup=remove_reply_keyboard(),
        )
        await send_main_menu(callback.message, app, db_user)
