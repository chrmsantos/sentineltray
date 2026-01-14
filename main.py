from __future__ import annotations

import sys
from pathlib import Path

from notificator.app import run
from notificator.config import load_config
from notificator.tray_app import run_tray


def main() -> int:
    config_path = Path("config.yaml")
    use_cli = False
    args = [arg for arg in sys.argv[1:] if arg]
    for arg in args:
        if arg == "--cli":
            use_cli = True
        else:
            config_path = Path(arg)

    config = load_config(str(config_path))
    if use_cli:
        run(config)
    else:
        run_tray(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
