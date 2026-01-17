from __future__ import annotations

from dataclasses import dataclass, replace
import os
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
    debounce_seconds: int
    max_history: int
    state_file: str
    log_file: str
    telemetry_file: str
    show_error_window: bool
    watchdog_timeout_seconds: int
    watchdog_restart: bool
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

    config = AppConfig(
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
        debounce_seconds=int(_get_required(data, "debounce_seconds")),
        max_history=int(_get_required(data, "max_history")),
        state_file=str(_get_required(data, "state_file")),
        log_file=str(_get_required(data, "log_file")),
        telemetry_file=str(_get_required(data, "telemetry_file")),
        show_error_window=bool(_get_required(data, "show_error_window")),
        watchdog_timeout_seconds=int(
            _get_required(data, "watchdog_timeout_seconds")
        ),
        watchdog_restart=bool(_get_required(data, "watchdog_restart")),
        whatsapp=whatsapp,
    )
    config = _apply_sensitive_path_policy(config)
    _validate_config(config)
    return config


def _resolve_sensitive_path(base: Path, value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return str(base / candidate)
    try:
        if candidate.resolve().is_relative_to(base.resolve()):
            return str(candidate)
    except OSError:
        pass
    return str(base / candidate.name)


def _apply_sensitive_path_policy(config: AppConfig) -> AppConfig:
    user_root = os.environ.get("USERPROFILE")
    if not user_root:
        raise ValueError("USERPROFILE is required for sensitive data storage")
    base = Path(user_root) / "sentineltray"

    return replace(
        config,
        state_file=_resolve_sensitive_path(base, config.state_file),
        log_file=_resolve_sensitive_path(base, config.log_file),
        telemetry_file=_resolve_sensitive_path(base, config.telemetry_file),
        whatsapp=replace(
            config.whatsapp,
            user_data_dir=_resolve_sensitive_path(base, config.whatsapp.user_data_dir),
        ),
    )


def _validate_config(config: AppConfig) -> None:
    if config.poll_interval_seconds < 1:
        raise ValueError("poll_interval_seconds must be >= 1")
    if config.healthcheck_interval_seconds < 1:
        raise ValueError("healthcheck_interval_seconds must be >= 1")
    if config.error_backoff_base_seconds < 1:
        raise ValueError("error_backoff_base_seconds must be >= 1")
    if config.error_backoff_max_seconds < config.error_backoff_base_seconds:
        raise ValueError("error_backoff_max_seconds must be >= error_backoff_base_seconds")
    if config.debounce_seconds < 0:
        raise ValueError("debounce_seconds must be >= 0")
    if config.max_history < 1:
        raise ValueError("max_history must be >= 1")
    if not config.state_file:
        raise ValueError("state_file is required")
    if not config.log_file:
        raise ValueError("log_file is required")
    if not config.telemetry_file:
        raise ValueError("telemetry_file is required")
    if config.whatsapp.timeout_seconds < 1:
        raise ValueError("whatsapp.timeout_seconds must be >= 1")
    if config.watchdog_timeout_seconds < 1:
        raise ValueError("watchdog_timeout_seconds must be >= 1")


def load_config(path: str) -> AppConfig:
    data = _load_yaml(Path(path))
    return _build_config(data)


def load_config_with_override(base_path: str, override_path: str) -> AppConfig:
    base = _load_yaml(Path(base_path))
    override = _load_yaml(Path(override_path))
    merged = _merge_dicts(base, override)
    return _build_config(merged)
