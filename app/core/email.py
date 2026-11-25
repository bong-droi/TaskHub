"""Gửi email: console (ghi log, dùng cho dev/test) hoặc SMTP thật."""

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("taskhub.email")
SMTP_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class EmailBackend(Protocol):
    async def send(self, message: Email) -> None: ...


class ConsoleEmailBackend:
    """Không gửi thật, chỉ ghi log. Mặc định cho dev và test."""

    async def send(self, message: Email) -> None:
        logger.info("[EMAIL console] to=%s subject=%s", message.to, message.subject)


class SmtpEmailBackend:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        starttls: bool,
    ) -> None:
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.sender, self.starttls = sender, starttls

    def _send_blocking(self, message: Email) -> None:
        mime = MimeMessage()
        mime["From"], mime["To"], mime["Subject"] = self.sender, message.to, message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            if self.starttls:
                smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(mime)

    async def send(self, message: Email) -> None:
        # smtplib là blocking: chạy trong thread để không chặn event loop
        await asyncio.to_thread(self._send_blocking, message)


@lru_cache
def get_email_backend() -> EmailBackend:
    if settings.EMAIL_BACKEND == "smtp":
        return SmtpEmailBackend(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD.get_secret_value(),
            settings.EMAIL_FROM,
            settings.SMTP_STARTTLS,
        )
    return ConsoleEmailBackend()
