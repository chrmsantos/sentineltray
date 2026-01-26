from __future__ import annotations

import atexit
import ctypes
import logging
import os
import subprocess
import sys
from pathlib import Path

_MUTEX_HANDLE = None


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent
    src_path = root / "src"
    src_value = str(src_path)
    if src_value not in sys.path:
        sys.path.insert(0, src_value)


_ensure_src_on_path()

from sentineltray.config import (
    encrypt_config_file,
    get_encrypted_config_path,
    get_user_data_dir,
    get_user_log_dir,
    is_portable_mode,
    select_encryption_method,
    load_config_secure,
)
from sentineltray.logging_setup import setup_logging
from sentineltray.tray_app import run_tray
from sentineltray import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)


def _pid_file_path() -> Path:
    base = get_user_data_dir()
    return base / "sentineltray.pid"



def _ensure_single_instance_mutex() -> bool:
    global _MUTEX_HANDLE
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\SentinelTrayMutex")
        _MUTEX_HANDLE = mutex
        if ctypes.windll.kernel32.GetLastError() == 183:
            return False
    except Exception:
        return True
    return True


def _terminate_previous(pid: int) -> None:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return


def _ensure_single_instance() -> None:
    _ensure_single_instance_mutex()
    pid_path = _pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    if pid_path.exists():
        try:
            existing_pid = int(pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            existing_pid = 0
        if existing_pid > 0 and existing_pid != os.getpid():
            _terminate_previous(existing_pid)

    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup() -> None:
        try:
            if pid_path.exists() and pid_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                pid_path.unlink()
        except Exception:
            return

    atexit.register(_cleanup)


def _ensure_local_override(path: Path) -> None:
    encrypted_path = get_encrypted_config_path(path)
    if not path.exists() and not encrypted_path.exists():
        raise SystemExit(
            "Local configuration not found.\n"
            f"Expected file: {path}\n"
            f"Or encrypted file: {encrypted_path}\n"
            "Create it from templates/local/config.local.yaml, "
            "fill the required fields, and run again."
        )

    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise SystemExit(
                "Local configuration is empty.\n"
                f"File: {path}\n"
                "Fill the required fields, save, and run again."
            )


def _handle_config_error(path: Path, exc: Exception) -> None:
    reason = str(exc)
    filename = path.name
    message = (
        "Configuration error.\n\n"
        f"File: {filename}\n"
        f"Details: {reason}\n\n"
        "Review the YAML formatting and required fields.\n"
        "After fixing, run again."
    )
    LOGGER.error("Config error: %s", reason, extra={"category": "config"})
    raise SystemExit(message) from exc


def _reject_extra_args(args: list[str]) -> None:
    if not args:
        return
    raise SystemExit(
        "Usage: run SentinelTray without arguments.\n"
        f"Arguments received: {' '.join(args)}"
    )


def _setup_boot_logging() -> None:
    if logging.getLogger().handlers:
        return
    log_root = get_user_log_dir()
    log_root.mkdir(parents=True, exist_ok=True)
    boot_log = log_root / "sentineltray_boot.log"
    setup_logging(
        str(boot_log),
        log_level="INFO",
        log_console_level="INFO",
        log_console_enabled=True,
        log_max_bytes=1_000_000,
        log_backup_count=5,
        log_run_files_keep=5,
        app_version=__version_label__,
        release_date=__release_date__,
        commit_hash="",
    )


def _ensure_windows() -> None:
    if sys.platform == "win32":
        return
    LOGGER.error(
        "Unsupported platform: %s (SentinelTray requires Windows)",
        sys.platform,
        extra={"category": "startup"},
    )
    raise SystemExit("SentinelTray requires Windows.")


def main() -> int:
    _ensure_single_instance()
    args = [arg for arg in sys.argv[1:] if arg]
    _reject_extra_args(args)

    try:
        local_path = get_user_data_dir() / "config.local.yaml"
        _ensure_local_override(local_path)
        _setup_boot_logging()
        _ensure_windows()
        LOGGER.info(
            "Portable mode: %s",
            "yes" if is_portable_mode(local_path.parent) else "no",
            extra={"category": "startup"},
        )
        LOGGER.info(
            "Config encryption: %s",
            select_encryption_method(local_path),
            extra={"category": "startup"},
        )
        config = load_config_secure(str(local_path))
        encrypted_path = get_encrypted_config_path(local_path)
        if local_path.exists() and not encrypted_path.exists():
            try:
                encrypt_config_file(str(local_path), remove_plain=True)
            except Exception as exc:
                sys.stderr.write(
                    f"Warning: failed to encrypt config file: {exc}\n"
                )
    except Exception as exc:
        _handle_config_error(local_path, exc)
    try:
        run_tray(config)
    except Exception as exc:
        LOGGER.error("Failed to start tray: %s", exc, extra={"category": "startup"})
        raise SystemExit(
            "Failed to start tray UI. Verify dependencies (pystray/Pillow)."
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
