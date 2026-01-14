from __future__ import annotations

import os
import sys
from pathlib import Path

from notificator.app import run
from notificator.config import load_config, load_config_with_override
from notificator.tray_app import run_tray


def main() -> int:
    config_path = Path("config.yaml")
    use_cli = False
    override_path: Path | None = None
    args = [arg for arg in sys.argv[1:] if arg]
    for arg in args:
        if arg == "--cli":
            use_cli = True
        else:
            override_path = Path(arg)

    env_path = os.environ.get("NOTIFICATOR_CONFIG")
    if env_path:
        override_path = Path(env_path)

    if override_path is None:
        local_root = os.environ.get("LOCALAPPDATA")
        if local_root:
            candidate = Path(local_root) / "Notificator" / "config.local.yaml"
            if candidate.exists():
                override_path = candidate

    if override_path is not None:
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
