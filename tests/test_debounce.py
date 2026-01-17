from datetime import datetime, timedelta, timezone

from sentineltray.app import Notifier
from sentineltray.config import AppConfig, WhatsappConfig
from sentineltray.status import StatusStore


def test_debounce_skips_recent_messages() -> None:
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=300,
        debounce_seconds=600,
        max_history=10,
        state_file="state.json",
        log_file="logs/sentineltray.log",
        telemetry_file="logs/telemetry.json",
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

    now = datetime.now(timezone.utc)
    notifier._last_sent = {
        "recent": now,
        "old": now - timedelta(seconds=700),
    }

    class FakeDetector:
        def find_matches(self, _: str) -> list[str]:
            return ["recent", "old"]

    class FakeSender:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, message: str) -> None:
            self.sent.append(message)

    notifier._detector = FakeDetector()
    sender = FakeSender()
    notifier._sender = sender

    notifier.scan_once()

    assert sender.sent == ["old"]
