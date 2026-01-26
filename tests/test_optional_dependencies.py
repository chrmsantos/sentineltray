from __future__ import annotations

from pathlib import Path

import pytest

from sentineltray.config import AppConfig, EmailConfig
from sentineltray import tray_app
from sentineltray import detector as detector_module
from sentineltray.detector import WindowTextDetector


def _make_config(tmp_path: Path) -> AppConfig:
    email = EmailConfig(
        smtp_host="",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        from_address="",
        to_addresses=[],
        use_tls=True,
        timeout_seconds=10,
        subject="SentinelTray",
        retry_attempts=1,
        retry_backoff_seconds=1,
        dry_run=True,
    )
    return AppConfig(
        window_title_regex="EXEMPLO",
        phrase_regex="ALERTA",
        poll_interval_seconds=10,
        healthcheck_interval_seconds=0,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=30,
        debounce_seconds=10,
        max_history=10,
        state_file=str(tmp_path / "state.json"),
        log_file=str(tmp_path / "logs" / "sentineltray.log"),
        log_level="INFO",
        log_console_level="WARNING",
        log_console_enabled=True,
        log_max_bytes=1000000,
        log_backup_count=1,
        log_run_files_keep=5,
        telemetry_file=str(tmp_path / "logs" / "telemetry.json"),
        status_export_file=str(tmp_path / "logs" / "status.json"),
        status_export_csv=str(tmp_path / "logs" / "status.csv"),
        allow_window_restore=True,
        log_only_mode=True,
        config_checksum_file=str(tmp_path / "logs" / "config.checksum"),
        min_free_disk_mb=10,
        watchdog_timeout_seconds=60,
        watchdog_restart=True,
        send_repeated_matches=True,
        email=email,
    )


def test_detector_requires_pywinauto_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detector_module, "Desktop", None)
    detector = WindowTextDetector("APP")
    with pytest.raises(RuntimeError, match="pywinauto is required"):
        detector._get_window()


def test_tray_requires_dependencies_when_missing(tmp_path: Path) -> None:
    if tray_app.pystray is not None:
        pytest.skip("pystray available; optional dependency test not applicable")
    config = _make_config(tmp_path)
    with pytest.raises(RuntimeError, match="Tray dependencies missing"):
        tray_app.run_tray(config)
