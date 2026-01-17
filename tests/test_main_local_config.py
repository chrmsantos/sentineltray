import os
import sys
from pathlib import Path

import pytest

import main


def test_ensure_local_override_creates_and_opens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: dict[str, str] = {}

    def fake_startfile(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    local_path = tmp_path / "config.local.yaml"

    with pytest.raises(SystemExit):
        main._ensure_local_override(local_path)

    assert local_path.exists()
    assert "window_title_regex" in local_path.read_text(encoding="utf-8")
    assert opened["path"] == str(local_path)


def test_ensure_local_override_handles_empty_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: dict[str, str] = {}

    def fake_startfile(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    local_path = tmp_path / "config.local.yaml"
    local_path.write_text("\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main._ensure_local_override(local_path)

    assert "whatsapp" in local_path.read_text(encoding="utf-8")
    assert opened["path"] == str(local_path)


def test_load_local_override_opens_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: dict[str, str] = {}

    def fake_startfile(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    base_path = Path(__file__).parent / "data" / "config.yaml"
    local_path = tmp_path / "config.local.yaml"
    local_path.write_text("whatsapp: [", encoding="utf-8")

    with pytest.raises(SystemExit):
        main._load_local_override(base_path, local_path)

    assert opened["path"] == str(local_path)


def test_main_creates_local_override_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: dict[str, str] = {}

    def fake_startfile(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.delenv("SENTINELTRAY_CONFIG", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    local_path = tmp_path / "sentineltray" / "config.local.yaml"
    assert not local_path.exists()

    with pytest.raises(SystemExit):
        main.main()

    assert local_path.exists()
    assert opened["path"] == str(local_path)
