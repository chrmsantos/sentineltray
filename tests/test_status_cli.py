from __future__ import annotations

from pathlib import Path

from sentineltray.config import AppConfig, EmailConfig
from sentineltray.status_cli import build_status_display


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


def test_build_status_display_includes_counter_and_queue(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    status_path = tmp_path / "logs" / "status.json"
    payload = {
        "running": True,
        "paused": False,
        "last_scan": "2026-01-26T12:00:00+00:00",
        "last_match": "2026-01-26T12:00:00+00:00",
        "last_match_at": "2026-01-26T12:00:00+00:00",
        "last_send": "2026-01-26T12:00:00+00:00",
        "last_error": "",
        "last_healthcheck": "",
        "uptime_seconds": 12,
        "error_count": 0,
        "monitor_count": 1,
        "email_queue": {
            "queued": 0,
            "sent": 1,
            "failed": 0,
            "deferred": 0,
            "oldest_age_seconds": 0,
        },
    }
    text = build_status_display(
        config=config,
        payload=payload,
        counter_seconds=3,
        status_path=status_path,
    )
    assert "Contador (s): 3" in text
    assert "Running: yes" in text
    assert "Monitored window: EXEMPLO" in text
    assert "Monitored text: ALERTA" in text
    assert "Email queue:" in text
