from __future__ import annotations

import os
import sys
from pathlib import Path

from sentineltray.app import run
from sentineltray.config import load_config, load_config_with_override
from sentineltray.tray_app import run_tray

LOCAL_TEMPLATE = """# SentinelTray local overrides
# Fill the values below and restart the app.

window_title_regex: ""
phrase_regex: ""
whatsapp:
  chat_target: ""
"""


def _open_for_editing(path: Path) -> None:
    if hasattr(os, "startfile"):
        try:
            os.startfile(str(path))
        except OSError:
            return


def _write_local_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LOCAL_TEMPLATE, encoding="utf-8")


def _ensure_local_override(path: Path) -> None:
    if not path.exists():
        _write_local_template(path)
        _open_for_editing(path)
        raise SystemExit(f"Local config created at {path}. Fill it and restart.")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        _write_local_template(path)
        _open_for_editing(path)
        raise SystemExit(f"Local config is empty at {path}. Fill it and restart.")


def _load_local_override(config_path: Path, override_path: Path):
    try:
        return load_config_with_override(str(config_path), str(override_path))
    except Exception as exc:
        _open_for_editing(override_path)
        raise SystemExit(
            f"Local config has errors at {override_path}. Fix and restart."
        ) from exc


def main() -> int:
    config_path = Path("config.yaml")
    use_cli = False
    override_path: Path | None = None
    local_override: Path | None = None
    args = [arg for arg in sys.argv[1:] if arg]
    for arg in args:
        if arg == "--cli":
            use_cli = True
        else:
            override_path = Path(arg)

    env_path = os.environ.get("SENTINELTRAY_CONFIG")
    if env_path:
        override_path = Path(env_path)

    if override_path is None:
        user_root = os.environ.get("USERPROFILE")
        if user_root:
            candidate = Path(user_root) / "sentineltray" / "config.local.yaml"
            local_override = candidate
            override_path = candidate

    if local_override is not None and override_path == local_override:
        _ensure_local_override(local_override)
        config = _load_local_override(config_path, local_override)
    elif override_path is not None:
        config = load_config_with_override(str(config_path), str(override_path))
    else:
        config = load_config(str(config_path))
    if use_cli:
        run(config)
    else:
        run_tray(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
