from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.app_context import AppContext


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        app: AppContext = data["app"]
        from_user = getattr(event, "from_user", None)
        if from_user:
            default_language = app.settings.default_language
            user = await app.users.ensure_user(
                telegram_id=from_user.id,
                username=from_user.username,
                first_name=from_user.first_name,
                language=default_language,
                is_admin=from_user.id in app.settings.admin_ids,
            )
            data["db_user"] = user
        return await handler(event, data)
