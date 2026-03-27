from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent


logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled update error", exc_info=event.exception)
    return True
