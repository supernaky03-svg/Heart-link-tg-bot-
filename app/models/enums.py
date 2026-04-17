from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    EN = "en"
    MY = "my"
    RU = "ru"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class LookingFor(str, Enum):
    MEN = "men"
    WOMEN = "women"
    EVERYONE = "everyone"


class MediaType(str, Enum):
    PHOTOS = "photos"
    VIDEO = "video"


class RecordType(str, Enum):
    USER_PROFILE = "USER_PROFILE"
    USER_SETTINGS = "USER_SETTINGS"
    USER_MEDIA = "USER_MEDIA"
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    PASS = "PASS"
    VIEW = "VIEW"
    MATCH = "MATCH"
    PREMIUM = "PREMIUM"
    REPORT = "REPORT"
    CONFIG = "CONFIG"
    ADMIN_LOG = "ADMIN_LOG"


class ReportReason(str, Enum):
    FAKE = "fake_profile"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate_content"
    UNDERAGE = "underage"
    HARASSMENT = "harassment"
    OTHER = "other"
