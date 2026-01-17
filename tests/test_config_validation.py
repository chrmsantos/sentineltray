from pathlib import Path

import pytest

from sentineltray.config import load_config


def test_invalid_poll_interval_rejected(tmp_path: Path) -> None:
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
                "telemetry_file: 'logs/telemetry.json'",
                "show_error_window: true",
                "watchdog_timeout_seconds: 60",
                "watchdog_restart: true",
                "whatsapp:",
                "  mode: 'web'",
                "  chat_target: ''",
                "  user_data_dir: 'session'",
                "  timeout_seconds: 10",
                "  dry_run: true",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="poll_interval_seconds"):
        load_config(str(config_path))
