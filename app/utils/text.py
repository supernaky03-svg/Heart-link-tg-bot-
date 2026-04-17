from __future__ import annotations

import html
import re


def sanitize_text(value: str) -> str:
    value = value.replace("\x00", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def safe_html(value: str) -> str:
    return html.escape(value or "")
