from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_item(raw: dict[str, Any], now: datetime) -> dict[str, object] | None:
    message = raw.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    created_at = raw.get("created_at")
    if not isinstance(created_at, str):
        created_at = now.isoformat()
    attempts = int(raw.get("attempts", 0))
    next_attempt_at = raw.get("next_attempt_at")
    if not isinstance(next_attempt_at, str):
        next_attempt_at = now.isoformat()
    return {
        "message": message,
        "created_at": created_at,
        "attempts": attempts,
        "next_attempt_at": next_attempt_at,
    }


def build_new_item(message: str, now: datetime) -> dict[str, object]:
    return {
        "message": message,
        "created_at": now.isoformat(),
        "attempts": 0,
        "next_attempt_at": now.isoformat(),
    }


def prune_items(
    items: list[dict[str, object]],
    *,
    now: datetime,
    max_items: int,
    max_age_seconds: int,
    max_attempts: int,
) -> list[dict[str, object]]:
    pruned: list[dict[str, object]] = []
    for item in items:
        created_raw = item.get("created_at")
        created_at = parse_timestamp(created_raw) if isinstance(created_raw, str) else None
        attempts = int(item.get("attempts", 0))
        if max_attempts and attempts > max_attempts:
            continue
        if max_age_seconds and created_at:
            if (now - created_at).total_seconds() > max_age_seconds:
                continue
        pruned.append(item)

    if max_items and len(pruned) > max_items:
        pruned = pruned[-max_items:]
    return pruned


def compute_next_attempt(now: datetime, *, attempts: int, retry_base_seconds: int) -> datetime:
    if retry_base_seconds <= 0:
        return now
    delay = retry_base_seconds * (2 ** max(0, attempts - 1))
    return now + timedelta(seconds=delay)


def compute_oldest_age_seconds(items: list[dict[str, object]], now: datetime) -> int:
    created_times = [
        parse_timestamp(item.get("created_at"))
        for item in items
    ]
    created_times = [value for value in created_times if value]
    if not created_times:
        return 0
    oldest = min(created_times)
    return int((now - oldest).total_seconds())
