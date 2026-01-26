from __future__ import annotations

from pathlib import Path


def test_run_script_has_logging() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.cmd"
    content = script.read_text(encoding="utf-8")
    assert "LOG_DIR" in content
    assert "run_" in content
    assert ":log" in content
    assert ":log_context" in content
    assert "/nonportable" in content
    assert ":prepare_runtime" in content
    assert "prepare_portable_runtime.cmd" in content
    assert "-NoExit" in content


def test_run_script_has_no_autostart_controls() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.cmd"
    content = script.read_text(encoding="utf-8")
    assert "/install-startup" not in content
    assert "/remove-startup" not in content
    assert "/startup-status" not in content
    assert "CurrentVersion\\Run" not in content
