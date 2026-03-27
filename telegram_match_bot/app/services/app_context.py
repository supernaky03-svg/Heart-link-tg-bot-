from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram import Bot


from app.config import Settings
from app.db.database import Database
from app.repositories.likes import LikeRepository
from app.repositories.reports import ReportRepository
from app.repositories.settings import SettingsRepository
from app.repositories.users import UserRepository
from app.services.i18n import I18n
from app.services.rate_limit import SlidingWindowRateLimiter


@dataclass(slots=True)
class AppContext:
    bot: Bot | None
    settings: Settings
    db: Database
    users: UserRepository
    likes: LikeRepository
    reports: ReportRepository
    app_settings: SettingsRepository
    i18n: I18n
    rate_limiter: SlidingWindowRateLimiter
