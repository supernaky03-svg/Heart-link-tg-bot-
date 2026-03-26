from __future__ import annotations

from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import browse_keyboard, report_reason_keyboard
from app.services.app_context import AppContext
from app.services.discovery import next_candidate
from app.utils.formatters import profile_card
from app.utils.states import ReportFlow


router = Router(name="user_browse")


async def send_candidate(message: Message, app: AppContext, user: dict[str, Any]) -> None:
    candidate = await next_candidate(app, user["id"])
    language = user.get("language")
    if not candidate:
        await message.answer(app.i18n.t(language, "no_profiles_found"))
        return
    text = f"{app.i18n.t(language, 'browse_intro')}\n\n{profile_card(candidate)}"
    keyboard = browse_keyboard(app.i18n, language, candidate["id"])
    if candidate.get("profile_photo_file_id"):
        await message.answer_photo(candidate["profile_photo_file_id"], caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


def match_keyboard(language: str, app: AppContext, username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=app.i18n.t(language, "open_telegram"), url=f"https://t.me/{username}")]
        ]
    )


async def notify_match(app: AppContext, liker: dict[str, Any], other: dict[str, Any]) -> None:
    for receiver, counterpart in ((liker, other), (other, liker)):
        if not receiver.get("notification_matches", True):
            continue
        language = receiver.get("language")
        username = counterpart.get("username")
        nickname = counterpart.get("nickname") or counterpart.get("first_name") or "Match"
        if not username:
            await app.db.execute(
                "INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason) VALUES (NULL, $1, 'match_username_missing', $2)",
                counterpart["id"],
                f"Counterpart username missing for matched user {receiver['id']}",
            )
            continue
        try:
            await app.bot.send_message(  # type: ignore[attr-defined]
                receiver["telegram_id"],
                app.i18n.t(language, "match_card", nickname=escape(nickname), username=f"@{username}"),
                reply_markup=match_keyboard(language, app, username),
            )
        except Exception:
            # Best effort notification; user can still see it in My Matches.
            pass


@router.message(Command("browse"))
async def command_browse(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not await ensure_username_or_prompt(message, app, db_user):
        return
    if not db_user.get("is_profile_complete"):
        await message.answer(app.i18n.t(db_user.get("language"), "profile_incomplete"))
        return
    ok, _ = app.rate_limiter.hit(db_user["id"], "browse_open", 8, 10)
    if not ok:
        await message.answer(app.i18n.t(db_user.get("language"), "rate_limited"))
        return
    await send_candidate(message, app, db_user)


@router.callback_query(F.data == "browse:back")
async def browse_back(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    await callback.answer()
    await send_main_menu(callback.message, app, db_user)


@router.callback_query(F.data.startswith("browse:skip:"))
async def browse_skip(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "skip", 30, 60)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await app.likes.create_skip(db_user["id"], target_id)
    await app.likes.log_action(db_user["id"], "skip")
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_candidate(callback.message, app, db_user)


@router.callback_query(F.data.startswith("browse:like:"))
async def browse_like(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "like", 20, 60)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await app.likes.log_action(db_user["id"], "like")
    recent_like_count = await app.likes.count_recent_actions(db_user["id"], "like", 3600)
    if recent_like_count > 80:
        await app.users.set_suspend(db_user["id"], True)
        await callback.answer(app.i18n.t(db_user.get("language"), "suspicious_activity_suspended"), show_alert=True)
        return

    result = await app.likes.process_like(db_user["id"], target_id)
    target = await app.users.get_by_id(target_id)
    await callback.answer()

    if result["result"] in {"pending", "already_liked"}:
        await callback.message.answer(
            app.i18n.t(db_user.get("language"), "liked_successfully" if result["result"] == "pending" else "already_liked")
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await send_candidate(callback.message, app, db_user)
        return

    if result["result"] in {"matched", "already_matched"}:
        if target and target.get("username"):
            text_key = "mutual_match_found" if result["result"] == "matched" else "already_matched"
            if text_key == "mutual_match_found":
                await callback.message.answer(
                    app.i18n.t(db_user.get("language"), text_key, username=f"@{target['username']}"),
                    reply_markup=match_keyboard(db_user.get("language"), app, target["username"]),
                )
            else:
                await callback.message.answer(app.i18n.t(db_user.get("language"), text_key))
        elif target:
            await callback.message.answer(app.i18n.t(db_user.get("language"), "username_revealed_missing"))
        if result["result"] == "matched" and target:
            await notify_match(app, db_user, target)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await send_candidate(callback.message, app, db_user)
        return

    await callback.message.answer(app.i18n.t(db_user.get("language"), "callback_expired"))


@router.callback_query(F.data.startswith("browse:report:"))
async def browse_report(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "report", 5, 300)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "report_rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await state.set_state(ReportFlow.waiting_reason_text)
    await state.update_data(report_target_id=target_id)
    await callback.answer()
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "report_select_reason"),
        reply_markup=report_reason_keyboard(app.i18n, db_user.get("language"), target_id),
    )


@router.callback_query(F.data.startswith("report_reason:"))
async def report_reason(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    _, target_id_str, reason = callback.data.split(":", 2)
    target_id = int(target_id_str)
    await callback.answer()
    if reason == "other":
        await state.set_state(ReportFlow.waiting_reason_text)
        await state.update_data(report_target_id=target_id)
        await callback.message.answer(app.i18n.t(db_user.get("language"), "report_other_reason"))
        return
    await app.reports.create_report(db_user["id"], target_id, reason)
    await state.clear()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "report_success"))


@router.message(ReportFlow.waiting_reason_text)
async def report_free_text(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    target_id = data.get("report_target_id")
    if not target_id:
        await state.clear()
        await message.answer(app.i18n.t(db_user.get("language"), "callback_expired"))
        return
    details = (message.text or "").strip()[:300]
    await app.reports.create_report(db_user["id"], int(target_id), "other", details)
    await state.clear()
    await message.answer(app.i18n.t(db_user.get("language"), "report_success"))
