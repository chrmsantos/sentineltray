from __future__ import annotations

import atexit
import ctypes
import logging
import os
import subprocess
import sys
import time
from builtins import input as input
from getpass import getpass
from pathlib import Path

from .config import (
    AppConfig,
    get_user_data_dir,
    get_user_log_dir,
    get_project_root,
    load_config,
)
from .console_app import run_console, run_console_config_error
from .email_sender import EmailAuthError, validate_smtp_credentials
from .config_reconcile import (
    ensure_local_config_from_template,
    read_template_config_text,
    reconcile_template_config,
)
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
        terminated = _terminate_existing_instance()
        if terminated:
            for _ in range(6):
                time.sleep(0.5)
                if _ensure_single_instance_mutex():
                    break
            else:
                LOGGER.error(
                    "Failed to acquire single-instance mutex after termination",
                    extra={"category": "startup"},
                )
                _show_already_running_notice()
                raise SystemExit(0)
        else:
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


def _terminate_existing_instance() -> bool:
    pid_path = _pid_file_path()
    if not pid_path.exists():
        LOGGER.warning(
            "Single-instance mutex exists but PID file is missing",
            extra={"category": "startup"},
        )
        return False
    try:
        prior_pid = pid_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        LOGGER.warning(
            "Failed to read PID file for termination: %s",
            exc,
            extra={"category": "startup"},
        )
        return False
    if not prior_pid:
        LOGGER.warning(
            "PID file was empty; cannot terminate prior instance",
            extra={"category": "startup"},
        )
        return False
    LOGGER.info(
        "Existing instance detected; terminating PID %s",
        prior_pid,
        extra={"category": "startup"},
    )
    try:
        result = subprocess.run(
            ["taskkill", "/PID", prior_pid, "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        LOGGER.error(
            "Failed to terminate prior instance PID %s: %s",
            prior_pid,
            exc,
            extra={"category": "startup"},
        )
        return False
    if result.returncode != 0:
        LOGGER.error(
            "taskkill failed for PID %s: %s",
            prior_pid,
            result.stderr.strip(),
            extra={"category": "startup"},
        )
        return False
    try:
        pid_path.unlink()
    except Exception:
        pass
    return True


def _ensure_local_override(path: Path) -> None:
    if not path.exists():
        raise SystemExit(
            "Local configuration not found.\n"
            f"Expected file: {path}\n"
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
    message = (
        "Configuration error.\n\n"
        f"Config file: {path}\n"
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
        log_backup_count=3,
        log_run_files_keep=3,
        app_version=__version_label__,
        release_date=__release_date__,
        commit_hash="",
    )


def _run_startup_integrity_checks(local_path: Path) -> None:
    data_dir = local_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    log_root = get_user_log_dir()
    log_root.mkdir(parents=True, exist_ok=True)

    template_text = read_template_config_text(get_project_root())
    if template_text is None:
        LOGGER.warning(
            "Config template not found; startup integrity limited",
            extra={"category": "startup"},
        )
    else:
        ensure_local_config_from_template(
            local_path,
            template_text=template_text,
            logger=LOGGER,
        )
        try:
            reconcile_template_config(
                local_path,
                template_text=template_text,
                dry_run=False,
                logger=LOGGER,
            )
        except Exception as exc:
            LOGGER.warning(
                "Failed to reconcile config template: %s",
                exc,
                extra={"category": "config"},
            )



def _validate_smtp_config(config: AppConfig) -> None:
    failures: list[str] = []
    for index, monitor in enumerate(config.monitors, start=1):
        email = monitor.email
        if email.dry_run:
            continue
        try:
            validate_smtp_credentials(email)
        except EmailAuthError as exc:
            failures.append(f"monitor {index}: {exc}")
        except Exception as exc:
            failures.append(f"monitor {index}: {exc}")
    if failures:
        raise ValueError("SMTP validation failed: " + "; ".join(failures))


def _ensure_windows() -> None:
    if sys.platform == "win32":
        return
    LOGGER.error(
        "Unsupported platform: %s (SentinelTray requires Windows)",
        sys.platform,
        extra={"category": "startup"},
    )
    raise SystemExit("SentinelTray requires Windows.")


def _require_dry_run_on_first_use(config) -> None:
    try:
        state_path = Path(config.state_file)
    except Exception:
        return
    if state_path.exists():
        return
    if config.log_only_mode:
        return
    for monitor in config.monitors:
        if not monitor.email.dry_run:
            raise ValueError(
                "First run requires dry_run=true to validate configuration safely."
            )


def _missing_smtp_passwords(config: AppConfig) -> list[tuple[int, str]]:
    missing: list[tuple[int, str]] = []
    global_password = os.environ.get("SENTINELTRAY_SMTP_PASSWORD", "").strip()
    for index, monitor in enumerate(config.monitors, start=1):
        username = str(monitor.email.smtp_username or "").strip()
        if not username:
            continue
        if str(monitor.email.smtp_password or "").strip():
            continue
        indexed_password = os.environ.get(f"SENTINELTRAY_SMTP_PASSWORD_{index}", "").strip()
        if indexed_password or global_password:
            continue
        missing.append((index, username))
    return missing


def _prompt_smtp_passwords(missing: list[tuple[int, str]]) -> None:
    if not missing:
        return
    print("SentinelTray - Login SMTP")
    print("")
    print("Informe a senha SMTP para continuar.")
    print("Opções: [Q] Sair")
    print("")
    for index, username in missing:
        while True:
            print(f"Usuário SMTP (monitor {index}): {username}")
            password = getpass("Senha SMTP: ").strip()
            if password:
                os.environ[f"SENTINELTRAY_SMTP_PASSWORD_{index}"] = password
                break
            choice = input("Senha vazia. [T]entar novamente ou [Q] Sair: ").strip().lower()
            if choice in ("q", "sair", "exit"):
                raise SystemExit("Senha SMTP não informada.")
            print("")
    print("")
    print("Senha SMTP registrada para a sessão.")


def main() -> int:
    _setup_boot_logging()
    _ensure_single_instance()
    args = [arg for arg in sys.argv[1:] if arg]
    _reject_extra_args(args)

    local_path = get_user_data_dir() / "config.local.yaml"
    config = None
    config_error_message = None
    try:
        _ensure_windows()
        _run_startup_integrity_checks(local_path)
        _ensure_local_override(local_path)
        config = load_config(str(local_path))
        missing_passwords = _missing_smtp_passwords(config)
        if missing_passwords:
            _prompt_smtp_passwords(missing_passwords)
            config = load_config(str(local_path))
        _require_dry_run_on_first_use(config)
        _validate_smtp_config(config)
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
