from __future__ import annotations

import smtplib
from email.message import EmailMessage

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import email as email_service


def test_send_email_rejects_when_smtp_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", False)

    with pytest.raises(HTTPException) as exc:
        email_service.send_email(
            to_email="user@example.com",
            subject="Test",
            text_body="Body",
        )

    assert exc.value.status_code == 503
    assert "not enabled" in exc.value.detail


def test_send_email_rejects_incomplete_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", True)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_from_email", "from@example.com")

    with pytest.raises(HTTPException) as exc:
        email_service.send_email(
            to_email="user@example.com",
            subject="Test",
            text_body="Body",
        )

    assert exc.value.status_code == 503
    assert "incomplete" in exc.value.detail


def test_send_email_uses_ssl_and_from_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", True)
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_from_email", "from@example.com")
    monkeypatch.setattr(settings, "smtp_from_name", "GAIA")
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    monkeypatch.setattr(settings, "smtp_use_tls", False)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)

    sent: list[EmailMessage] = []

    class FakeSMTPSSL:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            assert username == "user"
            assert password == "pass"

        def send_message(self, message: EmailMessage) -> None:
            sent.append(message)

    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTPSSL)

    email_service.send_email(
        to_email="user@example.com",
        subject="Subject",
        text_body="Plain",
        html_body="<p>HTML</p>",
    )

    assert len(sent) == 1
    assert sent[0]["From"] == "GAIA <from@example.com>"
    assert sent[0]["To"] == "user@example.com"
    assert sent[0]["Subject"] == "Subject"


def test_send_email_uses_tls_when_ssl_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", True)
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_from_email", "from@example.com")
    monkeypatch.setattr(settings, "smtp_from_name", "")
    monkeypatch.setattr(settings, "smtp_use_ssl", False)
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)

    tls_started = {"value": False}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def starttls(self) -> None:
            tls_started["value"] = True

        def login(self, username: str, password: str) -> None:
            pass

        def send_message(self, message: EmailMessage) -> None:
            assert message["From"] == "from@example.com"

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    email_service.send_email(
        to_email="user@example.com",
        subject="Subject",
        text_body="Plain",
    )

    assert tls_started["value"] is True


def test_send_email_maps_smtp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", True)
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_from_email", "from@example.com")
    monkeypatch.setattr(settings, "smtp_from_name", "")
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    monkeypatch.setattr(settings, "smtp_use_tls", False)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)

    class AuthErrorSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

        def send_message(self, message: EmailMessage) -> None:
            pass

    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", AuthErrorSMTP)

    with pytest.raises(HTTPException) as auth_exc:
        email_service.send_email(
            to_email="user@example.com",
            subject="Subject",
            text_body="Plain",
        )
    assert auth_exc.value.status_code == 502
    assert "authentication failed" in auth_exc.value.detail.lower()

    class GenericErrorSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            pass

        def send_message(self, message: EmailMessage) -> None:
            raise smtplib.SMTPException("delivery failed")

    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", GenericErrorSMTP)

    with pytest.raises(HTTPException) as generic_exc:
        email_service.send_email(
            to_email="user@example.com",
            subject="Subject",
            text_body="Plain",
        )
    assert generic_exc.value.status_code == 502
    assert generic_exc.value.detail == "SMTP delivery failed"
