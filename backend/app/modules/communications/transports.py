"""TLS-only SMTP/IMAP adapters. Called exclusively by the isolated worker."""

import contextlib
import imaplib
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime, formataddr
from pathlib import Path

from .policy import MAX_BYTES, Conflict, now


class SafeFailure(Exception):
    def __init__(self, code, *, retryable=False):
        super().__init__(code)
        self.code, self.retryable = code, retryable


class Uncertain(Exception):
    """DATA may have reached the peer; reconcile, never resubmit automatically."""


def read_secret(reference):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", reference):
        raise SafeFailure("secret_reference_invalid")
    root = Path(os.environ.get("COMMUNICATIONS_SECRETS_DIR", "/run/secrets"))
    path = root / reference
    try:
        if path.is_symlink() or path.stat().st_size > 16384:
            raise SafeFailure("secret_unavailable")
        secret = path.read_text().rstrip("\r\n")
    except OSError as exc:
        raise SafeFailure("secret_unavailable") from exc
    if not secret or "\r" in secret or "\n" in secret:
        raise SafeFailure("secret_invalid")
    return secret


def mime_message(message, account, attachments, technical_id):
    result = EmailMessage(policy=SMTP)
    result["From"] = formataddr((account.display_name, message.sender))
    result["To"] = message.recipient
    result["Subject"] = message.subject
    result["Date"] = format_datetime(now())
    result["Message-ID"] = technical_id
    result["X-GAIA-Communication-ID"] = str(message.id)
    result.set_content(message.body, subtype="plain", charset="utf-8")
    for attachment in attachments:
        result.add_attachment(
            attachment.content, maintype="application", subtype="pdf", filename=attachment.filename
        )
    content = result.as_bytes()
    if len(content) > account.max_bytes:
        raise Conflict("MIME oltre il limite dell'account")
    return content


def _oauth(username, secret):
    return f"user={username}\x01auth=Bearer {secret}\x01\x01"


class SMTPAdapter:
    def connect(self, account):
        context = ssl.create_default_context()
        if account.smtp_encryption == "tls":
            client = smtplib.SMTP_SSL(
                account.smtp_host, account.smtp_port, timeout=20, context=context
            )
        else:
            client = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=20)
            try:
                client.ehlo()
                client.starttls(context=context)
            except Exception:
                client.close()
                raise
        try:
            client.ehlo()
            secret = read_secret(account.secret_ref)
            if account.auth_method == "oauth2":
                client.auth("XOAUTH2", lambda challenge=None: _oauth(account.username, secret))
            else:
                client.login(account.username, secret)
        except Exception:
            client.close()
            raise
        return client

    def test(self, account):
        client = self.connect(account)
        client.close()

    def send(self, account, recipient, content):
        client = None
        in_data = False
        try:
            client = self.connect(account)
            code, _ = client.mail(account.sender)
            _smtp_response(code, "sender")
            code, _ = client.rcpt(recipient)
            _smtp_response(code, "recipient")
            in_data = True
            code, _ = client.data(content)
            _smtp_response(code, "data")
        except SafeFailure:
            raise
        except smtplib.SMTPDataError as exc:
            raise SafeFailure("smtp_data_rejected", retryable=400 <= exc.smtp_code < 500) from exc
        except (OSError, smtplib.SMTPException) as exc:
            if in_data:
                raise Uncertain("smtp_outcome_unknown") from exc
            raise SafeFailure("smtp_connection_failed", retryable=True) from exc
        finally:
            if client:
                with contextlib.suppress(Exception):
                    client.close()


def _smtp_response(code, stage):
    if not 200 <= code < 300:
        raise SafeFailure(f"smtp_{stage}_rejected", retryable=400 <= code < 500)


class IMAPAdapter:
    def connect(self, account):
        context = ssl.create_default_context()
        if account.imap_encryption == "tls":
            client = imaplib.IMAP4_SSL(
                account.imap_host, account.imap_port, ssl_context=context, timeout=20
            )
        else:
            client = imaplib.IMAP4(account.imap_host, account.imap_port, timeout=20)
            try:
                client.starttls(ssl_context=context)
            except Exception:
                client.shutdown()
                raise
        try:
            secret = read_secret(account.secret_ref)
            if account.auth_method == "oauth2":
                client.authenticate(
                    "XOAUTH2", lambda challenge: _oauth(account.username, secret).encode()
                )
            else:
                client.login(account.username, secret)
        except Exception:
            client.shutdown()
            raise
        return client

    def test(self, account):
        client = self.connect(account)
        client.logout()

    def fetch(self, account, validity, last_uid):
        client = self.connect(account)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise SafeFailure("imap_inbox_unavailable", retryable=True)
            _, values = client.response("UIDVALIDITY")
            current_validity = values[0].decode() if values and values[0] else ""
            if not current_validity.isdigit():
                raise SafeFailure("imap_uidvalidity_missing")
            start = last_uid + 1 if current_validity == validity else 1
            status, identifiers = client.uid("search", None, f"UID {start}:*")
            if status != "OK":
                raise SafeFailure("imap_search_failed", retryable=True)
            uids = sorted(int(value) for value in identifiers[0].split() if int(value) >= start)[
                :50
            ]
            for uid in uids:
                yield current_validity, uid, self._read(client, uid)
        finally:
            with contextlib.suppress(Exception):
                client.logout()

    def _read(self, client, uid):
        status, sizes = client.uid("fetch", str(uid), "(RFC822.SIZE)")
        match = re.search(rb"RFC822.SIZE (\d+)", sizes[0] or b"") if status == "OK" else None
        if not match or int(match.group(1)) > MAX_BYTES:
            raise SafeFailure("imap_message_size_invalid")
        status, parts = client.uid("fetch", str(uid), "(BODY.PEEK[])")
        if status != "OK":
            raise SafeFailure("imap_fetch_failed", retryable=True)
        raw = next((part[1] for part in parts if isinstance(part, tuple)), b"")
        if not raw or len(raw) > MAX_BYTES:
            raise SafeFailure("imap_message_size_invalid")
        return raw
