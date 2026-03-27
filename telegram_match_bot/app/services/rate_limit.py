from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    def hit(self, user_id: int, action: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        key = (user_id, action)
        queue = self._events[key]
        threshold = now - window_seconds
        while queue and queue[0] < threshold:
            queue.popleft()
        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])))
            return False, retry_after
        queue.append(now)
        return True, 0

    def suspicious_mass_like(self, user_id: int) -> bool:
        allowed, _ = self.hit(user_id, "suspicious_like_probe", 41, 3600)
        return not allowed
