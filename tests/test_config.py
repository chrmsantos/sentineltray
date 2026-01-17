from pathlib import Path

import pytest

from sentineltray.config import load_config


def test_load_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config_path = Path(__file__).parent / "data" / "config.yaml"
    config = load_config(str(config_path))

    assert config.window_title_regex == "Sino\\.Siscam\\.Desktop"
    assert config.phrase_regex == "ALERT"
    assert config.poll_interval_seconds == 300
    assert config.healthcheck_interval_seconds == 3600
    assert config.error_backoff_base_seconds == 5
    assert config.error_backoff_max_seconds == 300
    assert config.debounce_seconds == 600
    base = tmp_path / "sentineltray"
    assert config.log_file == str(base / "logs" / "sentineltray.log")
    assert config.telemetry_file == str(base / "logs" / "telemetry.json")
    assert config.show_error_window is True
    assert config.watchdog_timeout_seconds == 60
    assert config.watchdog_restart is True
    assert config.email.smtp_host == "smtp.local"
    assert config.email.smtp_port == 587
    assert config.email.from_address == "alerts@example.com"
    assert config.email.to_addresses == ["ops@example.com"]
    assert config.email.dry_run is False
    assert config.state_file == str(base / "state.json")
    assert config.telemetry_file == str(base / "logs" / "telemetry.json")
