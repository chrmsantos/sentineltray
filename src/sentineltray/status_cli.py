from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, get_user_data_dir, load_config_secure
from .status import StatusSnapshot, format_status


def _load_status_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_status_error": "status file not found"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_status_error": "status file unreadable"}
    if isinstance(data, dict):
        return dict(data)
    return {}


def load_status_payload(path: Path) -> dict[str, Any]:
    return _load_status_payload(path)


def _build_snapshot(payload: dict[str, Any]) -> StatusSnapshot:
    return StatusSnapshot(
        running=bool(payload.get("running", False)),
        paused=bool(payload.get("paused", False)),
        last_scan=str(payload.get("last_scan", "")),
        last_match=str(payload.get("last_match", "")),
        last_match_at=str(payload.get("last_match_at", "")),
        last_send=str(payload.get("last_send", "")),
        last_error=str(payload.get("last_error", "")),
        last_healthcheck=str(payload.get("last_healthcheck", "")),
        uptime_seconds=int(payload.get("uptime_seconds", 0) or 0),
        error_count=int(payload.get("error_count", 0) or 0),
    )


def _format_queue(payload: dict[str, Any]) -> list[str]:
    queue = payload.get("email_queue")
    if not isinstance(queue, dict):
        queue = {}
    queued = queue.get("queued", 0)
    sent = queue.get("sent", 0)
    failed = queue.get("failed", 0)
    deferred = queue.get("deferred", 0)
    oldest = queue.get("oldest_age_seconds", 0)
    return [
        "Email queue:",
        f"  queued: {queued}",
        f"  sent: {sent}",
        f"  failed: {failed}",
        f"  deferred: {deferred}",
        f"  oldest_age_seconds: {oldest}",
    ]


def _format_file_mtime(path: Path) -> str:
    try:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime)
        return timestamp.strftime("%d-%m-%Y - %H:%M:%S")
    except Exception:
        return ""


def build_status_display(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    counter_seconds: int,
    status_path: Path,
) -> str:
    snapshot = _build_snapshot(payload)
    status_text = format_status(
        snapshot,
        window_title_regex=config.window_title_regex,
        phrase_regex=config.phrase_regex,
        poll_interval_seconds=config.poll_interval_seconds,
    )
    monitor_count = payload.get("monitor_count", "")
    status_export_errors = payload.get("status_export_errors", "")
    status_csv_errors = payload.get("status_csv_errors", "")
    state_write_errors = payload.get("state_write_errors", "")
    last_update = _format_file_mtime(status_path)
    status_error = payload.get("_status_error", "")
    status_label = str(status_path)
    if status_error:
        status_label = f"{status_label} ({status_error})"
    header = [
        "SentinelTray - Status (tempo real)",
        f"Contador (s): {counter_seconds}",
        f"Arquivo de status: {status_label}",
        f"Última atualização: {last_update}",
        "",
    ]
    footer = [
        "",
        f"Monitores configurados: {monitor_count}",
        f"status_export_errors: {status_export_errors}",
        f"status_csv_errors: {status_csv_errors}",
        f"state_write_errors: {state_write_errors}",
    ]
    lines = header + status_text.splitlines() + _format_queue(payload) + footer
    return "\n".join(lines)


def _clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def clear_screen() -> None:
    _clear_screen()


def main() -> int:
    data_dir = get_user_data_dir()
    config_path = data_dir / "config.local.yaml"
    try:
        config = load_config_secure(str(config_path))
    except Exception as exc:
        print("Falha ao carregar configuração:")
        print(f"  {exc}")
        print(f"  Caminho: {config_path}")
        print("Verifique se o config.local.yaml (ou .enc) existe.")
        input("Pressione Enter para sair...")
        return 1

    status_path = Path(config.status_export_file)
    counter = 0
    try:
        while True:
            payload = _load_status_payload(status_path)
            _clear_screen()
            print(
                build_status_display(
                    config=config,
                    payload=payload,
                    counter_seconds=counter,
                    status_path=status_path,
                )
            )
            counter += 1
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
