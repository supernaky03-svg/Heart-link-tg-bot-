from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards.inline import discover_actions_keyboard
from app.locales.translations import t
from app.services.localization import get_user_language
from app.services.matchmaking import next_candidate
from app.services.notifier import notify_match, send_profile_media
from app.states import DiscoverStates
from app.utils.formatters import discover_card_text
from app.utils.text import sanitize_text

router = Router(name="discover")


async def show_next_profile(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    viewer = app.storage.get_user_profile(message.from_user.id)
    if not viewer or not viewer.is_active or viewer.is_banned:
        await message.answer(t(lang, "not_enough_profile"))
        return
    candidate = next_candidate(app.storage, viewer.user_id)
    if not candidate:
        await app.storage.set_last_candidate(viewer.user_id, None)
        await message.answer(t(lang, "discover_empty"))
        return
    await app.storage.save_view(viewer.user_id, candidate.user_id)
    await app.storage.set_last_candidate(viewer.user_id, candidate.user_id)
    await send_profile_media(
        message.bot,
        message.chat.id,
        candidate,
        discover_card_text(viewer, candidate),
        reply_markup=discover_actions_keyboard(lang, candidate.user_id),
    )


async def _process_like(message: Message, app: AppContext, source_user_id: int, target_user_id: int, intro: str | None = None) -> None:
    lang = get_user_language(app.storage, source_user_id)
    viewer = app.storage.get_user_profile(source_user_id)
    target = app.storage.get_user_profile(target_user_id)
    if not viewer or not target or source_user_id == target_user_id:
        await message.answer(t(lang, "cannot_match_self"))
        return
    like = await app.storage.save_like(source_user_id, target_user_id, intro_message=intro)
    reverse_like = app.storage.get_like(target_user_id, source_user_id)
    if reverse_like:
        await app.storage.create_match(source_user_id, target_user_id)
        await notify_match(message.bot, viewer, target, like, reverse_like)
    else:
        await message.answer(t(lang, "liked" if not intro else "intro_saved"))


@router.message(lambda m: m.text in {"💖 Discover"})
async def discover_entry(message: Message, app: AppContext) -> None:
    await show_next_profile(message, app)


@router.callback_query(F.data.startswith("react:"))
async def discover_reaction(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    _, action, target_raw = callback.data.split(":")
    target_user_id = int(target_raw)
    user_id = callback.from_user.id
    lang = get_user_language(app.storage, user_id)
    await callback.answer()

    if action == "love_msg":
        await state.set_state(DiscoverStates.waiting_intro)
        await state.update_data(target_user_id=target_user_id)
        await callback.message.answer(t(lang, "ask_intro"))
        return

    if action == "love":
        await _process_like(callback.message, app, user_id, target_user_id)
    elif action == "dislike":
        await app.storage.save_dislike(user_id, target_user_id)
        await callback.message.answer(t(lang, "disliked"))
    elif action == "pass":
        await app.storage.save_pass(user_id, target_user_id)
        await callback.message.answer(t(lang, "passed"))

    await show_next_profile(callback.message, app)


@router.message(DiscoverStates.waiting_intro)
async def intro_message_handler(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    intro = sanitize_text(message.text or "")
    if not intro:
        await message.answer(t(lang, "ask_intro"))
        return
    data = await state.get_data()
    target_user_id = int(data["target_user_id"])
    await _process_like(message, app, message.from_user.id, target_user_id, intro=intro)
    await state.clear()
    await show_next_profile(message, app)
