from __future__ import annotations

import csv
import ctypes
import hashlib
import importlib.metadata
import json
import logging
import os
import shutil
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
from .telemetry import JsonWriter
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def _get_idle_seconds() -> float:
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)) == 0:
        raise RuntimeError("GetLastInputInfo failed")
    tick = ctypes.windll.kernel32.GetTickCount()
    elapsed_ms = tick - info.dwTime
    return max(0.0, float(elapsed_ms) / 1000.0)


def _is_user_idle(min_seconds: int) -> bool:
    idle_seconds = _get_idle_seconds()
    return idle_seconds >= min_seconds


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


def _get_version() -> str:
    try:
        return importlib.metadata.version("sentineltray")
    except importlib.metadata.PackageNotFoundError:
        return __version_label__


def _get_release_date() -> str:
    return __release_date__


def _get_commit_hash() -> str:
    try:
        base = Path(__file__).resolve().parents[2]
        head_path = base / ".git" / "HEAD"
        if not head_path.exists():
            return ""
        ref = head_path.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = base / ".git" / ref.replace("ref:", "").strip()
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
        return ref
    except Exception:
        return ""


@dataclass
class Notifier:
    config: AppConfig
    status: StatusStore

    def __post_init__(self) -> None:
        self._detector = WindowTextDetector(
            self.config.window_title_regex,
            allow_window_restore=self.config.allow_window_restore,
        )
        self._sender = build_sender(self.config.email)
        self._state_path = Path(self.config.state_file)
        self._history = _load_state(self._state_path)
        self._last_sent = self._build_last_sent_map(self._history)
        self._started_at = datetime.now(timezone.utc)
        self._next_healthcheck = time.monotonic() + self.config.healthcheck_interval_seconds
        self._telemetry = JsonWriter(Path(self.config.telemetry_file))
        self._status_export = JsonWriter(Path(self.config.status_export_file))
        self._app_version = _get_version()
        self._release_date = _get_release_date()
        self._commit_hash = _get_commit_hash()
        self._update_config_checksum()

    def _reset_components(self) -> None:
        self._detector = WindowTextDetector(
            self.config.window_title_regex,
            allow_window_restore=self.config.allow_window_restore,
        )
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
            if self.config.log_only_mode:
                LOGGER.info("Log-only mode active, skipping send", extra={"category": "send"})
            else:
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
            if self.config.log_only_mode:
                LOGGER.info("Log-only mode active, skipping send", extra={"category": "send"})
            else:
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
            if self.config.log_only_mode:
                LOGGER.info("Log-only mode active, skipping send", extra={"category": "send"})
            else:
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
            "app_version": self._app_version,
            "release_date": self._release_date,
            "commit_hash": self._commit_hash,
            "running": snapshot.running,
            "paused": snapshot.paused,
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

        status_payload = {
            "running": snapshot.running,
            "paused": snapshot.paused,
            "last_scan": snapshot.last_scan,
            "last_match": snapshot.last_match,
            "last_send": snapshot.last_send,
            "last_error": snapshot.last_error,
            "last_healthcheck": snapshot.last_healthcheck,
            "uptime_seconds": snapshot.uptime_seconds,
            "error_count": snapshot.error_count,
        }
        try:
            self._status_export.write(status_payload)
        except Exception as exc:
            LOGGER.exception("Status export failed: %s", exc, extra={"category": "error"})

        self._write_status_csv(status_payload)

    def _write_status_csv(self, payload: dict[str, object]) -> None:
        path = Path(self.config.status_export_csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                for key, value in payload.items():
                    writer.writerow([key, value])
        except Exception as exc:
            LOGGER.exception("Status CSV export failed: %s", exc, extra={"category": "error"})

    def _update_config_checksum(self) -> None:
        try:
            user_root = os.environ.get("USERPROFILE")
            if not user_root:
                return
            config_path = Path(user_root) / "sentineltray" / "config.local.yaml"
            if not config_path.exists():
                return
            checksum = hashlib.sha256(config_path.read_bytes()).hexdigest()
            path = Path(self.config.config_checksum_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(checksum, encoding="utf-8")
        except Exception as exc:
            LOGGER.exception("Config checksum update failed: %s", exc, extra={"category": "error"})

    def _ensure_free_disk(self) -> None:
        try:
            base = Path(self.config.log_file).parent
            usage = shutil.disk_usage(base)
            free_mb = usage.free // (1024 * 1024)
            if free_mb < self.config.min_free_disk_mb:
                raise RuntimeError("Low disk space")
        except Exception as exc:
            raise RuntimeError(f"Low disk space: {exc}") from exc

    def _handle_watchdog(self, duration_seconds: float) -> None:
        if duration_seconds <= self.config.watchdog_timeout_seconds:
            return
        message = f"error: watchdog timeout after {duration_seconds:.1f}s"
        self._handle_error(message)
        if self.config.watchdog_restart:
            self._reset_components()
            LOGGER.info("Watchdog restart completed", extra={"category": "error"})

    def run_loop(self, stop_event: Event, pause_event: Event | None = None) -> None:
        setup_logging(
            self.config.log_file,
            log_level=self.config.log_level,
            log_console_level=self.config.log_console_level,
            log_console_enabled=self.config.log_console_enabled,
            log_max_bytes=self.config.log_max_bytes,
            log_backup_count=self.config.log_backup_count,
            log_run_files_keep=self.config.log_run_files_keep,
        )
        LOGGER.info(
            "SentinelTray started (beta %s, %s)",
            self._app_version,
            self._release_date,
            extra={"category": "startup"},
        )
        self.status.set_running(True)
        self.status.set_uptime_seconds(0)
        self._send_startup_test()
        self._update_telemetry()
        error_count = 0

        was_paused = False
        while not stop_event.is_set():
            if pause_event is not None and pause_event.is_set():
                if not was_paused:
                    LOGGER.info("Execution paused", extra={"category": "control"})
                was_paused = True
                self.status.set_paused(True)
                self._update_telemetry()
                stop_event.wait(0.5)
                continue
            if was_paused:
                LOGGER.info("Execution resumed", extra={"category": "control"})
            was_paused = False
            self.status.set_paused(False)
            started_at = time.monotonic()
            try:
                self._ensure_free_disk()
                if _is_user_idle(120):
                    self.scan_once()
                    self.status.set_last_error("")
                    error_count = 0
                else:
                    LOGGER.info(
                        "Skipping scan; user active",
                        extra={"category": "scan"},
                    )
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
        self.status.set_paused(False)


def run(config: AppConfig) -> None:
    status = StatusStore()
    notifier = Notifier(config=config, status=status)
    stop_event = Event()
    notifier.run_loop(stop_event)
