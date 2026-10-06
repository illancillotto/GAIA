import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/mcps/pki/gaia-ca.cnf"
TEST_PASSWORD = "synthetic-test-passphrase-not-for-production"


def openssl(*arguments, environ, succeeds=True):
    result = subprocess.run(
        ["openssl", *map(str, arguments)],
        env=environ,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert (result.returncode == 0) is succeeds, result.stderr
    return result


@pytest.fixture
def authority(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (tmp_path / "issued").mkdir(mode=0o700)
    (tmp_path / "index.txt").touch()
    (tmp_path / "serial").write_text("1000\n")
    (tmp_path / "crlnumber").write_text("1000\n")
    environ = {**os.environ, "GAIA_CA_DIR": str(tmp_path), "GAIA_TEST_CA_PASSWORD": TEST_PASSWORD}
    key = private / "gaia-root.key.pem"
    openssl(
        "genpkey",
        "-algorithm",
        "EC",
        "-pkeyopt",
        "ec_paramgen_curve:P-256",
        "-aes-256-cbc",
        "-pass",
        "env:GAIA_TEST_CA_PASSWORD",
        "-out",
        key,
        environ=environ,
    )
    openssl(
        "req",
        "-new",
        "-x509",
        "-config",
        CONFIG,
        "-key",
        key,
        "-passin",
        "env:GAIA_TEST_CA_PASSWORD",
        "-days",
        "3650",
        "-out",
        tmp_path / "gaia-root.crt",
        environ=environ,
    )
    return tmp_path, environ


def issue_server(authority, *, name="server", requested_san="gaia.lan"):
    directory, environ = authority
    key = directory / (name + ".key")
    request = directory / (name + ".csr")
    certificate = directory / (name + ".crt")
    openssl(
        "req",
        "-new",
        "-newkey",
        "ec",
        "-pkeyopt",
        "ec_paramgen_curve:P-256",
        "-noenc",
        "-keyout",
        key,
        "-out",
        request,
        "-subj",
        "/CN=gaia.lan",
        "-addext",
        "subjectAltName=DNS:" + requested_san,
        environ=environ,
    )
    openssl(
        "ca",
        "-batch",
        "-config",
        CONFIG,
        "-extensions",
        "gaia_server",
        "-notext",
        "-passin",
        "env:GAIA_TEST_CA_PASSWORD",
        "-in",
        request,
        "-out",
        certificate,
        environ=environ,
    )
    return key, certificate


def test_dedicated_root_is_encrypted_and_constrained(authority):
    directory, environ = authority
    key = directory / "private/gaia-root.key.pem"
    assert key.read_text().startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----")
    assert key.stat().st_mode & 0o777 == 0o600
    assert key.parent.stat().st_mode & 0o777 == 0o700
    openssl("pkey", "-in", key, "-passin", "pass:wrong", "-noout", environ=environ, succeeds=False)
    details = openssl(
        "x509", "-in", directory / "gaia-root.crt", "-noout", "-text", environ=environ
    ).stdout
    assert "CBO GAIA Root CA" in details
    assert "CA:TRUE, pathlen:0" in details
    assert "Certificate Sign, CRL Sign" in details
    openssl(
        "verify",
        "-CAfile",
        directory / "gaia-root.crt",
        directory / "gaia-root.crt",
        environ=environ,
    )
    fingerprint = (
        openssl(
            "x509",
            "-in",
            directory / "gaia-root.crt",
            "-noout",
            "-fingerprint",
            "-sha256",
            environ=environ,
        )
        .stdout.strip()
        .split("=", 1)[1]
    )
    verified = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/tls/validate-ca.sh"),
            str(directory / "gaia-root.crt"),
            fingerprint,
            "CBO GAIA Root CA",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env=environ,
    )
    assert verified.returncode == 0, verified.stderr


def test_leaf_chain_hostname_usage_and_private_key_match(authority):
    directory, environ = authority
    key, certificate = issue_server(authority)
    openssl(
        "verify",
        "-CAfile",
        directory / "gaia-root.crt",
        "-purpose",
        "sslserver",
        "-verify_hostname",
        "gaia.lan",
        certificate,
        environ=environ,
    )
    openssl(
        "verify",
        "-CAfile",
        directory / "gaia-root.crt",
        "-verify_hostname",
        "other.lan",
        certificate,
        environ=environ,
        succeeds=False,
    )
    openssl(
        "verify",
        "-CAfile",
        directory / "gaia-root.crt",
        "-purpose",
        "sslclient",
        certificate,
        environ=environ,
        succeeds=False,
    )
    cert_public_key = openssl(
        "x509", "-in", certificate, "-pubkey", "-noout", environ=environ
    ).stdout
    key_public_key = openssl("pkey", "-in", key, "-pubout", environ=environ).stdout
    assert cert_public_key == key_public_key
    details = openssl("x509", "-in", certificate, "-noout", "-text", environ=environ).stdout
    assert "CA:FALSE" in details
    assert "DNS:gaia.lan" in details
    dates = openssl("x509", "-in", certificate, "-noout", "-dates", environ=environ).stdout
    not_before, not_after = [
        datetime.strptime(line.split("=", 1)[1], "%b %d %H:%M:%S %Y %Z")
        for line in dates.splitlines()
    ]
    assert (not_after - not_before).days == 90


def test_csr_cannot_add_unapproved_hostname_and_serials_are_unique(authority):
    directory, environ = authority
    _, first = issue_server(authority, requested_san="unapproved.lan")
    _, second = issue_server(authority, name="renewed")
    details = openssl("x509", "-in", first, "-noout", "-text", environ=environ).stdout
    assert "unapproved.lan" not in details
    assert "DNS:gaia.lan" in details
    serials = [
        openssl("x509", "-in", cert, "-noout", "-serial", environ=environ).stdout
        for cert in [first, second]
    ]
    assert serials[0] != serials[1]
    assert len((directory / "index.txt").read_text().splitlines()) == 2


def test_revoked_leaf_is_rejected_when_crl_is_checked(authority):
    directory, environ = authority
    _, certificate = issue_server(authority)
    openssl(
        "ca",
        "-config",
        CONFIG,
        "-passin",
        "env:GAIA_TEST_CA_PASSWORD",
        "-revoke",
        certificate,
        "-crl_reason",
        "keyCompromise",
        environ=environ,
    )
    crl = directory / "gaia-root.crl.pem"
    openssl(
        "ca",
        "-config",
        CONFIG,
        "-passin",
        "env:GAIA_TEST_CA_PASSWORD",
        "-gencrl",
        "-out",
        crl,
        environ=environ,
    )
    result = openssl(
        "verify",
        "-CAfile",
        directory / "gaia-root.crt",
        "-CRLfile",
        crl,
        "-crl_check",
        certificate,
        environ=environ,
        succeeds=False,
    )
    assert "certificate revoked" in result.stderr
