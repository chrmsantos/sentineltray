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


def _ensure_pth(python_exe: str) -> None:
    python_dir = Path(python_exe).parent
    pth_file = next(python_dir.glob("*.pth"), None)
    if pth_file is None:
        pth_file = next(python_dir.glob("*._pth"), None)
    if pth_file is None:
        return
    text = pth_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    desired = ["Lib/site-packages", "Scripts", "import site"]
    updated = False
    for entry in desired:
        if entry not in lines:
            lines.append(entry)
            updated = True
    if updated:
        pth_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pip_extra_args() -> list[str]:
    extra: list[str] = []
    index_url = os.environ.get("SENTINELTRAY_PIP_INDEX_URL")
    trusted_host = os.environ.get("SENTINELTRAY_PIP_TRUSTED_HOST")
    proxy = os.environ.get("SENTINELTRAY_PIP_PROXY")
    if index_url:
        extra += ["--index-url", index_url]
    if trusted_host:
        extra += ["--trusted-host", trusted_host]
    if proxy:
        extra += ["--proxy", proxy]
    return extra


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
    _ensure_pth(sys.executable)
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
    install_args = [
        "install",
        "--no-index",
        "--find-links",
        str(wheel_dir),
        "-r",
        str(requirements),
    ]
    code = _run(pip_command + install_args)
    if code != 0:
        print("Wheelhouse missing packages; attempting to download.")
        download_args = [
            "download",
            "--only-binary=:all:",
            "--dest",
            str(wheel_dir),
            "-r",
            str(requirements),
        ]
        extra_args = _pip_extra_args()
        if extra_args:
            print("Using custom pip settings from environment.")
        if _run(pip_command + download_args + extra_args) == 0:
            code = _run(pip_command + install_args)
    if code != 0:
        print("Dependency installation failed.", file=sys.stderr)
        return code

    marker.write_text("ok", encoding="utf-8")
    print("Dependencies installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
