import sys
from pathlib import Path

import pytest

import main
from sentineltray.config import get_user_data_dir


def test_ensure_local_override_requires_file(tmp_path: Path) -> None:
    local_path = tmp_path / "config.local.yaml"

    with pytest.raises(SystemExit):
        main._ensure_local_override(local_path)

    assert not local_path.exists()


def test_ensure_local_override_rejects_empty_file(tmp_path: Path) -> None:
    local_path = tmp_path / "config.local.yaml"
    local_path.write_text("\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main._ensure_local_override(local_path)


def test_main_creates_local_override_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    local_path = get_user_data_dir() / "config.local.yaml"
    assert not local_path.exists()

    with pytest.raises(SystemExit):
        main.main()

    assert not local_path.exists()


def test_main_rejects_extra_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--other"])
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    with pytest.raises(SystemExit):
        main.main()


def test_ensure_single_instance_already_running(monkeypatch: pytest.MonkeyPatch) -> None:
    notice = {"called": False}

    monkeypatch.setattr(main, "_ensure_single_instance_mutex", lambda: False)
    monkeypatch.setattr(
        main,
        "_show_already_running_notice",
        lambda: notice.__setitem__("called", True),
    )

    with pytest.raises(SystemExit) as excinfo:
        main._ensure_single_instance()

    assert excinfo.value.code == 0
    assert notice["called"] is True
