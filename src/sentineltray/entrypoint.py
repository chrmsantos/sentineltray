from __future__ import annotations

import atexit
import ctypes
import logging
import os
import sys
from pathlib import Path

from .config import (
    encrypt_config_file,
    get_encrypted_config_path,
    get_user_data_dir,
    get_user_log_dir,
    is_portable_mode,
    load_config_secure,
    select_encryption_method,
)
from .console_app import run_console, run_console_config_error
from .logging_setup import setup_logging
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)
_mutex_handle = None


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
    global _mutex_handle
    try:
        kernel32 = ctypes.windll.kernel32
    except Exception:
        return True
    for name in ("Global\\SentinelTrayMutex", "Local\\SentinelTrayMutex"):
        try:
            mutex = kernel32.CreateMutexW(None, False, name)
            _mutex_handle = mutex
            if kernel32.GetLastError() == 183:
                return False
            if mutex:
                LOGGER.info(
                    "Single-instance mutex acquired: %s",
                    name,
                    extra={"category": "startup"},
                )
                return True
        except Exception as exc:
            LOGGER.warning(
                "Failed to create mutex %s: %s",
                name,
                exc,
                extra={"category": "startup"},
            )
            continue
    return True


def _ensure_single_instance() -> None:
    if not _ensure_single_instance_mutex():
        _show_already_running_notice()
        raise SystemExit(0)
    pid_path = _pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    if pid_path.exists():
        try:
            pid_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup() -> None:
        try:
            if (
                pid_path.exists()
                and pid_path.read_text(encoding="utf-8").strip() == str(os.getpid())
            ):
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


def _handle_config_error(path: Path, exc: Exception) -> str:
    reason = str(exc)
    encrypted_path = get_encrypted_config_path(path)
    message = (
        "Configuration error.\n\n"
        f"Config file: {path}\n"
        f"Encrypted config: {encrypted_path}\n"
        f"Details: {reason}\n\n"
        "Review the YAML formatting and required fields.\n"
        "After fixing, reopen SentinelTray.\n\n"
        "Quick actions:\n"
        "- Use the console menu: Config (opens an editable temporary file).\n"
        "- Use the console menu: Detalhes (shows this message).\n"
        "- For test mode only, set email.dry_run=true.\n"
    )
    LOGGER.error("Config error: %s", reason, extra={"category": "config"})
    return message


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

    local_path = get_user_data_dir() / "config.local.yaml"
    config = None
    config_error_message = None
    try:
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
        config_error_message = _handle_config_error(local_path, exc)

    try:
        if config_error_message is not None:
            run_console_config_error(config_error_message)
        else:
            if config is None:
                raise SystemExit("Configuration not loaded.")
            run_console(config)
    except Exception as exc:
        LOGGER.error("Failed to start console UI: %s", exc, extra={"category": "startup"})
        raise SystemExit("Failed to start console UI.") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
