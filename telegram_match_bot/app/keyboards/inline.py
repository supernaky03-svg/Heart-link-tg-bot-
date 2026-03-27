from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import I18n


def language_keyboard(i18n: I18n) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
            for code, name in i18n.available_languages()
        ]
    )


def username_recheck_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "username_recheck"), callback_data="recheck_username")]
        ]
    )


def browse_keyboard(i18n: I18n, language: str, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "like"), callback_data=f"browse:like:{target_user_id}"),
                InlineKeyboardButton(text=i18n.t(language, "next"), callback_data=f"browse:skip:{target_user_id}"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "report"), callback_data=f"browse:report:{target_user_id}")],
            [InlineKeyboardButton(text=i18n.t(language, "back_to_menu"), callback_data="browse:back")],
        ]
    )


def profile_gender_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_male"), callback_data="profile_gender:male"),
                InlineKeyboardButton(text=i18n.t(language, "gender_female"), callback_data="profile_gender:female"),
            ],
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_non_binary"), callback_data="profile_gender:non_binary"),
                InlineKeyboardButton(text=i18n.t(language, "gender_other"), callback_data="profile_gender:other"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def profile_interest_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_male"), callback_data="profile_interest:male"),
                InlineKeyboardButton(text=i18n.t(language, "gender_female"), callback_data="profile_interest:female"),
            ],
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_non_binary"), callback_data="profile_interest:non_binary"),
                InlineKeyboardButton(text=i18n.t(language, "gender_other"), callback_data="profile_interest:other"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "interested_any"), callback_data="profile_interest:any")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def photo_skip_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "skip_photo"), callback_data="profile_skip_photo")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def profile_confirm_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "profile_confirm"), callback_data="profile_confirm")],
            [InlineKeyboardButton(text=i18n.t(language, "profile_restart"), callback_data="profile_restart")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def settings_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "change_language"), callback_data="settings:language")],
            [InlineKeyboardButton(text=i18n.t(language, "edit_profile"), callback_data="settings:edit_profile")],
            [InlineKeyboardButton(text=i18n.t(language, "recheck_username"), callback_data="settings:recheck_username")],
            [InlineKeyboardButton(text=i18n.t(language, "toggle_match_notifications"), callback_data="settings:toggle_notifications")],
        ]
    )


def report_reason_keyboard(i18n: I18n, language: str, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_spam"), callback_data=f"report_reason:{target_user_id}:spam")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_fake"), callback_data=f"report_reason:{target_user_id}:fake_profile")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_harassment"), callback_data=f"report_reason:{target_user_id}:harassment")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_inappropriate"), callback_data=f"report_reason:{target_user_id}:inappropriate_content")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_other"), callback_data=f"report_reason:{target_user_id}:other")],
        ]
    )


def admin_panel_keyboard(i18n: I18n, language: str, maintenance_enabled: bool) -> InlineKeyboardMarkup:
    maintenance_text = (
        i18n.t(language, "admin_maintenance_off") if maintenance_enabled else i18n.t(language, "admin_maintenance_on")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "admin_stats"), callback_data="admin:stats")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_search"), callback_data="admin:search")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_reports"), callback_data="admin:reports")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_broadcast"), callback_data="admin:broadcast")],
            [InlineKeyboardButton(text=maintenance_text, callback_data="admin:maintenance_toggle")],
        ]
    )


def admin_user_actions_keyboard(i18n: I18n, language: str, user: dict) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.t(language, "unban_user") if user.get("is_banned") else i18n.t(language, "ban_user"),
                callback_data=f"admin_user:ban_toggle:{user['id']}",
            ),
            InlineKeyboardButton(
                text=i18n.t(language, "unsuspend_user") if user.get("is_suspended") else i18n.t(language, "suspend_user"),
                callback_data=f"admin_user:suspend_toggle:{user['id']}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=i18n.t(language, "unhide_profile") if user.get("is_hidden") else i18n.t(language, "hide_profile"),
                callback_data=f"admin_user:hide_toggle:{user['id']}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_review_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Review", callback_data=f"admin_report:review:{report_id}"),
                InlineKeyboardButton(text="❌ Dismiss", callback_data=f"admin_report:dismiss:{report_id}"),
            ]
        ]
    )
