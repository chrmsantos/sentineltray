from pathlib import Path

import pytest

from sentineltray.config import get_user_log_dir, load_config


def test_load_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config_path = Path(__file__).parent / "data" / "config.yaml"
    config = load_config(str(config_path))

    assert config.window_title_regex == "Sino\\.Siscam\\.Desktop"
    assert config.phrase_regex == "ALERT"
    assert config.poll_interval_seconds == 180
    assert config.healthcheck_interval_seconds == 3600
    assert config.error_backoff_base_seconds == 5
    assert config.error_backoff_max_seconds == 300
    assert config.debounce_seconds == 600
    log_root = get_user_log_dir()
    assert config.log_file == str(log_root / "sentineltray.log")
    assert config.log_level == "INFO"
    assert config.log_console_level == "WARNING"
    assert config.log_console_enabled is True
    assert config.log_max_bytes == 5000000
    assert config.log_backup_count == 5
    assert config.log_run_files_keep == 5
    assert config.telemetry_file == str(log_root / "telemetry.json")


def test_log_retention_is_capped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config_path = tmp_path / "config.yaml"
    base_config = (Path(__file__).parent / "data" / "config.yaml").read_text(encoding="utf-8")
    updated = base_config.replace("log_backup_count: 5", "log_backup_count: 12")
    updated = updated.replace("log_run_files_keep: 5", "log_run_files_keep: 9")
    config_path.write_text(updated, encoding="utf-8")

    config = load_config(str(config_path))

    assert config.log_backup_count == 5
    assert config.log_run_files_keep == 5
