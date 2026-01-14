from pathlib import Path

from sentineltray.config import load_config_with_override


def test_load_config_with_override() -> None:
    base_path = Path(__file__).parent / "data" / "config.yaml"
    override_path = Path(__file__).parent / "data" / "config_override.yaml"

    config = load_config_with_override(str(base_path), str(override_path))

    assert config.window_title_regex == "SECRET_APP"
    assert config.whatsapp.chat_target == "Local User"
    assert config.phrase_regex == "ALERT"
