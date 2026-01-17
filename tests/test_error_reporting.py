from sentineltray.app import Notifier
from sentineltray.config import AppConfig, WhatsappConfig
from sentineltray.status import StatusStore


def test_handle_error_sets_status_and_sends() -> None:
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

    sent: dict[str, str] = {}

    class FakeSender:
        def send(self, message: str) -> None:
            sent["message"] = message

    notifier._sender = FakeSender()

    notifier._handle_error("error: target window not found")

    snapshot = status.snapshot()
    assert snapshot.last_error == "error: target window not found"
    assert sent["message"] == "error: target window not found"
    assert snapshot.last_send
