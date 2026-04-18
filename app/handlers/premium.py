from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.context import AppContext
from app.keyboards.inline import premium_buy_keyboard
from app.locales.translations import t
from app.services.localization import get_user_language
from app.utils.formatters import premium_text

router = Router(name="premium")


def _premium_variants() -> set[str]:
    return {t("en", "menu_premium"), t("my", "menu_premium"), t("ru", "menu_premium")}


@router.message(lambda m: (m.text or "").strip() in _premium_variants())
async def premium_screen(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    profile = app.storage.get_user_profile(message.from_user.id)
    config = app.storage.get_config()
    premium_until = profile.premium_until if profile else None
    await message.answer(
        premium_text(lang, config.premium_plans, premium_until),
        reply_markup=premium_buy_keyboard(lang, config.premium_plans),
    )


@router.callback_query(F.data.startswith("premium_buy:"))
async def premium_buy(callback: CallbackQuery, app: AppContext) -> None:
    lang = get_user_language(app.storage, callback.from_user.id)
    await callback.answer()
    plan_id = int(callback.data.split(":", 1)[1])
    profile = app.storage.get_user_profile(callback.from_user.id)
    if not profile or not profile.is_active:
        await callback.message.answer(t(lang, "not_enough_profile"))
        return
    cfg = app.storage.get_config()
    plan = next((p for p in cfg.premium_plans if p.plan_id == plan_id), None)
    if not plan:
        await callback.message.answer(t(lang, "premium_plan_not_found"))
        return

    quote = app.payments.build_premium_quote(callback.from_user.id, plan)
    await callback.message.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=quote.title,
        description=quote.description,
        payload=quote.payload,
        currency="XTR",
        prices=[LabeledPrice(label=quote.title, amount=quote.amount_stars)],
        provider_token="",
    )


@router.pre_checkout_query()
async def premium_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def premium_success(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    payment = message.successful_payment
    if not payment or payment.currency != "XTR":
        return
    plan_info = app.payments.parse_premium_payload(payment.invoice_payload)
    if not plan_info or plan_info[0] != message.from_user.id:
        await message.answer(t(lang, "premium_payment_invalid"))
        return
    _, _plan_id, days, _stars = plan_info
    profile = app.storage.get_user_profile(message.from_user.id)
    if not profile:
        await message.answer(t(lang, "not_enough_profile"))
        return
    await app.storage.grant_premium(message.from_user.id, days, granted_by=message.from_user.id)
    await app.storage.log_admin_action(
        message.from_user.id,
        "premium_payment",
        user_id=message.from_user.id,
        days=days,
        stars=payment.total_amount,
        currency=payment.currency,
        charge_id=payment.telegram_payment_charge_id,
    )
    await message.answer(t(lang, "premium_payment_success"))
