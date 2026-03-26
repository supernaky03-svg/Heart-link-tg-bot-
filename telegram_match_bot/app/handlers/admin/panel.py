from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.filters.admin import AdminFilter
from app.keyboards.inline import admin_panel_keyboard, admin_user_actions_keyboard, report_review_keyboard
from app.services.admin import collect_stats
from app.services.app_context import AppContext
from app.utils.formatters import admin_user_card, report_card
from app.utils.states import AdminBroadcastFlow, AdminSearchFlow


router = Router(name="admin_panel")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def command_admin(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    maintenance_enabled = await app.app_settings.is_maintenance_mode()
    await message.answer(
        app.i18n.t(db_user.get("language"), "admin_panel"),
        reply_markup=admin_panel_keyboard(app.i18n, db_user.get("language"), maintenance_enabled),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    stats = await collect_stats(app)
    recent_signups = await app.users.list_recent_signups(limit=5)
    recent_active = await app.users.list_recently_active(limit=5)
    text = app.i18n.t(db_user.get("language"), "admin_stats_text", **stats)
    if recent_signups:
        text += "\n\n<b>Recent signups</b>\n" + "\n".join(
            f"• {user.get('nickname') or user.get('first_name') or 'Unknown'} (@{user.get('username') or '-'})"
            for user in recent_signups
        )
    if recent_active:
        text += "\n\n<b>Recently active</b>\n" + "\n".join(
            f"• {user.get('nickname') or user.get('first_name') or 'Unknown'} (@{user.get('username') or '-'})"
            for user in recent_active
        )
    await callback.message.answer(text)


@router.callback_query(F.data == "admin:search")
async def admin_search(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminSearchFlow.waiting_query)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "admin_user_prompt"))


@router.message(AdminSearchFlow.waiting_query)
async def admin_search_input(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    query = (message.text or "").strip()
    user = None
    if query.isdigit():
        user = await app.users.search_by_telegram_id(int(query))
    else:
        user = await app.users.search_by_username(query)
    await state.clear()
    if not user:
        await message.answer(app.i18n.t(db_user.get("language"), "admin_user_not_found"))
        return
    await message.answer(
        admin_user_card(user),
        reply_markup=admin_user_actions_keyboard(app.i18n, db_user.get("language"), user),
    )


@router.callback_query(F.data.startswith("admin_user:"))
async def admin_user_action(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    _, action, target_id_str = callback.data.split(":", 2)
    target_id = int(target_id_str)
    target = await app.users.get_by_id(target_id)
    if not target:
        await callback.answer(app.i18n.t(db_user.get("language"), "admin_user_not_found"), show_alert=True)
        return

    if action == "ban_toggle":
        await app.users.set_ban(target_id, not bool(target.get("is_banned")))
        await app.users.log_admin_action(db_user["id"], target_id, "ban_toggle")
    elif action == "suspend_toggle":
        await app.users.set_suspend(target_id, not bool(target.get("is_suspended")))
        await app.users.log_admin_action(db_user["id"], target_id, "suspend_toggle")
    elif action == "hide_toggle":
        await app.users.set_hidden(target_id, not bool(target.get("is_hidden")))
        await app.users.log_admin_action(db_user["id"], target_id, "hide_toggle")
    updated = await app.users.get_by_id(target_id)
    await callback.answer(app.i18n.t(db_user.get("language"), "admin_action_done"))
    if updated:
        await callback.message.answer(
            admin_user_card(updated),
            reply_markup=admin_user_actions_keyboard(app.i18n, db_user.get("language"), updated),
        )


@router.callback_query(F.data == "admin:reports")
async def admin_reports(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    reports = await app.reports.list_open_reports(limit=10)
    if not reports:
        await callback.message.answer(app.i18n.t(db_user.get("language"), "no_open_reports"))
        return
    await callback.message.answer(app.i18n.t(db_user.get("language"), "recent_reports"))
    for report in reports:
        await callback.message.answer(report_card(report), reply_markup=report_review_keyboard(report["id"]))


@router.callback_query(F.data.startswith("admin_report:"))
async def admin_report_action(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    _, action, report_id_str = callback.data.split(":", 2)
    report_id = int(report_id_str)
    report = await app.reports.get_report(report_id)
    if not report:
        await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
        return
    status = "reviewed" if action == "review" else "dismissed"
    await app.reports.review_report(report_id, db_user["id"], status)
    await app.users.log_admin_action(db_user["id"], report["target_user_id"], f"report_{status}")
    await callback.answer(app.i18n.t(db_user.get("language"), "admin_action_done"))


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminBroadcastFlow.waiting_message)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "admin_broadcast_prompt"))


@router.message(AdminBroadcastFlow.waiting_message)
async def admin_broadcast_message(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    text = (message.text or "").strip()
    await state.clear()
    sent = 0
    failed = 0
    for user in await app.users.iterate_broadcast_targets():
        if user.get("is_suspended"):
            continue
        try:
            await app.bot.send_message(user["telegram_id"], text)  # type: ignore[attr-defined]
            sent += 1
        except Exception:
            failed += 1
    await app.users.log_admin_action(db_user["id"], None, "broadcast", metadata={"sent": sent, "failed": failed})
    await message.answer(app.i18n.t(db_user.get("language"), "admin_broadcast_done", sent=sent, failed=failed))


@router.callback_query(F.data == "admin:maintenance_toggle")
async def admin_toggle_maintenance(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    current = await app.app_settings.is_maintenance_mode()
    new_value = not current
    await app.app_settings.set_maintenance_mode(new_value)
    await app.users.log_admin_action(db_user["id"], None, "maintenance_toggle", metadata={"enabled": new_value})
    await callback.answer(app.i18n.t(db_user.get("language"), "maintenance_enabled" if new_value else "maintenance_disabled"))
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "admin_panel"),
        reply_markup=admin_panel_keyboard(app.i18n, db_user.get("language"), new_value),
    )
