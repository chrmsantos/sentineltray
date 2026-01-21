from __future__ import annotations

import atexit
import ctypes
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

from sentineltray.config import get_user_data_dir, load_config
from sentineltray.tray_cli import run_tray_cli


def _pid_file_path() -> Path:
    base = get_user_data_dir()
    return base / "sentineltray.pid"


def _startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ValueError("APPDATA is required for Windows startup path")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _startup_cmd_path() -> Path:
    return _startup_dir() / "SentinelTray.cmd"


def _set_run_key(command: str | None) -> None:
    try:
        import winreg
    except Exception:
        return
    key_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if command is None:
                try:
                    winreg.DeleteValue(key, "SentinelTray")
                except FileNotFoundError:
                    return
            else:
                winreg.SetValueEx(key, "SentinelTray", 0, winreg.REG_SZ, command)
    except Exception:
        return


def _ensure_autostart(enabled: bool) -> None:
    try:
        startup_dir = _startup_dir()
        startup_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return

    cmd_path = _startup_cmd_path()
    if not enabled:
        try:
            if cmd_path.exists():
                cmd_path.unlink()
        except Exception:
            return
        _set_run_key(None)
        return

    root = Path(__file__).resolve().parent
    run_cmd = root / "scripts" / "run.cmd"
    content = "\r\n".join(
        [
            "@echo off",
            f'cd /d "{root}"',
            f'start "" /min "{run_cmd}"',
        ]
    ) + "\r\n"
    try:
        if cmd_path.exists():
            current = cmd_path.read_text(encoding="utf-8", errors="ignore")
            if current == content:
                _set_run_key(f'"{cmd_path}"')
                return
        cmd_path.write_text(content, encoding="utf-8")
    except Exception:
        return
    _set_run_key(f'"{cmd_path}"')


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
    if not path.exists():
        raise SystemExit(
            "Config local ausente. Crie o arquivo em: "
            f"{path}\n"
            "Preencha todos os campos obrigatorios e reinicie o programa."
        )

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise SystemExit(
            "Config local vazio. Preencha o arquivo em: "
            f"{path}\n"
            "Salve as alteracoes e reinicie o programa."
        )


def _handle_config_error(path: Path, exc: Exception) -> None:
    reason = str(exc)
    message = (
        "Erro nas configuracoes.\n\n"
        f"Arquivo: {path}\n"
        f"Detalhe: {reason}\n\n"
        "Corrija o arquivo e reinicie o programa.\n"
        "O SentinelTray sera encerrado para permitir as correcoes."
    )
    raise SystemExit(message) from exc


def main() -> int:
    _ensure_single_instance()
    args = [arg for arg in sys.argv[1:] if arg]

    try:
        local_path = get_user_data_dir() / "config.local.yaml"
        _ensure_local_override(local_path)
        config = load_config(str(local_path))
    except Exception as exc:
        _handle_config_error(local_path, exc)
    _ensure_autostart(getattr(config, "auto_start", True))
    return run_tray_cli(config)


if __name__ == "__main__":
    raise SystemExit(main())
