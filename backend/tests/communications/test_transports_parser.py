import imaplib
import smtplib
import ssl
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.modules.communications import policy, receipt_parser, transports

from .conftest import account_input, pdf
from .test_worker_receipts import pec_raw


def account(**overrides):
    return SimpleNamespace(**(account_input().model_dump() | overrides))


def test_pdf_limits_corrupt_encrypted_empty_and_multipage():
    assert policy.pdf_pages(pdf()) == 3
    for raw in (
        b"not pdf",
        b"%PDF-not-valid",
        pdf(0),
        pdf(201),
        b"%PDF-" + b"x" * policy.MAX_BYTES,
    ):
        with pytest.raises(policy.Conflict):
            policy.pdf_pages(raw)
    from io import BytesIO

    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("synthetic")
    writer.write(output)
    with pytest.raises(policy.Conflict):
        policy.pdf_pages(output.getvalue())


@pytest.mark.parametrize(
    "field,value",
    [
        ("sender", "bad-address"),
        ("smtp_host", "https://smtp.invalid"),
        ("username", "bad\nuser"),
        ("display_name", "bad\rname"),
        ("secret_ref", "../secret"),
    ],
)
def test_account_schema_rejects_headers_and_invalid_configuration(field, value):
    with pytest.raises(ValidationError):
        account_input(**{field: value})


