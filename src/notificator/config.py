from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CloudApiConfig:
    access_token: str
    phone_number_id: str
    to: str


@dataclass(frozen=True)
class WhatsappConfig:
    mode: str
    chat_target: str
    user_data_dir: str
    timeout_seconds: int
    dry_run: bool
    cloud_api: CloudApiConfig


@dataclass(frozen=True)
class AppConfig:
    window_title_regex: str
    phrase_regex: str
    poll_interval_seconds: int
    max_history: int
    state_file: str
    log_file: str
    whatsapp: WhatsappConfig


def _get_required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required config key: {key}")
    return data[key]


def load_config(path: str) -> AppConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    whatsapp_data = _get_required(data, "whatsapp")
    cloud_data = _get_required(whatsapp_data, "cloud_api")

    cloud_api = CloudApiConfig(
        access_token=str(_get_required(cloud_data, "access_token")),
        phone_number_id=str(_get_required(cloud_data, "phone_number_id")),
        to=str(_get_required(cloud_data, "to")),
    )

    whatsapp = WhatsappConfig(
        mode=str(_get_required(whatsapp_data, "mode")),
        chat_target=str(_get_required(whatsapp_data, "chat_target")),
        user_data_dir=str(_get_required(whatsapp_data, "user_data_dir")),
        timeout_seconds=int(_get_required(whatsapp_data, "timeout_seconds")),
        dry_run=bool(_get_required(whatsapp_data, "dry_run")),
        cloud_api=cloud_api,
    )

    return AppConfig(
        window_title_regex=str(_get_required(data, "window_title_regex")),
        phrase_regex=str(_get_required(data, "phrase_regex")),
        poll_interval_seconds=int(_get_required(data, "poll_interval_seconds")),
        max_history=int(_get_required(data, "max_history")),
        state_file=str(_get_required(data, "state_file")),
        log_file=str(_get_required(data, "log_file")),
        whatsapp=whatsapp,
    )
