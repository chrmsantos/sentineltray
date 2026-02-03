from pathlib import Path

import pytest
pytest.importorskip("cryptography")

from sentineltray.config import (
    encrypt_config_file,
    get_encrypted_config_path,
    load_config_secure,
    select_encryption_method,
)
from sentineltray.security_utils import (
    decrypt_text_portable,
    encrypt_text_portable,
    get_portable_key_path,
    parse_payload,
)


def _sample_config_text() -> str:
    return "\n".join(
        [
            "monitors:",
            "  - window_title_regex: 'APP'",
            "    phrase_regex: 'ALERT'",
            "    email:",
            "      smtp_host: ''",
            "      smtp_port: 587",
            "      smtp_username: ''",
            "      smtp_password: ''",
            "      from_address: ''",
            "      to_addresses: []",
            "      use_tls: true",
            "      timeout_seconds: 10",
            "      subject: 'SentinelTray Notification'",
            "      retry_attempts: 0",
            "      retry_backoff_seconds: 0",
            "      dry_run: true",
            "poll_interval_seconds: 1",
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
            "log_backup_count: 3",
            "log_run_files_keep: 3",
            "telemetry_file: 'logs/telemetry.json'",
            "allow_window_restore: true",
            "log_only_mode: false",
        ]
    )


def test_portable_encrypt_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.local.yaml"
    key_path = get_portable_key_path(config_path)

    payload = encrypt_text_portable("hello", key_path=key_path)
    assert key_path.exists()
    decoded = decrypt_text_portable(payload, key_path=key_path)
    assert decoded == "hello"


def test_load_config_secure_portable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SENTINELTRAY_DATA_DIR", str(tmp_path))

    config_path = tmp_path / "config.local.yaml"
    config_path.write_text(_sample_config_text(), encoding="utf-8")

    encrypt_config_file(str(config_path), remove_plain=True, method="portable")

    encrypted_path = get_encrypted_config_path(config_path)
    assert encrypted_path.exists()

    payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
    assert payload.method == "portable"

    config = load_config_secure(str(config_path))
    assert config.monitors[0].window_title_regex == "APP"
    assert config.monitors[0].phrase_regex == "ALERT"


def test_select_encryption_method_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.local.yaml"
    monkeypatch.setenv("SENTINELTRAY_CONFIG_ENCRYPTION", "dpapi")
    assert select_encryption_method(config_path) == "dpapi"
