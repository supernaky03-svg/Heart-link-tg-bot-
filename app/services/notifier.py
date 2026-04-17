from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales.translations import t
from app.models.records import LikeRecord, UserProfileRecord
from app.utils.formatters import profile_preview_text

logger = logging.getLogger(__name__)


async def send_profile_media(bot: Bot, chat_id: int, profile: UserProfileRecord, caption: str, reply_markup=None) -> None:
    if profile.media_type == "video":
        await bot.send_video(chat_id, profile.media_file_ids[0], caption=caption, reply_markup=reply_markup)
    else:
        await bot.send_photo(chat_id, profile.media_file_ids[0], caption=caption, reply_markup=reply_markup)


async def notify_match(
    bot: Bot,
    left: UserProfileRecord,
    right: UserProfileRecord,
    left_intro: LikeRecord | None = None,
    right_intro: LikeRecord | None = None,
) -> None:
    for receiver, target, other_intro in (
        (left, right, right_intro),
        (right, left, left_intro),
    ):
        lines = [t(receiver.language.value, "match_created"), t(receiver.language.value, "match_with", name=target.name)]
        if target.username:
            lines.append(t(receiver.language.value, "match_contact", username=target.username))
        else:
            lines.append(t(receiver.language.value, "match_no_username"))
        if other_intro and other_intro.intro_message:
            lines.extend(["", t(receiver.language.value, "match_intro_from_other", intro=other_intro.intro_message)])
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(receiver.language.value, "btn_report"), callback_data=f"report:{target.user_id}")]
            ]
        )
        try:
            await send_profile_media(bot, receiver.user_id, target, "\n".join(lines), reply_markup=markup)
        except (TelegramForbiddenError, TelegramBadRequest):
            logger.warning("Could not notify match user_id=%s", receiver.user_id)


async def notify_admins(bot: Bot, admin_ids: list[int], text: str) -> None:
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Failed to notify admin %s", admin_id)
