from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import Settings
from app.models.enums import RecordType, ReportReason
from app.models.records import (
    AdminLogRecord,
    ConfigRecord,
    DislikeRecord,
    LikeRecord,
    MatchRecord,
    PassRecord,
    PremiumRecord,
    ReportRecord,
    UserMediaRecord,
    UserProfileRecord,
    UserSettingsRecord,
    ViewRecord,
)

logger = logging.getLogger(__name__)

RECORD_MODELS = {
    RecordType.USER_PROFILE.value: UserProfileRecord,
    RecordType.USER_SETTINGS.value: UserSettingsRecord,
    RecordType.USER_MEDIA.value: UserMediaRecord,
    RecordType.LIKE.value: LikeRecord,
    RecordType.DISLIKE.value: DislikeRecord,
    RecordType.PASS.value: PassRecord,
    RecordType.VIEW.value: ViewRecord,
    RecordType.MATCH.value: MatchRecord,
    RecordType.PREMIUM.value: PremiumRecord,
    RecordType.REPORT.value: ReportRecord,
    RecordType.CONFIG.value: ConfigRecord,
    RecordType.ADMIN_LOG.value: AdminLogRecord,
}


@dataclass
class StoredEnvelope:
    version: int
    record_type: str
    record_id: str
    message_id: int
    payload: Dict[str, Any]


