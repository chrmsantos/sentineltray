from pathlib import Path


def test_bootstrap_runtime_uses_scripts_pip_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "bootstrap_runtime.py"
    content = script.read_text(encoding="utf-8")
    assert "Scripts" in content
    assert "pip.exe" in content
