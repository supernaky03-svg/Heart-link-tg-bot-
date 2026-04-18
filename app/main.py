from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiohttp import web
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
            BotCommand(command="profile", description="Open my profile"),
            BotCommand(command="help", description="Help"),
            BotCommand(command="admin", description="Admin panel"),
            BotCommand(command="stats", description="Admin stats"),
        ]
    )


async def index(_: web.Request) -> web.Response:
    return web.Response(text="Heart Link Bot is alive")


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "heart-link-bot"})


async def start_http_server() -> web.AppRunner:
    http_app = web.Application()
    http_app.router.add_get("/", index)
    http_app.router.add_get("/health", health)

    runner = web.AppRunner(http_app)
    await runner.setup()

    host = "0.0.0.0"
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()

    logging.getLogger("heart_link").info("HTTP health server started on %s:%s", host, port)
    return runner


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("heart_link")

    http_runner = await start_http_server()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = TelegramChannelStorage(settings)
    await storage.rebuild_cache()

    app = AppContext(settings=settings, storage=storage, payments=PaymentService())

    dp = Dispatcher()
    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())
    dp.include_router(setup_routers())

    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("Bot started with %s cached profiles", len(storage.profiles))
    try:
        await dp.start_polling(bot, app=app)
    finally:
        await http_runner.cleanup()
        await storage.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
