from __future__ import annotations

from typing import Any

import asyncpg

from app.db.database import Database


class LikeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_likes,
                COUNT(*) FILTER (WHERE status='pending') AS pending_likes,
                COUNT(*) FILTER (WHERE status='matched') AS matched_likes
            FROM likes
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def create_skip(self, user_id: int, skipped_user_id: int) -> None:
        await self.db.execute(
            "INSERT INTO skips (user_id, skipped_user_id) VALUES ($1, $2)",
            user_id,
            skipped_user_id,
        )

    async def log_action(self, user_id: int, action_type: str) -> None:
        await self.db.execute(
            "INSERT INTO user_action_logs (user_id, action_type) VALUES ($1, $2)",
            user_id,
            action_type,
        )

    async def count_recent_actions(self, user_id: int, action_type: str, window_seconds: int) -> int:
        value = await self.db.fetchval(
            """
            SELECT COUNT(*)
            FROM user_action_logs
            WHERE user_id=$1
              AND action_type=$2
              AND created_at >= NOW() - ($3 || ' seconds')::interval
            """,
            user_id,
            action_type,
            window_seconds,
        )
        return int(value or 0)

    async def process_like(self, from_user_id: int, to_user_id: int) -> dict[str, Any]:
        if from_user_id == to_user_id:
            return {"result": "invalid_self"}

        conn = await self.db.acquire()
        try:
            async with conn.transaction():
                # Lock both user rows in a deterministic order to prevent race conditions.
                await conn.fetch(
                    "SELECT id FROM users WHERE id = ANY($1::bigint[]) ORDER BY id FOR UPDATE",
                    [from_user_id, to_user_id],
                )

                current_like = await conn.fetchrow(
                    "SELECT * FROM likes WHERE from_user_id=$1 AND to_user_id=$2 FOR UPDATE",
                    from_user_id,
                    to_user_id,
                )
                reciprocal_like = await conn.fetchrow(
                    "SELECT * FROM likes WHERE from_user_id=$1 AND to_user_id=$2 FOR UPDATE",
                    to_user_id,
                    from_user_id,
                )

                user1_id, user2_id = sorted((from_user_id, to_user_id))
                existing_match = await conn.fetchrow(
                    "SELECT * FROM matches WHERE user1_id=$1 AND user2_id=$2 FOR UPDATE",
                    user1_id,
                    user2_id,
                )

                if existing_match:
                    await conn.execute(
                        """
                        UPDATE likes SET status='matched', updated_at=NOW()
                        WHERE (from_user_id=$1 AND to_user_id=$2) OR (from_user_id=$2 AND to_user_id=$1)
                        """,
                        from_user_id,
                        to_user_id,
                    )
                    return {"result": "already_matched", "match": dict(existing_match)}

                if current_like and not reciprocal_like:
                    return {"result": "already_liked"}

                if not current_like:
                    current_like = await conn.fetchrow(
                        """
                        INSERT INTO likes (from_user_id, to_user_id, status)
                        VALUES ($1, $2, 'pending')
                        RETURNING *
                        """,
                        from_user_id,
                        to_user_id,
                    )

                if reciprocal_like:
                    match_row = await conn.fetchrow(
                        """
                        INSERT INTO matches (user1_id, user2_id, status)
                        VALUES ($1, $2, 'active')
                        ON CONFLICT (user1_id, user2_id) DO UPDATE SET status='active'
                        RETURNING *
                        """,
                        user1_id,
                        user2_id,
                    )
                    await conn.execute(
                        """
                        UPDATE likes SET status='matched', updated_at=NOW()
                        WHERE (from_user_id=$1 AND to_user_id=$2) OR (from_user_id=$2 AND to_user_id=$1)
                        """,
                        from_user_id,
                        to_user_id,
                    )
                    return {
                        "result": "matched",
                        "match": dict(match_row) if match_row else None,
                    }

                return {"result": "pending", "like": dict(current_like)}
        finally:
            await self.db.release(conn)

    async def list_matches_for_user(self, user_id: int) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT
                m.id AS match_id,
                m.created_at AS match_created_at,
                other.id AS other_user_id,
                other.nickname,
                other.username,
                other.region,
                other.age,
                other.gender
            FROM matches m
            JOIN users other
              ON other.id = CASE WHEN m.user1_id=$1 THEN m.user2_id ELSE m.user1_id END
            WHERE (m.user1_id=$1 OR m.user2_id=$1)
              AND m.status='active'
            ORDER BY m.created_at DESC
            """,
            user_id,
        )
        return [dict(row) for row in rows]

   async def discovery_candidate(self, user_id: int) -> dict[str, Any] | None:
    row = await self.db.fetchrow(
        """
        WITH me AS (
            SELECT * FROM users WHERE id=$1
        )
        SELECT
            u.*,
            (
                CASE
                    WHEN u.gender = (SELECT interested_in FROM me) THEN 1
                    ELSE 0
                END
                +
                CASE
                    WHEN (SELECT gender FROM me) = u.interested_in THEN 1
                    ELSE 0
                END
            ) AS compatibility_score,
            CASE
                WHEN s.id IS NULL THEN 0 ELSE 1
            END AS skipped_before,
            s.created_at AS last_skipped_at,
            CASE
                WHEN u.latitude IS NOT NULL
                     AND u.longitude IS NOT NULL
                     AND (SELECT latitude FROM me) IS NOT NULL
                     AND (SELECT longitude FROM me) IS NOT NULL
                THEN (
                    6371 * ACOS(
                        LEAST(
                            1.0,
                            GREATEST(
                                -1.0,
                                COS(RADIANS((SELECT latitude FROM me)))
                                * COS(RADIANS(u.latitude))
                                * COS(RADIANS(u.longitude) - RADIANS((SELECT longitude FROM me)))
                                +
                                SIN(RADIANS((SELECT latitude FROM me)))
                                * SIN(RADIANS(u.latitude))
                            )
                        )
                    )
                )
                ELSE NULL
            END AS distance_km
        FROM users u
        CROSS JOIN me
        LEFT JOIN likes sent_like
            ON sent_like.from_user_id = (SELECT id FROM me)
           AND sent_like.to_user_id = u.id
        LEFT JOIN matches m
            ON (
                m.user1_id = LEAST((SELECT id FROM me), u.id)
                AND m.user2_id = GREATEST((SELECT id FROM me), u.id)
            )
        LEFT JOIN LATERAL (
            SELECT id, created_at
            FROM skips
            WHERE user_id=(SELECT id FROM me)
              AND skipped_user_id=u.id
            ORDER BY created_at DESC
            LIMIT 1
        ) s ON TRUE
        WHERE u.id <> (SELECT id FROM me)
          AND u.is_profile_complete = TRUE
          AND u.is_banned = FALSE
          AND u.is_suspended = FALSE
          AND u.is_hidden = FALSE
          AND sent_like.id IS NULL
          AND m.id IS NULL
        ORDER BY
            compatibility_score DESC,
            CASE
                WHEN distance_km IS NULL THEN 0
                WHEN distance_km <= 10 THEN 3
                WHEN distance_km <= 50 THEN 2
                WHEN distance_km <= 150 THEN 1
                ELSE 0
            END DESC,
            skipped_before ASC,
            last_skipped_at ASC NULLS FIRST,
            COALESCE(distance_km, 999999) ASC,
            u.last_seen_at DESC NULLS LAST,
            random()
        LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None
