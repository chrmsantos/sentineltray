from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WhatsappConfig:
    mode: str
    chat_target: str
    user_data_dir: str
    timeout_seconds: int
    dry_run: bool


@dataclass(frozen=True)
class AppConfig:
    window_title_regex: str
    phrase_regex: str
    poll_interval_seconds: int
    healthcheck_interval_seconds: int
    error_backoff_base_seconds: int
    error_backoff_max_seconds: int
    max_history: int
    state_file: str
    log_file: str
    whatsapp: WhatsappConfig


def _get_required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required config key: {key}")
    return data[key]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
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


def _build_config(data: dict[str, Any]) -> AppConfig:
    whatsapp_data = _get_required(data, "whatsapp")
    whatsapp = WhatsappConfig(
        mode=str(_get_required(whatsapp_data, "mode")),
        chat_target=str(_get_required(whatsapp_data, "chat_target")),
        user_data_dir=str(_get_required(whatsapp_data, "user_data_dir")),
        timeout_seconds=int(_get_required(whatsapp_data, "timeout_seconds")),
        dry_run=bool(_get_required(whatsapp_data, "dry_run")),
    )

    return AppConfig(
        window_title_regex=str(_get_required(data, "window_title_regex")),
        phrase_regex=str(_get_required(data, "phrase_regex")),
        poll_interval_seconds=int(_get_required(data, "poll_interval_seconds")),
        healthcheck_interval_seconds=int(
            _get_required(data, "healthcheck_interval_seconds")
        ),
        error_backoff_base_seconds=int(
            _get_required(data, "error_backoff_base_seconds")
        ),
        error_backoff_max_seconds=int(
            _get_required(data, "error_backoff_max_seconds")
        ),
        max_history=int(_get_required(data, "max_history")),
        state_file=str(_get_required(data, "state_file")),
        log_file=str(_get_required(data, "log_file")),
        whatsapp=whatsapp,
    )


def load_config(path: str) -> AppConfig:
    data = _load_yaml(Path(path))
    return _build_config(data)


def load_config_with_override(base_path: str, override_path: str) -> AppConfig:
    base = _load_yaml(Path(base_path))
    override = _load_yaml(Path(override_path))
    merged = _merge_dicts(base, override)
    return _build_config(merged)
