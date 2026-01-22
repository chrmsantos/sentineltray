from __future__ import annotations

import pytest

from sentineltray.validation_utils import validate_email_address, validate_regex


def test_validate_regex_accepts_valid() -> None:
    validate_regex("pattern", r"^test\d+$")


def test_validate_regex_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_regex("pattern", r"[")


def test_validate_email_address_accepts_valid() -> None:
    validate_email_address("email", "user@example.com")


def test_validate_email_address_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_email_address("email", "invalid")
