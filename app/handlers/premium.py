from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.context import AppContext
from app.keyboards.inline import premium_buy_keyboard
from app.locales.translations import t
from app.services.localization import get_user_language
from app.utils.formatters import premium_text

router = Router(name="premium")
logger = logging.getLogger("heart_link")


def _premium_variants() -> set[str]:
    return {
        t("en", "menu_premium").strip(),
        t("my", "menu_premium").strip(),
        t("ru", "menu_premium").strip(),
        "⭐ Premium",
    }


async def _show_premium_screen(message: Message, app: AppContext) -> None:
    logger.info("PREMIUM menu hit text=%r user_id=%s", message.text, message.from_user.id)

    lang = get_user_language(app.storage, message.from_user.id)
    profile = app.storage.get_user_profile(message.from_user.id)
    config = app.storage.get_config()
    premium_until = profile.premium_until if profile else None

    await message.answer(
        premium_text(lang, config.premium_plans, premium_until),
        reply_markup=premium_buy_keyboard(lang, config.premium_plans),
    )


@router.message(Command("premium"))
async def premium_command(message: Message, app: AppContext) -> None:
    await _show_premium_screen(message, app)


@router.message(lambda m: (m.text or "").strip() in _premium_variants())
async def premium_screen(message: Message, app: AppContext) -> None:
    await _show_premium_screen(message, app)


@router.callback_query(F.data.startswith("premium_buy:"))
async def premium_buy(callback: CallbackQuery, app: AppContext) -> None:
    lang = get_user_language(app.storage, callback.from_user.id)
    plan_id = callback.data.split(":", 1)[1]
    config = app.storage.get_config()
    plan = next((p for p in config.premium_plans if p.plan_id == plan_id), None)

    if not plan:
        await callback.answer(t(lang, "generic_error"), show_alert=True)
        return

    payload = app.payments.build_premium_payload(callback.from_user.id, plan)

    await callback.message.answer_invoice(
        title=t(lang, "premium_title"),
        description=t(lang, "premium_description"),
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=f"{plan.days} days", amount=plan.stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def premium_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)

@router.callback_query(F.data == "premium_close")
async def premium_close(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()


@router.message(F.successful_payment)
async def premium_success(message: Message, app: AppContext) -> None:
    payment = message.successful_payment
    if not payment or payment.currency != "XTR":
        return

    lang = get_user_language(app.storage, message.from_user.id)
    ok = await app.payments.apply_successful_premium_payment(app.storage, payment)

    if not ok:
        await message.answer(t(lang, "generic_error"))
        return

    await message.answer(t(lang, "premium_activated"))
