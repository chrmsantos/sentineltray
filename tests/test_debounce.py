from datetime import datetime, timedelta, timezone

from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig
from sentineltray.detector import WindowTextDetector
from sentineltray.status import StatusStore


def test_debounce_skips_recent_messages(monkeypatch) -> None:
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=300,
        debounce_seconds=600,
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
        status_refresh_seconds=1,
        allow_window_restore=True,
        start_minimized=True,
        log_only_mode=False,
        config_checksum_file="logs/config.checksum",
        min_free_disk_mb=100,
        show_error_window=True,
        watchdog_timeout_seconds=60,
        watchdog_restart=True,
        send_repeated_matches=False,
        email=EmailConfig(
            smtp_host="smtp.local",
            smtp_port=587,
            smtp_username="",
            smtp_password="",
            from_address="alerts@example.com",
            to_addresses=["ops@example.com"],
            use_tls=True,
            timeout_seconds=10,
            subject="SentinelTray Notification",
            retry_attempts=0,
            retry_backoff_seconds=0,
            dry_run=True,
        ),
    )
    status = StatusStore()
    notifier = Notifier(config=config, status=status)

    now = datetime.now(timezone.utc)
    for monitor in notifier._monitors:
        monitor.last_sent = {
            "recent": now,
            "old": now - timedelta(seconds=700),
        }

    class FakeSender:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, message: str) -> None:
            self.sent.append(message)

    monkeypatch.setattr(
        WindowTextDetector,
        "find_matches",
        lambda _self, _pattern: ["recent", "old"],
    )
    sender = FakeSender()
    notifier._sender = sender

    notifier.scan_once()

    assert sender.sent == ["old"]
