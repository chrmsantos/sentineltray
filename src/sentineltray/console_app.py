from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from threading import Event, Thread
from typing import Callable

from .app import Notifier
from .config import (
    AppConfig,
    decrypt_config_payload,
    encrypt_config_text,
    get_encrypted_config_path,
    get_user_data_dir,
    get_user_log_dir,
    load_config,
)
from .security_utils import parse_payload
from .status import StatusStore
from .status_cli import build_status_display, clear_screen, load_status_payload

LOGGER = logging.getLogger(__name__)


def _start_notifier(
    config: AppConfig,
    status: StatusStore,
    stop_event: Event,
    pause_event: Event,
    manual_scan_event: Event,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(
        target=notifier.run_loop,
        args=(stop_event, pause_event, manual_scan_event),
        daemon=True,
    )
    thread.start()
    return thread


def _create_config_editor() -> tuple[Callable[[], None], Callable[[], None]]:
    edit_process: subprocess.Popen[str] | None = None

    def on_open() -> None:
        nonlocal edit_process
        if edit_process is not None and edit_process.poll() is None:
            return
        try:
            data_dir = get_user_data_dir()
            config_path = data_dir / "config.local.yaml"
            encrypted_path = get_encrypted_config_path(config_path)
            temp_path = data_dir / "config.local.yaml.edit"

            if encrypted_path.exists():
                payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
                plaintext = decrypt_config_payload(payload, config_path=config_path)
                temp_path.write_text(plaintext, encoding="utf-8")
            elif config_path.exists():
                temp_path.write_text(
                    config_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            else:
                LOGGER.warning("Config file not found to edit")
                return

            edit_process = subprocess.Popen(["notepad.exe", str(temp_path)], text=True)
        except Exception as exc:
            LOGGER.warning("Failed to open config editor: %s", exc)

    def finalize_config_edit() -> None:
        nonlocal edit_process
        if edit_process is None:
            return
        if edit_process.poll() is None:
            return
        edit_process = None
        try:
            data_dir = get_user_data_dir()
            config_path = data_dir / "config.local.yaml"
            encrypted_path = get_encrypted_config_path(config_path)
            temp_path = data_dir / "config.local.yaml.edit"
            if not temp_path.exists():
                return
            try:
                load_config(str(temp_path))
            except Exception as exc:
                LOGGER.warning("Config validation failed after edit: %s", exc)
                temp_path.unlink(missing_ok=True)
                return

            plaintext = temp_path.read_text(encoding="utf-8")
            encoded = encrypt_config_text(plaintext, config_path=config_path)
            encrypted_path.write_text(encoded, encoding="utf-8")
            if config_path.exists():
                config_path.unlink()
            temp_path.unlink(missing_ok=True)
        except Exception as exc:
            LOGGER.warning("Failed to finalize config edit: %s", exc)

    return on_open, finalize_config_edit


def _write_config_error_details(message: str) -> Path:
    log_dir = get_user_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "config_error.txt"
    path.write_text(message.strip() + "\n", encoding="utf-8")
    return path


def _open_text_file(path: Path) -> None:
    try:
        subprocess.Popen(["notepad.exe", str(path)])
    except Exception as exc:
        LOGGER.warning("Failed to open details: %s", exc)


def _read_key() -> str | None:
    if os.name != "nt":
        return None
    try:
        import msvcrt

        if msvcrt.kbhit():
            return msvcrt.getwch()
    except Exception:
        return None
    return None


def _status_snapshot_text(
    config: AppConfig,
    *,
    status_path: Path,
    counter_seconds: int,
) -> str:
    payload = load_status_payload(status_path)
    return build_status_display(
        config=config,
        payload=payload,
        counter_seconds=counter_seconds,
        status_path=status_path,
    )


def _show_status_once(config: AppConfig, *, status_path: Path, counter_seconds: int) -> None:
    clear_screen()
    print(_status_snapshot_text(config, status_path=status_path, counter_seconds=counter_seconds))
    print("")
    input("Pressione Enter para voltar...")


def _watch_status(config: AppConfig, *, status_path: Path, started_at: float, finalize: Callable[[], None]) -> None:
    try:
        while True:
            counter = int(time.monotonic() - started_at)
            clear_screen()
            print(_status_snapshot_text(config, status_path=status_path, counter_seconds=counter))
            print("")
            print("Pressione Enter ou Q para voltar ao menu.")
            key = _read_key()
            if key in ("\r", "\n", "q", "Q"):
                return
            finalize()
            time.sleep(1)
    except KeyboardInterrupt:
        return


def _menu_header(status: StatusStore) -> list[str]:
    snapshot = status.snapshot()
    if snapshot.paused:
        state = "PAUSADO"
    elif snapshot.running:
        state = "EM EXECUÇÃO"
    else:
        state = "PARADO"
    return [
        "SentinelTray - Console",
        f"Status atual: {state}",
        "",
    ]


def run_console(config: AppConfig) -> None:
    status = StatusStore()
    stop_event = Event()
    pause_event = Event()
    manual_scan_event = Event()
    started_at = time.monotonic()
    notifier_thread = _start_notifier(
        config, status, stop_event, pause_event, manual_scan_event
    )
    on_open, finalize_config_edit = _create_config_editor()
    status_path = Path(config.status_export_file)

    try:
        while True:
            clear_screen()
            for line in _menu_header(status):
                print(line)
            print("Comandos:")
            print("  [S] Status agora")
            print("  [W] Status em tempo real")
            print("  [C] Editar config")
            print("  [P] Pausar/Retomar")
            print("  [M] Scan manual")
            print("  [Q] Sair")
            print("")
            try:
                command = input("Comando: ").strip().lower()
            except KeyboardInterrupt:
                return
            if command in ("q", "quit", "exit", "sair"):
                return
            if command in ("c", "config"):
                on_open()
            elif command in ("s", "status"):
                counter = int(time.monotonic() - started_at)
                _show_status_once(
                    config,
                    status_path=status_path,
                    counter_seconds=counter,
                )
            elif command in ("w", "watch"):
                _watch_status(
                    config,
                    status_path=status_path,
                    started_at=started_at,
                    finalize=finalize_config_edit,
                )
            elif command in ("p", "pause", "pausar", "retomar", "resume"):
                if pause_event.is_set():
                    pause_event.clear()
                else:
                    pause_event.set()
            elif command in ("m", "manual", "scan"):
                manual_scan_event.set()
                print("Scan manual solicitado.")
                time.sleep(1)
            finalize_config_edit()
    except KeyboardInterrupt:
        return
    finally:
        stop_event.set()
        try:
            notifier_thread.join(timeout=5)
        finally:
            finalize_config_edit()


def run_console_config_error(error_details: str) -> None:
    on_open, finalize_config_edit = _create_config_editor()
    details_path = _write_config_error_details(error_details)
    try:
        while True:
            clear_screen()
            print("SentinelTray - Erro de Configuração")
            print("")
            print(error_details)
            print("")
            print("Comandos:")
            print("  [C] Editar config")
            print("  [D] Abrir detalhes")
            print("  [Q] Sair")
            print("")
            try:
                command = input("Comando: ").strip().lower()
            except KeyboardInterrupt:
                return
            if command in ("q", "quit", "exit", "sair"):
                return
            if command in ("c", "config"):
                on_open()
            elif command in ("d", "details", "detalhes"):
                _open_text_file(details_path)
            finalize_config_edit()
    except KeyboardInterrupt:
        return
