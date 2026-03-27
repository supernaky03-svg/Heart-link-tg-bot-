from __future__ import annotations

from html import escape
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.common import ensure_allowed_message
from app.services.app_context import AppContext


router = Router(name="user_matches")


@router.message(Command("matches"))
async def command_matches(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    matches = await app.likes.list_matches_for_user(db_user["id"])
    if not matches:
        await message.answer(app.i18n.t(db_user.get("language"), "matches_empty"))
        return
    lines = [f"<b>{app.i18n.t(db_user.get('language'), 'matches_title')}</b>"]
    for match in matches[:20]:
        username = match.get("username")
        nickname = match.get("nickname") or "Match"
        tg = f"@{escape(username)}" if username else "-"
        lines.append(f"• <b>{escape(nickname)}</b> — {tg} — {escape(str(match.get('match_created_at'))[:16])}")
    await message.answer("\n".join(lines))
