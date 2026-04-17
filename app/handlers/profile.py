from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards.inline import profile_edit_keyboard
from app.keyboards.reply import gender_keyboard, language_keyboard, location_keyboard, looking_for_keyboard, main_menu_keyboard, media_keyboard
from app.locales.translations import parse_gender, parse_looking_for, t
from app.models.enums import MediaType
from app.services.localization import get_user_language
from app.services.notifier import send_profile_media
from app.states import EditProfileStates, OnboardingStates
from app.utils.formatters import profile_preview_text
from app.utils.text import sanitize_text

router = Router(name="profile")


async def show_profile(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    profile = app.storage.get_user_profile(message.from_user.id)
    settings = app.storage.get_user_settings(message.from_user.id)
    if not profile:
        await message.answer(t(lang, "not_enough_profile"))
        return
    paused = settings.paused if settings else False
    await send_profile_media(
        message.bot,
        message.chat.id,
        profile,
        profile_preview_text(lang, profile),
        reply_markup=profile_edit_keyboard(lang, paused),
    )


@router.message(lambda m: m.text in {"👤 My Profile"})
async def my_profile_menu(message: Message, app: AppContext) -> None:
    await show_profile(message, app)


@router.callback_query(F.data == "profile:toggle_pause")
async def toggle_pause(callback: CallbackQuery, app: AppContext) -> None:
    lang = get_user_language(app.storage, callback.from_user.id)
    settings = app.storage.get_user_settings(callback.from_user.id)
    profile = app.storage.get_user_profile(callback.from_user.id)
    if not profile:
        await callback.answer()
        return
    paused = not (settings.paused if settings else False)
    await app.storage.save_user_settings(
        user_id=callback.from_user.id,
        language=profile.language.value,
        paused=paused,
        deleted=settings.deleted if settings else False,
        last_candidate_id=settings.last_candidate_id if settings else None,
    )
    await callback.message.answer(t(lang, "profile_paused" if paused else "profile_resumed"), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "profile:delete")
async def delete_profile(callback: CallbackQuery, app: AppContext) -> None:
    lang = get_user_language(app.storage, callback.from_user.id)
    profile = app.storage.get_user_profile(callback.from_user.id)
    settings = app.storage.get_user_settings(callback.from_user.id)
    if not profile:
        await callback.answer()
        return
    await app.storage.update_user_profile(callback.from_user.id, is_active=False)
    await app.storage.save_user_settings(
        user_id=callback.from_user.id,
        language=profile.language.value,
        paused=True,
        deleted=True,
        last_candidate_id=settings.last_candidate_id if settings else None,
    )
    await callback.message.answer(t(lang, "profile_deleted"), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("edit:"))
async def start_edit(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    field = callback.data.split(":", 1)[1]
    lang = get_user_language(app.storage, callback.from_user.id)
    await state.update_data(profile_edit_field=field)

    if field == "age":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_age"))
    elif field == "gender":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_gender"), reply_markup=gender_keyboard(lang))
    elif field == "looking_for":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_looking_for"), reply_markup=looking_for_keyboard(lang))
    elif field == "city":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_city"))
    elif field == "location":
        await state.set_state(EditProfileStates.waiting_location)
        await callback.message.answer(t(lang, "ask_location"), reply_markup=location_keyboard(lang))
    elif field == "name":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_name"))
    elif field == "bio":
        await state.set_state(EditProfileStates.waiting_value)
        await callback.message.answer(t(lang, "ask_bio"))
    elif field == "media":
        await state.set_state(EditProfileStates.waiting_media)
        await state.update_data(media_file_ids=[], media_type=None)
        await callback.message.answer(t(lang, "ask_media"), reply_markup=media_keyboard(lang))
    elif field == "language":
        await state.set_state(OnboardingStates.language)
        await state.update_data(profile_edit_field="language", language_change_only=False)
        await callback.message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())
    await callback.answer()


@router.message(EditProfileStates.waiting_value)
async def edit_value(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    data = await state.get_data()
    field = data.get("profile_edit_field")
    profile = app.storage.get_user_profile(message.from_user.id)
    if not profile or not field:
        await state.clear()
        return

    update_data = {}
    text = sanitize_text(message.text or "")

    if field == "age":
        try:
            age = int(text)
        except Exception:
            await message.answer(t(lang, "age_invalid"))
            return
        if age < 18:
            await message.answer(t(lang, "age_underage"))
            return
        update_data["age"] = age
    elif field == "gender":
        gender = parse_gender(message.text or "")
        if not gender:
            await message.answer(t(lang, "ask_gender"), reply_markup=gender_keyboard(lang))
            return
        update_data["gender"] = gender
    elif field == "looking_for":
        looking_for = parse_looking_for(message.text or "")
        if not looking_for:
            await message.answer(t(lang, "ask_looking_for"), reply_markup=looking_for_keyboard(lang))
            return
        update_data["looking_for"] = looking_for
    elif field == "city":
        update_data["city"] = text
    elif field == "name":
        if not text or len(text) > app.settings.max_name_length:
            await message.answer(t(lang, "name_invalid"))
            return
        update_data["name"] = text
    elif field == "bio":
        if not text or len(text) > app.settings.max_bio_length:
            await message.answer(t(lang, "bio_invalid"))
            return
        update_data["bio"] = text

    await app.storage.update_user_profile(message.from_user.id, **update_data)
    await state.clear()
    await message.answer(t(lang, "edit_saved"), reply_markup=main_menu_keyboard(lang))
    await show_profile(message, app)


@router.message(EditProfileStates.waiting_location, F.location)
async def edit_location(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await app.storage.update_user_profile(
        message.from_user.id,
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )
    await state.clear()
    await message.answer(t(lang, "edit_saved"))
    await show_profile(message, app)


@router.message(EditProfileStates.waiting_location)
async def edit_location_invalid(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await message.answer(t(lang, "must_share_location"), reply_markup=location_keyboard(lang))


@router.message(EditProfileStates.waiting_media, F.photo)
async def edit_media_photo(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    data = await state.get_data()
    media_file_ids = list(data.get("media_file_ids") or [])
    if data.get("media_type") == MediaType.VIDEO or len(media_file_ids) >= 3:
        await message.answer(t(lang, "media_invalid"), reply_markup=media_keyboard(lang))
        return
    media_file_ids.append(message.photo[-1].file_id)
    await state.update_data(media_file_ids=media_file_ids, media_type=MediaType.PHOTOS)
    await message.answer(
        f"{t(lang, 'media_added_photo', count=len(media_file_ids))}\n{t(lang, 'media_done_hint')}",
        reply_markup=media_keyboard(lang),
    )


@router.message(EditProfileStates.waiting_media, F.video)
async def edit_media_video(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    data = await state.get_data()
    if message.video.duration > 15 or (data.get("media_file_ids") or []):
        await message.answer(t(lang, "media_invalid"), reply_markup=media_keyboard(lang))
        return
    await state.update_data(media_type=MediaType.VIDEO, media_file_ids=[message.video.file_id])
    await app.storage.update_user_profile(message.from_user.id, media_type=MediaType.VIDEO, media_file_ids=[message.video.file_id])
    await state.clear()
    await message.answer(t(lang, "edit_saved"))
    await show_profile(message, app)


@router.message(EditProfileStates.waiting_media)
async def edit_media_invalid(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    data = await state.get_data()
    text = message.text or ""
    if text == t(lang, "btn_add_more"):
        await message.answer(t(lang, "ask_media"), reply_markup=media_keyboard(lang))
        return
    if text == t(lang, "btn_done_save"):
        media_file_ids = list(data.get("media_file_ids") or [])
        if not media_file_ids:
            await message.answer(t(lang, "media_min_required"), reply_markup=media_keyboard(lang))
            return
        await app.storage.update_user_profile(message.from_user.id, media_type=MediaType.PHOTOS, media_file_ids=media_file_ids)
        await state.clear()
        await message.answer(t(lang, "edit_saved"))
        await show_profile(message, app)
        return
    if text == t(lang, "btn_cancel"):
        await state.clear()
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))
        return
    await message.answer(t(lang, "media_invalid"), reply_markup=media_keyboard(lang))
