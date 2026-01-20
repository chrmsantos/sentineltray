from __future__ import annotations

import atexit
import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

_MUTEX_HANDLE = None


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent
    src_path = root / "src"
    src_value = str(src_path)
    if src_value not in sys.path:
        sys.path.insert(0, src_value)


_ensure_src_on_path()

from sentineltray.app import run
from sentineltray.config import get_user_data_dir, load_config
from sentineltray.tray_app import run_tray

LOCAL_TEMPLATE = """# SentinelTray sobrescritas locais
# Preencha os valores abaixo e reinicie o app.

window_title_regex: ""
phrase_regex: ""
email:
    smtp_host: ""
    smtp_port: 587
    smtp_username: ""
    smtp_password: ""
    from_address: ""
    to_addresses: []
    use_tls: true
    timeout_seconds: 45
    subject: "SentinelTray Notification"
    retry_attempts: 3
    retry_backoff_seconds: 5
    dry_run: true
status_export_csv: "logs/status.csv"
status_refresh_seconds: 1
allow_window_restore: true
start_minimized: false
log_only_mode: false
config_checksum_file: "logs/config.checksum"
min_free_disk_mb: 100
"""


def _open_for_editing(path: Path) -> None:
    if hasattr(os, "startfile"):
        try:
            os.startfile(str(path))
        except OSError:
            return


def _ask_reedit(path: Path, reason: str) -> bool:
    message = (
        "Erro nas configuracoes.\n\n"
        f"Arquivo: {path}\n"
        f"Motivo: {reason}\n\n"
        "Deseja reabrir o arquivo para editar?"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        try:
            return messagebox.askyesno("SentinelTray", message)
        finally:
            root.destroy()
    except Exception:
        return False


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


def _write_local_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LOCAL_TEMPLATE, encoding="utf-8")


def _ensure_local_override(path: Path) -> None:
    if not path.exists():
        _write_local_template(path)
        _open_for_editing(path)
        raise SystemExit(f"Local config created at {path}. Fill it and restart.")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        _write_local_template(path)
        _open_for_editing(path)
        raise SystemExit(f"Local config is empty at {path}. Fill it and restart.")


def _handle_config_error(path: Path, exc: Exception) -> None:
    reason = str(exc)
    if _ask_reedit(path, reason):
        _open_for_editing(path)
        raise SystemExit(f"Reabra e edite o arquivo: {path}") from exc
    raise SystemExit("Execucao encerrada pelo usuario.") from exc


def main() -> int:
    _ensure_single_instance()
    use_cli = False
    args = [arg for arg in sys.argv[1:] if arg]
    for arg in args:
        if arg == "--cli":
            use_cli = True
        else:
            raise SystemExit("Somente --cli e permitido. Use config.local.yaml.")

    try:
        local_path = get_user_data_dir() / "config.local.yaml"
        _ensure_local_override(local_path)
        config = load_config(str(local_path))
    except Exception as exc:
        _handle_config_error(local_path, exc)
    if use_cli:
        run(config)
    else:
        run_tray(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
