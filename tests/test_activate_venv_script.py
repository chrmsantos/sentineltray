from pathlib import Path


def test_activate_venv_script_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "activate_venv.cmd"
    assert script.exists()
