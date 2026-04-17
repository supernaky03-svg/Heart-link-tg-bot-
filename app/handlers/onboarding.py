from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards.inline import profile_draft_edit_keyboard
from app.keyboards.reply import (
    gender_keyboard,
    language_keyboard,
    location_keyboard,
    looking_for_keyboard,
    main_menu_keyboard,
    media_keyboard,
    yes_edit_cancel_keyboard,
)
from app.locales.translations import parse_gender, parse_language_from_text, parse_looking_for, t
from app.models.enums import MediaType
from app.models.records import UserProfileRecord
from app.services.localization import get_user_language
from app.services.notifier import send_profile_media
from app.states import OnboardingStates
from app.utils.formatters import profile_preview_text
from app.utils.text import sanitize_text

router = Router(name="onboarding")


async def _ask_gender(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.gender)
    await message.answer(t(lang, "ask_gender"), reply_markup=gender_keyboard(lang))


async def _ask_looking_for(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.looking_for)
    await message.answer(t(lang, "ask_looking_for"), reply_markup=looking_for_keyboard(lang))


async def _ask_city(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.city)
    await message.answer(t(lang, "ask_city"))


async def _ask_location(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.location)
    await message.answer(t(lang, "ask_location"), reply_markup=location_keyboard(lang))


async def _ask_name(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.name)
    await message.answer(t(lang, "ask_name"))


async def _ask_bio(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.bio)
    await message.answer(t(lang, "ask_bio"))


async def _ask_media(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.media)
    await message.answer(t(lang, "ask_media"), reply_markup=media_keyboard(lang))


