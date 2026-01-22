from __future__ import annotations

import re


def validate_regex(label: str, value: str) -> None:
    try:
        re.compile(value)
    except re.error as exc:
        raise ValueError(f"{label} invalid regex: {exc}") from exc


def validate_email_address(label: str, value: str) -> None:
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError(f"{label} must be a valid email address")
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError(f"{label} must be a valid email address")
