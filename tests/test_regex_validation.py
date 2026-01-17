from pathlib import Path

import pytest

from sentineltray.config import load_config


def test_invalid_regex_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_title_regex: '('",
                "phrase_regex: 'ALERT'",
                "poll_interval_seconds: 1",
                "healthcheck_interval_seconds: 60",
                "error_backoff_base_seconds: 5",
                "error_backoff_max_seconds: 10",
                "debounce_seconds: 0",
                "max_history: 10",
                "state_file: 'state.json'",
                "log_file: 'logs/sentineltray.log'",
                "telemetry_file: 'logs/telemetry.json'",
                "status_export_file: 'logs/status.json'",
                "status_export_csv: 'logs/status.csv'",
                "status_refresh_seconds: 1",
                "allow_window_restore: true",
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

    with pytest.raises(ValueError, match="window_title_regex invalid regex"):
        load_config(str(config_path))
