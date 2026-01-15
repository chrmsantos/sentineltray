import pytest

from sentineltray.config import WhatsappConfig
from sentineltray.whatsapp_sender import WebWhatsappSender, build_sender


def test_build_sender_returns_web_sender() -> None:
    config = WhatsappConfig(
        mode="web",
        chat_target="Operator",
        user_data_dir="session",
        timeout_seconds=30,
        dry_run=True,
    )

    sender = build_sender(config)
    assert isinstance(sender, WebWhatsappSender)


def test_build_sender_rejects_cloud_api_mode() -> None:
    config = WhatsappConfig(
        mode="cloud_api",
        chat_target="Operator",
        user_data_dir="session",
        timeout_seconds=30,
        dry_run=True,
    )

    with pytest.raises(ValueError, match="web mode"):
        build_sender(config)
