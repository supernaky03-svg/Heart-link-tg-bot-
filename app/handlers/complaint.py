from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards.inline import report_reason_keyboard
from app.keyboards.reply import skip_keyboard
from app.locales.translations import parse_report_reason, t
from app.models.enums import ReportReason
from app.services.localization import get_user_language
from app.services.notifier import notify_admins
from app.states import ComplaintStates
from app.utils.text import sanitize_text

router = Router(name="complaint")


@router.message(lambda m: (m.text or "").strip() in {t("en", "menu_complain"), t("my", "menu_complain"), t("ru", "menu_complain")})
async def manual_complaint_entry(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await state.set_state(ComplaintStates.waiting_target)
    await message.answer(t(lang, "complain_intro"))


@router.callback_query(F.data.startswith("report:"))
async def report_from_profile(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    target_user_id = int(callback.data.split(":")[1])
    lang = get_user_language(app.storage, callback.from_user.id)
    await state.set_state(ComplaintStates.waiting_reason)
    await state.update_data(target_user_id=target_user_id)
    await callback.message.answer(t(lang, "complain_reason"), reply_markup=report_reason_keyboard(lang, target_user_id))
    await callback.answer()


@router.message(ComplaintStates.waiting_target)
async def manual_complaint_target(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    try:
        target_user_id = int((message.text or "").strip())
    except Exception:
        await message.answer(t(lang, "manual_report_invalid"))
        return
    await state.set_state(ComplaintStates.waiting_reason)
    await state.update_data(target_user_id=target_user_id)
    await message.answer(t(lang, "complain_reason"), reply_markup=report_reason_keyboard(lang, target_user_id))


@router.callback_query(F.data.startswith("report_reason:"))
async def report_reason_selected(callback: CallbackQuery, state: FSMContext, app: AppContext) -> None:
    _, target_raw, reason_raw = callback.data.split(":")
    target_user_id = int(target_raw) or None
    lang = get_user_language(app.storage, callback.from_user.id)
    await state.set_state(ComplaintStates.waiting_text)
    await state.update_data(target_user_id=target_user_id, report_reason=reason_raw)
    await callback.message.answer(t(lang, "complain_text"), reply_markup=skip_keyboard(lang))
    await callback.answer()


@router.message(ComplaintStates.waiting_text)
async def complaint_text(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    data = await state.get_data()
    text = None
    if (message.text or "") != t(lang, "btn_skip"):
        text = sanitize_text(message.text or "")
    reason = ReportReason(data["report_reason"])
    target_user_id = data.get("target_user_id")
    report = await app.storage.save_report(message.from_user.id, target_user_id, reason, text)
    await notify_admins(
        message.bot,
        app.settings.admin_ids,
        f"🚨 New report\nReporter: {report.reporter_id}\nTarget: {report.target_user_id}\nReason: {reason.value}\nText: {report.text or '-'}",
    )
    await state.clear()
    await message.answer(t(lang, "complain_saved"))
