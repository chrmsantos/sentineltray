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
from sentineltray.app import run


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
    if not path.exists():
        raise SystemExit(
            "Configuração local não encontrada.\n"
            f"Arquivo esperado: {path}\n"
            "Crie o arquivo a partir de templates/local/config.local.yaml, "
            "preencha os campos obrigatórios e execute novamente."
        )

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise SystemExit(
            "Configuração local vazia.\n"
            f"Arquivo: {path}\n"
            "Preencha os campos obrigatórios, salve e execute novamente."
        )


def _handle_config_error(path: Path, exc: Exception) -> None:
    reason = str(exc)
    filename = path.name
    message = (
        "Erro nas configurações.\n\n"
        f"Arquivo: {filename}\n"
        f"Detalhe: {reason}\n\n"
        "Revise a formatação YAML e os campos obrigatórios.\n"
        "Após corrigir, execute novamente."
    )
    raise SystemExit(message) from exc


def _reject_extra_args(args: list[str]) -> None:
    if not args:
        return
    raise SystemExit(
        "Uso: execute o SentinelTray sem argumentos.\n"
        f"Argumentos recebidos: {' '.join(args)}"
    )


def main() -> int:
    _ensure_single_instance()
    args = [arg for arg in sys.argv[1:] if arg]
    _reject_extra_args(args)

    try:
        local_path = get_user_data_dir() / "config.local.yaml"
        _ensure_local_override(local_path)
        config = load_config(str(local_path))
    except Exception as exc:
        _handle_config_error(local_path, exc)
    run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
