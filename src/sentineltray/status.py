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
    last_healthcheck: str
    uptime_seconds: int
    error_count: int


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._last_scan = ""
        self._last_match = ""
        self._last_send = ""
        self._last_error = ""
        self._last_healthcheck = ""
        self._uptime_seconds = 0
        self._error_count = 0

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

    def set_last_healthcheck(self, value: str) -> None:
        with self._lock:
            self._last_healthcheck = value

    def set_uptime_seconds(self, value: int) -> None:
        with self._lock:
            self._uptime_seconds = value

    def increment_error_count(self) -> None:
        with self._lock:
            self._error_count += 1

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(
                running=self._running,
                last_scan=self._last_scan,
                last_match=self._last_match,
                last_send=self._last_send,
                last_error=self._last_error,
                last_healthcheck=self._last_healthcheck,
                uptime_seconds=self._uptime_seconds,
                error_count=self._error_count,
            )


def format_status(snapshot: StatusSnapshot) -> str:
    running = "sim" if snapshot.running else "nao"
    lines = [
        f"executando: {running}",
        f"ultima_verificacao: {snapshot.last_scan}",
        f"ultima_correspondencia: {snapshot.last_match}",
        f"ultimo_envio: {snapshot.last_send}",
        f"ultimo_erro: {snapshot.last_error}",
        f"ultimo_healthcheck: {snapshot.last_healthcheck}",
        f"tempo_ativo_segundos: {snapshot.uptime_seconds}",
        f"erros_total: {snapshot.error_count}",
    ]
    return "\n".join(lines)
