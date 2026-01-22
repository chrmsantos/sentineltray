from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_text as _atomic_write_text


@dataclass
class JsonWriter:
    path: Path

    def write(self, payload: dict[str, Any]) -> None:
        payload_json = json.dumps(payload, ensure_ascii=True, indent=2)
        atomic_write_text(self.path, payload_json, encoding="utf-8")


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    _atomic_write_text(path, content, encoding=encoding)
