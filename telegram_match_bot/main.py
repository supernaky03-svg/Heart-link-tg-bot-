from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import load_settings
from app.db.database import Database
from app.handlers import include_routers
from app.middlewares.user_context import UserContextMiddleware
from app.repositories.likes import LikeRepository
from app.repositories.reports import ReportRepository
from app.repositories.settings import SettingsRepository
from app.repositories.users import UserRepository
from app.services.app_context import AppContext
from app.services.i18n import I18n
from app.services.rate_limit import SlidingWindowRateLimiter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_http_app(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info("HTTP server started on %s:%s", host, port)
    return runner


async def build_app() -> tuple[Bot, Dispatcher, AppContext, Database]:
    settings = load_settings()
    db = Database(settings)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    app_context = AppContext(
        bot=bot,
        settings=settings,
        db=db,
        users=UserRepository(db),
        likes=LikeRepository(db),
        reports=ReportRepository(db),
        app_settings=SettingsRepository(db),
        i18n=I18n(settings.default_language),
        rate_limiter=SlidingWindowRateLimiter(),
    )

    dp = Dispatcher()
    dp["app"] = app_context
    user_context = UserContextMiddleware()
    dp.message.middleware(user_context)
    dp.callback_query.middleware(user_context)
    include_routers(dp)
    return bot, dp, app_context, db


async def run_polling(bot: Bot, dp: Dispatcher, app_context: AppContext) -> None:
    await bot.delete_webhook(drop_pending_updates=False)
    health_app = web.Application()
    health_app.router.add_get("/health", health)
    runner = await start_http_app(health_app, app_context.settings.host, app_context.settings.port)
    try:
        logger.info("Starting long polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()


async def run_webhook(bot: Bot, dp: Dispatcher, app_context: AppContext) -> None:
    if not app_context.settings.webhook_url:
        raise RuntimeError("WEBHOOK_BASE_URL must be set when USE_WEBHOOK=true")

    web_app = web.Application()
    web_app.router.add_get("/health", health)
    request_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    request_handler.register(web_app, path=app_context.settings.webhook_path)
    setup_application(web_app, dp, bot=bot)

    await bot.set_webhook(url=app_context.settings.webhook_url)
    runner = await start_http_app(web_app, app_context.settings.host, app_context.settings.port)
    try:
        logger.info("Webhook mode started at %s", app_context.settings.webhook_url)
        stop_event = asyncio.Event()
        await stop_event.wait()
    finally:
        with suppress(Exception):
            await bot.delete_webhook(drop_pending_updates=False)
        await runner.cleanup()


async def main() -> None:
    bot, dp, app_context, db = await build_app()
    try:
        if app_context.settings.use_webhook:
            await run_webhook(bot, dp, app_context)
        else:
            await run_polling(bot, dp, app_context)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
