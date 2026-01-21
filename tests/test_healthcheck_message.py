from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig
from sentineltray.status import StatusStore


def test_send_healthcheck_updates_status_and_sends() -> None:
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

    sent: list[str] = []

    class FakeSender:
        def send(self, message: str) -> None:
            sent.append(message)

    notifier._sender = FakeSender()
    status.set_last_scan("t1")
    status.set_last_send("s1")
    status.set_last_error("")

    notifier._send_healthcheck()

    snapshot = status.snapshot()
    assert sent
    assert sent[0].startswith("info: healthcheck")
    assert snapshot.last_healthcheck
    assert snapshot.uptime_seconds >= 0
