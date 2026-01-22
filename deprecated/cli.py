"""Deprecated CLI module. GUI is the primary interface."""

from __future__ import annotations

from typing import Iterable

from .config import AppConfig


def run_cli(
    config: AppConfig,
    args: Iterable[str] | None = None,
    *,
    exit_event: object | None = None,
) -> int:
    raise RuntimeError("CLI removida; use a interface GUI (tray_app.run_tray)")
