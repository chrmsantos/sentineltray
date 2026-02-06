from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock


@dataclass(frozen=True)
class StatusSnapshot:
    running: bool
    last_scan: str
    last_scan_result: str
    last_match: str
    last_match_at: str
    last_send: str
    last_error: str
    last_healthcheck: str
    uptime_seconds: int
    error_count: int
    email_queue: dict[str, int]
    monitor_failures: dict[str, int]
    breaker_active_count: int


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._last_scan = ""
        self._last_scan_result = ""
        self._last_match = ""
        self._last_match_at = ""
        self._last_send = ""
        self._last_error = ""
        self._last_healthcheck = ""
        self._uptime_seconds = 0
        self._error_count = 0
        self._email_queue = {
            "queued": 0,
            "sent": 0,
            "failed": 0,
            "deferred": 0,
            "oldest_age_seconds": 0,
        }
        self._monitor_failures: dict[str, int] = {}
        self._monitor_breakers_active: dict[str, bool] = {}

    def set_running(self, value: bool) -> None:
        with self._lock:
            self._running = value

    def set_last_scan(self, value: str) -> None:
        with self._lock:
            self._last_scan = value

    def set_last_scan_result(self, value: str) -> None:
        with self._lock:
            self._last_scan_result = value

    def set_last_match(self, value: str) -> None:
        with self._lock:
            self._last_match = value

    def set_last_match_at(self, value: str) -> None:
        with self._lock:
            self._last_match_at = value

    def set_last_send(self, value: str) -> None:
        with self._lock:
            self._last_send = value

    def set_last_error(self, value: str) -> None:
        with self._lock:
            self._last_error = value

    def set_last_healthcheck(self, value: str) -> None:
        with self._lock:
            self._last_healthcheck = value

    def set_uptime_seconds(self, value: int) -> None:
        with self._lock:
            self._uptime_seconds = value

    def increment_error_count(self) -> None:
        with self._lock:
            self._error_count += 1

    def set_email_queue_stats(self, value: dict[str, int]) -> None:
        with self._lock:
            self._email_queue = dict(value)

    def set_monitor_state(self, key: str, *, failure_count: int, breaker_active: bool) -> None:
        with self._lock:
            self._monitor_failures[key] = max(0, int(failure_count))
            self._monitor_breakers_active[key] = bool(breaker_active)

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            breaker_active_count = sum(1 for active in self._monitor_breakers_active.values() if active)
            return StatusSnapshot(
                running=self._running,
                last_scan=self._last_scan,
                last_scan_result=self._last_scan_result,
                last_match=self._last_match,
                last_match_at=self._last_match_at,
                last_send=self._last_send,
                last_error=self._last_error,
                last_healthcheck=self._last_healthcheck,
                uptime_seconds=self._uptime_seconds,
                error_count=self._error_count,
                email_queue=dict(self._email_queue),
                monitor_failures=dict(self._monitor_failures),
                breaker_active_count=breaker_active_count,
            )


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        timestamp = datetime.fromisoformat(value)
        return timestamp.strftime("%d-%m-%Y - %H:%M")
    except ValueError:
        return value


def format_timestamp(value: str) -> str:
    return _format_timestamp(value)


def _format_next_check(last_scan: str, poll_interval_seconds: int | None) -> str:
    if not last_scan or not poll_interval_seconds:
        return ""
    try:
        timestamp = datetime.fromisoformat(last_scan)
        next_timestamp = timestamp + timedelta(seconds=int(poll_interval_seconds))
        return next_timestamp.strftime("%d-%m-%Y - %H:%M")
    except ValueError:
        return ""


def _format_failure_summary(failures: dict[str, int]) -> str:
    if not failures:
        return ""
    items = [(key, count) for key, count in failures.items() if count > 0]
    if not items:
        return ""
    items.sort(key=lambda item: item[1], reverse=True)
    summary_parts = []
    for key, count in items[:3]:
        label = key if len(key) <= 32 else f"{key[:29]}..."
        summary_parts.append(f"{label}={count}")
    return ", ".join(summary_parts)


def format_status(
    snapshot: StatusSnapshot,
    *,
    window_title_regex: str = "",
    phrase_regex: str = "",
    poll_interval_seconds: int | None = None,
) -> str:
    running = "yes" if snapshot.running else "no"
    phrase_label = phrase_regex or "<any text>"
    window_label = window_title_regex or "<configured window>"
    last_scan = _format_timestamp(snapshot.last_scan)
    next_check = _format_next_check(snapshot.last_scan, poll_interval_seconds)
    last_identification = _format_timestamp(snapshot.last_match) or snapshot.last_match
    last_match_at = _format_timestamp(snapshot.last_match_at)
    failure_summary = _format_failure_summary(snapshot.monitor_failures) or "none"
    lines = [
        f"Running: {running}",
        f"Monitored window: {window_label}",
        f"Monitored text: {phrase_label}",
        f"Last check: {last_scan}",
        f"Next check: {next_check}",
        f"Last detection: {last_identification}",
        f"Last match timestamp: {last_match_at}",
        f"Last alert sent: {_format_timestamp(snapshot.last_send)}",
        f"Last error recorded: {_format_timestamp(snapshot.last_error)}",
        f"Last health summary: {_format_timestamp(snapshot.last_healthcheck)}",
        f"Email queue pending: {snapshot.email_queue.get('queued', 0)}",
        f"Circuit breakers active: {snapshot.breaker_active_count}",
        f"Monitor failures: {failure_summary}",
        f"Uptime (seconds): {snapshot.uptime_seconds}",
        f"Total errors: {snapshot.error_count}",
    ]
    return "\n".join(lines)
