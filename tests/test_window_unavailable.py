from __future__ import annotations

from threading import Event

import pytest

from sentineltray.app import Notifier
from sentineltray import app as app_module
from sentineltray.config import AppConfig, EmailConfig, MonitorConfig, get_user_data_dir, get_user_log_dir
from sentineltray.detector import WindowUnavailableError
from sentineltray.status import StatusStore


def test_run_loop_skips_window_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    base = get_user_data_dir()
    log_root = get_user_log_dir()
    email = EmailConfig(
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
    )
    config = AppConfig(
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=300,
        debounce_seconds=600,
        max_history=10,
        state_file=str(base / "state.json"),
        log_file=str(log_root / "sentineltray.log"),
        log_level="INFO",
        log_console_level="WARNING",
        log_console_enabled=False,
        log_max_bytes=5000000,
        log_backup_count=3,
        log_run_files_keep=3,
        telemetry_file=str(log_root / "telemetry.json"),
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
    stop_event = Event()

    def fake_scan_once() -> None:
        raise WindowUnavailableError("Target window not enabled")

    notifier.scan_once = fake_scan_once  # type: ignore[assignment]
    monkeypatch.setattr(app_module, "_is_user_idle", lambda _: True)

    sends = {"count": 0}

    class FakeSender:
        def send(self, _message: str) -> None:
            sends["count"] += 1

    notifier._sender = FakeSender()  # type: ignore[assignment]

    calls = {"count": 0}

    def fake_update_telemetry() -> None:
        calls["count"] += 1
        if calls["count"] >= 2:
            stop_event.set()

    notifier._update_telemetry = fake_update_telemetry  # type: ignore[assignment]

    notifier.run_loop(stop_event)

    snapshot = notifier.status.snapshot()
    assert snapshot.error_count == 0
    assert snapshot.last_error
    assert sends["count"] == 1
