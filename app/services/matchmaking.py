from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from app.models.enums import Gender, LookingFor
from app.models.records import UserProfileRecord
from app.services.storage import TelegramChannelStorage
from app.utils.geo import haversine_meters


def _compatible(viewer: UserProfileRecord, target: UserProfileRecord) -> bool:
    if viewer.user_id == target.user_id:
        return False
    if not target.is_active or target.is_banned:
        return False
    if viewer.looking_for == LookingFor.MEN and target.gender != Gender.MALE:
        return False
    if viewer.looking_for == LookingFor.WOMEN and target.gender != Gender.FEMALE:
        return False
    if target.looking_for == LookingFor.MEN and viewer.gender != Gender.MALE:
        return False
    if target.looking_for == LookingFor.WOMEN and viewer.gender != Gender.FEMALE:
        return False
    return True


def _score(viewer: UserProfileRecord, target: UserProfileRecord) -> float:
    completeness = 0.0
    completeness += 1.0 if target.bio else 0.0
    completeness += min(len(target.media_file_ids), 3) * 0.4
    completeness += 0.5 if target.city else 0.0

    premium_boost = 2.5 if target.is_premium else 0.0

    hours_since_update = max((datetime.now(timezone.utc) - target.updated_at).total_seconds() / 3600.0, 1.0)
    recency = max(0.0, 2.0 - min(hours_since_update / 72.0, 2.0))

    distance_boost = 0.0
    if viewer.latitude is not None and target.latitude is not None:
        meters = haversine_meters(viewer.latitude, viewer.longitude, target.latitude, target.longitude)
        distance_boost = max(0.0, 2.0 - min(meters / 50000.0, 2.0))

    fairness_seed = f"{viewer.user_id}:{target.user_id}:{datetime.now(timezone.utc).date().isoformat()}".encode()
    fairness_hash = int(hashlib.sha256(fairness_seed).hexdigest()[:8], 16) / 0xFFFFFFFF
    fairness = fairness_hash * 0.75

    return completeness + premium_boost + recency + distance_boost + fairness


def next_candidate(storage: TelegramChannelStorage, viewer_user_id: int) -> Optional[UserProfileRecord]:
    viewer = storage.get_user_profile(viewer_user_id)
    if not viewer:
        return None
    candidates: list[tuple[float, UserProfileRecord]] = []
    for profile in storage.active_profiles():
        if not _compatible(viewer, profile):
            continue
        if storage.has_match(viewer.user_id, profile.user_id):
            continue
        if storage.has_like(viewer.user_id, profile.user_id):
            continue
        if (viewer.user_id, profile.user_id) in storage.dislikes:
            continue
        if storage.should_hide_passed(viewer.user_id, profile.user_id):
            continue
        candidates.append((_score(viewer, profile), profile))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]
