import os
from pathlib import Path

import pytest

import main
from sentineltray.config import get_user_data_dir


def test_single_instance_kills_previous(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    pid_path = get_user_data_dir() / "sentineltray.pid"
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


def test_mutex_returns_false_when_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKernel32:
        def CreateMutexW(self, *_args):
            return 123

        def GetLastError(self) -> int:
            return 183

    class FakeWindll:
        kernel32 = FakeKernel32()

    monkeypatch.setattr(main, "_MUTEX_HANDLE", None)
    monkeypatch.setattr(main.ctypes, "windll", FakeWindll())
    assert main._ensure_single_instance_mutex() is False


def test_mutex_returns_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKernel32:
        def CreateMutexW(self, *_args):
            return 123

        def GetLastError(self) -> int:
            return 0

    class FakeWindll:
        kernel32 = FakeKernel32()

    monkeypatch.setattr(main, "_MUTEX_HANDLE", None)
    monkeypatch.setattr(main.ctypes, "windll", FakeWindll())
    assert main._ensure_single_instance_mutex() is True


def test_mutex_falls_back_to_local_when_global_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeKernel32:
        def CreateMutexW(self, *_args):
            name = _args[2] if len(_args) > 2 else ""
            calls.append(str(name))
            if "Global" in str(name):
                raise RuntimeError("access denied")
            return 123

        def GetLastError(self) -> int:
            return 0

    class FakeWindll:
        kernel32 = FakeKernel32()

    monkeypatch.setattr(main, "_MUTEX_HANDLE", None)
    monkeypatch.setattr(main.ctypes, "windll", FakeWindll())
    assert main._ensure_single_instance_mutex() is True
    assert any("Global" in name for name in calls)
    assert any("Local" in name for name in calls)
