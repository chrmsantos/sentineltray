from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class StatusSnapshot:
    running: bool
    last_scan: str
    last_match: str
    last_send: str
    last_error: str


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._last_scan = ""
        self._last_match = ""
        self._last_send = ""
        self._last_error = ""

    def set_running(self, value: bool) -> None:
        with self._lock:
            self._running = value

    def set_last_scan(self, value: str) -> None:
        with self._lock:
            self._last_scan = value

    def set_last_match(self, value: str) -> None:
        with self._lock:
            self._last_match = value

    def set_last_send(self, value: str) -> None:
        with self._lock:
            self._last_send = value

    def set_last_error(self, value: str) -> None:
        with self._lock:
            self._last_error = value

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(
                running=self._running,
                last_scan=self._last_scan,
                last_match=self._last_match,
                last_send=self._last_send,
                last_error=self._last_error,
            )


def format_status(snapshot: StatusSnapshot) -> str:
    running = "yes" if snapshot.running else "no"
    lines = [
        f"running: {running}",
        f"last_scan: {snapshot.last_scan}",
        f"last_match: {snapshot.last_match}",
        f"last_send: {snapshot.last_send}",
        f"last_error: {snapshot.last_error}",
    ]
    return "\n".join(lines)
