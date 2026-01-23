from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlretrieve


def _run(command: list[str]) -> int:
    result = subprocess.run(command, check=False)
    return result.returncode


def _ensure_pip(python_exe: str) -> bool:
    if _run([python_exe, "-m", "pip", "--version"]) == 0:
        return True
    if _run([python_exe, "-m", "ensurepip", "--upgrade"]) == 0:
        return _run([python_exe, "-m", "pip", "--version"]) == 0
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            get_pip = Path(temp_dir) / "get-pip.py"
            urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)
            if _run([python_exe, str(get_pip)]) != 0:
                return False
        if _run([python_exe, "-m", "pip", "--version"]) == 0:
            return True
        scripts_dir = Path(python_exe).parent / "Scripts" / "pip.exe"
        if scripts_dir.exists():
            return _run([str(scripts_dir), "--version"]) == 0
        return False
    except Exception:
        return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    wheel_dir = Path(
        os.environ.get("SENTINELTRAY_WHEEL_DIR", str(root / "runtime" / "wheels"))
    )
    marker = Path(
        os.environ.get("SENTINELTRAY_DEPS_MARKER", str(root / "runtime" / ".deps_ready"))
    )
    requirements = root / "requirements.lock"
    scripts_pip = Path(sys.executable).parent / "Scripts" / "pip.exe"

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
    if not _ensure_pip(sys.executable):
        print(
            "pip installation failed. Check internet access or use prepare_portable_runtime.cmd.",
            file=sys.stderr,
        )
        return 1

    print("Installing dependencies from wheelhouse...")
    pip_command = [sys.executable, "-m", "pip"]
    if _run([sys.executable, "-m", "pip", "--version"]) != 0 and scripts_pip.exists():
        pip_command = [str(scripts_pip)]
    code = _run(
        pip_command
        + [
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
