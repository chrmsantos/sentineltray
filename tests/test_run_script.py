from __future__ import annotations

from pathlib import Path


def test_run_script_starts_main() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.cmd"
    content = script.read_text(encoding="utf-8")
    assert "main.py" in content


def test_run_script_has_no_autostart_controls() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.cmd"
    content = script.read_text(encoding="utf-8")
    assert "/install-startup" not in content
    assert "/remove-startup" not in content
    assert "/startup-status" not in content
    assert "CurrentVersion\\Run" not in content
