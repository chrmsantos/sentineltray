from __future__ import annotations

from dataclasses import dataclass, replace
import logging
import os
from pathlib import Path
from typing import Any

import yaml

MAX_LOG_FILES = 5


def _get_user_root() -> Path:
    user_root = os.environ.get("USERPROFILE")
    if not user_root:
        raise ValueError("USERPROFILE is required for SentinelTray paths")
    return Path(user_root)


def get_user_data_dir() -> Path:
    return (
        _get_user_root()
        / "AppData"
        / "Local"
        / "AxonZ"
        / "SentinelTray"
        / "UserData"
    )


def get_user_log_dir() -> Path:
    return get_user_data_dir() / "logs"


def get_project_root() -> Path:
    return (
        _get_user_root()
        / "AppData"
        / "Local"
        / "AxonZ"
        / "SentinelTray"
        / "SystemData"
        / "sentineltray"
    )


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_address: str
    to_addresses: list[str]
    use_tls: bool
    timeout_seconds: int
    subject: str
    retry_attempts: int
    retry_backoff_seconds: int
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
    log_level: str
    log_console_level: str
    log_console_enabled: bool
    log_max_bytes: int
    log_backup_count: int
    log_run_files_keep: int
    telemetry_file: str
    status_export_file: str
    status_export_csv: str
    status_refresh_seconds: int
    allow_window_restore: bool
    start_minimized: bool
    log_only_mode: bool
    config_checksum_file: str
    min_free_disk_mb: int
    show_error_window: bool
    watchdog_timeout_seconds: int
    watchdog_restart: bool
    send_repeated_matches: bool
    email: EmailConfig
    auto_start: bool = True


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
    email_data = _get_required(data, "email")
    to_raw = _get_required(email_data, "to_addresses")
    if isinstance(to_raw, str):
        to_addresses = [item.strip() for item in to_raw.split(",") if item.strip()]
    elif isinstance(to_raw, list):
        to_addresses = [str(item).strip() for item in to_raw if str(item).strip()]
    else:
        raise ValueError("email.to_addresses must be a list or comma-separated string")

    email = EmailConfig(
        smtp_host=str(_get_required(email_data, "smtp_host")),
        smtp_port=int(_get_required(email_data, "smtp_port")),
        smtp_username=str(_get_required(email_data, "smtp_username")),
        smtp_password=str(_get_required(email_data, "smtp_password")),
        from_address=str(_get_required(email_data, "from_address")),
        to_addresses=to_addresses,
        use_tls=bool(_get_required(email_data, "use_tls")),
        timeout_seconds=int(_get_required(email_data, "timeout_seconds")),
        subject=str(_get_required(email_data, "subject")),
        retry_attempts=int(_get_required(email_data, "retry_attempts")),
        retry_backoff_seconds=int(_get_required(email_data, "retry_backoff_seconds")),
        dry_run=bool(_get_required(email_data, "dry_run")),
    )

    log_backup_count = int(_get_required(data, "log_backup_count"))
    log_run_files_keep = int(_get_required(data, "log_run_files_keep"))
    if log_backup_count > MAX_LOG_FILES:
        logging.getLogger(__name__).warning(
            "log_backup_count capped at %s (requested %s)",
            MAX_LOG_FILES,
            log_backup_count,
        )
        log_backup_count = MAX_LOG_FILES
    if log_run_files_keep > MAX_LOG_FILES:
        logging.getLogger(__name__).warning(
            "log_run_files_keep capped at %s (requested %s)",
            MAX_LOG_FILES,
            log_run_files_keep,
        )
        log_run_files_keep = MAX_LOG_FILES

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
        log_level=str(_get_required(data, "log_level")),
        log_console_level=str(_get_required(data, "log_console_level")),
        log_console_enabled=bool(_get_required(data, "log_console_enabled")),
        log_max_bytes=int(_get_required(data, "log_max_bytes")),
        log_backup_count=log_backup_count,
        log_run_files_keep=log_run_files_keep,
        telemetry_file=str(_get_required(data, "telemetry_file")),
        status_export_file=str(_get_required(data, "status_export_file")),
        status_export_csv=str(_get_required(data, "status_export_csv")),
        status_refresh_seconds=int(_get_required(data, "status_refresh_seconds")),
        allow_window_restore=bool(_get_required(data, "allow_window_restore")),
        start_minimized=bool(_get_required(data, "start_minimized")),
        log_only_mode=bool(_get_required(data, "log_only_mode")),
        config_checksum_file=str(_get_required(data, "config_checksum_file")),
        min_free_disk_mb=int(_get_required(data, "min_free_disk_mb")),
        show_error_window=bool(_get_required(data, "show_error_window")),
        watchdog_timeout_seconds=int(
            _get_required(data, "watchdog_timeout_seconds")
        ),
        watchdog_restart=bool(_get_required(data, "watchdog_restart")),
        send_repeated_matches=bool(data.get("send_repeated_matches", True)),
        email=email,
        auto_start=bool(data.get("auto_start", True)),
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