class TelegramChannelStorage:
    PREFIX = "HLDB"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = TelegramClient(
            StringSession(settings.storage_session),
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )
        self._lock = asyncio.Lock()
        self._channel_entity = None
        self.latest_records: dict[str, dict[str, StoredEnvelope]] = defaultdict(dict)
        self.profiles: dict[int, UserProfileRecord] = {}
        self.settings_cache: dict[int, UserSettingsRecord] = {}
        self.likes: dict[tuple[int, int], LikeRecord] = {}
        self.dislikes: dict[tuple[int, int], DislikeRecord] = {}
        self.passes: dict[tuple[int, int], PassRecord] = {}
        self.views: dict[tuple[int, int], ViewRecord] = {}
        self.matches: dict[tuple[int, int], MatchRecord] = {}
        self.reports: list[ReportRecord] = []
        self.config: ConfigRecord | None = None
        self.message_index: dict[str, int] = {}

    async def connect(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError(
                    "STORAGE_SESSION is invalid or expired. Generate a new Telethon StringSession for the storage account."
                )
        logger.info("Telethon storage user client connected.")

    async def close(self) -> None:
        if self.client.is_connected():
            await self.client.disconnect()

    async def _get_channel_entity(self):
        if self._channel_entity is None:
            await self.client.get_dialogs()
            self._channel_entity = await self.client.get_entity(self.settings.private_db_channel_id)
        return self._channel_entity

    def _serialize(self, record: BaseModel, version: int) -> str:
        payload = json.dumps(record.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        header = f"{self.PREFIX}|{record.record_type.value}|{record.record_id}|{version}"
        return f"{header}\n{payload}"

    def _parse_message(self, text: str) -> Optional[tuple[str, str, int, dict[str, Any]]]:
        if not text or not text.startswith(f"{self.PREFIX}|"):
            return None
        try:
            header, payload = text.split("\n", 1)
            _, record_type, record_id, version_raw = header.split("|", 3)
            version = int(version_raw)
            data = json.loads(payload)
            return record_type, record_id, version, data
        except Exception:
            logger.exception("Failed to parse DB message")
            return None

    async def rebuild_cache(self) -> None:
        await self.connect()
        logger.info("Rebuilding cache from private DB channel %s", self.settings.private_db_channel_id)
        channel = await self._get_channel_entity()
        count = 0
        async for message in self.client.iter_messages(channel, reverse=True):
            parsed = self._parse_message(message.message or "")
            if not parsed:
                continue
            record_type, record_id, version, data = parsed
            env = StoredEnvelope(version=version, record_type=record_type, record_id=record_id, message_id=message.id, payload=data)
            current = self.latest_records[record_type].get(record_id)
            if current is None or version >= current.version:
                self.latest_records[record_type][record_id] = env
                self.message_index[f"{record_type}:{record_id}"] = message.id
            count += 1
        logger.info("Loaded %s channel-backed records", count)
        self._rebuild_indexes()
        if self.config is None:
            self.config = ConfigRecord.default()
            self.config.pass_ttl_hours = self.settings.discover_pass_ttl_hours
            await self.append_record(self.config)

    def _rebuild_indexes(self) -> None:
        self.profiles.clear()
        self.settings_cache.clear()
        self.likes.clear()
        self.dislikes.clear()
        self.passes.clear()
        self.views.clear()
        self.matches.clear()
        self.reports.clear()
        self.config = None

        for record_type, mapping in self.latest_records.items():
            for env in mapping.values():
                model = RECORD_MODELS[record_type].model_validate(env.payload)
                if record_type == RecordType.USER_PROFILE.value:
                    self.profiles[model.user_id] = model
                elif record_type == RecordType.USER_SETTINGS.value:
                    self.settings_cache[model.user_id] = model
                elif record_type == RecordType.LIKE.value:
                    self.likes[(model.source_user_id, model.target_user_id)] = model
                elif record_type == RecordType.DISLIKE.value:
                    self.dislikes[(model.source_user_id, model.target_user_id)] = model
                elif record_type == RecordType.PASS.value:
                    self.passes[(model.source_user_id, model.target_user_id)] = model
                elif record_type == RecordType.VIEW.value:
                    self.views[(model.viewer_user_id, model.target_user_id)] = model
                elif record_type == RecordType.MATCH.value:
                    self.matches[self._match_key(model.user_a, model.user_b)] = model
                elif record_type == RecordType.REPORT.value:
                    self.reports.append(model)
                elif record_type == RecordType.CONFIG.value:
                    self.config = model

        self.reports.sort(key=lambda r: r.created_at, reverse=True)

    async def append_record(self, record: BaseModel) -> int:
        async with self._lock:
            current = self.latest_records[record.record_type.value].get(record.record_id)
            version = 1 if current is None else current.version + 1
            body = self._serialize(record, version)
            channel = await self._get_channel_entity()
            message = await self.client.send_message(channel, body)
            env = StoredEnvelope(
                version=version,
                record_type=record.record_type.value,
                record_id=record.record_id,
                message_id=message.id,
                payload=record.model_dump(mode="json"),
            )
            self.latest_records[record.record_type.value][record.record_id] = env
            self.message_index[f"{record.record_type.value}:{record.record_id}"] = message.id
            self._rebuild_indexes()
            return message.id

    async def log_admin_action(self, admin_user_id: int, action: str, **meta: Any) -> None:
        record = AdminLogRecord(
            record_id=str(uuid.uuid4()),
            admin_user_id=admin_user_id,
            action=action,
            meta={k: str(v) for k, v in meta.items()},
        )
        await self.append_record(record)

    def _profile_record_id(self, user_id: int) -> str:
        return str(user_id)

    def _settings_record_id(self, user_id: int) -> str:
        return str(user_id)

    def _pair_record_id(self, left: int, right: int) -> str:
        return f"{left}:{right}"

    def _match_key(self, user_a: int, user_b: int) -> tuple[int, int]:
        return tuple(sorted((user_a, user_b)))

    async def save_user_settings(self, user_id: int, language: str, paused: bool | None = None, deleted: bool | None = None, last_candidate_id: int | None = None) -> UserSettingsRecord:
        current = self.settings_cache.get(user_id)
        record = UserSettingsRecord(
            record_id=self._settings_record_id(user_id),
            user_id=user_id,
            language=language,
            paused=paused if paused is not None else (current.paused if current else False),
            deleted=deleted if deleted is not None else (current.deleted if current else False),
            last_candidate_id=last_candidate_id if last_candidate_id is not None else (current.last_candidate_id if current else None),
        )
        await self.append_record(record)
        return record

    async def save_user_profile(self, profile: UserProfileRecord) -> UserProfileRecord:
        await self.append_record(profile)
        media_record = UserMediaRecord(
            record_id=str(profile.user_id),
            user_id=profile.user_id,
            media_type=profile.media_type,
            media_file_ids=profile.media_file_ids,
        )
        await self.append_record(media_record)
        return profile

    async def update_user_profile(self, user_id: int, **fields: Any) -> UserProfileRecord:
        current = self.get_user_profile(user_id)
        if not current:
            raise ValueError("Profile not found")
        new_data = current.model_dump()
        new_data.update(fields)
        new_data["record_id"] = self._profile_record_id(user_id)
        new_data["updated_at"] = datetime.now(timezone.utc)
        profile = UserProfileRecord.model_validate(new_data)
        await self.save_user_profile(profile)
        return profile

    def get_user_profile(self, user_id: int) -> Optional[UserProfileRecord]:
        profile = self.profiles.get(user_id)
        if not profile:
            return None
        if profile.premium_until and profile.premium_until <= datetime.now(timezone.utc):
            expired = profile.model_copy(update={"premium_until": None})
            self.profiles[user_id] = expired
            return expired
        return profile

    def get_user_settings(self, user_id: int) -> Optional[UserSettingsRecord]:
        return self.settings_cache.get(user_id)

    async def save_like(self, source_user_id: int, target_user_id: int, intro_message: str | None = None) -> LikeRecord:
        record = LikeRecord(
            record_id=self._pair_record_id(source_user_id, target_user_id),
            source_user_id=source_user_id,
            target_user_id=target_user_id,
            intro_message=intro_message,
        )
        await self.append_record(record)
        profile = self.get_user_profile(target_user_id)
        if profile:
            await self.update_user_profile(target_user_id, likes_received=profile.likes_received + 1)
        return record

    async def save_dislike(self, source_user_id: int, target_user_id: int) -> DislikeRecord:
        record = DislikeRecord(
            record_id=self._pair_record_id(source_user_id, target_user_id),
            source_user_id=source_user_id,
            target_user_id=target_user_id,
        )
        await self.append_record(record)
        return record

    async def save_pass(self, source_user_id: int, target_user_id: int) -> PassRecord:
        record = PassRecord(
            record_id=self._pair_record_id(source_user_id, target_user_id),
            source_user_id=source_user_id,
            target_user_id=target_user_id,
        )
        await self.append_record(record)
        return record

    async def save_view(self, viewer_user_id: int, target_user_id: int) -> ViewRecord:
        record = ViewRecord(
            record_id=self._pair_record_id(viewer_user_id, target_user_id),
            viewer_user_id=viewer_user_id,
            target_user_id=target_user_id,
        )
        await self.append_record(record)
        profile = self.get_user_profile(target_user_id)
        if profile:
            await self.update_user_profile(target_user_id, profile_views=profile.profile_views + 1)
        return record

    async def create_match(self, user_a: int, user_b: int) -> MatchRecord:
        key = self._match_key(user_a, user_b)
        if key in self.matches:
            return self.matches[key]
        record = MatchRecord(record_id=f"{key[0]}:{key[1]}", user_a=key[0], user_b=key[1])
        await self.append_record(record)
        for user_id in key:
            profile = self.get_user_profile(user_id)
            if profile:
                await self.update_user_profile(user_id, matches_count=profile.matches_count + 1)
        return record

    def has_match(self, user_a: int, user_b: int) -> bool:
        return self._match_key(user_a, user_b) in self.matches

    def has_like(self, source_user_id: int, target_user_id: int) -> bool:
        return (source_user_id, target_user_id) in self.likes

    def get_like(self, source_user_id: int, target_user_id: int) -> LikeRecord | None:
        return self.likes.get((source_user_id, target_user_id))

    def should_hide_passed(self, source_user_id: int, target_user_id: int) -> bool:
        record = self.passes.get((source_user_id, target_user_id))
        if not record:
            return False
        ttl = timedelta(hours=self.config.pass_ttl_hours if self.config else self.settings.discover_pass_ttl_hours)
        return datetime.now(timezone.utc) - record.created_at < ttl

    async def save_report(self, reporter_id: int, target_user_id: int | None, reason: ReportReason, text: str | None = None) -> ReportRecord:
        record = ReportRecord(
            record_id=str(uuid.uuid4()),
            reporter_id=reporter_id,
            target_user_id=target_user_id,
            reason=reason,
            text=text,
        )
        await self.append_record(record)
        if target_user_id is not None:
            profile = self.get_user_profile(target_user_id)
            if profile:
                await self.update_user_profile(target_user_id, reports_count=profile.reports_count + 1)
        return record

    async def update_config(self, config: ConfigRecord) -> ConfigRecord:
        config.record_id = "global"
        await self.append_record(config)
        return config

    def get_config(self) -> ConfigRecord:
        if self.config is None:
            self.config = ConfigRecord.default()
        return self.config

    async def grant_premium(self, user_id: int, days: int, granted_by: int | None = None) -> UserProfileRecord:
        profile = self.get_user_profile(user_id)
        if not profile:
            raise ValueError("Profile not found")
        base = profile.premium_until if profile.premium_until and profile.premium_until > datetime.now(timezone.utc) else datetime.now(timezone.utc)
        premium_until = base + timedelta(days=days)
        record = PremiumRecord(record_id=str(user_id), user_id=user_id, premium_until=premium_until, granted_by=granted_by)
        await self.append_record(record)
        return await self.update_user_profile(user_id, premium_until=premium_until)

    async def remove_premium(self, user_id: int, granted_by: int | None = None) -> UserProfileRecord:
        profile = self.get_user_profile(user_id)
        if not profile:
            raise ValueError("Profile not found")
        record = PremiumRecord(record_id=str(user_id), user_id=user_id, premium_until=datetime.now(timezone.utc), granted_by=granted_by)
        await self.append_record(record)
        return await self.update_user_profile(user_id, premium_until=None)

    def active_profiles(self) -> list[UserProfileRecord]:
        items = []
        for profile in self.profiles.values():
            settings = self.get_user_settings(profile.user_id)
            if not profile.is_active or profile.is_banned:
                continue
            if settings and (settings.paused or settings.deleted):
                continue
            items.append(profile)
        return items

    async def set_last_candidate(self, user_id: int, candidate_user_id: int | None) -> None:
        settings = self.get_user_settings(user_id)
        language = settings.language if settings else self.settings.default_language
        await self.save_user_settings(
            user_id=user_id,
            language=language,
            paused=settings.paused if settings else False,
            deleted=settings.deleted if settings else False,
            last_candidate_id=candidate_user_id,
        )
