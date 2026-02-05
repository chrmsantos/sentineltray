import sys
from pathlib import Path

import pytest

from sentineltray import entrypoint
from sentineltray.config import get_user_data_dir


def test_ensure_local_override_requires_file(tmp_path: Path) -> None:
    local_path = tmp_path / "config.local.yaml"

    with pytest.raises(SystemExit):
        entrypoint._ensure_local_override(local_path)

    assert not local_path.exists()


def test_ensure_local_override_rejects_empty_file(tmp_path: Path) -> None:
    local_path = tmp_path / "config.local.yaml"
    local_path.write_text("\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        entrypoint._ensure_local_override(local_path)


def test_main_creates_local_override_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv(
        "SENTINELTRAY_ROOT",
        str(Path(__file__).resolve().parents[1]),
    )
    monkeypatch.setattr(entrypoint, "_setup_boot_logging", lambda: None)
    monkeypatch.setattr(entrypoint, "_ensure_single_instance", lambda: None)
    monkeypatch.setattr(entrypoint, "_ensure_windows", lambda: None)
    monkeypatch.setattr(
        entrypoint,
        "run_console_config_error",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SystemExit()),
    )

    local_path = get_user_data_dir() / "config.local.yaml"
    assert not local_path.exists()

    with pytest.raises(SystemExit):
        entrypoint.main()

    assert local_path.exists()


def test_main_rejects_extra_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--other"])
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(entrypoint, "_setup_boot_logging", lambda: None)
    monkeypatch.setattr(entrypoint, "_ensure_single_instance", lambda: None)

    with pytest.raises(SystemExit):
        entrypoint.main()


def test_ensure_single_instance_already_running(monkeypatch: pytest.MonkeyPatch) -> None:
    notice = {"called": False}

    monkeypatch.setattr(entrypoint, "_ensure_single_instance_mutex", lambda: False)
    monkeypatch.setattr(entrypoint, "_terminate_existing_instance", lambda: False)
    monkeypatch.setattr(
        entrypoint,
        "_show_already_running_notice",
        lambda: notice.__setitem__("called", True),
    )

    with pytest.raises(SystemExit) as excinfo:
        entrypoint._ensure_single_instance()

    assert excinfo.value.code == 0
    assert notice["called"] is True
