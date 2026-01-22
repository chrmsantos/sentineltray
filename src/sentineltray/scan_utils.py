from __future__ import annotations

from datetime import datetime
from typing import Iterable


def dedupe_items(items: Iterable[str]) -> tuple[list[str], int]:
    deduped: list[str] = []
    seen: set[str] = set()
    removed = 0
    for item in items:
        if item in seen:
            removed += 1
            continue
        seen.add(item)
        deduped.append(item)
    return deduped, removed


def filter_debounce(
    items: Iterable[str],
    last_sent: dict[str, datetime],
    debounce_seconds: int,
    now: datetime,
) -> tuple[list[str], list[tuple[str, int]]]:
    if debounce_seconds <= 0:
        return list(items), []

    selected: list[str] = []
    skipped: list[tuple[str, int]] = []
    for text in items:
        sent_at = last_sent.get(text)
        if sent_at is None:
            selected.append(text)
            continue
        age_seconds = int((now - sent_at).total_seconds())
        if age_seconds >= debounce_seconds:
            selected.append(text)
        else:
            skipped.append((text, age_seconds))
    return selected, skipped


def filter_min_repeat(
    items: Iterable[str],
    last_sent: dict[str, datetime],
    min_repeat_seconds: int,
    now: datetime,
) -> tuple[list[str], list[tuple[str, int]]]:
    if min_repeat_seconds <= 0:
        return list(items), []

    selected: list[str] = []
    skipped: list[tuple[str, int]] = []
    for text in items:
        sent_at = last_sent.get(text)
        if sent_at is None:
            selected.append(text)
            continue
        age_seconds = int((now - sent_at).total_seconds())
        if age_seconds >= min_repeat_seconds:
            selected.append(text)
        else:
            skipped.append((text, age_seconds))
    return selected, skipped
