from __future__ import annotations

from builtins import input as input

import logging
import os
import subprocess
import time
from getpass import getpass
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
    load_config_secure,
)
from .config_reconcile import (
    TemplateReconcileSummary,
    apply_template_to_config_text,
    hash_text,
    read_template_config_text,
    reconcile_template_config,
)
from .security_utils import parse_payload
from .status import StatusStore, format_timestamp

LOGGER = logging.getLogger(__name__)

def _prune_files(path: Path, pattern: str, keep: int = 3) -> None:
    entries = sorted(
        path.glob(pattern),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for entry in entries[keep:]:
        try:
            entry.unlink()
        except Exception:
            continue


def _run_template_reconcile(
    config_path: Path,
    template_text: str,
    *,
    dry_run: bool,
) -> TemplateReconcileSummary | None:
    try:
        return reconcile_template_config(
            config_path,
            template_text=template_text,
            dry_run=dry_run,
            logger=LOGGER,
        )
    except Exception as exc:
        LOGGER.warning("Failed to reconcile config template: %s", exc)
        print("Falha ao validar a configuração durante a reconciliação.")
        return None


def _print_reconcile_summary(summary: TemplateReconcileSummary | None, *, dry_run: bool) -> None:
    if summary is None:
        return
    if summary.skipped_reason == "template_missing":
        print("Template oficial não encontrado.")
        return
    if summary.skipped_reason == "config_missing":
        print("Configuração local não encontrada.")
        return
    if summary.added == 0 and summary.changed == 0:
        print("Configuração já está alinhada ao template.")
        return
    if dry_run:
        print("Reconciliação do template (dry-run).")
    else:
        print("Reconciliação do template aplicada.")
    print(f"  Chaves adicionadas: {summary.added}")
    print(f"  Chaves alteradas: {summary.changed}")
    if summary.template_sha256:
        print(f"  Template SHA256: {summary.template_sha256}")
    if summary.config_sha256:
        print(f"  Config SHA256: {summary.config_sha256}")


def _reconcile_template(*, dry_run: bool) -> None:
    data_dir = get_user_data_dir()
    config_path = data_dir / "config.local.yaml"
    template_text = read_template_config_text()
    if template_text is None:
        print("Template oficial não encontrado.")
        return
    summary = _run_template_reconcile(config_path, template_text, dry_run=dry_run)
    _print_reconcile_summary(summary, dry_run=dry_run)


def _start_notifier(
    config: AppConfig,
    status: StatusStore,
    stop_event: Event,
    manual_scan_event: Event,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(
        target=notifier.run_loop,
        args=(stop_event, manual_scan_event),
        daemon=True,
    )
    thread.start()
    return thread


def _create_config_editor() -> tuple[Callable[[], None], Callable[[], AppConfig | None]]:
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
            template_text = read_template_config_text()

            _prune_files(data_dir, "config.local.yaml.edit.*", keep=3)

            if temp_path.exists():
                edit_process = subprocess.Popen(["notepad.exe", str(temp_path)], text=True)
                return

            if encrypted_path.exists():
                payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
                plaintext = decrypt_config_payload(payload, config_path=config_path)
                merged_text = apply_template_to_config_text(plaintext, template_text)
                temp_path.write_text(merged_text, encoding="utf-8")
            elif config_path.exists():
                legacy_text = config_path.read_text(encoding="utf-8")
                merged_text = apply_template_to_config_text(legacy_text, template_text)
                temp_path.write_text(merged_text, encoding="utf-8")
            else:
                LOGGER.warning("Config file not found to edit")
                return

            if template_text is not None:
                LOGGER.info(
                    "Config template synchronized for editor",
                    extra={
                        "category": "config",
                        "template_sha256": hash_text(template_text),
                        "config_sha256": hash_text(merged_text),
                    },
                )

            edit_process = subprocess.Popen(["notepad.exe", str(temp_path)], text=True)
        except Exception as exc:
            LOGGER.warning("Failed to open config editor: %s", exc)

    def finalize_config_edit() -> AppConfig | None:
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
                new_config = load_config(str(temp_path))
            except Exception as exc:
                LOGGER.warning("Config validation failed after edit: %s", exc)
                return None

            plaintext = temp_path.read_text(encoding="utf-8")
            encoded = encrypt_config_text(plaintext, config_path=config_path)
            encrypted_path.write_text(encoded, encoding="utf-8")
            if config_path.exists():
                config_path.unlink()
            temp_path.unlink(missing_ok=True)
            return new_config
        except Exception as exc:
            LOGGER.warning("Failed to finalize config edit: %s", exc)
        return None

    return on_open, finalize_config_edit


def _write_config_error_details(message: str) -> Path:
    log_dir = get_user_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "config_error.txt"
    if path.exists():
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        rotated = log_dir / f"config_error.{timestamp}.txt"
        try:
            path.rename(rotated)
        except Exception:
            pass
    path.write_text(message.strip() + "\n", encoding="utf-8")
    _prune_files(log_dir, "config_error*.txt", keep=3)
    return path


def _open_text_file(path: Path) -> None:
    try:
        subprocess.Popen(["notepad.exe", str(path)])
    except Exception as exc:
        LOGGER.warning("Failed to open details: %s", exc)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _menu_header(status: StatusStore) -> list[str]:
    snapshot = status.snapshot()
    state = "EXECUTANDO" if snapshot.running else "PARADO"
    last_send_at = format_timestamp(snapshot.last_send)
    last_message = f"ENVIADA ({last_send_at})" if last_send_at else "NENHUMA"
    queue = snapshot.email_queue
    queue_line = (
        "Fila e-mail: "
        f"{queue.get('queued', 0)} pendentes, "
        f"{queue.get('deferred', 0)} atrasados, "
        f"{queue.get('failed', 0)} falhas"
    )
    return [
        "SentinelTray - Console",
        f"Status atual: {state}",
        f"ERROS: {snapshot.error_count}",
        f"Última mensagem: {last_message}",
        queue_line,
        "",
    ]


def run_console(config: AppConfig) -> None:
    status = StatusStore()
    stop_event = Event()
    manual_scan_event = Event()
    notifier_thread = _start_notifier(
        config, status, stop_event, manual_scan_event
    )
    on_open, finalize_config_edit = _create_config_editor()

    def save_config_edit() -> AppConfig | None:
        return finalize_config_edit()

    def apply_config_edit() -> None:
        nonlocal config, notifier_thread, stop_event
        new_config = save_config_edit()
        if new_config is None:
            return
        config = new_config
        stop_event.set()
        try:
            notifier_thread.join(timeout=5)
        except Exception as exc:
            LOGGER.warning("Failed to stop notifier for config reload: %s", exc)
        stop_event = Event()
        notifier_thread = _start_notifier(
            config,
            status,
            stop_event,
            manual_scan_event,
        )

    try:
        while True:
            clear_screen()
            for line in _menu_header(status):
                print(line)
            print("Comandos:")
            print("  [C] Editar config")
            print("  [R] Reconciliar template")
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
            elif command in ("r", "reconcile", "reconciliar"):
                _reconcile_template(dry_run=True)
                apply_now = input("Aplicar reconciliação? (s/N) ").strip().lower()
                if apply_now in ("s", "sim", "y", "yes"):
                    _reconcile_template(dry_run=False)
            elif command in ("m", "manual", "scan"):
                manual_scan_event.set()
                print("Scan manual solicitado.")
                time.sleep(1)
            apply_config_edit()
    except KeyboardInterrupt:
        return
    finally:
        stop_event.set()
        try:
            notifier_thread.join(timeout=5)
        finally:
            save_config_edit()


def run_console_config_error(error_details: str) -> None:
    on_open, finalize_config_edit = _create_config_editor()
    details_path = _write_config_error_details(error_details)
    local_path = get_user_data_dir() / "config.local.yaml"
    supports_smtp_prompt = "SENTINELTRAY_SMTP_PASSWORD" in error_details
    smtp_usernames: list[str] = []
    try:
        config = load_config_secure(str(local_path))
        smtp_usernames = [
            monitor.email.smtp_username
            for monitor in config.monitors
            if monitor.email.smtp_username
        ]
    except Exception:
        smtp_usernames = []
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
            if supports_smtp_prompt:
                print("  [P] Definir senha SMTP")
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
            elif supports_smtp_prompt and command in ("p", "smtp"):
                print("")
                if smtp_usernames:
                    for username in smtp_usernames:
                        print(f"Usuário SMTP: {username}")
                else:
                    print("Usuário SMTP: (não definido no config)")
                password = getpass("Senha SMTP (SENTINELTRAY_SMTP_PASSWORD): ").strip()
                if password:
                    os.environ["SENTINELTRAY_SMTP_PASSWORD"] = password
                try:
                    config = load_config_secure(str(local_path))
                except Exception as exc:
                    print(f"Falha ao validar config: {exc}")
                    time.sleep(2)
                    continue
                run_console(config)
                return
            finalize_config_edit()
    except KeyboardInterrupt:
        return
