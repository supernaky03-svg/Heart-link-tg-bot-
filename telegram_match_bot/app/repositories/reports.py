from __future__ import annotations

from typing import Any

from app.db.database import Database


class ReportRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_report(
        self,
        reporter_id: int,
        target_user_id: int,
        reason: str,
        details: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO reports (reporter_id, target_user_id, reason, details)
            VALUES ($1, $2, $3, $4)
            """,
            reporter_id,
            target_user_id,
            reason,
            details,
        )

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_reports,
                COUNT(*) FILTER (WHERE status='open') AS open_reports
            FROM reports
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def list_open_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT
                r.*,
                reporter.username AS reporter_username,
                reporter.nickname AS reporter_nickname,
                target.username AS target_username,
                target.nickname AS target_nickname
            FROM reports r
            JOIN users reporter ON reporter.id = r.reporter_id
            JOIN users target ON target.id = r.target_user_id
            WHERE r.status='open'
            ORDER BY r.created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]

    async def get_report(self, report_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT
                r.*,
                reporter.username AS reporter_username,
                reporter.nickname AS reporter_nickname,
                target.username AS target_username,
                target.nickname AS target_nickname
            FROM reports r
            JOIN users reporter ON reporter.id = r.reporter_id
            JOIN users target ON target.id = r.target_user_id
            WHERE r.id=$1
            """,
            report_id,
        )
        return dict(row) if row else None

    async def review_report(self, report_id: int, admin_id: int, status: str) -> None:
        await self.db.execute(
            """
            UPDATE reports
            SET status=$3, reviewed_by=$2, reviewed_at=NOW()
            WHERE id=$1
            """,
            report_id,
            admin_id,
            status,
        )
