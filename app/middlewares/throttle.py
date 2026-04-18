from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, interval_seconds: float = 0.7) -> None:
        self.interval_seconds = interval_seconds
        self._last_seen: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        key = f"{user.id}:{type(event).__name__}"
        now = time.monotonic()
        async with self._lock:
            last = self._last_seen.get(key, 0.0)
            if now - last < self.interval_seconds:
                return None
            self._last_seen[key] = now
        return await handler(event, data)
