from __future__ import annotations

import json

from typing import Any

from app.db.database import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_json(self, key: str, default: Any = None) -> Any:
        row = await self.db.fetchrow("SELECT value FROM app_settings WHERE key=$1", key)
        if not row:
            return default
        return row["value"]

    async def set_json(self, key: str, value: Any) -> None:
        await self.db.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
            """,
            key,
            json.dumps(value),
        )

    async def is_maintenance_mode(self) -> bool:
        value = await self.get_json("maintenance_mode", False)
        return bool(value)

    async def set_maintenance_mode(self, enabled: bool) -> None:
        await self.set_json("maintenance_mode", enabled)
