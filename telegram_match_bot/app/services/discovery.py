from __future__ import annotations

from typing import Any

from app.services.app_context import AppContext


async def next_candidate(app: AppContext, user_id: int) -> dict[str, Any] | None:
    return await app.likes.discovery_candidate(user_id)
