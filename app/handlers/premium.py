from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.locales.translations import t
from app.services.localization import get_user_language
from app.utils.formatters import premium_text

router = Router(name="premium")


@router.message(lambda m: m.text in {"⭐ Premium"})
async def premium_screen(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    profile = app.storage.get_user_profile(message.from_user.id)
    config = app.storage.get_config()
    premium_until = profile.premium_until if profile else None
    await message.answer(premium_text(lang, config.premium_plans, premium_until))


@router.callback_query(F.data.startswith("premium_buy:"))
async def premium_buy_placeholder(callback: CallbackQuery, app: AppContext) -> None:
    lang = get_user_language(app.storage, callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        t(lang, "premium_title") + "\n\nPayment integration layer is isolated in app/services/payments.py.",
    )