def test_secret_store_only_uses_external_files(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMUNICATIONS_SECRETS_DIR", str(tmp_path))
    secret = tmp_path / "synthetic"
    secret.write_text("synthetic-password\n")
    assert transports.read_secret("synthetic") == "synthetic-password"
    for value in ("../bad", "missing"):
        with pytest.raises(transports.SafeFailure):
            transports.read_secret(value)
    secret.write_text("")
    with pytest.raises(transports.SafeFailure):
        transports.read_secret("synthetic")
    secret.write_text("a\nb")
    with pytest.raises(transports.SafeFailure):
        transports.read_secret("synthetic")
    secret.write_text("x" * 16385)
    with pytest.raises(transports.SafeFailure):
        transports.read_secret("synthetic")
    (tmp_path / "linked").symlink_to(secret)
    with pytest.raises(transports.SafeFailure):
        transports.read_secret("linked")


@pytest.mark.parametrize("encryption,auth", [("tls", "password"), ("starttls", "oauth2")])
def test_smtp_tls_auth_and_success_without_test_message(monkeypatch, encryption, auth):
    client = MagicMock()
    for command in ("mail", "rcpt", "data"):
        getattr(client, command).return_value = (250, b"OK")
    monkeypatch.setattr(transports.smtplib, "SMTP_SSL", lambda *a, **k: client)
    monkeypatch.setattr(transports.smtplib, "SMTP", lambda *a, **k: client)
    monkeypatch.setattr(transports, "read_secret", lambda reference: "synthetic-token")
    adapter = transports.SMTPAdapter()
    value = account(smtp_encryption=encryption, auth_method=auth)
    adapter.test(value)
    client.mail.assert_not_called()
    adapter.send(value, "recipient@example.org", b"raw mime")
    client.data.assert_called_once_with(b"raw mime")
    if auth == "oauth2":
        assert "auth=Bearer synthetic-token" in client.auth.call_args.args[1]()
        assert client.starttls.call_args.kwargs["context"].verify_mode == ssl.CERT_REQUIRED
    else:
        client.login.assert_called_with("synthetic", "synthetic-token")


@pytest.mark.parametrize(
    "stage,error,expected",
    [
        ("connect", TimeoutError(), transports.SafeFailure),
        (
            "login",
            smtplib.SMTPAuthenticationError(535, b"secret must not leak"),
            transports.SafeFailure,
        ),
        ("mail", TimeoutError(), transports.SafeFailure),
        ("rcpt", smtplib.SMTPServerDisconnected(), transports.SafeFailure),
        ("data", TimeoutError(), transports.Uncertain),
        ("data", smtplib.SMTPServerDisconnected(), transports.Uncertain),
        ("data", smtplib.SMTPDataError(451, b"explicit rejection"), transports.SafeFailure),
    ],
)
def test_smtp_failure_boundary(monkeypatch, stage, error, expected):
    client = MagicMock()
    for name in ("mail", "rcpt", "data"):
        getattr(client, name).return_value = (250, b"OK")
    if stage == "connect":
        monkeypatch.setattr(transports.smtplib, "SMTP_SSL", MagicMock(side_effect=error))
    else:
        getattr(client, stage).side_effect = error
        monkeypatch.setattr(transports.smtplib, "SMTP_SSL", lambda *a, **k: client)
    monkeypatch.setattr(transports, "read_secret", lambda reference: "synthetic")
    with pytest.raises(expected) as caught:
        transports.SMTPAdapter().send(account(), "r@example.org", b"mime")
    assert "secret must not leak" not in str(caught.value)


@pytest.mark.parametrize("stage,code", [("mail", 550), ("rcpt", 450), ("data", 554)])
def test_explicit_smtp_negative_responses_are_known(monkeypatch, stage, code):
    client = MagicMock()
    for command in ("mail", "rcpt", "data"):
        getattr(client, command).return_value = (code if command == stage else 250, b"result")
    monkeypatch.setattr(transports.SMTPAdapter, "connect", lambda self, value: client)
    with pytest.raises(transports.SafeFailure) as error:
        transports.SMTPAdapter().send(account(), "r@example.org", b"mime")
    assert error.value.retryable == (400 <= code < 500)


def test_starttls_failure_closes_connection(monkeypatch):
    client = MagicMock()
    client.starttls.side_effect = ssl.SSLError("synthetic")
    monkeypatch.setattr(transports.smtplib, "SMTP", lambda *a, **k: client)
    with pytest.raises(ssl.SSLError):
        transports.SMTPAdapter().connect(account(smtp_encryption="starttls"))
    client.close.assert_called_once()


@pytest.mark.parametrize("encryption,auth", [("tls", "password"), ("starttls", "oauth2")])
def test_imap_tls_readonly_and_peek_uidvalidity(monkeypatch, encryption, auth):
    client = MagicMock()
    client.select.return_value = ("OK", [])
    client.response.return_value = ("UIDVALIDITY", [b"42"])
    raw = b"Message-ID: <receipt@synthetic>\r\n\r\nreceipt"

    def uid(command, *args):
        if command == "search":
            return "OK", [b"1 2"]
        if args[-1] == "(RFC822.SIZE)":
            return "OK", [b"1 (RFC822.SIZE 44)"]
        return "OK", [(b"1", raw), b")"]

    client.uid.side_effect = uid
    monkeypatch.setattr(transports.imaplib, "IMAP4_SSL", lambda *a, **k: client)
    monkeypatch.setattr(transports.imaplib, "IMAP4", lambda *a, **k: client)
    monkeypatch.setattr(transports, "read_secret", lambda reference: "synthetic")
    adapter = transports.IMAPAdapter()
    value = account(imap_encryption=encryption, auth_method=auth)
    adapter.test(value)
    assert list(adapter.fetch(value, "42", 1)) == [("42", 2, raw)]
    assert len(list(adapter.fetch(value, "different", 100))) == 2
    client.select.assert_called_with("INBOX", readonly=True)
    assert not client.store.called and not client.expunge.called
    if auth == "oauth2":
        assert b"Bearer synthetic" in client.authenticate.call_args.args[1](None)


@pytest.mark.parametrize("stage", ["starttls", "login"])
def test_imap_connection_failure_closes(monkeypatch, stage):
    error_type = imaplib.IMAP4.error
    client = MagicMock()
    getattr(client, stage).side_effect = imaplib.IMAP4.error("synthetic")
    monkeypatch.setattr(transports.imaplib, "IMAP4", lambda *a, **k: client)
    monkeypatch.setattr(transports, "read_secret", lambda reference: "synthetic")
    with pytest.raises(error_type):
        transports.IMAPAdapter().connect(account(imap_encryption="starttls"))
    client.shutdown.assert_called_once()


@pytest.mark.parametrize(
    "stage,result",
    [
        ("select", ("NO", [])),
        ("response", ("UIDVALIDITY", [None])),
        ("response", ("UIDVALIDITY", [])),
        ("uid", ("NO", [])),
    ],
)
def test_imap_mailbox_failures_preserve_mailbox(monkeypatch, stage, result):
    client = MagicMock()
    client.select.return_value = ("OK", [])
    client.response.return_value = ("UIDVALIDITY", [b"42"])
    getattr(client, stage).return_value = result
    monkeypatch.setattr(transports.IMAPAdapter, "connect", lambda self, value: client)
    with pytest.raises(transports.SafeFailure):
        list(transports.IMAPAdapter().fetch(account(), None, 0))
    client.logout.assert_called_once()


@pytest.mark.parametrize(
    "responses",
    [
        [("NO", [])],
        [("OK", [b"bad size"])],
        [("OK", [b"RFC822.SIZE 33554433"])],
        [("OK", [b"RFC822.SIZE 4"]), ("NO", [])],
        [("OK", [b"RFC822.SIZE 4"]), ("OK", [b")"])],
        [("OK", [b"RFC822.SIZE 4"]), ("OK", [(b"x", b"a" * 33554433)])],
    ],
)
def test_imap_size_and_payload_bounds(responses):
    client = MagicMock()
    client.uid.side_effect = responses
    with pytest.raises(transports.SafeFailure):
        transports.IMAPAdapter()._read(client, 1)


def test_signed_pec_verifies_real_synthetic_cms(tmp_path, monkeypatch):
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=Synthetic PEC",
            "-addext",
            "extendedKeyUsage=emailProtection",
        ],
        check=True,
        capture_output=True,
    )
    raw = pec_raw()
    signed = subprocess.run(
        [
            "openssl",
            "smime",
            "-sign",
            "-signer",
            str(cert),
            "-inkey",
            str(key),
            "-outform",
            "SMIME",
        ],
        input=raw,
        check=True,
        capture_output=True,
    ).stdout
    monkeypatch.setenv("COMMUNICATIONS_PEC_CA_BUNDLE", str(cert))
    monkeypatch.setenv(
        "COMMUNICATIONS_PEC_SIGNER_SHA256",
        policy.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())),
    )
    assert receipt_parser.parse(signed, "pec").kind == "delivered"
    monkeypatch.setenv("COMMUNICATIONS_PEC_SIGNER_SHA256", "0" * 64)
    assert receipt_parser.parse(signed, "pec").kind == "unverified_pec"
    assert receipt_parser.verified_pec_content(b"not signed") is None


