from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from threading import Event, Thread
from typing import Iterable, Tuple

from .app import Notifier
from .config import AppConfig, get_project_root, get_user_data_dir, get_user_log_dir
from .status import StatusStore, format_status

LOGGER = logging.getLogger(__name__)


def _start_notifier(
    config: AppConfig,
    status: StatusStore,
    stop_event: Event,
    pause_event: Event,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(target=notifier.run_loop, args=(stop_event, pause_event), daemon=True)
    thread.start()
    return thread


def _parse_command(raw: str) -> Tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        return "", ""
    lowered = text.lower()
    if lowered in {"status", "pause", "resume", "toggle", "help", "exit", "quit"}:
        return lowered, ""
    if lowered.startswith("watch"):
        parts = text.split(maxsplit=1)
        return "watch", parts[1].strip() if len(parts) > 1 else ""
    if lowered.startswith("open "):
        parts = text.split(maxsplit=1)
        return "open", parts[1].strip().lower() if len(parts) > 1 else ""
    return lowered, ""


def _open_target(target: str) -> None:
    path = None
    if target == "config":
        path = get_user_data_dir() / "config.local.yaml"
    elif target == "data":
        path = get_user_data_dir()
    elif target == "logs":
        path = get_user_log_dir()
    elif target == "repo":
        path = get_project_root()

    if path is None:
        print("Comando open invalido. Use: open config | open data | open logs | open repo")
        return

    if hasattr(os, "startfile"):
        try:
            os.startfile(str(path))
            return
        except OSError as exc:
            LOGGER.warning("Falha ao abrir %s: %s", path, exc)
    print(f"Nao foi possivel abrir: {path}")


def _watch_status(config: AppConfig, status: StatusStore, interval_seconds: int) -> None:
    interval = max(1, int(interval_seconds))
    print("Monitorando status. Pressione Ctrl+C para sair.")
    try:
        while True:
            print(format_status(status.snapshot(), window_title_regex=config.window_title_regex, phrase_regex=config.phrase_regex))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Monitoramento interrompido.")


def _print_help() -> None:
    lines = [
        "Comandos principais:",
        "- status",
        "- pause / resume / toggle",
        "- watch [segundos]",
        "- open config | open data | open logs | open repo",
        "- help",
        "- exit",
    ]
    print("\n".join(lines))


def run_cli(config: AppConfig, args: Iterable[str] | None = None) -> int:
    _ = list(args or [])
    status = StatusStore()
    stop_event = Event()
    pause_event = Event()
    notifier_thread = _start_notifier(config, status, stop_event, pause_event)

    print("SentinelTray CLI iniciado. Digite 'help' para comandos.")
    exit_code = 0
    try:
        while True:
            try:
                raw = input("> ")
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando...")
                break

            command, arg = _parse_command(raw)
            if not command:
                continue
            if command == "status":
                print(format_status(status.snapshot(), window_title_regex=config.window_title_regex, phrase_regex=config.phrase_regex))
            elif command == "pause":
                pause_event.set()
                print("Pausado.")
            elif command == "resume":
                pause_event.clear()
                print("Retomado.")
            elif command == "toggle":
                if pause_event.is_set():
                    pause_event.clear()
                    print("Retomado.")
                else:
                    pause_event.set()
                    print("Pausado.")
            elif command == "watch":
                seconds = int(arg) if arg.isdigit() else int(config.status_refresh_seconds)
                _watch_status(config, status, seconds)
            elif command == "open":
                _open_target(arg)
            elif command == "help":
                _print_help()
            elif command in {"exit", "quit"}:
                break
            else:
                print("Comando invalido. Digite 'help'.")
    finally:
        stop_event.set()
        notifier_thread.join(timeout=5)

    return exit_code
