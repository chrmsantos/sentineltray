from __future__ import annotations

from pathlib import Path


def test_bootstrap_script_has_logging() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_self_contained.cmd"
    content = script.read_text(encoding="utf-8")
    assert "LOG_DIR" in content
    assert "bootstrap_" in content
    assert "Select-Object -Skip 5" in content
    assert ":log" in content
    assert "Invoke-WebRequest" not in content


def test_create_shortcut_supports_start_menu() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "create_shortcut.ps1"
    content = script.read_text(encoding="utf-8")
    assert "CreateStartMenu" in content
    assert "WScript.Shell" in content
    assert "StartMenuName" in content


def test_uninstall_script_exists() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "uninstall.cmd"
    content = script.read_text(encoding="utf-8")
    assert "install.cmd" in content
    assert "/uninstall" in content


def test_config_template_exists() -> None:
    template = Path(__file__).resolve().parents[1] / "templates" / "local" / "config.local.yaml"
    assert template.exists()