@pytest.mark.parametrize("case", ["timeout", "oserror", "badcert", "no_signer"])
def test_cms_errors_fail_closed(tmp_path, monkeypatch, case):
    monkeypatch.setenv("COMMUNICATIONS_PEC_CA_BUNDLE", str(tmp_path / "ca.pem"))
    monkeypatch.setenv("COMMUNICATIONS_PEC_SIGNER_SHA256", "a" * 64)

    def execute(args, **kwargs):
        if case == "timeout":
            raise subprocess.TimeoutExpired("openssl", 20)
        if case == "oserror":
            raise OSError()
        if case == "badcert":
            Path(args[-1]).write_text("bad certificate")
        return SimpleNamespace(returncode=0, stdout=b"verified")

    monkeypatch.setattr(receipt_parser.subprocess, "run", execute)
    assert receipt_parser.verified_pec_content(b"raw") is None


@pytest.mark.parametrize(
    "raw",
    [
        b"<!DOCTYPE x>",
        b"<broken",
        b"<x/>",
        b"x" * 262145,
        b'<postacert><data zona="bad"/><giorno>bad</giorno><ora>bad</ora><msgid>x</msgid><destinatari>x</destinatari></postacert>',
    ],
)
def test_bad_pec_xml_has_no_delivery_effect(raw):
    assert receipt_parser._pec_xml(raw).kind == "unclassified"


def test_unclassified_pec_and_dsn_branches():
    assert receipt_parser.parse(b"x" * (policy.MAX_BYTES + 1), "pec").kind == "unclassified"
    assert receipt_parser.parse(b"no XML", "pec", verifier=lambda raw: raw).kind == "unclassified"
    assert (
        receipt_parser.parse(pec_raw("avviso-gestore"), "pec", verifier=lambda raw: raw).kind
        == "provider_notice"
    )
    assert (
        receipt_parser.parse(pec_raw(identifier=""), "pec", verifier=lambda raw: raw).kind
        == "unclassified"
    )
    assert (
        receipt_parser.parse(pec_raw(identifier="x" * 201), "pec", verifier=lambda raw: raw).kind
        == "unclassified"
    )
    assert receipt_parser.parse(b"no report", "email").kind == "unclassified"
    part = MagicMock()
    part.get_content_type.return_value = "message/delivery-status"
    part.get_payload.return_value = "invalid list"
    assert (
        receipt_parser._dsn(SimpleNamespace(walk=lambda: [part], get=lambda key: None)).kind
        == "unclassified"
    )
    part.get_payload.return_value = [{}, {"Action": "delayed"}]
    assert (
        receipt_parser._dsn(SimpleNamespace(walk=lambda: [part], get=lambda key: None)).kind
        == "unclassified"
    )
