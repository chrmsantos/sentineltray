from __future__ import annotations

import logging
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage

from .config import EmailConfig

LOGGER = logging.getLogger(__name__)


def _to_ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


class EmailSender:
    def send(self, message: str) -> None:
        raise NotImplementedError()


@dataclass
class SmtpEmailSender(EmailSender):
    config: EmailConfig

    def _is_auth_error(self, exc: smtplib.SMTPException) -> bool:
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return True
        if isinstance(exc, smtplib.SMTPResponseException):
            return exc.smtp_code in {534, 535}
        return False

    def send(self, message: str) -> None:
        if self.config.dry_run:
            LOGGER.info("Dry run enabled, skipping send", extra={"category": "send"})
            return

        if not self.config.smtp_host:
            raise ValueError("smtp_host is required")
        if not self.config.from_address:
            raise ValueError("from_address is required")
        if not self.config.to_addresses:
            raise ValueError("to_addresses is required")

        safe_message = _to_ascii(message)

        email = EmailMessage()
        email["From"] = self.config.from_address
        email["To"] = ", ".join(self.config.to_addresses)
        email["Subject"] = self.config.subject
        email.set_content(safe_message)

        attempts = max(0, self.config.retry_attempts)
        backoff = max(0, self.config.retry_backoff_seconds)

        for attempt in range(attempts + 1):
            try:
                with smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.config.timeout_seconds,
                ) as client:
                    if self.config.use_tls:
                        client.starttls()
                    if self.config.smtp_username or self.config.smtp_password:
                        client.login(self.config.smtp_username, self.config.smtp_password)
                    client.send_message(email)
                return
            except smtplib.SMTPException as exc:
                if self._is_auth_error(exc):
                    LOGGER.error(
                        "SMTP authentication failed (check app password)",
                        extra={"category": "send"},
                    )
                    raise
                if attempt >= attempts:
                    raise
                LOGGER.warning(
                    "SMTP failure, retrying: %s",
                    exc,
                    extra={"category": "send"},
                )
                if backoff:
                    time.sleep(backoff * (2**attempt))


def build_sender(config: EmailConfig) -> EmailSender:
    return SmtpEmailSender(config=config)
