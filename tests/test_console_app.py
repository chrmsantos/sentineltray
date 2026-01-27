from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pytest

from sentineltray import console_app
from sentineltray.config import AppConfig, EmailConfig


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


def test_run_console_status_and_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SENTINELTRAY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(console_app, "clear_screen", lambda: None)
    def fake_load(_path: Path) -> dict[str, object]:
        return {}

    monkeypatch.setattr(console_app, "load_status_payload", fake_load)

    calls: dict[str, Any] = {"display": 0, "finalize": 0, "opened": 0, "joined": False}

    def fake_display(**_kwargs: Any) -> str:
        calls["display"] += 1
        return "STATUS"

    def fake_create_editor():
        def on_open() -> None:
            calls["opened"] += 1

        def finalize() -> None:
            calls["finalize"] += 1

        return on_open, finalize

    class DummyThread:
        def join(self, timeout: float | None = None) -> None:
            calls["joined"] = True

    monkeypatch.setattr(console_app, "build_status_display", fake_display)
    monkeypatch.setattr(console_app, "_create_config_editor", fake_create_editor)
    def fake_start_notifier(*_args: object, **_kwargs: object) -> DummyThread:
        return DummyThread()

    monkeypatch.setattr(console_app, "_start_notifier", fake_start_notifier)
    monkeypatch.setattr(console_app.time, "monotonic", lambda: 0)
    def noop_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(console_app.time, "sleep", noop_sleep)

    inputs: Iterator[str] = iter(["s", "", "q"])
    def fake_input(_prompt: str) -> str:
        return next(inputs)

    monkeypatch.setattr(console_app, "input", fake_input)

    console_app.run_console(_make_config(tmp_path))

    assert calls["display"] >= 1
    assert calls["joined"] is True


def test_run_console_config_error_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SENTINELTRAY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(console_app, "clear_screen", lambda: None)
    monkeypatch.setattr(console_app, "_create_config_editor", lambda: (lambda: None, lambda: None))

    opened: dict[str, Path] = {}

    def fake_open(path: Path) -> None:
        opened["path"] = path

    monkeypatch.setattr(console_app, "_open_text_file", fake_open)

    inputs: Iterator[str] = iter(["d", "q"])

    def fake_input(_prompt: str) -> str:
        return next(inputs)

    monkeypatch.setattr(console_app, "input", fake_input)

    console_app.run_console_config_error("details")

    assert "path" in opened