async def _show_draft_preview(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = data.get("language") or get_user_language(app.storage, message.from_user.id)
    media_type = data.get("media_type")
    media_file_ids = data.get("media_file_ids") or []
    profile = UserProfileRecord(
        record_id=str(message.from_user.id),
        user_id=message.from_user.id,
        username=message.from_user.username,
        language=lang,
        age=int(data["age"]),
        gender=data["gender"],
        looking_for=data["looking_for"],
        city=data["city"],
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
        name=data["name"],
        bio=data["bio"],
        media_type=media_type,
        media_file_ids=media_file_ids,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await state.set_state(OnboardingStates.confirm)
    await message.answer(t(lang, "profile_preview_title"))
    await send_profile_media(
        message.bot,
        message.chat.id,
        profile,
        profile_preview_text(lang, profile),
        reply_markup=None,
    )
    await message.answer(t(lang, "is_correct"), reply_markup=yes_edit_cancel_keyboard(lang))


def _is_draft_edit(data: dict[str, Any], field: str) -> bool:
    return data.get("draft_edit_field") == field


@router.message(OnboardingStates.language)
async def onboarding_language(message: Message, state: FSMContext, app: AppContext) -> None:
    language = parse_language_from_text(message.text or "")
    if not language:
        await message.answer(t(app.settings.default_language, "choose_language"), reply_markup=language_keyboard())
        return

    data = await state.get_data()
    settings = app.storage.get_user_settings(message.from_user.id)
    paused = settings.paused if settings else False
    deleted = settings.deleted if settings else False
    last_candidate_id = settings.last_candidate_id if settings else None
    await app.storage.save_user_settings(
        user_id=message.from_user.id,
        language=language.value,
        paused=paused,
        deleted=deleted,
        last_candidate_id=last_candidate_id,
    )

    await state.update_data(language=language)
    profile = app.storage.get_user_profile(message.from_user.id)

    if data.get("language_change_only"):
        if profile:
            await app.storage.update_user_profile(message.from_user.id, language=language)
        await state.clear()
        await message.answer(t(language, "language_changed"), reply_markup=main_menu_keyboard(language))
        return

    if _is_draft_edit(data, "language"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return

    if data.get("profile_edit_field") == "language" and profile:
        await app.storage.update_user_profile(message.from_user.id, language=language)
        await state.clear()
        await message.answer(t(language, "language_changed"), reply_markup=main_menu_keyboard(language))
        return

    await message.answer(t(language, "lang_saved"))
    await message.answer(t(language, "welcome_new"))
    await state.set_state(OnboardingStates.age)
    await message.answer(t(language, "ask_age"))


@router.message(OnboardingStates.age)
async def onboarding_age(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    try:
        age = int((message.text or "").strip())
    except Exception:
        await message.answer(t(lang, "age_invalid"))
        return
    if age < 18:
        await message.answer(t(lang, "age_underage"))
        await state.clear()
        return

    await state.update_data(age=age)
    if _is_draft_edit(data, "age"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await _ask_gender(message, lang, state)


@router.message(OnboardingStates.gender)
async def onboarding_gender(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    gender = parse_gender(message.text or "")
    if not gender:
        await message.answer(t(lang, "ask_gender"), reply_markup=gender_keyboard(lang))
        return
    await state.update_data(gender=gender)
    if _is_draft_edit(data, "gender"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await _ask_looking_for(message, lang, state)


@router.message(OnboardingStates.looking_for)
async def onboarding_looking_for(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    looking_for = parse_looking_for(message.text or "")
    if not looking_for:
        await message.answer(t(lang, "ask_looking_for"), reply_markup=looking_for_keyboard(lang))
        return
    await state.update_data(looking_for=looking_for)
    if _is_draft_edit(data, "looking_for"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await _ask_city(message, lang, state)


@router.message(OnboardingStates.city)
async def onboarding_city(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    city = sanitize_text(message.text or "")
    if not city:
        await message.answer(t(lang, "ask_city"))
        return
    await state.update_data(city=city)
    if _is_draft_edit(data, "city"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await _ask_location(message, lang, state)


@router.message(OnboardingStates.location, F.location)
async def onboarding_location(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    await state.update_data(latitude=message.location.latitude, longitude=message.location.longitude)
    if _is_draft_edit(data, "location"):
        await state.update_data(draft_edit_field=None)
        await message.answer(t(lang, "location_saved"))
        await _show_draft_preview(message, state, app)
        return
    await message.answer(t(lang, "location_saved"))
    await _ask_name(message, lang, state)


@router.message(OnboardingStates.location)
async def onboarding_location_invalid(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    await message.answer(t(lang, "must_share_location"), reply_markup=location_keyboard(lang))


@router.message(OnboardingStates.name)
async def onboarding_name(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    name = sanitize_text(message.text or "")
    if not name or len(name) > app.settings.max_name_length:
        await message.answer(t(lang, "name_invalid"))
        return
    await state.update_data(name=name)
    if _is_draft_edit(data, "name"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await _ask_bio(message, lang, state)


@router.message(OnboardingStates.bio)
async def onboarding_bio(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    bio = sanitize_text(message.text or "")
    if not bio or len(bio) > app.settings.max_bio_length:
        await message.answer(t(lang, "bio_invalid"))
        return
    await state.update_data(bio=bio)
    if _is_draft_edit(data, "bio"):
        await state.update_data(draft_edit_field=None)
        await _show_draft_preview(message, state, app)
        return
    await state.update_data(media_file_ids=[], media_type=None)
    await _ask_media(message, lang, state)


@router.message(OnboardingStates.media, F.photo)
async def onboarding_media_photo(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    media_file_ids = list(data.get("media_file_ids") or [])
    if data.get("media_type") == MediaType.VIDEO:
        await message.answer(t(lang, "media_invalid"))
        return
    if len(media_file_ids) >= 3:
        await message.answer(t(lang, "media_invalid"))
        return
    media_file_ids.append(message.photo[-1].file_id)
    await state.update_data(media_type=MediaType.PHOTOS, media_file_ids=media_file_ids)
    await message.answer(
        f"{t(lang, 'media_added_photo', count=len(media_file_ids))}\n{t(lang, 'media_done_hint')}",
        reply_markup=media_keyboard(lang),
    )
    if len(media_file_ids) >= 3:
        await _show_draft_preview(message, state, app)


@router.message(OnboardingStates.media, F.video)
async def onboarding_media_video(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    if message.video.duration > 15:
        await message.answer(t(lang, "media_video_too_long"))
        return
    if data.get("media_file_ids"):
        await message.answer(t(lang, "media_invalid"))
        return
    await state.update_data(media_type=MediaType.VIDEO, media_file_ids=[message.video.file_id])
    await message.answer(t(lang, "media_added_video"), reply_markup=media_keyboard(lang))
    await _show_draft_preview(message, state, app)


@router.message(OnboardingStates.media)
async def onboarding_media_text(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    text = message.text or ""
    if text == t(lang, "btn_done_save"):
        if not (data.get("media_file_ids") or []):
            await message.answer(t(lang, "media_min_required"))
            return
        await _show_draft_preview(message, state, app)
        return
    if text == t(lang, "btn_add_more"):
        await message.answer(t(lang, "ask_media"), reply_markup=media_keyboard(lang))
        return
    if text == t(lang, "btn_cancel"):
        await state.clear()
        await message.answer(t(lang, "profile_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    await message.answer(t(lang, "media_invalid"), reply_markup=media_keyboard(lang))


@router.message(OnboardingStates.confirm)
async def onboarding_confirm(message: Message, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, message.from_user.id))
    text = message.text or ""
    if text == t(lang, "btn_yes"):
        profile = UserProfileRecord(
            record_id=str(message.from_user.id),
            user_id=message.from_user.id,
            username=message.from_user.username,
            language=data["language"],
            age=int(data["age"]),
            gender=data["gender"],
            looking_for=data["looking_for"],
            city=data["city"],
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            name=data["name"],
            bio=data["bio"],
            media_type=data["media_type"],
            media_file_ids=data["media_file_ids"],
            is_active=True,
        )
        await app.storage.save_user_profile(profile)
        settings = app.storage.get_user_settings(message.from_user.id)
        await app.storage.save_user_settings(
            user_id=message.from_user.id,
            language=profile.language.value,
            paused=settings.paused if settings else False,
            deleted=False,
            last_candidate_id=settings.last_candidate_id if settings else None,
        )
        await state.clear()
        await message.answer(t(lang, "profile_saved"), reply_markup=main_menu_keyboard(lang))
        return
    if text == t(lang, "btn_edit"):
        await message.answer(t(lang, "edit_prompt"), reply_markup=profile_draft_edit_keyboard(lang))
        return
    if text == t(lang, "btn_cancel"):
        await state.clear()
        await message.answer(t(lang, "profile_cancelled"), reply_markup=main_menu_keyboard(lang))
        return
    await message.answer(t(lang, "is_correct"), reply_markup=yes_edit_cancel_keyboard(lang))


@router.callback_query(F.data.startswith("draft_edit:"))
async def draft_edit_callback(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    data = await state.get_data()
    lang = (data.get("language").value if data.get("language") else get_user_language(app.storage, callback.from_user.id))
    field = callback.data.split(":", 1)[1]
    await state.update_data(draft_edit_field=field)
    if field == "age":
        await state.set_state(OnboardingStates.age)
        await callback.message.answer(t(lang, "ask_age"))
    elif field == "gender":
        await _ask_gender(callback.message, lang, state)
    elif field == "looking_for":
        await _ask_looking_for(callback.message, lang, state)
    elif field == "city":
        await _ask_city(callback.message, lang, state)
    elif field == "location":
        await _ask_location(callback.message, lang, state)
    elif field == "name":
        await _ask_name(callback.message, lang, state)
    elif field == "bio":
        await _ask_bio(callback.message, lang, state)
    elif field == "media":
        await state.update_data(media_file_ids=[], media_type=None)
        await _ask_media(callback.message, lang, state)
    elif field == "language":
        await state.set_state(OnboardingStates.language)
        await callback.message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())
    await callback.answer()
