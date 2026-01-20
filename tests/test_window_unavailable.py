from __future__ import annotations

from threading import Event

import pytest

from sentineltray.app import Notifier
from sentineltray.config import AppConfig, EmailConfig, get_user_log_dir
from sentineltray.detector import WindowUnavailableError
from sentineltray.status import StatusStore


def test_run_loop_skips_window_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    base = (
        tmp_path
        / "AppData"
        / "Local"
        / "AxonZ"
        / "SentinelTray"
        / "UserData"
    )
    log_root = get_user_log_dir()
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
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
        log_backup_count=5,
        log_run_files_keep=5,
        telemetry_file=str(log_root / "telemetry.json"),
        status_export_file=str(log_root / "status.json"),
        status_export_csv=str(log_root / "status.csv"),
        status_refresh_seconds=1,
        allow_window_restore=True,
        start_minimized=True,
        log_only_mode=False,
        config_checksum_file=str(log_root / "config.checksum"),
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
    stop_event = Event()

    def fake_scan_once() -> None:
        raise WindowUnavailableError("Target window not enabled")

    notifier.scan_once = fake_scan_once  # type: ignore[assignment]
    monkeypatch.setattr("sentineltray.app._is_user_idle", lambda _: True)

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
    assert sends["count"] == 2
