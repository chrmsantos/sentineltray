from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run(command: list[str]) -> int:
    result = subprocess.run(command, check=False)
    return result.returncode


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    wheel_dir = Path(
        os.environ.get("SENTINELTRAY_WHEEL_DIR", str(root / "runtime" / "wheels"))
    )
    marker = Path(
        os.environ.get("SENTINELTRAY_DEPS_MARKER", str(root / "runtime" / ".deps_ready"))
    )
    requirements = root / "requirements.lock"

    if marker.exists():
        print("Runtime dependencies already bootstrapped.")
        return 0

    if not wheel_dir.exists():
        print(f"Wheel directory not found: {wheel_dir}", file=sys.stderr)
        return 1
    if not requirements.exists():
        print(f"requirements.lock not found: {requirements}", file=sys.stderr)
        return 1

    print("Ensuring pip is available...")
    if _run([sys.executable, "-m", "pip", "--version"]) != 0:
        _run([sys.executable, "-m", "ensurepip", "--upgrade"])

    print("Installing dependencies from wheelhouse...")
    code = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheel_dir),
            "-r",
            str(requirements),
        ]
    )
    if code != 0:
        print("Dependency installation failed.", file=sys.stderr)
        return code

    marker.write_text("ok", encoding="utf-8")
    print("Dependencies installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
