import sentineltray.whatsapp_sender as whatsapp_sender
from sentineltray.config import WhatsAppConfig
from sentineltray.whatsapp_sender import build_message_template, WhatsAppSender


def test_build_message_template_replaces_tokens() -> None:
    result = build_message_template(
        "Alerta: {message} @ {window} {timestamp}",
        message="texto",
        window="APP",
    )
    assert "texto" in result
    assert "APP" in result
    assert "{timestamp}" not in result


def test_whatsapp_sender_requires_contact() -> None:
    config = WhatsAppConfig(enabled=True, contact_name="", message_template="msg")
    sender = WhatsAppSender(config=config)
    try:
        sender.send("hello")
    except ValueError as exc:
        assert "contact_name" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing contact")


def test_whatsapp_sender_sends_message(monkeypatch) -> None:
    config = WhatsAppConfig(enabled=True, contact_name="Ops", message_template="msg")
    sender = WhatsAppSender(config=config)

    calls: list[str] = []

    def fake_send_keys(value: str, *args, **kwargs) -> None:
        calls.append(value)

    class FakeWindow:
        def descendants(self):
            return []

    class FakeSpec:
        def wrapper_object(self):
            return FakeWindow()

    class FakeDesktop:
        def __init__(self, backend: str = "uia") -> None:
            return None

        def window(self, **_kwargs):
            return FakeSpec()

    monkeypatch.setattr(whatsapp_sender, "send_keys", fake_send_keys)
    monkeypatch.setattr(whatsapp_sender, "Desktop", FakeDesktop)
    sender._ensure_foreground = lambda _window: None
    sender._check_logged_in = lambda _window: None

    sender.send("hello")

    assert any("hello" in value for value in calls)
