from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from .config import AppConfig
from .detector import WindowTextDetector
from .logging_setup import setup_logging
from .status import StatusStore
from .email_sender import build_sender
from .telemetry import TelemetryWriter

LOGGER = logging.getLogger(__name__)


def _load_state(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                now = _now_iso()
                return [{"text": str(item), "sent_at": now} for item in data]
            items: list[dict[str, str]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                sent_at = item.get("sent_at")
                if isinstance(text, str) and isinstance(sent_at, str):
                    items.append({"text": text, "sent_at": sent_at})
            return items
    except Exception:
        return []
    return []


def _save_state(path: Path, items: list[dict[str, str]]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def _to_ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


@dataclass
class Notifier:
    config: AppConfig
    status: StatusStore

    def __post_init__(self) -> None:
        self._detector = WindowTextDetector(self.config.window_title_regex)
        self._sender = build_sender(self.config.email)
        self._state_path = Path(self.config.state_file)
        self._history = _load_state(self._state_path)
        self._last_sent = self._build_last_sent_map(self._history)
        self._started_at = datetime.now(timezone.utc)
        self._next_healthcheck = time.monotonic() + self.config.healthcheck_interval_seconds
        self._telemetry = TelemetryWriter(Path(self.config.telemetry_file))

    def _reset_components(self) -> None:
        self._detector = WindowTextDetector(self.config.window_title_regex)
        self._sender = build_sender(self.config.email)

    def _build_last_sent_map(self, history: list[dict[str, str]]) -> dict[str, datetime]:
        last_sent: dict[str, datetime] = {}
        for item in history:
            text = item.get("text")
            sent_at = item.get("sent_at")
            if not isinstance(text, str) or not isinstance(sent_at, str):
                continue
            try:
                timestamp = datetime.fromisoformat(sent_at)
            except ValueError:
                continue
            last_sent[text] = timestamp
        return last_sent

    def scan_once(self) -> None:
        self.status.set_last_scan(_now_iso())
        matches = self._detector.find_matches(self.config.phrase_regex)
        normalized = [_normalize(text) for text in matches if text]
        now = datetime.now(timezone.utc)
        send_items: list[str] = []
        for text in normalized:
            last_sent = self._last_sent.get(text)
            if last_sent is None:
                send_items.append(text)
                continue
            age_seconds = int((now - last_sent).total_seconds())
            if age_seconds >= self.config.debounce_seconds:
                send_items.append(text)
            else:
                LOGGER.info(
                    "Debounce active for %s (age %s seconds)",
                    text,
                    age_seconds,
                    extra={"category": "send"},
                )

        if normalized:
            self.status.set_last_match(normalized[0])

        for text in send_items:
            self._sender.send(text)
            self.status.set_last_send(_now_iso())
            LOGGER.info("Sent message", extra={"category": "send"})
            sent_at = _now_iso()
            self._history.append({"text": text, "sent_at": sent_at})
            self._last_sent[text] = datetime.fromisoformat(sent_at)

        if len(self._history) > self.config.max_history:
            self._history = self._history[-self.config.max_history :]
            self._last_sent = self._build_last_sent_map(self._history)
            _save_state(self._state_path, self._history)
        elif send_items:
            _save_state(self._state_path, self._history)

    def _handle_error(self, message: str) -> None:
        safe_message = _to_ascii(message)
        self.status.set_last_error(safe_message)
        try:
            self._sender.send(safe_message)
            self.status.set_last_send(_now_iso())
            LOGGER.info("Sent error notification", extra={"category": "error"})
        except Exception as exc:
            LOGGER.exception(
                "Failed to send error notification: %s",
                exc,
                extra={"category": "error"},
            )

    def _send_startup_test(self) -> None:
        message = "info: startup test message"
        try:
            self._sender.send(message)
            self.status.set_last_send(_now_iso())
            LOGGER.info("Sent startup test message", extra={"category": "send"})
        except Exception as exc:
            error_message = f"error: startup test send failed: {exc}"
            self._handle_error(error_message)

    def _send_healthcheck(self) -> None:
        uptime_seconds = int((datetime.now(timezone.utc) - self._started_at).total_seconds())
        self.status.set_uptime_seconds(uptime_seconds)
        snapshot = self.status.snapshot()
        message = (
            "info: healthcheck "
            f"uptime_seconds={uptime_seconds} "
            f"last_scan={snapshot.last_scan} "
            f"last_send={snapshot.last_send} "
            f"last_error={snapshot.last_error}"
        )
        safe_message = _to_ascii(message)
        try:
            self._sender.send(safe_message)
            self.status.set_last_send(_now_iso())
            self.status.set_last_healthcheck(_now_iso())
            LOGGER.info("Sent healthcheck message", extra={"category": "send"})
        except Exception as exc:
            error_message = f"error: healthcheck send failed: {exc}"
            self._handle_error(error_message)

    def _compute_backoff_seconds(self, error_count: int) -> int:
        if error_count <= 0:
            return 0
        base = max(1, self.config.error_backoff_base_seconds)
        maximum = max(base, self.config.error_backoff_max_seconds)
        backoff = base * (2 ** (error_count - 1))
        return min(maximum, backoff)

    def _update_telemetry(self) -> None:
        snapshot = self.status.snapshot()
        payload = {
            "updated_at": _now_iso(),
            "running": snapshot.running,
            "uptime_seconds": snapshot.uptime_seconds,
            "last_scan": _to_ascii(snapshot.last_scan),
            "last_match": _to_ascii(snapshot.last_match),
            "last_send": _to_ascii(snapshot.last_send),
            "last_error": _to_ascii(snapshot.last_error),
            "last_healthcheck": _to_ascii(snapshot.last_healthcheck),
            "error_count": snapshot.error_count,
        }
        try:
            self._telemetry.write(payload)
        except Exception as exc:
            LOGGER.exception("Telemetry write failed: %s", exc, extra={"category": "error"})

    def _handle_watchdog(self, duration_seconds: float) -> None:
        if duration_seconds <= self.config.watchdog_timeout_seconds:
            return
        message = f"error: watchdog timeout after {duration_seconds:.1f}s"
        self._handle_error(message)
        if self.config.watchdog_restart:
            self._reset_components()
            LOGGER.info("Watchdog restart completed", extra={"category": "error"})

    def run_loop(self, stop_event: Event) -> None:
        setup_logging(self.config.log_file)
        LOGGER.info("SentinelTray started", extra={"category": "startup"})
        self.status.set_running(True)
        self.status.set_uptime_seconds(0)
        self._send_startup_test()
        self._update_telemetry()
        error_count = 0

        while not stop_event.is_set():
            started_at = time.monotonic()
            try:
                self.scan_once()
                self.status.set_last_error("")
                error_count = 0
            except Exception as exc:
                message = f"error: {exc}"
                self._handle_error(message)
                LOGGER.exception("Loop error: %s", exc, extra={"category": "error"})
                error_count += 1
                self.status.increment_error_count()
            finally:
                duration = time.monotonic() - started_at
                self._handle_watchdog(duration)

            self.status.set_uptime_seconds(
                int((datetime.now(timezone.utc) - self._started_at).total_seconds())
            )
            now = time.monotonic()
            if now >= self._next_healthcheck:
                self._send_healthcheck()
                self._next_healthcheck = now + self.config.healthcheck_interval_seconds

            self._update_telemetry()

            backoff_seconds = self._compute_backoff_seconds(error_count)
            wait_seconds = max(self.config.poll_interval_seconds, backoff_seconds)
            if backoff_seconds:
                LOGGER.info(
                    "Backoff enabled: %s seconds",
                    backoff_seconds,
                    extra={"category": "error"},
                )
            stop_event.wait(wait_seconds)

        self.status.set_running(False)


def run(config: AppConfig) -> None:
    status = StatusStore()
    notifier = Notifier(config=config, status=status)
    stop_event = Event()
    notifier.run_loop(stop_event)
