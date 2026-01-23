from __future__ import annotations

from datetime import datetime, timezone

from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig
from sentineltray.detector import WindowTextDetector
from sentineltray.status import StatusStore


def _config() -> AppConfig:
    return AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=300,
        debounce_seconds=0,
        max_history=10,
        state_file="state.json",
        log_file="logs/sentineltray.log",
        log_level="INFO",
        log_console_level="WARNING",
        log_console_enabled=True,
        log_max_bytes=5000000,
        log_backup_count=5,
        log_run_files_keep=5,
        telemetry_file="logs/telemetry.json",
        status_export_file="logs/status.json",
        status_export_csv="logs/status.csv",
        allow_window_restore=True,
        log_only_mode=False,
        config_checksum_file="logs/config.checksum",
        min_free_disk_mb=100,
        watchdog_timeout_seconds=60,
        watchdog_restart=True,
        send_repeated_matches=True,
        min_repeat_seconds=0,
        error_notification_cooldown_seconds=300,
        window_error_backoff_base_seconds=5,
        window_error_backoff_max_seconds=120,
        window_error_circuit_threshold=3,
        window_error_circuit_seconds=300,
        email_queue_file="logs/email_queue.json",
        email_queue_max_items=0,
        email_queue_max_age_seconds=0,
        email_queue_max_attempts=0,
        email_queue_retry_base_seconds=0,
        log_throttle_seconds=60,
        email=EmailConfig(
            smtp_host="",
            smtp_port=587,
            smtp_username="",
            smtp_password="",
            from_address="",
            to_addresses=[],
            use_tls=True,
            timeout_seconds=10,
            subject="SentinelTray",
            retry_attempts=0,
            retry_backoff_seconds=0,
            dry_run=True,
        ),
    )


def test_skips_identical_to_previous_scan(monkeypatch) -> None:
    config = _config()
    status = StatusStore()
    notifier = Notifier(config=config, status=status)

    class FakeSender:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, message: str) -> None:
            self.sent.append(message)

    sender = FakeSender()
    notifier._sender = sender

    matches = ["100 ABC", "100 ABC"]
    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: matches)
    notifier.scan_once()

    # Second scan with identical first match should be skipped.
    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: ["100 ABC"])
    notifier.scan_once()

    assert sender.sent == ["100 ABC"]


def test_skips_lower_leading_number(monkeypatch) -> None:
    config = _config()
    status = StatusStore()
    notifier = Notifier(config=config, status=status)

    class FakeSender:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, message: str) -> None:
            self.sent.append(message)

    sender = FakeSender()
    notifier._sender = sender

    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: ["200 ALERT"])
    notifier.scan_once()

    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: ["150 ALERT"])
    notifier.scan_once()

    # Lower leading number should be skipped.
    assert sender.sent == ["200 ALERT"]


def test_allows_higher_leading_number(monkeypatch) -> None:
    config = _config()
    status = StatusStore()
    notifier = Notifier(config=config, status=status)

    class FakeSender:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, message: str) -> None:
            self.sent.append(message)

    sender = FakeSender()
    notifier._sender = sender

    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: ["100 ALERT"])
    notifier.scan_once()

    monkeypatch.setattr(WindowTextDetector, "find_matches", lambda _self, _pattern: ["101 ALERT"])
    notifier.scan_once()

    assert sender.sent == ["100 ALERT", "101 ALERT"]
