from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales.translations import t
from app.models.enums import ReportReason


def discover_actions_keyboard(lang: str, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_love"), callback_data=f"react:love:{target_user_id}"),
                InlineKeyboardButton(text=t(lang, "btn_love_msg"), callback_data=f"react:love_msg:{target_user_id}"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_dislike"), callback_data=f"react:dislike:{target_user_id}"),
                InlineKeyboardButton(text=t(lang, "btn_pass"), callback_data=f"react:pass:{target_user_id}"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_report"), callback_data=f"report:{target_user_id}")],
        ]
    )


def profile_draft_edit_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_age"), callback_data="draft_edit:age"),
            InlineKeyboardButton(text=t(lang, "btn_edit_gender"), callback_data="draft_edit:gender"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_looking_for"), callback_data="draft_edit:looking_for"),
            InlineKeyboardButton(text=t(lang, "btn_edit_city"), callback_data="draft_edit:city"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_location"), callback_data="draft_edit:location"),
            InlineKeyboardButton(text=t(lang, "btn_edit_name"), callback_data="draft_edit:name"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_bio"), callback_data="draft_edit:bio"),
            InlineKeyboardButton(text=t(lang, "btn_edit_media"), callback_data="draft_edit:media"),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_edit_language"), callback_data="draft_edit:language")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_edit_keyboard(lang: str, paused: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_age"), callback_data="edit:age"),
            InlineKeyboardButton(text=t(lang, "btn_edit_gender"), callback_data="edit:gender"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_looking_for"), callback_data="edit:looking_for"),
            InlineKeyboardButton(text=t(lang, "btn_edit_city"), callback_data="edit:city"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_location"), callback_data="edit:location"),
            InlineKeyboardButton(text=t(lang, "btn_edit_name"), callback_data="edit:name"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_edit_bio"), callback_data="edit:bio"),
            InlineKeyboardButton(text=t(lang, "btn_edit_media"), callback_data="edit:media"),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_edit_language"), callback_data="edit:language")],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_resume") if paused else t(lang, "btn_pause"),
                callback_data="profile:toggle_pause",
            ),
            InlineKeyboardButton(text=t(lang, "btn_delete"), callback_data="profile:delete"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_reason_keyboard(lang: str, target_user_id: int | None) -> InlineKeyboardMarkup:
    rows = []
    for reason in ReportReason:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, f"reason_{reason.value}"),
                    callback_data=f"report_reason:{target_user_id or 0}:{reason.value}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_plans_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="1", callback_data="premium_plan:1")],
        [InlineKeyboardButton(text="2", callback_data="premium_plan:2")],
        [InlineKeyboardButton(text="3", callback_data="premium_plan:3")],
        [InlineKeyboardButton(text="4", callback_data="premium_plan:4")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_edit_keyboard(plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Edit Days", callback_data=f"premium_edit:{plan_id}:days"),
                InlineKeyboardButton(text="Edit Stars", callback_data=f"premium_edit:{plan_id}:stars"),
            ]
        ]
    )
