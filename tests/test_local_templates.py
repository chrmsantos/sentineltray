from pathlib import Path


def test_local_templates_exist() -> None:
    base = Path(__file__).resolve().parents[1] / "templates" / "local"
    config_path = base / "config.local.yaml"
    state_path = base / "state.json"
    readme_path = base / "README.md"

    assert config_path.exists()
    assert state_path.exists()
    assert readme_path.exists()

    content = config_path.read_text(encoding="utf-8")
    assert "window_title_regex" in content
    assert "whatsapp" in content
