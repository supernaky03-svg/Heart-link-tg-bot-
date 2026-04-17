from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import get_settings
from app.context import AppContext
from app.handlers import setup_routers
from app.middlewares.throttle import ThrottleMiddleware
from app.services.payments import PaymentService
from app.services.storage import TelegramChannelStorage


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start / create profile"),
            BotCommand(command="menu", description="Open main menu"),
            BotCommand(command="help", description="Help"),
            BotCommand(command="admin", description="Admin panel"),
            BotCommand(command="stats", description="Admin stats"),
        ]
    )


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("heart_link")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = TelegramChannelStorage(settings)
    await storage.rebuild_cache()

    app = AppContext(settings=settings, storage=storage, payments=PaymentService())

    dp = Dispatcher()
    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())
    dp.include_router(setup_routers())

    await set_bot_commands(bot)
    logger.info("Bot started with %s cached profiles", len(storage.profiles))
    try:
        await dp.start_polling(bot, app=app)
    finally:
        await storage.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
