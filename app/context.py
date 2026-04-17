from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.services.payments import PaymentService
from app.services.storage import TelegramChannelStorage


@dataclass
class AppContext:
    settings: Settings
    storage: TelegramChannelStorage
    payments: PaymentService
