from __future__ import annotations

import atexit
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from sentineltray.app import run
from sentineltray.config import load_config, load_config_with_override
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
    dry_run: true
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
    user_root = os.environ.get("USERPROFILE")
    if not user_root:
        raise ValueError("USERPROFILE nao definido")
    return Path(user_root) / "sentineltray" / "sentineltray.pid"


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


def _ensure_local_config_path(path: Path) -> None:
    user_root = os.environ.get("USERPROFILE")
    if not user_root:
        raise ValueError("USERPROFILE nao definido")
    base = (Path(user_root) / "sentineltray").resolve()
    try:
        if path.resolve().is_relative_to(base):
            return
    except OSError:
        pass
    raise ValueError(
        f"Configuracoes pessoais devem ficar em {base}."
    )


def _load_local_override(config_path: Path, override_path: Path):
    try:
        return load_config_with_override(str(config_path), str(override_path))
    except Exception as exc:
        _handle_config_error(override_path, exc)


def main() -> int:
    _ensure_single_instance()
    config_path = Path("config.yaml")
    use_cli = False
    override_path: Path | None = None
    local_override: Path | None = None
    args = [arg for arg in sys.argv[1:] if arg]
    for arg in args:
        if arg == "--cli":
            use_cli = True
        else:
            override_path = Path(arg)

    env_path = os.environ.get("SENTINELTRAY_CONFIG")
    if env_path:
        override_path = Path(env_path)

    if override_path is None:
        user_root = os.environ.get("USERPROFILE")
        if user_root:
            candidate = Path(user_root) / "sentineltray" / "config.local.yaml"
            local_override = candidate
            override_path = candidate

    try:
        if local_override is not None and override_path == local_override:
            _ensure_local_override(local_override)
            config = _load_local_override(config_path, local_override)
        elif override_path is not None:
            _ensure_local_config_path(override_path)
            config = load_config_with_override(str(config_path), str(override_path))
        else:
            config = load_config(str(config_path))
    except Exception as exc:
        _handle_config_error(override_path or config_path, exc)
    if use_cli:
        run(config)
    else:
        run_tray(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
