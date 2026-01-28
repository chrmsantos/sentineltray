from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent
    src_path = root / "src"
    src_value = str(src_path)
    if src_value not in sys.path:
        sys.path.insert(0, src_value)


_ensure_src_on_path()

from sentineltray import entrypoint as _entrypoint
from sentineltray.config import get_user_data_dir
from sentineltray.entrypoint import main

_MUTEX_HANDLE = None


def _pid_file_path() -> Path:
    base = get_user_data_dir()
    return base / "sentineltray.pid"


def _show_already_running_notice() -> None:
    message = (
        "SentinelTray já está em execução.\n\n"
        "Use a janela do console para acessar Config e Status."
    )
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "SentinelTray",
            0x00000040,
        )
    except Exception:
        sys.stderr.write(f"{message}\n")


def _ensure_single_instance_mutex() -> bool:
    global _MUTEX_HANDLE
    try:
        kernel32 = ctypes.windll.kernel32
    except Exception:
        return True
    for name in ("Global\\SentinelTrayMutex", "Local\\SentinelTrayMutex"):
        try:
            mutex = kernel32.CreateMutexW(None, False, name)
            _MUTEX_HANDLE = mutex
            if kernel32.GetLastError() == 183:
                return False
            if mutex:
                return True
        except Exception:
            continue
    return True


def _ensure_single_instance() -> None:
    pid_path = _pid_file_path()
    if not _ensure_single_instance_mutex():
        if not pid_path.exists():
            _show_already_running_notice()
            raise SystemExit(0)

    pid_path.parent.mkdir(parents=True, exist_ok=True)

    if pid_path.exists():
        prior_pid = pid_path.read_text(encoding="utf-8").strip()
        if prior_pid:
            subprocess.run(["taskkill", "/PID", prior_pid, "/F"], check=False)

    pid_path.write_text(str(os.getpid()), encoding="utf-8")


def _ensure_local_override(path: Path) -> None:
    _entrypoint._ensure_local_override(path)


if __name__ == "__main__":
    raise SystemExit(main())
