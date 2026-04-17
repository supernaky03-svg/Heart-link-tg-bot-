from __future__ import annotations

from datetime import datetime

from app.locales.translations import t
from app.models.records import PremiumPlan, UserProfileRecord
from app.utils.geo import format_distance, haversine_meters


def profile_preview_text(lang: str, profile: UserProfileRecord) -> str:
    return t(
        lang,
        "profile_preview",
        name=profile.name,
        age=profile.age,
        city=profile.city,
        bio=profile.bio,
    )


def discover_card_text(viewer: UserProfileRecord, target: UserProfileRecord) -> str:
    distance = "?"
    if viewer.latitude is not None and target.latitude is not None:
        meters = haversine_meters(viewer.latitude, viewer.longitude, target.latitude, target.longitude)
        distance = format_distance(meters)
    return t(
        viewer.language.value,
        "discover_card",
        name=target.name,
        age=target.age,
        city=target.city,
        distance=distance,
        bio=target.bio,
    )


def premium_text(lang: str, plans: list[PremiumPlan], premium_until: datetime | None) -> str:
    lines = [t(lang, "premium_title"), ""]
    for plan in plans:
        lines.append(f"{plan.plan_id}. {plan.days} days • ⭐ {plan.stars}")
    lines.append("")
    if premium_until:
        lines.append(t(lang, "premium_active_until", date=premium_until.strftime("%Y-%m-%d %H:%M UTC")))
    else:
        lines.append(t(lang, "premium_not_active"))
    return "\n".join(lines)
