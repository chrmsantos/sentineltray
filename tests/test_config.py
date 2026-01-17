from pathlib import Path

from sentineltray.config import load_config


def test_load_config() -> None:
    config_path = Path(__file__).parent / "data" / "config.yaml"
    config = load_config(str(config_path))

    assert config.window_title_regex == "Sino\\.Siscam\\.Desktop"
    assert config.phrase_regex == "ALERT"
    assert config.poll_interval_seconds == 300
    assert config.healthcheck_interval_seconds == 3600
    assert config.log_file == "logs/sentineltray.log"
    assert config.whatsapp.mode == "web"
    assert config.whatsapp.chat_target == ""
    assert config.whatsapp.dry_run is False
