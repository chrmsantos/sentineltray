from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock


@dataclass(frozen=True)
class StatusSnapshot:
    running: bool
    paused: bool
    last_scan: str
    last_match: str
    last_send: str
    last_report_send: str
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
        self._last_send = ""
        self._last_report_send = ""
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

    def set_last_send(self, value: str) -> None:
        with self._lock:
            self._last_send = value

    def set_last_report_send(self, value: str) -> None:
        with self._lock:
            self._last_report_send = value

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
                last_send=self._last_send,
                last_report_send=self._last_report_send,
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


def format_status(
    snapshot: StatusSnapshot,
    *,
    window_title_regex: str = "",
    phrase_regex: str = "",
) -> str:
    running = "sim" if snapshot.running else "nao"
    paused = "sim" if snapshot.paused else "nao"
    phrase_label = phrase_regex or "<qualquer texto>"
    window_label = window_title_regex or "<janela configurada>"
    lines = [
        f"Em execução: {running}",
        f"Pausado: {paused}",
        f"Última verificação: {_format_timestamp(snapshot.last_scan)}",
        (
            "Última incidência de "
            f"{phrase_label} encontrada em {window_label}: "
            f"{_format_timestamp(snapshot.last_match)}"
        ),
        f"Último envio de alerta: {_format_timestamp(snapshot.last_send)}",
        f"Último envio de relatório: {_format_timestamp(snapshot.last_report_send)}",
        f"Último erro registrado: {_format_timestamp(snapshot.last_error)}",
        f"Último resumo de saúde: {_format_timestamp(snapshot.last_healthcheck)}",
        f"Tempo ativo (segundos): {snapshot.uptime_seconds}",
        f"Total de erros: {snapshot.error_count}",
    ]
    return "\n".join(lines)
