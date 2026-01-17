from sentineltray.app import Notifier
from sentineltray.config import AppConfig, WhatsappConfig
from sentineltray.status import StatusStore


def test_send_startup_test_message_sends_and_updates_status() -> None:
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        max_history=10,
        state_file="state.json",
        log_file="logs/sentineltray.log",
        whatsapp=WhatsappConfig(
            mode="web",
            chat_target="Operator",
            user_data_dir="session",
            timeout_seconds=10,
            dry_run=True,
        ),
    )
    status = StatusStore()
    notifier = Notifier(config=config, status=status)

    sent: list[str] = []

    class FakeSender:
        def send(self, message: str) -> None:
            sent.append(message)

    notifier._sender = FakeSender()

    notifier._send_startup_test()

    snapshot = status.snapshot()
    assert sent == ["info: startup test message"]
    assert snapshot.last_send
