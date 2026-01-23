from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import get_user_data_dir


COMMAND_QUEUE_NAME = "cli_commands.jsonl"


@dataclass(frozen=True)
class CliCommand:
    command: str
    payload: dict[str, object]
    timestamp: float


def get_command_queue_path() -> Path:
    return get_user_data_dir() / COMMAND_QUEUE_NAME


def write_command(command: str, payload: dict[str, object] | None = None) -> None:
    entry = CliCommand(command=command, payload=payload or {}, timestamp=time.time())
    path = get_command_queue_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")


def drain_commands() -> list[CliCommand]:
    path = get_command_queue_path()
    if not path.exists():
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    try:
        path.write_text("", encoding="utf-8")
    except Exception:
        return []

    commands: list[CliCommand] = []
    for line in raw_lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        command = str(data.get("command", "")).strip()
        if not command:
            continue
        payload = data.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        timestamp = data.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            timestamp = time.time()
        commands.append(CliCommand(command=command, payload=payload, timestamp=float(timestamp)))
    return commands


def format_commands(commands: Iterable[CliCommand]) -> str:
    return ", ".join(command.command for command in commands)
