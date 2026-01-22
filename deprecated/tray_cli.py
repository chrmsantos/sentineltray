"""Deprecated tray CLI shim. GUI is the primary interface."""

from __future__ import annotations

from .config import AppConfig
from .tray_app import run_tray


def run_tray_cli(config: AppConfig) -> int:
    run_tray(config)
    return 0