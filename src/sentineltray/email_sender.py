from __future__ import annotations

import json
import logging
import smtplib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Callable

from .config import EmailConfig
from .email_queue_utils import (
    build_new_item,
    compute_next_attempt,
    compute_oldest_age_seconds,
    normalize_item,
    parse_timestamp,
    prune_items,
)
from .telemetry import atomic_write_text

LOGGER = logging.getLogger(__name__)


class EmailAuthError(RuntimeError):
    """Raised when SMTP authentication fails and sending should be disabled."""


class EmailQueued(RuntimeError):
    """Raised when a message is queued after a transient failure."""


def _build_subject(subject: str, category: str) -> str:
    if category == "Alert":
        return "SentinelTray Match Alert"
    if category == "Error":
        return "SentinelTray Error Alert"
    base = (subject or "").strip()
    if base:
        cleaned = base
        while cleaned.lower().startswith("sentineltray"):
            cleaned = cleaned[len("sentineltray") :].strip()
            cleaned = cleaned.lstrip("-–—:|/").strip()
            if not cleaned:
                break
        base = cleaned
    if base:
        return f"SentinelTray {base} - {category}"
    return f"SentinelTray {category}"


def _build_body(message: str) -> tuple[str, str]:
    text = (message or "").strip()
    category = "Alert"
    details = text
    if text.lower().startswith("error:"):
        category = "Error"
        details = text.split(":", 1)[1].strip() or "An error occurred."
    elif text.lower().startswith("info:"):
        category = "Info"
        details = text.split(":", 1)[1].strip() or "System update."

    if not details:
        details = "No additional details."

    if category == "Alert" and details == text:
        details = "The following text was found on screen:\n" + details

    body = (
        "SentinelTray\n\n"
        f"{category}:\n"
        f"{details}\n\n"
        "This is an automated message from SentinelTray."
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
        if category == "Info":
            LOGGER.info(
                "Info notification suppressed",
                extra={"category": "send"},
            )
            return

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
                    LOGGER.error(
                        "SMTP failure after %s attempts: %s",
                        attempts + 1,
                        exc,
                        extra={"category": "send"},
                    )
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
        now = self._now()
        for raw in data:
            if not isinstance(raw, dict):
                continue
            normalized = normalize_item(raw, now)
            if normalized:
                items.append(normalized)
        return items

    def _save_items(self, items: list[dict[str, object]]) -> None:
        payload = json.dumps(items, ensure_ascii=False, indent=2)
        atomic_write_text(self._path, payload, encoding="utf-8")

    def enqueue(self, message: str) -> None:
        items = self._load_items()
        items.append(build_new_item(message, self._now()))
        items = prune_items(
            items,
            now=self._now(),
            max_items=self._max_items,
            max_age_seconds=self._max_age_seconds,
            max_attempts=self._max_attempts,
        )
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
                parse_timestamp(next_attempt_raw)
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
                next_attempt_at = compute_next_attempt(
                    now,
                    attempts=attempts,
                    retry_base_seconds=self._retry_base_seconds,
                )
                item["attempts"] = attempts
                item["next_attempt_at"] = next_attempt_at.isoformat()
                remaining.append(item)

        remaining = prune_items(
            remaining,
            now=now,
            max_items=self._max_items,
            max_age_seconds=self._max_age_seconds,
            max_attempts=self._max_attempts,
        )
        self._save_items(remaining)
        oldest_age_seconds = compute_oldest_age_seconds(remaining, now)

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
        oldest_age_seconds = compute_oldest_age_seconds(items, now)
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
    queue_path: Path,
    queue_max_items: int = 500,
    queue_max_age_seconds: int = 86400,
    queue_max_attempts: int = 10,
    queue_retry_base_seconds: int = 30,
) -> EmailSender:
    base_sender = SmtpEmailSender(config=config)
    queue = DiskEmailQueue(
        queue_path,
        max_items=max(1, queue_max_items),
        max_age_seconds=max(0, queue_max_age_seconds),
        max_attempts=max(0, queue_max_attempts),
        retry_base_seconds=max(0, queue_retry_base_seconds),
    )
    return QueueingEmailSender(sender=base_sender, queue=queue)
