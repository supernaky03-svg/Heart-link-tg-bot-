from __future__ import annotations

import json

from typing import Any

import asyncpg

from app.db.database import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language: str,
        is_admin: bool,
    ) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO users (telegram_id, username, first_name, language, language_chosen, is_admin, last_seen_at, updated_at)
            VALUES ($1, $2, $3, $4, FALSE, $5, NOW(), NOW())
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                is_admin = users.is_admin OR EXCLUDED.is_admin,
                last_seen_at = NOW(),
                updated_at = NOW()
            RETURNING *
            """,
            telegram_id,
            username,
            first_name,
            language,
            is_admin,
        )
        return dict(row) if row else {}

    async def update_language(self, telegram_id: int, language: str) -> None:
        await self.db.execute(
            "UPDATE users SET language=$2, language_chosen=TRUE, updated_at=NOW() WHERE telegram_id=$1",
            telegram_id,
            language,
        )

    async def get_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow("SELECT * FROM users WHERE telegram_id=$1", telegram_id)
        return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
        return dict(row) if row else None

    async def search_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_by_telegram_id(telegram_id)

    async def search_by_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.lstrip("@").lower()
        row = await self.db.fetchrow(
            "SELECT * FROM users WHERE LOWER(username)=$1",
            normalized,
        )
        return dict(row) if row else None

    async def set_profile(
        self,
        telegram_id: int,
        *,
        nickname: str,
        age: int,
        gender: str,
        interested_in: str,
        bio: str,
        interests: list[str],
        profile_photo_file_id: str,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            UPDATE users
            SET nickname=$2,
                age=$3,
                gender=$4,
                interested_in=$5,
                region=NULL,
                bio=$6,
                interests=$7::jsonb,
                profile_photo_file_id=$8,
                latitude=$9,
                longitude=$10,
                is_profile_complete=TRUE,
                updated_at=NOW()
            WHERE telegram_id=$1
            RETURNING *
            """,
            telegram_id,
            nickname,
            age,
            gender,
            interested_in,
            bio,
            json.dumps(interests),
            profile_photo_file_id,
            latitude,
            longitude,
        )
        return dict(row) if row else None

    async def set_hidden(self, target_user_id: int, hidden: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_hidden=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            hidden,
        )

    async def set_ban(self, target_user_id: int, banned: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_banned=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            banned,
        )

    async def set_suspend(self, target_user_id: int, suspended: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_suspended=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            suspended,
        )

    async def set_notification_matches(self, telegram_id: int, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE users SET notification_matches=$2, updated_at=NOW() WHERE telegram_id=$1",
            telegram_id,
            enabled,
        )

    async def list_recent_signups(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]

    async def list_recently_active(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            "SELECT * FROM users ORDER BY last_seen_at DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]

    async def iterate_broadcast_targets(self) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT telegram_id, language, is_banned, is_suspended
            FROM users
            WHERE is_banned=FALSE
            ORDER BY id ASC
            """
        )
        return [dict(row) for row in rows]

    async def complete_profiles_count(self) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_profile_complete=TRUE"
            )
            or 0
        )

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_users,
                COUNT(*) FILTER (WHERE is_profile_complete) AS complete_profiles,
                COUNT(*) FILTER (WHERE is_banned) AS banned_users,
                COUNT(*) FILTER (WHERE is_suspended) AS suspended_users,
                COUNT(*) FILTER (WHERE last_seen_at >= NOW() - INTERVAL '24 hours') AS active_users_24h
            FROM users
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def log_admin_action(
        self,
        admin_id: int | None,
        target_user_id: int | None,
        action_type: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        conn: asyncpg.Connection | None = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        if conn:
            await conn.execute(
                """
                INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason, metadata)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                admin_id,
                target_user_id,
                action_type,
                reason,
                payload,
            )
            return
        await self.db.execute(
            """
            INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            admin_id,
            target_user_id,
            action_type,
            reason,
            payload,
        )
