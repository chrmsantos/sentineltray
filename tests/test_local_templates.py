from pathlib import Path


def test_local_templates_exist() -> None:
    base = Path(__file__).resolve().parents[1] / "templates" / "local"
    state_path = base / "state.json"
    readme_path = base / "README.md"

    assert state_path.exists()
    assert readme_path.exists()
