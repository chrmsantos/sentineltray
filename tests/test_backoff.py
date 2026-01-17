from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig
from sentineltray.status import StatusStore


def test_compute_backoff_seconds_caps() -> None:
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=20,
        debounce_seconds=600,
        max_history=10,
        state_file="state.json",
        log_file="logs/sentineltray.log",
        telemetry_file="logs/telemetry.json",
        status_export_file="logs/status.json",
        status_export_csv="logs/status.csv",
        status_refresh_seconds=1,
        allow_window_restore=True,
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
    notifier = Notifier(config=config, status=StatusStore())

    assert notifier._compute_backoff_seconds(0) == 0
    assert notifier._compute_backoff_seconds(1) == 5
    assert notifier._compute_backoff_seconds(2) == 10
    assert notifier._compute_backoff_seconds(3) == 20
    assert notifier._compute_backoff_seconds(4) == 20
