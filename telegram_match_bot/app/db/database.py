from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import asyncpg

from app.config import Settings


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool: asyncpg.Pool | None = None

    async def connect(self, retries: int = 8, base_delay: float = 1.5) -> None:
        attempt = 0
        last_error: Exception | None = None
        while attempt < retries:
            attempt += 1
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.settings.database_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    server_settings={"application_name": "telegram_match_bot"},
                )
                await self._init_schema()
                logger.info("Database connection established")
                return
            except Exception as exc:  # pragma: no cover - startup resilience
                last_error = exc
                logger.exception("Database connection failed on attempt %s/%s", attempt, retries)
                await asyncio.sleep(base_delay * attempt)
        raise RuntimeError("Could not connect to the database") from last_error

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(sql)

    def _require_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self.pool

    async def execute(self, query: str, *args: Any) -> str:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def acquire(self) -> asyncpg.Connection:
        pool = self._require_pool()
        return await pool.acquire()

    async def release(self, conn: asyncpg.Connection) -> None:
        pool = self._require_pool()
        await pool.release(conn)
