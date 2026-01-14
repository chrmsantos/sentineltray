from __future__ import annotations

import sys
from pathlib import Path

from notificator.app import run
from notificator.config import load_config


def main() -> int:
    config_path = Path("config.yaml")
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])

    config = load_config(str(config_path))
    run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
