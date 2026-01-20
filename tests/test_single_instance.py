import os
from pathlib import Path

import pytest

import main


def test_single_instance_kills_previous(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    pid_path = (
        tmp_path
        / "AppData"
        / "Local"
        / "AxonZ"
        / "SentinelTray"
        / "UserData"
        / "sentineltray.pid"
    )
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("1234", encoding="utf-8")

    called: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        called["args"] = args
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    monkeypatch.setattr(main.os, "getpid", lambda: 4321)

    main._ensure_single_instance()

    assert called["args"][0] == "taskkill"
    assert pid_path.read_text(encoding="utf-8") == "4321"
