from __future__ import annotations

from typing import Any

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.app_context import AppContext


class AdminFilter(Filter):
    async def __call__(self, event: TelegramObject, app: AppContext, **kwargs: Any) -> bool:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return False
        user = await app.users.get_by_telegram_id(from_user.id)
        return bool(user and user.get("is_admin"))
