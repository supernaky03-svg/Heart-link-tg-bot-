from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards.inline import premium_edit_keyboard, premium_plans_keyboard
from app.locales.translations import t
from app.services.localization import get_user_language
from app.states import AdminBroadcastStates, PremiumPriceStates

router = Router(name="admin")


def _is_admin(app: AppContext, user_id: int) -> bool:
    return user_id in app.settings.admin_ids


async def _admin_guard(message: Message | CallbackQuery, app: AppContext) -> bool:
    user_id = message.from_user.id
    if _is_admin(app, user_id):
        return True
    lang = get_user_language(app.storage, user_id)
    target = message.message if isinstance(message, CallbackQuery) else message
    await target.answer(t(lang, "admin_only"))
    return False


@router.message(Command("admin"))
async def admin_panel(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "admin_panel"))


@router.message(Command("stats"))
async def stats(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    profiles = list(app.storage.profiles.values())
    active = len(app.storage.active_profiles())
    premium = len([p for p in profiles if p.is_premium])
    text = t(
        get_user_language(app.storage, message.from_user.id),
        "stats_text",
        users=len(profiles),
        active=active,
        premium=premium,
        matches=len(app.storage.matches),
        reports=len(app.storage.reports),
        likes=len(app.storage.likes),
    )
    await message.answer(text)


@router.message(Command("user"))
async def user_lookup(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /user <user_id>")
        return
    try:
        user_id = int(parts[1])
    except Exception:
        await message.answer("Invalid user_id")
        return
    profile = app.storage.get_user_profile(user_id)
    if not profile:
        await message.answer(t(get_user_language(app.storage, message.from_user.id), "user_not_found"))
        return
    await message.answer(f"<pre>{profile.model_dump_json(indent=2)}</pre>")


@router.message(Command("ban"))
async def ban_user(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /ban <user_id>")
        return
    user_id = int(parts[1])
    profile = app.storage.get_user_profile(user_id)
    if not profile:
        await message.answer(t(get_user_language(app.storage, message.from_user.id), "user_not_found"))
        return
    await app.storage.update_user_profile(user_id, is_banned=True, is_active=False)
    await app.storage.log_admin_action(message.from_user.id, "ban", user_id=user_id)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "user_banned"))


@router.message(Command("unban"))
async def unban_user(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /unban <user_id>")
        return
    user_id = int(parts[1])
    profile = app.storage.get_user_profile(user_id)
    if not profile:
        await message.answer(t(get_user_language(app.storage, message.from_user.id), "user_not_found"))
        return
    await app.storage.update_user_profile(user_id, is_banned=False, is_active=True)
    await app.storage.log_admin_action(message.from_user.id, "unban", user_id=user_id)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "user_unbanned"))


@router.message(Command("setpremium"))
async def set_premium(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Usage: /setpremium <user_id> <days>")
        return
    user_id = int(parts[1])
    days = int(parts[2])
    await app.storage.grant_premium(user_id, days, granted_by=message.from_user.id)
    await app.storage.log_admin_action(message.from_user.id, "setpremium", user_id=user_id, days=days)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "premium_set"))


@router.message(Command("delpremium"))
async def del_premium(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /delpremium <user_id>")
        return
    user_id = int(parts[1])
    await app.storage.remove_premium(user_id, granted_by=message.from_user.id)
    await app.storage.log_admin_action(message.from_user.id, "delpremium", user_id=user_id)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "premium_removed"))


@router.message(Command("broadcast"))
async def start_broadcast(message: Message, state: FSMContext, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    await state.set_state(AdminBroadcastStates.waiting_message)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "broadcast_prompt"))


@router.message(AdminBroadcastStates.waiting_message)
async def do_broadcast(message: Message, state: FSMContext, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    ok = 0
    failed = 0
    for profile in app.storage.active_profiles():
        if profile.user_id == message.from_user.id:
            continue
        try:
            await message.bot.copy_message(chat_id=profile.user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            ok += 1
        except Exception:
            failed += 1
        await asyncio.sleep(app.settings.broadcast_delay_ms / 1000)
    await state.clear()
    await app.storage.log_admin_action(message.from_user.id, "broadcast", ok=ok, failed=failed)
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "broadcast_done", ok=ok, failed=failed))


@router.message(Command("reports"))
async def recent_reports(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    lang = get_user_language(app.storage, message.from_user.id)
    lines = [t(lang, "reports_title")]
    for report in app.storage.reports[:10]:
        lines.append(
            f"- {report.created_at:%Y-%m-%d %H:%M} | reporter={report.reporter_id} | target={report.target_user_id} | {report.reason.value}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("config"))
async def show_config(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    lang = get_user_language(app.storage, message.from_user.id)
    cfg = app.storage.get_config()
    await message.answer(f"{t(lang, 'config_title')}\n<pre>{cfg.model_dump_json(indent=2)}</pre>")


@router.message(Command("PremiumPrice"))
async def premium_price(message: Message, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    cfg = app.storage.get_config()
    lines = [t(get_user_language(app.storage, message.from_user.id), "premium_price_title")]
    for plan in cfg.premium_plans:
        lines.append(f"{plan.plan_id}. {plan.days} days • ⭐ {plan.stars}")
    await message.answer("\n".join(lines), reply_markup=premium_plans_keyboard())


@router.callback_query(F.data.startswith("premium_plan:"))
async def premium_plan_selected(callback: CallbackQuery, app: AppContext) -> None:
    if not await _admin_guard(callback, app):
        return
    plan_id = int(callback.data.split(":")[1])
    lang = get_user_language(app.storage, callback.from_user.id)
    await callback.message.answer(t(lang, "premium_edit_choose"), reply_markup=premium_edit_keyboard(plan_id))
    await callback.answer()


@router.callback_query(F.data.startswith("premium_edit:"))
async def premium_edit_selected(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    if not await _admin_guard(callback, app):
        return
    _, plan_id_raw, field = callback.data.split(":")
    plan_id = int(plan_id_raw)
    await state.set_state(PremiumPriceStates.waiting_value)
    await state.update_data(plan_id=plan_id, premium_edit_field=field)
    lang = get_user_language(app.storage, callback.from_user.id)
    await callback.message.answer(t(lang, "premium_edit_days" if field == "days" else "premium_edit_stars"))
    await callback.answer()


@router.message(PremiumPriceStates.waiting_value)
async def premium_edit_value(message: Message, state: FSMContext, app: AppContext) -> None:
    if not await _admin_guard(message, app):
        return
    data = await state.get_data()
    plan_id = data["plan_id"]
    field = data["premium_edit_field"]
    value = int((message.text or "").split()[-1])
    cfg = app.storage.get_config()
    plans = []
    for plan in cfg.premium_plans:
        if plan.plan_id == plan_id:
            if field == "days":
                plan = plan.model_copy(update={"days": value})
            else:
                plan = plan.model_copy(update={"stars": value})
        plans.append(plan)
    cfg = cfg.model_copy(update={"premium_plans": plans})
    await app.storage.update_config(cfg)
    await app.storage.log_admin_action(message.from_user.id, "premium_price_update", plan_id=plan_id, field=field, value=value)
    await state.clear()
    await message.answer(t(get_user_language(app.storage, message.from_user.id), "premium_plan_updated"))
