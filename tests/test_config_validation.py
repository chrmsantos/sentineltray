from pathlib import Path

import pytest

from sentineltray.config import get_user_log_dir, load_config


def test_invalid_poll_interval_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_title_regex: 'APP'",
                "phrase_regex: 'ALERT'",
                "poll_interval_seconds: 0",
                "healthcheck_interval_seconds: 60",
                "error_backoff_base_seconds: 5",
                "error_backoff_max_seconds: 10",
                "debounce_seconds: 0",
                "max_history: 10",
                "state_file: 'state.json'",
                "log_file: 'logs/sentineltray.log'",
                "log_level: 'INFO'",
                "log_console_level: 'WARNING'",
                "log_console_enabled: true",
                "log_max_bytes: 5000000",
                "log_backup_count: 5",
                "log_run_files_keep: 5",
                "telemetry_file: 'logs/telemetry.json'",
                "status_export_file: 'logs/status.json'",
                "status_export_csv: 'logs/status.csv'",
                "status_refresh_seconds: 1",
                "allow_window_restore: true",
                "start_minimized: true",
                "log_only_mode: false",
                "config_checksum_file: 'logs/config.checksum'",
                "min_free_disk_mb: 100",
                "show_error_window: true",
                "watchdog_timeout_seconds: 60",
                "watchdog_restart: true",
                "email:",
                "  smtp_host: ''",
                "  smtp_port: 587",
                "  smtp_username: ''",
                "  smtp_password: ''",
                "  from_address: ''",
                "  to_addresses: []",
                "  use_tls: true",
                "  timeout_seconds: 10",
                "  subject: 'SentinelTray Notification'",
                "  retry_attempts: 0",
                "  retry_backoff_seconds: 0",
                "  dry_run: true",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="poll_interval_seconds"):
        load_config(str(config_path))


def test_log_paths_are_rehomed_to_user_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    log_root = get_user_log_dir()
    outside_log = log_root.parent / "other" / "sentineltray.log"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_title_regex: 'APP'",
                "phrase_regex: 'ALERT'",
                "poll_interval_seconds: 1",
                "healthcheck_interval_seconds: 60",
                "error_backoff_base_seconds: 5",
                "error_backoff_max_seconds: 10",
                "debounce_seconds: 0",
                "max_history: 10",
                "state_file: 'state.json'",
                f"log_file: '{outside_log}'",
                "log_level: 'INFO'",
                "log_console_level: 'WARNING'",
                "log_console_enabled: true",
                "log_max_bytes: 5000000",
                "log_backup_count: 5",
                "log_run_files_keep: 5",
                "telemetry_file: 'logs/telemetry.json'",
                "status_export_file: 'logs/status.json'",
                "status_export_csv: 'logs/status.csv'",
                "status_refresh_seconds: 1",
                "allow_window_restore: true",
                "start_minimized: true",
                "log_only_mode: false",
                "config_checksum_file: 'logs/config.checksum'",
                "min_free_disk_mb: 100",
                "show_error_window: true",
                "watchdog_timeout_seconds: 60",
                "watchdog_restart: true",
                "email:",
                "  smtp_host: ''",
                "  smtp_port: 587",
                "  smtp_username: ''",
                "  smtp_password: ''",
                "  from_address: ''",
                "  to_addresses: []",
                "  use_tls: true",
                "  timeout_seconds: 10",
                "  subject: 'SentinelTray Notification'",
                "  retry_attempts: 0",
                "  retry_backoff_seconds: 0",
                "  dry_run: true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.log_file == str(log_root / "sentineltray.log")
