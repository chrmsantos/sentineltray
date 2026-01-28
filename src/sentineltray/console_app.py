from __future__ import annotations

import hashlib
import io
import logging
import os
import subprocess
import time
from collections.abc import MutableMapping
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable

import yaml

from .app import Notifier
from .config import (
    AppConfig,
    decrypt_config_payload,
    encrypt_config_text,
    get_encrypted_config_path,
    get_project_root,
    get_user_data_dir,
    get_user_log_dir,
    load_config,
)
from .security_utils import parse_payload
from .status import StatusStore
from .status_cli import build_status_display, clear_screen, load_status_payload

LOGGER = logging.getLogger(__name__)

try:
    from ruamel.yaml import YAML  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YAML = None


def _load_yaml_mapping(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("Config must be a mapping")
    return data


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_into_template(template: MutableMapping[str, Any], legacy: MutableMapping[str, Any]) -> None:
    for key, value in legacy.items():
        if (
            key in template
            and isinstance(template.get(key), MutableMapping)
            and isinstance(value, MutableMapping)
        ):
            _merge_into_template(template[key], value)
        else:
            template[key] = value


def _get_ruamel_yaml() -> YAML | None:
    if YAML is None:
        return None
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    yaml_rt.indent(mapping=2, sequence=4, offset=2)
    return yaml_rt


def _read_template_config_text() -> str | None:
    try:
        root = get_project_root()
        template_path = root / "templates" / "local" / "config.local.yaml"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
    except Exception as exc:
        LOGGER.warning("Failed to read config template: %s", exc)
    return None


def _apply_template_to_config_text(legacy_text: str, template_text: str | None) -> str:
    if not template_text:
        return legacy_text
    try:
        yaml_rt = _get_ruamel_yaml()
        if yaml_rt is not None:
            template_data = yaml_rt.load(template_text) or {}
            legacy_data = yaml_rt.load(legacy_text) or {}
            if not isinstance(template_data, MutableMapping) or not isinstance(
                legacy_data, MutableMapping
            ):
                raise ValueError("Config must be a mapping")
            _merge_into_template(template_data, legacy_data)
            buffer = io.StringIO()
            yaml_rt.dump(template_data, buffer)
            return buffer.getvalue()
        template_data = _load_yaml_mapping(template_text)
        legacy_data = _load_yaml_mapping(legacy_text)
        merged = _merge_dicts(template_data, legacy_data)
        return yaml.safe_dump(merged, sort_keys=False, allow_unicode=True)
    except Exception as exc:
        LOGGER.warning("Failed to merge config template: %s", exc)
        return legacy_text


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prune_files(path: Path, pattern: str, keep: int = 5) -> None:
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


def _load_current_config_text(config_path: Path) -> str:
    encrypted_path = get_encrypted_config_path(config_path)
    if encrypted_path.exists():
        payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
        return decrypt_config_payload(payload, config_path=config_path)
    return config_path.read_text(encoding="utf-8")


def _diff_counts(old: Any, new: Any) -> tuple[int, int]:
    added = 0
    changed = 0
    if isinstance(old, dict) and isinstance(new, dict):
        for key, new_value in new.items():
            if key not in old:
                added += 1
            else:
                old_value = old[key]
                if isinstance(old_value, dict) and isinstance(new_value, dict):
                    sub_added, sub_changed = _diff_counts(old_value, new_value)
                    added += sub_added
                    changed += sub_changed
                elif old_value != new_value:
                    changed += 1
        return added, changed
    return (0, 1) if old != new else (0, 0)


def _reconcile_template(*, dry_run: bool) -> None:
    data_dir = get_user_data_dir()
    config_path = data_dir / "config.local.yaml"
    template_text = _read_template_config_text()
    if not template_text:
        print("Template oficial não encontrado.")
        return
    try:
        legacy_text = _load_current_config_text(config_path)
    except Exception as exc:
        LOGGER.warning("Failed to load config for reconcile: %s", exc)
        print("Falha ao carregar a configuração local.")
        return

    merged_text = _apply_template_to_config_text(legacy_text, template_text)
    try:
        legacy_data = _load_yaml_mapping(legacy_text)
        merged_data = _load_yaml_mapping(merged_text)
    except Exception as exc:
        LOGGER.warning("Failed to parse config during reconcile: %s", exc)
        print("Falha ao validar a configuração durante a reconciliação.")
        return
    added, changed = _diff_counts(legacy_data, merged_data)
    template_hash = _hash_text(template_text)
    merged_hash = _hash_text(merged_text)

    if added == 0 and changed == 0:
        print("Configuração já está alinhada ao template.")
        return

    print("Reconciliação do template (dry-run).")
    print(f"  Chaves adicionadas: {added}")
    print(f"  Chaves alteradas: {changed}")
    print(f"  Template SHA256: {template_hash}")
    print(f"  Config SHA256: {merged_hash}")
    if dry_run:
        return

    encrypted_path = get_encrypted_config_path(config_path)
    encoded = encrypt_config_text(merged_text, config_path=config_path)
    encrypted_path.write_text(encoded, encoding="utf-8")
    if config_path.exists():
        config_path.unlink()
    LOGGER.info(
        "Config template reconciled",
        extra={
            "category": "config",
            "template_sha256": template_hash,
            "config_sha256": merged_hash,
        },
    )


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
            template_text = _read_template_config_text()

            _prune_files(data_dir, "config.local.yaml.edit.*", keep=5)

            if temp_path.exists():
                edit_process = subprocess.Popen(["notepad.exe", str(temp_path)], text=True)
                return

            if encrypted_path.exists():
                payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
                plaintext = decrypt_config_payload(payload, config_path=config_path)
                merged_text = _apply_template_to_config_text(plaintext, template_text)
                temp_path.write_text(merged_text, encoding="utf-8")
            elif config_path.exists():
                legacy_text = config_path.read_text(encoding="utf-8")
                merged_text = _apply_template_to_config_text(legacy_text, template_text)
                temp_path.write_text(merged_text, encoding="utf-8")
            else:
                LOGGER.warning("Config file not found to edit")
                return

            if template_text is not None:
                LOGGER.info(
                    "Config template synchronized for editor",
                    extra={
                        "category": "config",
                        "template_sha256": _hash_text(template_text),
                        "config_sha256": _hash_text(merged_text),
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
    _prune_files(log_dir, "config_error*.txt", keep=5)
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

    def save_config_edit() -> AppConfig | None:
        return finalize_config_edit()

    def apply_config_edit() -> None:
        nonlocal config, status_path, notifier_thread, stop_event, started_at
        new_config = save_config_edit()
        if new_config is None:
            return
        config = new_config
        status_path = Path(config.status_export_file)
        started_at = time.monotonic()
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
            pause_event,
            manual_scan_event,
        )

    try:
        while True:
            clear_screen()
            for line in _menu_header(status):
                print(line)
            print("Comandos:")
            print("  [S] Status agora")
            print("  [W] Status em tempo real")
            print("  [C] Editar config")
            print("  [R] Reconciliar template")
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
            elif command in ("r", "reconcile", "reconciliar"):
                _reconcile_template(dry_run=True)
                apply_now = input("Aplicar reconciliação? (s/N) ").strip().lower()
                if apply_now in ("s", "sim", "y", "yes"):
                    _reconcile_template(dry_run=False)
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
                    finalize=apply_config_edit,
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
