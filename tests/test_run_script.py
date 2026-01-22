from __future__ import annotations

from pathlib import Path


def test_run_script_has_logging() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.cmd"
    content = script.read_text(encoding="utf-8")
    assert "LOG_DIR" in content
    assert "run_" in content
    assert ":log" in content
    assert ":log_context" in content
