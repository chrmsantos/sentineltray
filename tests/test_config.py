from pathlib import Path

from sentineltray.config import load_config


def test_load_config() -> None:
    config_path = Path(__file__).parent / "data" / "config.yaml"
    config = load_config(str(config_path))

    assert config.window_title_regex == "Sino\\.Siscam\\.Desktop"
    assert config.phrase_regex == "ALERT"
    assert config.poll_interval_seconds == 120
    assert config.log_file == "logs/sentineltray.log"
    assert config.whatsapp.mode == "cloud_api"
    assert config.whatsapp.chat_target == "Christian Martin dos Santos"
    assert config.whatsapp.dry_run is False
    assert config.whatsapp.cloud_api.to == "5511999999999"
