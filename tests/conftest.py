from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_runtime_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Isolate tests from user-specific directories and keep logs/data in temp."""
    data_dir = tmp_path / "config"
    root_dir = tmp_path / "Root"
    data_dir.mkdir(parents=True, exist_ok=True)
    root_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("SENTINELTRAY_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SENTINELTRAY_ROOT", str(root_dir))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    if "USERPROFILE" not in os.environ:
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
