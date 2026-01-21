from __future__ import annotations

import csv
import io
import ctypes
import hashlib
import importlib.metadata
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from .config import AppConfig, MonitorConfig, get_project_root, get_user_data_dir
from .detector import WindowTextDetector, WindowUnavailableError
from .logging_setup import sanitize_text, setup_logging
from .status import StatusStore
from .email_sender import EmailAuthError, EmailQueued, QueueingEmailSender, build_sender
from .telemetry import JsonWriter, atomic_write_text
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


@dataclass
class MonitorRuntime:
    key: str
    config: MonitorConfig
    detector: WindowTextDetector
    sender: object
    last_sent: dict[str, datetime] = field(default_factory=dict)
    email_disabled: bool = False
    failure_count: int = 0
    breaker_until: float = 0.0
    last_window_ok_at: str = ""
    last_window_error_at: str = ""
    last_error_notification_at: float = 0.0
    last_send_queued: bool = False


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
    atomic_write_text(
        path,
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def _to_ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _summarize_text(text: str) -> str:
    cleaned = _normalize(text or "")
    if not cleaned:
        return ""
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
    return f"texto(len={len(cleaned)}, sha={digest})"


def _hash_value(value: str) -> str:
    cleaned = _normalize(value or "")
    if not cleaned:
        return ""
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def _safe_status_text(text: str) -> str:
    if not text:
        return ""
    return sanitize_text(_to_ascii(text))


def _get_version() -> str:
    try:
        return importlib.metadata.version("sentineltray")
    except importlib.metadata.PackageNotFoundError:
        return __version_label__


def _get_release_date() -> str:
    return __release_date__


def _get_commit_hash() -> str:
    try:
        base = get_project_root()
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
        self._monitors = self._build_monitors()
        self._state_path = Path(self.config.state_file)
        self._history = _load_state(self._state_path)
        for monitor in self._monitors:
            monitor.last_sent = self._build_last_sent_map(self._history, monitor.key)
        self._started_at = datetime.now(timezone.utc)
        self._next_healthcheck = time.monotonic() + self.config.healthcheck_interval_seconds
        self._next_queue_drain = time.monotonic() + 30
        self._telemetry = JsonWriter(Path(self.config.telemetry_file))
        self._status_export = JsonWriter(Path(self.config.status_export_file))
        self._app_version = _get_version()
        self._release_date = _get_release_date()
        self._commit_hash = _get_commit_hash()
        self._telemetry_write_errors = 0
        self._status_export_errors = 0
        self._status_csv_errors = 0
        self._state_write_errors = 0
        self._last_scan_error = False
        self._last_error_notification_at = 0.0
        self._queue_stats = {
            "queued": 0,
            "sent": 0,
            "failed": 0,
            "deferred": 0,
            "oldest_age_seconds": 0,
        }
        self._sender = None
        self._update_config_checksum()

    def _reset_components(self) -> None:
        for monitor in self._monitors:
            monitor.detector = WindowTextDetector(
                monitor.config.window_title_regex,
                allow_window_restore=self.config.allow_window_restore,
                log_throttle_seconds=self.config.log_throttle_seconds,
            )
            monitor.sender = build_sender(
                monitor.config.email,
                queue_path=self._queue_path_for_monitor(monitor.key, len(self._monitors)),
                queue_max_items=self.config.email_queue_max_items,
                queue_max_age_seconds=self.config.email_queue_max_age_seconds,
                queue_max_attempts=self.config.email_queue_max_attempts,
                queue_retry_base_seconds=self.config.email_queue_retry_base_seconds,
            )
            monitor.email_disabled = False
            monitor.failure_count = 0
            monitor.breaker_until = 0.0

    def _build_last_sent_map(
        self, history: list[dict[str, str]], monitor_key: str | None
    ) -> dict[str, datetime]:
        last_sent: dict[str, datetime] = {}
        for item in history:
            text = item.get("text")
            sent_at = item.get("sent_at")
            item_monitor = item.get("monitor")
            if not isinstance(text, str) or not isinstance(sent_at, str):
                continue
            if monitor_key and item_monitor not in (None, monitor_key):
                continue
            try:
                timestamp = datetime.fromisoformat(sent_at)
            except ValueError:
                continue
            last_sent[text] = timestamp
        return last_sent

    def _build_monitors(self) -> list[MonitorRuntime]:
        monitors = self.config.monitors
        if not monitors:
            monitors = [
                MonitorConfig(
                    window_title_regex=self.config.window_title_regex,
                    phrase_regex=self.config.phrase_regex,
                    email=self.config.email,
                )
            ]

        runtimes: list[MonitorRuntime] = []
        monitor_count = len(monitors)
        for monitor in monitors:
            key = f"{monitor.window_title_regex}|{monitor.phrase_regex}"
            runtimes.append(
                MonitorRuntime(
                    key=key,
                    config=monitor,
                    detector=WindowTextDetector(
                        monitor.window_title_regex,
                        allow_window_restore=self.config.allow_window_restore,
                        log_throttle_seconds=self.config.log_throttle_seconds,
                    ),
                    sender=build_sender(
                        monitor.email,
                        queue_path=self._queue_path_for_monitor(key, monitor_count),
                        queue_max_items=self.config.email_queue_max_items,
                        queue_max_age_seconds=self.config.email_queue_max_age_seconds,
                        queue_max_attempts=self.config.email_queue_max_attempts,
                        queue_retry_base_seconds=self.config.email_queue_retry_base_seconds,
                    ),
                )
            )
        return runtimes

    def _queue_path_for_monitor(self, monitor_key: str, monitor_count: int) -> Path:
        base = Path(self.config.email_queue_file)
        if monitor_count <= 1:
            return base
        suffix = base.suffix or ".json"
        stem = base.stem
        digest = hashlib.sha256(monitor_key.encode("utf-8")).hexdigest()[:8]
        return base.with_name(f"{stem}-{digest}{suffix}")

    def _send_message(
        self,
        monitor: "MonitorRuntime",
        message: str,
        *,
        category: str,
        force_send: bool = False,
    ) -> bool:
        if monitor.email_disabled:
            LOGGER.warning(
                "Email disabled after authentication failure; skipping send",
                extra={"category": category},
            )
            return False
        if self.config.log_only_mode and not force_send:
            LOGGER.info(
                "Log-only mode active, skipping send",
                extra={"category": category},
            )
            return False
        sender = self._sender or monitor.sender
        try:
            monitor.last_send_queued = False
            sender.send(message)
            return True
        except EmailQueued:
            monitor.last_send_queued = True
            LOGGER.info("Message queued for retry", extra={"category": category})
            return True
        except EmailAuthError as exc:
            monitor.email_disabled = True
            self.status.set_last_error(
                _safe_status_text(f"error: smtp auth failed: {exc}")
            )
            LOGGER.error(
                "SMTP authentication failed; disabling email notifications",
                extra={"category": category},
            )
            return False

    def _compute_monitor_backoff_seconds(self, failure_count: int) -> int:
        if failure_count <= 0:
            return 0
        base = max(1, self.config.window_error_backoff_base_seconds)
        maximum = max(base, self.config.window_error_backoff_max_seconds)
        backoff = base * (2 ** (failure_count - 1))
        return min(maximum, backoff)

    def _should_notify_error(self, last_notification_at: float) -> bool:
        cooldown = max(0, self.config.error_notification_cooldown_seconds)
        if cooldown == 0:
            return True
        return (time.monotonic() - last_notification_at) >= cooldown

    def _handle_monitor_error(self, monitor: MonitorRuntime, message: str) -> None:
        monitor.failure_count += 1
        monitor.last_window_error_at = _now_iso()
        self.status.set_last_error(_safe_status_text(message))
        if self._should_notify_error(monitor.last_error_notification_at):
            sent_any = False
            for current in self._monitors:
                if current.key != monitor.key:
                    continue
                if self._send_message(current, message, category="error", force_send=True):
                    sent_any = True
            if sent_any:
                monitor.last_error_notification_at = time.monotonic()
                self.status.set_last_send(_now_iso())

        if monitor.failure_count >= self.config.window_error_circuit_threshold:
            breaker_seconds = max(0, self.config.window_error_circuit_seconds)
            monitor.breaker_until = max(
                monitor.breaker_until, time.monotonic() + breaker_seconds
            )
            LOGGER.warning(
                "Circuit breaker active for monitor %s (%ss)",
                _summarize_text(monitor.key),
                breaker_seconds,
                extra={"category": "scan"},
            )
            if breaker_seconds > 0:
                critical_message = (
                    "error: monitor em pausa por "
                    f"{breaker_seconds}s (muitas falhas consecutivas)"
                )
                for current in self._monitors:
                    if current.key != monitor.key:
                        continue
                    self._send_message(
                        current,
                        critical_message,
                        category="error",
                        force_send=True,
                    )
        else:
            backoff_seconds = self._compute_monitor_backoff_seconds(monitor.failure_count)
            if backoff_seconds:
                monitor.breaker_until = max(
                    monitor.breaker_until, time.monotonic() + backoff_seconds
                )

    def scan_once(self) -> None:
        self.status.set_last_scan(_now_iso())
        any_match = False
        self._last_scan_error = False
        for monitor in self._monitors:
            now_mono = time.monotonic()
            if monitor.breaker_until and now_mono < monitor.breaker_until:
                LOGGER.info(
                    "Skipping scan; circuit breaker active for monitor",
                    extra={"category": "scan"},
                )
                continue
            try:
                matches = monitor.detector.find_matches(monitor.config.phrase_regex)
                monitor.failure_count = 0
                monitor.breaker_until = 0.0
                monitor.last_window_ok_at = _now_iso()
            except WindowUnavailableError as exc:
                message = f"error: janela indisponível: {exc}"
                self._handle_monitor_error(monitor, message)
                self._last_scan_error = True
                continue
            except Exception as exc:
                message = f"error: {exc}"
                self._handle_monitor_error(monitor, message)
                LOGGER.exception("Scan error: %s", exc, extra={"category": "error"})
                self._last_scan_error = True
                continue

            normalized = [_normalize(text) for text in matches if text]
            if normalized:
                deduped: list[str] = []
                seen: set[str] = set()
                for text in normalized:
                    if text in seen:
                        continue
                    seen.add(text)
                    deduped.append(text)
                if len(deduped) != len(normalized):
                    LOGGER.info(
                        "Deduplicated %s repeated matches in scan",
                        len(normalized) - len(deduped),
                        extra={"category": "scan"},
                    )
                normalized = deduped
            if self.config.send_repeated_matches:
                send_items = list(normalized)
            else:
                now = datetime.now(timezone.utc)
                send_items = []
                for text in normalized:
                    last_sent = monitor.last_sent.get(text)
                    if last_sent is None:
                        send_items.append(text)
                        continue
                    age_seconds = int((now - last_sent).total_seconds())
                    if age_seconds >= self.config.debounce_seconds:
                        send_items.append(text)
                    else:
                        summary = _summarize_text(text)
                        LOGGER.info(
                            "Debounce active for %s (age %s seconds)",
                            summary,
                            age_seconds,
                            extra={"category": "send"},
                        )

            if send_items and self.config.min_repeat_seconds > 0:
                now = datetime.now(timezone.utc)
                repeat_filtered: list[str] = []
                for text in send_items:
                    last_sent = monitor.last_sent.get(text)
                    if last_sent is None:
                        repeat_filtered.append(text)
                        continue
                    age_seconds = int((now - last_sent).total_seconds())
                    if age_seconds >= self.config.min_repeat_seconds:
                        repeat_filtered.append(text)
                    else:
                        summary = _summarize_text(text)
                        LOGGER.info(
                            "Min repeat window active for %s (age %s seconds)",
                            summary,
                            age_seconds,
                            extra={"category": "send"},
                        )
                send_items = repeat_filtered

            if normalized:
                any_match = True
                self.status.set_last_match(_summarize_text(normalized[0]))
                self.status.set_last_match_at(_now_iso())

            for text in send_items:
                if self._send_message(monitor, text, category="send", force_send=True):
                    self.status.set_last_send(_now_iso())
                    if monitor.last_send_queued:
                        LOGGER.info("Queued message", extra={"category": "send"})
                    else:
                        LOGGER.info("Sent message", extra={"category": "send"})
                    sent_at = _now_iso()
                    self._history.append(
                        {"text": text, "sent_at": sent_at, "monitor": monitor.key}
                    )
                    monitor.last_sent[text] = datetime.fromisoformat(sent_at)

        if len(self._history) > self.config.max_history:
            self._history = self._history[-self.config.max_history :]
            for monitor in self._monitors:
                monitor.last_sent = self._build_last_sent_map(self._history, monitor.key)
            self._persist_state()
        elif any_match:
            self._persist_state()

    def _persist_state(self) -> None:
        try:
            _save_state(self._state_path, self._history)
        except Exception as exc:
            self._state_write_errors += 1
            LOGGER.exception(
                "State persistence failed: %s",
                exc,
                extra={"category": "error"},
            )

    def _handle_error(self, message: str) -> None:
        safe_message = _safe_status_text(message)
        self.status.set_last_error(safe_message)
        try:
            if self.config.log_only_mode:
                LOGGER.info(
                    "Log-only mode active; sending error notification anyway",
                    extra={"category": "error"},
                )
            sent_any = False
            if self._should_notify_error(self._last_error_notification_at):
                for monitor in self._monitors:
                    if self._send_message(
                        monitor,
                        safe_message,
                        category="error",
                        force_send=True,
                    ):
                        sent_any = True
            if sent_any:
                self._last_error_notification_at = time.monotonic()
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
            sent_any = False
            sent_direct = False
            queued_any = False
            for monitor in self._monitors:
                if self._send_message(monitor, message, category="send", force_send=True):
                    sent_any = True
                    if monitor.last_send_queued:
                        queued_any = True
                    else:
                        sent_direct = True
            if sent_any or self.config.log_only_mode:
                self.status.set_last_send(_now_iso())
                if sent_direct:
                    LOGGER.info("Sent startup test message", extra={"category": "send"})
                elif queued_any:
                    LOGGER.info("Queued startup test message", extra={"category": "send"})
        except Exception as exc:
            error_message = f"error: startup test send failed: {exc}"
            self._handle_error(error_message)

    def _send_healthcheck(self) -> None:
        uptime_seconds = int((datetime.now(timezone.utc) - self._started_at).total_seconds())
        self.status.set_uptime_seconds(uptime_seconds)
        snapshot = self.status.snapshot()
        match_age_seconds = 0
        if snapshot.last_match_at:
            try:
                last_match_at = datetime.fromisoformat(snapshot.last_match_at)
                match_age_seconds = int((datetime.now(timezone.utc) - last_match_at).total_seconds())
            except ValueError:
                match_age_seconds = 0
        message = (
            "info: healthcheck "
            f"uptime_seconds={uptime_seconds} "
            f"last_scan={snapshot.last_scan} "
            f"last_match_age_seconds={match_age_seconds} "
            f"last_send={snapshot.last_send} "
            f"last_error={snapshot.last_error}"
        )
        safe_message = _safe_status_text(message)
        try:
            sent_any = False
            sent_direct = False
            queued_any = False
            for monitor in self._monitors:
                if self._send_message(monitor, safe_message, category="send"):
                    sent_any = True
                    if monitor.last_send_queued:
                        queued_any = True
                    else:
                        sent_direct = True
            if sent_any or self.config.log_only_mode:
                self.status.set_last_send(_now_iso())
                self.status.set_last_healthcheck(_now_iso())
                if sent_direct:
                    LOGGER.info("Sent healthcheck message", extra={"category": "send"})
                elif queued_any:
                    LOGGER.info("Queued healthcheck message", extra={"category": "send"})
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
        match_age_seconds = 0
        if snapshot.last_match_at:
            try:
                last_match_at = datetime.fromisoformat(snapshot.last_match_at)
                match_age_seconds = int((datetime.now(timezone.utc) - last_match_at).total_seconds())
            except ValueError:
                match_age_seconds = 0
        monitor_payload = []
        for monitor in self._monitors:
            breaker_remaining = max(0.0, monitor.breaker_until - time.monotonic())
            monitor_payload.append(
                {
                    "monitor_key_hash": _hash_value(monitor.key),
                    "window_title_hash": _hash_value(monitor.config.window_title_regex),
                    "phrase_hash": _hash_value(monitor.config.phrase_regex),
                    "failure_count": monitor.failure_count,
                    "breaker_remaining_seconds": int(breaker_remaining),
                    "last_window_ok": _safe_status_text(monitor.last_window_ok_at),
                    "last_window_error": _safe_status_text(monitor.last_window_error_at),
                }
            )
        payload = {
            "updated_at": _now_iso(),
            "app_version": self._app_version,
            "release_date": self._release_date,
            "commit_hash": self._commit_hash,
            "window_title_hash": _hash_value(self.config.window_title_regex),
            "window_title_hashes": [
                _hash_value(monitor.config.window_title_regex) for monitor in self._monitors
            ],
            "monitor_count": len(self._monitors),
            "monitors": monitor_payload,
            "running": snapshot.running,
            "paused": snapshot.paused,
            "uptime_seconds": snapshot.uptime_seconds,
            "last_scan": _safe_status_text(snapshot.last_scan),
            "last_match": _safe_status_text(snapshot.last_match),
            "last_match_at": _safe_status_text(snapshot.last_match_at),
            "last_match_age_seconds": match_age_seconds,
            "last_send": _safe_status_text(snapshot.last_send),
            "last_error": _safe_status_text(snapshot.last_error),
            "last_healthcheck": _safe_status_text(snapshot.last_healthcheck),
            "error_count": snapshot.error_count,
            "email_queue": self._queue_stats,
            "telemetry_write_errors": self._telemetry_write_errors,
            "status_export_errors": self._status_export_errors,
            "status_csv_errors": self._status_csv_errors,
            "state_write_errors": self._state_write_errors,
        }
        try:
            self._telemetry.write(payload)
        except Exception as exc:
            self._telemetry_write_errors += 1
            LOGGER.exception("Telemetry write failed: %s", exc, extra={"category": "error"})

        status_payload = {
            "running": snapshot.running,
            "paused": snapshot.paused,
            "last_scan": _safe_status_text(snapshot.last_scan),
            "last_match": _safe_status_text(snapshot.last_match),
            "last_match_at": _safe_status_text(snapshot.last_match_at),
            "last_match_age_seconds": match_age_seconds,
            "last_send": _safe_status_text(snapshot.last_send),
            "last_error": _safe_status_text(snapshot.last_error),
            "last_healthcheck": _safe_status_text(snapshot.last_healthcheck),
            "uptime_seconds": snapshot.uptime_seconds,
            "error_count": snapshot.error_count,
            "monitor_count": len(self._monitors),
            "email_queue": self._queue_stats,
            "status_export_errors": self._status_export_errors,
            "status_csv_errors": self._status_csv_errors,
            "state_write_errors": self._state_write_errors,
        }
        try:
            self._status_export.write(status_payload)
        except Exception as exc:
            self._status_export_errors += 1
            LOGGER.exception("Status export failed: %s", exc, extra={"category": "error"})

        self._write_status_csv(status_payload)

    def _write_status_csv(self, payload: dict[str, object]) -> None:
        path = Path(self.config.status_export_csv)
        try:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            for key, value in payload.items():
                writer.writerow([key, value])
            atomic_write_text(path, buffer.getvalue(), encoding="utf-8")
        except Exception as exc:
            self._status_csv_errors += 1
            LOGGER.exception("Status CSV export failed: %s", exc, extra={"category": "error"})

    def _update_config_checksum(self) -> None:
        try:
            base = get_user_data_dir()
            config_path = base / "config.local.yaml"
            if not config_path.exists():
                return
            checksum = hashlib.sha256(config_path.read_bytes()).hexdigest()
            path = Path(self.config.config_checksum_file)
            atomic_write_text(path, checksum, encoding="utf-8")
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

    def _drain_queues(self) -> None:
        total = {
            "queued": 0,
            "sent": 0,
            "failed": 0,
            "deferred": 0,
            "oldest_age_seconds": 0,
        }
        for monitor in self._monitors:
            sender = monitor.sender
            if isinstance(sender, QueueingEmailSender):
                try:
                    stats = sender.drain()
                    total["queued"] += stats.queued
                    total["sent"] += stats.sent
                    total["failed"] += stats.failed
                    total["deferred"] += stats.deferred
                    total["oldest_age_seconds"] = max(
                        total["oldest_age_seconds"], stats.oldest_age_seconds
                    )
                except EmailAuthError as exc:
                    monitor.email_disabled = True
                    self.status.set_last_error(
                        _safe_status_text(f"error: smtp auth failed: {exc}")
                    )
                except Exception as exc:
                    LOGGER.warning(
                        "Email queue drain failed: %s",
                        exc,
                        extra={"category": "send"},
                    )
        self._queue_stats = total

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
                now = time.monotonic()
                if now >= self._next_queue_drain:
                    self._drain_queues()
                    self._next_queue_drain = now + 30
                if _is_user_idle(120):
                    self.scan_once()
                    if self._last_scan_error:
                        error_count += 1
                        self.status.increment_error_count()
                    else:
                        self.status.set_last_error("")
                        error_count = 0
                else:
                    LOGGER.info(
                        "Skipping scan; user active",
                        extra={"category": "scan"},
                    )
            except WindowUnavailableError as exc:
                self._handle_error(f"error: janela indisponível: {exc}")
                LOGGER.info(
                    "Skipping scan; %s",
                    exc,
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
