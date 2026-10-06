import json
import os
import shutil
import struct
import subprocess
import tarfile

import pytest
from test_gaia_pki import ROOT, openssl
from test_gaia_pki import authority as authority


def make(target, *, environ, succeeds=True, **variables):
    result = subprocess.run(
        ["make", target, *[f"{key}={value}" for key, value in variables.items()]],
        cwd=ROOT,
        env=environ,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert (result.returncode == 0) is succeeds, result.stdout + result.stderr
    return result


def fingerprint(authority):
    directory, environ = authority
    return (
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
        .replace(":", "")
    )


def test_real_windows_bundle_and_publication_contain_only_public_artifacts(authority):
    directory, environ = authority
    pin = fingerprint(authority)
    environ = {**environ, "MCP_CA_SHA256": pin, "MCP_CA_COMMON_NAME": "CBO GAIA Root CA"}
    bundle = directory / "client-bundle"
    make(
        "mcp-ca-bundle",
        environ=environ,
        GO_BIN=os.environ.get("GO_BIN", "go"),
        MCP_CA_CERT=directory / "gaia-root.crt",
        MCP_CA_BUNDLE=bundle,
    )
    for architecture, machine in [("amd64", 0x8664), ("arm64", 0xAA64)]:
        executable = (bundle / f"CBO-CA-GAIA-Windows-{architecture}.exe").read_bytes()
        assert executable[:2] == b"MZ"
        offset = struct.unpack_from("<I", executable, 0x3C)[0]
        assert executable[offset : offset + 4] == b"PE\x00\x00"
        assert struct.unpack_from("<H", executable, offset + 4)[0] == machine
        assert (directory / "gaia-root.crt").read_bytes() in executable
    guide = (bundle / "GUIDA-CLIENT.txt").read_text()
    assert pin in guide and "@CA_" not in guide
    assert "sudo bash installa-ca-linux.sh" in guide
    assert "sudo bash Installa-CA-macOS.command" in guide
    with tarfile.open(str(bundle) + ".tar.gz") as archive:
        assert len(archive.getmembers()) == len(list(bundle.iterdir())) + 1
        assert not any(
            member.name.endswith((".key", ".key.pem")) for member in archive.getmembers()
        )
        assert all(member.isfile() or member.isdir() for member in archive.getmembers())
    public = directory / "public"
    make(
        "mcp-ca-login-assets", environ=environ, MCP_CA_BUNDLE=bundle, MCP_CA_PUBLIC_DIRECTORY=public
    )
    assert json.loads((public / "manifest.json").read_text()) == {"sha256": pin}
    artifacts = public / pin
    assert {path.name for path in artifacts.iterdir()} == {
        "CBO-CA-GAIA-Windows-amd64.exe",
        "CBO-CA-GAIA-Windows-arm64.exe",
        "GUIDA-CLIENT.txt",
        "CBO-GAIA-Root-CA.crt",
        "SHA256SUMS",
        "GAIA-CA-client.tar.gz",
    }
    verified = subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS"], cwd=artifacts, text=True, capture_output=True, timeout=20
    )
    assert verified.returncode == 0, verified.stderr
    before = (public / "manifest.json").read_bytes()
    make(
        "mcp-ca-login-assets",
        environ=environ,
        succeeds=False,
        MCP_CA_BUNDLE=bundle,
        MCP_CA_PUBLIC_DIRECTORY=public,
    )
    assert (public / "manifest.json").read_bytes() == before


@pytest.mark.parametrize("reason", ["missing-package", "wrong-ca", "noncanonical-pin"])
def test_incomplete_or_unapproved_bundle_never_publishes_login_manifest(authority, reason):
    directory, environ = authority
    pin = fingerprint(authority)
    if reason == "wrong-ca":
        pin = "0" * 64
    elif reason == "noncanonical-pin":
        pin = ":".join(pin[offset : offset + 2] for offset in range(0, len(pin), 2))
    bundle = directory / "incomplete"
    bundle.mkdir()
    shutil.copyfile(directory / "gaia-root.crt", bundle / "CBO-GAIA-Root-CA.crt")
    public = directory / "public"
    make(
        "mcp-ca-login-assets",
        environ={**environ, "MCP_CA_SHA256": pin, "MCP_CA_COMMON_NAME": "CBO GAIA Root CA"},
        succeeds=False,
        MCP_CA_BUNDLE=bundle,
        MCP_CA_PUBLIC_DIRECTORY=public,
    )
    assert not public.exists()
