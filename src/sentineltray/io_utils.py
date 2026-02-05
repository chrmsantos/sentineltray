from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    temp_path = path.with_name(temp_name)
    try:
        with temp_path.open("w", encoding=encoding, newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def read_text_safe(
    path: Path,
    *,
    encoding: str = "utf-8",
    default: str = "",
    context: str | None = None,
) -> str:
    try:
        return path.read_text(encoding=encoding)
    except FileNotFoundError:
        return default
    except Exception as exc:
        label = context or str(path)
        LOGGER.warning(
            "Failed to read %s: %s",
            label,
            exc,
            extra={"category": "io"},
        )
        return default


def read_json_safe(
    path: Path,
    *,
    default: Any,
    context: str | None = None,
) -> Any:
    text = read_text_safe(path, default="", context=context)
    if not text.strip():
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        label = context or str(path)
        LOGGER.warning(
            "Failed to parse JSON from %s: %s",
            label,
            exc,
            extra={"category": "io"},
        )
        return default
