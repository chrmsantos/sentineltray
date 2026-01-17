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
        telemetry_file="logs/telemetry.json",
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
