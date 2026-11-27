import logging
import smtplib

from app.core import email as email_module
from app.core.config import settings
from app.core.email import ConsoleEmailBackend, Email, SmtpEmailBackend, get_email_backend

MSG = Email(
    to="bob@t.dev",
    subject="Chủ đề",
    body="Nội dung tiếng Việt",
    task_id=10,
    recipient_user_id=2,
)


async def test_console_backend_only_logs_without_pii(caplog):
    caplog.set_level(logging.INFO, logger="taskhub.email")
    await ConsoleEmailBackend().send(MSG)
    assert any("user_id=2" in m and "task_id=10" in m and "Chủ đề" in m for m in caplog.messages)
    assert all("bob@t.dev" not in m for m in caplog.messages)  # không ghi email (PII) vào log


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls, self.sent, self.closed = [], None, False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.sent = message


async def test_smtp_backend_builds_and_sends_message(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    backend = SmtpEmailBackend("smtp.x.com", 2525, "user", "pw", "TaskHub <a@b.c>", True)
    await backend.send(MSG)
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.x.com", 2525) and smtp.timeout > 0
    assert smtp.calls == ["starttls", ("login", "user", "pw")]  # TLS trước, rồi mới đăng nhập
    assert smtp.sent is not None
    assert smtp.sent["To"] == "bob@t.dev" and smtp.sent["From"] == "TaskHub <a@b.c>"
    assert smtp.sent["Subject"] == "Chủ đề"
    assert "Nội dung tiếng Việt" in smtp.sent.get_content()
    assert smtp.closed  # luôn đóng kết nối


async def test_smtp_backend_skips_tls_and_login_when_not_configured(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    await SmtpEmailBackend("h", 25, "", "", "a@b.c", False).send(MSG)
    assert FakeSMTP.instances[0].calls == []


def test_factory_picks_backend_from_settings(monkeypatch):
    get_email_backend.cache_clear()
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")
    assert isinstance(get_email_backend(), ConsoleEmailBackend)
    get_email_backend.cache_clear()
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    backend = get_email_backend()
    assert isinstance(backend, email_module.SmtpEmailBackend) and backend.host == "smtp.example.com"
    get_email_backend.cache_clear()
