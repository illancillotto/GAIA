"""Bounded PEC/DSN parsing, independent from persistence and correlation."""

import os
import ssl
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path

from .policy import MAX_BYTES, sha256


@dataclass(frozen=True)
class ParsedReceipt:
    kind: str = "unclassified"
    correlated_id: str | None = None
    recipient: str | None = None
    occurred_at: datetime | None = None
    verified: bool = False


def verified_pec_content(raw):
    """Only configured PEC trust anchors AND approved signer pins authorize classification."""
    bundle = os.environ.get("COMMUNICATIONS_PEC_CA_BUNDLE")
    pins = os.environ.get("COMMUNICATIONS_PEC_SIGNER_SHA256", "").lower().split(",")
    if not bundle or not any(pins):
        return None
    with tempfile.TemporaryDirectory(prefix="gaia-pec-") as folder:
        signer = Path(folder) / "signer.pem"
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "smime",
                    "-verify",
                    "-CAfile",
                    bundle,
                    "-purpose",
                    "smimesign",
                    "-signer",
                    str(signer),
                ],
                input=raw,
                capture_output=True,
                timeout=20,
                check=False,
            )
            if result.returncode or not signer.is_file():
                return None
            certificate = ssl.PEM_cert_to_DER_cert(signer.read_text())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None
        return result.stdout if sha256(certificate) in pins else None


def parse(raw, channel, *, verifier=verified_pec_content):
    if len(raw) > MAX_BYTES:
        return ParsedReceipt()
    if channel == "pec":
        signed = verifier(raw)
        if signed is None:
            return ParsedReceipt(kind="unverified_pec")
        message = BytesParser(policy=policy.default).parsebytes(signed)
        xmls = [
            part.get_payload(decode=True)
            for part in message.walk()
            if (part.get_filename() or "").lower() == "daticert.xml"
        ]
        if len(xmls) != 1:
            return ParsedReceipt()
        return _pec_xml(xmls[0] or b"")
    return _dsn(BytesParser(policy=policy.default).parsebytes(raw))


def _pec_xml(raw):
    if len(raw) > 256 * 1024 or b"<!" in raw:
        return ParsedReceipt()
    try:
        root = ET.fromstring(raw)
        values = {node.tag.rsplit("}", 1)[-1]: node for node in root.iter()}
        identifier = _text(values, "msgid")
        recipient = _text(values, "destinatari").strip().lower()
        kind = {
            "accettazione": "accepted",
            "avvenuta-consegna": "delivered",
            "errore-consegna": "not_delivered",
            "mancata-consegna": "not_delivered",
            "non-accettazione": "not_delivered",
        }.get(root.attrib.get("tipo"), "provider_notice")
        day, time = _text(values, "giorno"), _text(values, "ora")
        zone = values["data"].attrib["zona"]
        occurred = datetime.strptime(f"{day} {time} {zone}", "%d/%m/%Y %H:%M:%S %z")
        if not identifier or not recipient or len(identifier) > 200:
            return ParsedReceipt()
        return ParsedReceipt(kind, identifier, recipient, occurred, True)
    except (ET.ParseError, ValueError, KeyError):
        return ParsedReceipt()


def _text(values, key):
    return (values[key].text or "").strip()


def _dsn(message):
    identifier = str(message.get("In-Reply-To") or "").strip()
    for part in message.walk():
        if part.get_content_type() != "message/delivery-status":
            continue
        blocks = part.get_payload()
        if not isinstance(blocks, list):
            continue
        result = _recipient_report(blocks, identifier)
        if result is not None:
            return result
    return ParsedReceipt()


def _recipient_report(blocks, fallback_id):
    if not blocks:
        return None
    identifier = str(blocks[0].get("Original-Message-ID") or fallback_id).strip()
    for block in blocks[1:]:
        recipient = str(block.get("Final-Recipient") or "").partition(";")[2].strip().lower()
        kind = {
            "failed": "not_delivered",
            "delivered": "dsn_delivered",
            "delayed": "dsn_delayed",
        }.get(str(block.get("Action") or "").lower(), "provider_notice")
        if identifier and recipient and len(identifier) <= 200:
            return ParsedReceipt(kind, identifier, recipient)
    return None
