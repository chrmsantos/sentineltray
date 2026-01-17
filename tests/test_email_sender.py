from sentineltray.config import EmailConfig
from sentineltray.email_sender import SmtpEmailSender, build_sender


def test_build_sender_returns_smtp_sender() -> None:
    config = EmailConfig(
        smtp_host="smtp.local",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        from_address="alerts@example.com",
        to_addresses=["ops@example.com"],
        use_tls=True,
        timeout_seconds=30,
        subject="SentinelTray Notification",
        retry_attempts=0,
        retry_backoff_seconds=0,
        dry_run=True,
    )

    sender = build_sender(config)
    assert isinstance(sender, SmtpEmailSender)
