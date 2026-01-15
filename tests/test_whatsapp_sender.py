import json

import requests
import pytest

from sentineltray.config import CloudApiConfig, WhatsappConfig
from sentineltray.whatsapp_sender import CloudApiWhatsappSender


def test_cloud_api_send_posts_message(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, headers: dict[str, str], data: str, timeout: int) -> "Response":
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["timeout"] = timeout

        class Response:
            def raise_for_status(self) -> None:
                return None

        return Response()

    monkeypatch.setattr(requests, "post", fake_post)

    config = WhatsappConfig(
        mode="cloud_api",
        chat_target="",
        user_data_dir="",
        timeout_seconds=30,
        dry_run=False,
        cloud_api=CloudApiConfig(
            access_token="token",
            phone_number_id="123456",
            to="5511999999999",
        ),
    )

    sender = CloudApiWhatsappSender(config=config)
    sender.send("hello")

    payload = json.loads(captured["data"])
    assert captured["url"] == "https://graph.facebook.com/v19.0/123456/messages"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert payload["text"]["body"] == "hello"
    assert captured["timeout"] == 30
