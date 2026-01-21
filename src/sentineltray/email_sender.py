from __future__ import annotations

import json
import logging
import smtplib
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Callable

from .config import EmailConfig
from .telemetry import atomic_write_text

LOGGER = logging.getLogger(__name__)


class EmailAuthError(RuntimeError):
    """Raised when SMTP authentication fails and sending should be disabled."""


class EmailQueued(RuntimeError):
    """Raised when a message is queued after a transient failure."""


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


@dataclass
class QueueStats:
    queued: int
    sent: int
    failed: int
    deferred: int
    oldest_age_seconds: int


class DiskEmailQueue:
    def __init__(
        self,
        path: Path,
        *,
        max_items: int,
        max_age_seconds: int,
        max_attempts: int,
        retry_base_seconds: int,
    ) -> None:
        self._path = path
        self._max_items = max_items
        self._max_age_seconds = max_age_seconds
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_timestamp(self, value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _load_items(self) -> list[dict[str, object]]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        items: list[dict[str, object]] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            message = raw.get("message")
            if not isinstance(message, str) or not message.strip():
                continue
            created_at = raw.get("created_at")
            if not isinstance(created_at, str):
                created_at = self._now().isoformat()
            attempts = int(raw.get("attempts", 0))
            next_attempt_at = raw.get("next_attempt_at")
            if not isinstance(next_attempt_at, str):
                next_attempt_at = self._now().isoformat()
            items.append(
                {
                    "message": message,
                    "created_at": created_at,
                    "attempts": attempts,
                    "next_attempt_at": next_attempt_at,
                }
            )
        return items

    def _prune_items(self, items: list[dict[str, object]]) -> list[dict[str, object]]:
        now = self._now()
        pruned: list[dict[str, object]] = []
        for item in items:
            created_raw = item.get("created_at")
            created_at = (
                self._parse_timestamp(created_raw)
                if isinstance(created_raw, str)
                else None
            )
            attempts = int(item.get("attempts", 0))
            if self._max_attempts and attempts > self._max_attempts:
                continue
            if self._max_age_seconds and created_at:
                if (now - created_at).total_seconds() > self._max_age_seconds:
                    continue
            pruned.append(item)

        if self._max_items and len(pruned) > self._max_items:
            pruned = pruned[-self._max_items :]
        return pruned

    def _save_items(self, items: list[dict[str, object]]) -> None:
        payload = json.dumps(items, ensure_ascii=False, indent=2)
        atomic_write_text(self._path, payload, encoding="utf-8")

    def enqueue(self, message: str) -> None:
        items = self._load_items()
        items.append(
            {
                "message": message,
                "created_at": self._now().isoformat(),
                "attempts": 0,
                "next_attempt_at": self._now().isoformat(),
            }
        )
        items = self._prune_items(items)
        self._save_items(items)

    def drain(self, send_func: Callable[[str], None]) -> QueueStats:
        items = self._load_items()
        if not items:
            return QueueStats(queued=0, sent=0, failed=0, deferred=0, oldest_age_seconds=0)

        now = self._now()
        remaining: list[dict[str, object]] = []
        sent = 0
        failed = 0
        deferred = 0

        for item in items:
            message = str(item.get("message", ""))
            next_attempt_raw = item.get("next_attempt_at")
            next_attempt_at = (
                self._parse_timestamp(next_attempt_raw)
                if isinstance(next_attempt_raw, str)
                else None
            )
            if next_attempt_at and next_attempt_at > now:
                deferred += 1
                remaining.append(item)
                continue
            try:
                send_func(message)
                sent += 1
                continue
            except EmailAuthError:
                raise
            except Exception:
                failed += 1
                attempts = int(item.get("attempts", 0)) + 1
                delay = 0
                if self._retry_base_seconds:
                    delay = self._retry_base_seconds * (2 ** max(0, attempts - 1))
                next_attempt_at = now + timedelta(seconds=delay)
                item["attempts"] = attempts
                item["next_attempt_at"] = next_attempt_at.isoformat()
                remaining.append(item)

        remaining = self._prune_items(remaining)
        self._save_items(remaining)

        oldest_age_seconds = 0
        if remaining:
            created_times = [
                self._parse_timestamp(item.get("created_at"))
                for item in remaining
            ]
            created_times = [value for value in created_times if value]
            if created_times:
                oldest = min(created_times)
                oldest_age_seconds = int((now - oldest).total_seconds())

        return QueueStats(
            queued=len(remaining),
            sent=sent,
            failed=failed,
            deferred=deferred,
            oldest_age_seconds=oldest_age_seconds,
        )

    def get_stats(self) -> QueueStats:
        items = self._load_items()
        if not items:
            return QueueStats(queued=0, sent=0, failed=0, deferred=0, oldest_age_seconds=0)
        now = self._now()
        created_times = [
            self._parse_timestamp(item.get("created_at")) for item in items
        ]
        created_times = [value for value in created_times if value]
        oldest_age_seconds = 0
        if created_times:
            oldest = min(created_times)
            oldest_age_seconds = int((now - oldest).total_seconds())
        return QueueStats(
            queued=len(items),
            sent=0,
            failed=0,
            deferred=0,
            oldest_age_seconds=oldest_age_seconds,
        )


@dataclass
class QueueingEmailSender(EmailSender):
    sender: SmtpEmailSender
    queue: DiskEmailQueue

    def send(self, message: str) -> None:
        try:
            self.drain()
        except EmailAuthError:
            raise
        except Exception as exc:
            LOGGER.warning("Failed to drain email queue: %s", exc, extra={"category": "send"})

        try:
            self.sender.send(message)
        except EmailAuthError:
            raise
        except Exception as exc:
            LOGGER.warning(
                "Transient send failure; queued for retry: %s",
                exc,
                extra={"category": "send"},
            )
            self.queue.enqueue(message)
            raise EmailQueued("Message queued for retry") from exc

    def drain(self) -> QueueStats:
        return self.queue.drain(self.sender.send)

    def get_queue_stats(self) -> QueueStats:
        return self.queue.get_stats()


def build_sender(
    config: EmailConfig,
    *,
    queue_path: Path | None = None,
    queue_max_items: int = 0,
    queue_max_age_seconds: int = 0,
    queue_max_attempts: int = 0,
    queue_retry_base_seconds: int = 0,
) -> EmailSender:
    base_sender = SmtpEmailSender(config=config)
    if queue_path is None or queue_max_items <= 0:
        return base_sender
    queue = DiskEmailQueue(
        queue_path,
        max_items=queue_max_items,
        max_age_seconds=queue_max_age_seconds,
        max_attempts=queue_max_attempts,
        retry_base_seconds=queue_retry_base_seconds,
    )
    return QueueingEmailSender(sender=base_sender, queue=queue)
