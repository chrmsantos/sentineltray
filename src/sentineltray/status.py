from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock


@dataclass(frozen=True)
class StatusSnapshot:
    running: bool
    paused: bool
    last_scan: str
    last_match: str
    last_match_at: str
    last_send: str
    last_error: str
    last_healthcheck: str
    uptime_seconds: int
    error_count: int


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._paused = False
        self._last_scan = ""
        self._last_match = ""
        self._last_match_at = ""
        self._last_send = ""
        self._last_error = ""
        self._last_healthcheck = ""
        self._uptime_seconds = 0
        self._error_count = 0

    def set_running(self, value: bool) -> None:
        with self._lock:
            self._running = value

    def set_paused(self, value: bool) -> None:
        with self._lock:
            self._paused = value

    def set_last_scan(self, value: str) -> None:
        with self._lock:
            self._last_scan = value

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

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(
                running=self._running,
                paused=self._paused,
                last_scan=self._last_scan,
                last_match=self._last_match,
                last_match_at=self._last_match_at,
                last_send=self._last_send,
                last_error=self._last_error,
                last_healthcheck=self._last_healthcheck,
                uptime_seconds=self._uptime_seconds,
                error_count=self._error_count,
            )


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        timestamp = datetime.fromisoformat(value)
        return timestamp.strftime("%d-%m-%Y - %H:%M")
    except ValueError:
        return value


def _format_next_check(last_scan: str, poll_interval_seconds: int | None) -> str:
    if not last_scan or not poll_interval_seconds:
        return ""
    try:
        timestamp = datetime.fromisoformat(last_scan)
        next_timestamp = timestamp + timedelta(seconds=int(poll_interval_seconds))
        return next_timestamp.strftime("%d-%m-%Y - %H:%M")
    except ValueError:
        return ""


def format_status(
    snapshot: StatusSnapshot,
    *,
    window_title_regex: str = "",
    phrase_regex: str = "",
    poll_interval_seconds: int | None = None,
) -> str:
    running = "sim" if snapshot.running else "nao"
    paused = "sim" if snapshot.paused else "nao"
    phrase_label = phrase_regex or "<qualquer texto>"
    window_label = window_title_regex or "<janela configurada>"
    last_scan = _format_timestamp(snapshot.last_scan)
    next_check = _format_next_check(snapshot.last_scan, poll_interval_seconds)
    last_identification = _format_timestamp(snapshot.last_match) or snapshot.last_match
    last_match_at = _format_timestamp(snapshot.last_match_at)
    lines = [
        f"Em execução: {running}",
        f"Pausado: {paused}",
        f"janela monitorada: {window_label}",
        f"texto monitorado: {phrase_label}",
        f"Última verificação: {last_scan}",
        f"próxima verificação: {next_check}",
        f"Última identificação: {last_identification}",
        f"Último match (momento): {last_match_at}",
        f"Último envio de alerta: {_format_timestamp(snapshot.last_send)}",
        f"Último erro registrado: {_format_timestamp(snapshot.last_error)}",
        f"Último resumo de saúde: {_format_timestamp(snapshot.last_healthcheck)}",
        f"Tempo ativo (segundos): {snapshot.uptime_seconds}",
        f"Total de erros: {snapshot.error_count}",
    ]
    return "\n".join(lines)
