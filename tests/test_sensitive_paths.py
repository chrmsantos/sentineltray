from pathlib import Path

import pytest

from sentineltray.config import load_config


def test_sensitive_paths_forced_to_user_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    other_root = tmp_path / "other"
    other_root.mkdir()

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
                f"state_file: '{other_root / 'state.json'}'",
                f"log_file: '{other_root / 'logs' / 'sentineltray.log'}'",
                f"telemetry_file: '{other_root / 'telemetry.json'}'",
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
                "  dry_run: true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    base = tmp_path / "sentineltray"
    assert config.state_file == str(base / "state.json")
    assert config.log_file == str(base / "sentineltray.log")
    assert config.telemetry_file == str(base / "telemetry.json")
