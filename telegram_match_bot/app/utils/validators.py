from __future__ import annotations

import re


def validate_nickname(value: str, min_len: int = 2, max_len: int = 32) -> bool:
    value = value.strip()
    return min_len <= len(value) <= max_len


def validate_age(value: str) -> int | None:
    value = value.strip()
    if not value.isdigit():
        return None
    age = int(value)
    if 10 <= age <= 100:
        return age
    return None


def validate_region(value: str) -> bool:
    value = value.strip()
    return 2 <= len(value) <= 40


def validate_bio(value: str, min_len: int = 10, max_len: int = 280) -> bool:
    value = value.strip()
    return min_len <= len(value) <= max_len


def parse_interests(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,\n]", value) if part.strip()]
    normalized: list[str] = []
    seen: set[str] = set()
    for part in parts:
        clean = re.sub(r"\s+", " ", part)
        lower = clean.casefold()
        if lower in seen:
            continue
        seen.add(lower)
        normalized.append(clean[:24])
    if 1 <= len(normalized) <= 8:
        return normalized
    return []
