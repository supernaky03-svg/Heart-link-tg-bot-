from __future__ import annotations

from app.services.app_context import AppContext


async def collect_stats(app: AppContext) -> dict[str, int]:
    user_counts = await app.users.counts()
    like_counts = await app.likes.counts()
    report_counts = await app.reports.counts()
    total_matches = int(await app.db.fetchval("SELECT COUNT(*) FROM matches WHERE status='active'") or 0)
    return {
        **user_counts,
        **like_counts,
        **report_counts,
        "total_matches": total_matches,
    }
