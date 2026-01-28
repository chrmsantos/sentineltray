from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig, MonitorConfig
from sentineltray.email_sender import EmailAuthError
from sentineltray.status import StatusStore


def test_auth_failure_disables_email_sends() -> None:
    email = EmailConfig(
        smtp_host="smtp.local",
        smtp_port=587,
        smtp_username="user",
        smtp_password="bad",
        from_address="alerts@example.com",
        to_addresses=["ops@example.com"],
        use_tls=True,
        timeout_seconds=10,
        subject="SentinelTray Notification",
        retry_attempts=0,
        retry_backoff_seconds=0,
        dry_run=False,
    )
    config = AppConfig(
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
        allow_window_restore=True,
        log_only_mode=False,
        send_repeated_matches=True,
        monitors=[
            MonitorConfig(
                window_title_regex="APP",
                phrase_regex="ALERT",
                email=email,
            )
        ],
    )

    notifier = Notifier(config=config, status=StatusStore())

    calls = {"count": 0}

    class FakeSender:
        def send(self, _message: str) -> None:
            calls["count"] += 1
            raise EmailAuthError("SMTP authentication failed")

    notifier._sender = FakeSender()

    notifier._send_startup_test()
    notifier._send_startup_test()

    assert calls["count"] == 1
    assert notifier._monitors[0].email_disabled
    assert "smtp auth failed" in notifier.status.snapshot().last_error.lower()
