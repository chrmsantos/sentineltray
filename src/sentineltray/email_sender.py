from __future__ import annotations

import logging
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage

from .config import EmailConfig

LOGGER = logging.getLogger(__name__)


class EmailAuthError(RuntimeError):
    """Raised when SMTP authentication fails and sending should be disabled."""


def _build_subject(_subject: str, category: str) -> str:
    return f"SentinelTray {category}"


def _build_body(message: str) -> tuple[str, str]:
    text = (message or "").strip()
    category = "Alerta"
    details = text
    if text.lower().startswith("error:"):
        category = "Erro"
        details = text.split(":", 1)[1].strip() or "Ocorreu um erro."
    elif text.lower().startswith("info:"):
        category = "Informação"
        details = text.split(":", 1)[1].strip() or "Atualização do sistema."

    if not details:
        details = "Sem detalhes adicionais."

    if category == "Alerta" and details == text:
        details = "Encontrado o seguinte texto na tela:\n" + details

    body = (
        "SentinelTray\n\n"
        f"{category}:\n"
        f"{details}\n\n"
        "Esta é uma mensagem automática do SentinelTray."
    )
    return category, body


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

        category, body = _build_body(message)

        email = EmailMessage()
        email["From"] = self.config.from_address
        email["To"] = ", ".join(self.config.to_addresses)
        email["Subject"] = _build_subject(self.config.subject, category)
        email.set_content(body)

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
                    raise EmailAuthError("SMTP authentication failed") from exc
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
