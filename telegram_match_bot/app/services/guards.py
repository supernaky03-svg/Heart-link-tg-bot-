from __future__ import annotations

from typing import Any

from app.services.app_context import AppContext


async def can_use_bot(app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> tuple[bool, str | None]:
    if not user:
        return False, None
    if user.get("is_banned"):
        return False, "banned_notice"
    if user.get("is_suspended"):
        return False, "suspended_notice"
    if not admin_bypass and await app.app_settings.is_maintenance_mode() and not user.get("is_admin"):
        return False, "maintenance_mode"
    return True, None


def has_username(user: dict[str, Any]) -> bool:
    username = user.get("username")
    return bool(username and str(username).strip())
