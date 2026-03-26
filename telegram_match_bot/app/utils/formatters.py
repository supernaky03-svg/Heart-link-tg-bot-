from __future__ import annotations

from html import escape
from typing import Any


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def profile_card(user: dict[str, Any]) -> str:
    interests = user.get("interests") or []
    if isinstance(interests, str):
        interests_text = interests
    else:
        interests_text = ", ".join(str(item) for item in interests) if interests else "-"
    username = user.get("username")
    username_line = f"\nTelegram: @{escape(username)}" if username else ""
    return (
        f"<b>{escape(user.get('nickname') or user.get('first_name') or 'Unknown')}</b>, {user.get('age') or '-'}\n"
        f"Gender: {escape(user.get('gender') or '-')}\n"
        f"Interested in: {escape(user.get('interested_in') or '-')}\n"
        f"Region: {escape(user.get('region') or '-')}\n"
        f"Bio: {escape(user.get('bio') or '-')}\n"
        f"Interests: {escape(interests_text)}"
        f"{username_line}"
    )


def admin_user_card(user: dict[str, Any]) -> str:
    return (
        f"<b>{escape(user.get('nickname') or user.get('first_name') or 'Unknown')}</b>\n"
        f"ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{escape(user.get('username') or '-')}\n"
        f"Profile complete: {yes_no(bool(user.get('is_profile_complete')))}\n"
        f"Banned: {yes_no(bool(user.get('is_banned')))}\n"
        f"Suspended: {yes_no(bool(user.get('is_suspended')))}\n"
        f"Hidden: {yes_no(bool(user.get('is_hidden')))}\n"
        f"Language: {escape(user.get('language') or 'en')}\n"
        f"Last seen: {escape(str(user.get('last_seen_at')))}"
    )


def report_card(report: dict[str, Any]) -> str:
    details = report.get("details") or "-"
    return (
        f"<b>Report #{report['id']}</b>\n"
        f"Reporter: @{escape(report.get('reporter_username') or report.get('reporter_nickname') or '-')}\n"
        f"Target: @{escape(report.get('target_username') or report.get('target_nickname') or '-')}\n"
        f"Reason: {escape(report.get('reason') or '-')}\n"
        f"Details: {escape(details)}\n"
        f"Created: {escape(str(report.get('created_at')))}"
    )
