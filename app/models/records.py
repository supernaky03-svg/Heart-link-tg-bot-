from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Gender, Language, LookingFor, MediaType, RecordType, ReportReason


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PremiumPlan(BaseModel):
    plan_id: int
    days: int
    stars: int


class BaseRecord(BaseModel):
    record_type: RecordType
    record_id: str
    created_at: datetime = Field(default_factory=utcnow)


class UserSettingsRecord(BaseRecord):
    record_type: RecordType = RecordType.USER_SETTINGS
    record_id: str
    user_id: int
    language: Language = Language.EN
    paused: bool = False
    deleted: bool = False
    last_candidate_id: Optional[int] = None


class UserProfileRecord(BaseRecord):
    record_type: RecordType = RecordType.USER_PROFILE
    record_id: str
    user_id: int
    username: Optional[str] = None
    language: Language = Language.EN
    age: int
    gender: Gender
    looking_for: LookingFor
    city: str
    latitude: float
    longitude: float
    name: str
    bio: str
    media_type: MediaType
    media_file_ids: List[str]
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    is_active: bool = True
    is_banned: bool = False
    premium_until: Optional[datetime] = None
    profile_views: int = 0
    likes_received: int = 0
    matches_count: int = 0
    reports_count: int = 0

    @property
    def is_premium(self) -> bool:
        return bool(self.premium_until and self.premium_until > utcnow())

    @field_validator("media_file_ids")
    @classmethod
    def validate_media(cls, value: List[str]):
        if not value:
            raise ValueError("At least one media file_id is required")
        return value


class UserMediaRecord(BaseRecord):
    record_type: RecordType = RecordType.USER_MEDIA
    record_id: str
    user_id: int
    media_type: MediaType
    media_file_ids: List[str]


class LikeRecord(BaseRecord):
    record_type: RecordType = RecordType.LIKE
    record_id: str
    source_user_id: int
    target_user_id: int
    intro_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class ViewRecord(BaseRecord):
    record_type: RecordType = RecordType.VIEW
    record_id: str
    viewer_user_id: int
    target_user_id: int
    created_at: datetime = Field(default_factory=utcnow)


class DislikeRecord(BaseRecord):
    record_type: RecordType = RecordType.DISLIKE
    record_id: str
    source_user_id: int
    target_user_id: int
    created_at: datetime = Field(default_factory=utcnow)


class PassRecord(BaseRecord):
    record_type: RecordType = RecordType.PASS
    record_id: str
    source_user_id: int
    target_user_id: int
    created_at: datetime = Field(default_factory=utcnow)


class MatchRecord(BaseRecord):
    record_type: RecordType = RecordType.MATCH
    record_id: str
    user_a: int
    user_b: int
    created_at: datetime = Field(default_factory=utcnow)


class PremiumRecord(BaseRecord):
    record_type: RecordType = RecordType.PREMIUM
    record_id: str
    user_id: int
    premium_until: datetime
    granted_by: Optional[int] = None


class ReportRecord(BaseRecord):
    record_type: RecordType = RecordType.REPORT
    record_id: str
    reporter_id: int
    target_user_id: Optional[int] = None
    reason: ReportReason
    text: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class ConfigRecord(BaseRecord):
    record_type: RecordType = RecordType.CONFIG
    record_id: str = "global"
    premium_plans: List[PremiumPlan] = Field(default_factory=list)
    pass_ttl_hours: int = 48

    @classmethod
    def default(cls) -> "ConfigRecord":
        return cls(
            premium_plans=[
                PremiumPlan(plan_id=1, days=2, stars=20),
                PremiumPlan(plan_id=2, days=10, stars=150),
                PremiumPlan(plan_id=3, days=30, stars=400),
                PremiumPlan(plan_id=4, days=90, stars=1000),
            ],
            pass_ttl_hours=48,
        )


class AdminLogRecord(BaseRecord):
    record_type: RecordType = RecordType.ADMIN_LOG
    record_id: str
    admin_user_id: int
    action: str
    meta: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
