from __future__ import annotations

from pathlib import Path


def test_install_script_has_logging_and_retention() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "install.cmd"
    content = script.read_text(encoding="utf-8")
    assert "LOG_DIR" in content
    assert "install_" in content
    assert "Select-Object -Skip 5" in content
    assert ":fail" in content
    assert ":log" in content