def _resolve_log_path(base: Path, log_root: Path, value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return str(base / candidate)
    try:
        if candidate.resolve().is_relative_to(log_root.resolve()):
            return str(candidate)
    except OSError:
        pass
    return str(log_root / candidate.name)


def _apply_sensitive_path_policy(config: AppConfig) -> AppConfig:
    base = get_user_data_dir()
    log_root = get_user_log_dir()

    return replace(
        config,
        state_file=_resolve_sensitive_path(base, config.state_file),
        log_file=_resolve_log_path(base, log_root, config.log_file),
        telemetry_file=_resolve_log_path(base, log_root, config.telemetry_file),
        status_export_file=_resolve_log_path(base, log_root, config.status_export_file),
        status_export_csv=_resolve_log_path(base, log_root, config.status_export_csv),
        config_checksum_file=_resolve_log_path(base, log_root, config.config_checksum_file),
    )


def _validate_config(config: AppConfig) -> None:
    log_root = get_user_log_dir().resolve()

    def _must_be_under_logs(path_value: str, label: str) -> None:
        try:
            resolved = Path(path_value).resolve()
            if not resolved.is_relative_to(log_root):
                raise ValueError(f"{label} must be under {log_root}")
        except OSError as exc:
            raise ValueError(f"{label} must be under {log_root}") from exc

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
    if config.log_max_bytes < 1024:
        raise ValueError("log_max_bytes must be >= 1024")
    if config.log_backup_count < 0:
        raise ValueError("log_backup_count must be >= 0")
    if config.log_run_files_keep < 1:
        raise ValueError("log_run_files_keep must be >= 1")
    if str(config.log_level).upper() not in logging._nameToLevel:
        raise ValueError("log_level must be a valid logging level")
    if str(config.log_console_level).upper() not in logging._nameToLevel:
        raise ValueError("log_console_level must be a valid logging level")
    if not config.telemetry_file:
        raise ValueError("telemetry_file is required")
    if not config.status_export_file:
        raise ValueError("status_export_file is required")
    if not config.status_export_csv:
        raise ValueError("status_export_csv is required")
    _must_be_under_logs(config.log_file, "log_file")
    _must_be_under_logs(config.telemetry_file, "telemetry_file")
    _must_be_under_logs(config.status_export_file, "status_export_file")
    _must_be_under_logs(config.status_export_csv, "status_export_csv")
    _must_be_under_logs(config.config_checksum_file, "config_checksum_file")
    if config.status_refresh_seconds < 1:
        raise ValueError("status_refresh_seconds must be >= 1")
    if config.min_free_disk_mb < 1:
        raise ValueError("min_free_disk_mb must be >= 1")
    if config.email.timeout_seconds < 1:
        raise ValueError("email.timeout_seconds must be >= 1")
    if config.email.smtp_port < 1:
        raise ValueError("email.smtp_port must be >= 1")
    if config.email.retry_attempts < 0:
        raise ValueError("email.retry_attempts must be >= 0")
    if config.email.retry_backoff_seconds < 0:
        raise ValueError("email.retry_backoff_seconds must be >= 0")
    if not config.email.dry_run:
        if not config.email.smtp_host:
            raise ValueError("email.smtp_host is required")
        if not config.email.from_address:
            raise ValueError("email.from_address is required")
        if not config.email.to_addresses:
            raise ValueError("email.to_addresses is required")
    if config.window_title_regex:
        _validate_regex("window_title_regex", config.window_title_regex)
    if config.phrase_regex:
        _validate_regex("phrase_regex", config.phrase_regex)
    if config.watchdog_timeout_seconds < 1:
        raise ValueError("watchdog_timeout_seconds must be >= 1")


def _validate_regex(label: str, value: str) -> None:
    import re

    try:
        re.compile(value)
    except re.error as exc:
        raise ValueError(f"{label} invalid regex: {exc}") from exc


def load_config(path: str) -> AppConfig:
    data = _load_yaml(Path(path))
    return _build_config(data)


def load_config_with_override(base_path: str, override_path: str) -> AppConfig:
    base = _load_yaml(Path(base_path))
    override = _load_yaml(Path(override_path))
    merged = _merge_dicts(base, override)
    return _build_config(merged)
