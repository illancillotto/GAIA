"""Versioned email blocks: no executable HTML or remote image sources."""

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from .policy import Conflict
from .policy import render_template as render_plain

PREFIX = "GAIA-BLOCKS/1\n"
KINDS = {"logo", "title", "paragraph", "list", "link", "button"}
LOGO = Path(__file__).resolve().parents[1] / "ruolo/assets/notice-cbo-logo.png"
LOGO_CID = "gaia-official-logo"


def valid_url(value):
    """Allow absolute HTTPS destinations, without credentials or control characters."""
    try:
        parsed = urlsplit(value)
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not re.search(r"[\s<>\"\\\x00-\x1f\x7f]", value)
        )
    except ValueError:
        return False


def decode(body):
    blocks = json.loads(body[len(PREFIX) :])
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 60:
        raise ValueError("Inserire da 1 a 60 blocchi")
    for block in blocks:
        validate_block(block)
    return blocks


def validate_body(body):
    if body.startswith(PREFIX):
        decode(body)
    return body


def validate_block(block):
    if not isinstance(block, dict) or not isinstance(block.get("kind"), str):
        raise ValueError("Tipo di blocco non valido")
    if block["kind"] not in KINDS:
        raise ValueError("Tipo di blocco non valido")
    kind = block["kind"]
    fields = {"kind"} if kind == "logo" else {"kind", "text"}
    if kind in {"link", "button"}:
        fields.add("url")
        validate_destination(block.get("url"))
    if set(block) != fields:
        raise ValueError("Campi del blocco non validi")
    if kind != "logo" and (not isinstance(block["text"], str) or not block["text"].strip()):
        raise ValueError("Compilare il testo di ogni blocco")


def validate_destination(url):
    if not isinstance(url, str) or not valid_url(url):
        raise ValueError("Il link deve essere un URL HTTPS completo")
    # Destinations remain fixed even when taxpayer data contains URL syntax.
    if "{{" in url:
        raise ValueError("Le variabili sono ammesse nel testo, non nell'URL")


def substitute(body, replace):
    blocks = decode(body)
    for block in blocks:
        if "text" in block:
            block["text"] = replace(block["text"])
    return PREFIX + json.dumps(blocks, ensure_ascii=False)


def render_template(body, variables):
    """Render each text field separately, preserving JSON even for quoted taxpayer names."""
    if not body.startswith(PREFIX):
        return render_plain(body, variables)
    try:
        return substitute(body, lambda text: render_plain(text, variables))
    except ValueError as exc:
        raise Conflict(str(exc)) from exc


def block_content(block):
    kind = block["kind"]
    if kind == "logo":
        return (
            "Consorzio di Bonifica dell'Oristanese",
            f'<p><img src="cid:{LOGO_CID}" width="180" '
            'alt="Logo Consorzio di Bonifica dell&#39;Oristanese"></p>',
        )
    text = block["text"]
    safe = escape(text).replace("\n", "<br>")
    if kind in {"link", "button"}:
        url = block["url"]
        style = "color:#245537"
        if kind == "button":
            style = "display:inline-block;background:#245537;color:#fff;padding:12px 20px;border-radius:6px"
        return (
            f"{text}: {url}",
            f'<p><a href="{escape(url, quote=True)}" style="{style}">{safe}</a></p>',
        )
    if kind == "list":
        items = "".join(f"<li>{escape(line)}</li>" for line in text.splitlines())
        return "\n".join(f"• {line}" for line in text.splitlines()), f"<ul>{items}</ul>"
    tag = "h2" if kind == "title" else "p"
    return text, f"<{tag}>{safe}</{tag}>"


def email_content(body):
    if not body.startswith(PREFIX):
        return body, None, False
    blocks = decode(body)
    parts = [block_content(block) for block in blocks]
    html = (
        '<!doctype html><html lang="it"><head><meta charset="utf-8"></head>'
        '<body><div style="max-width:640px;margin:auto;font-family:Arial,sans-serif;'
        'font-size:16px;line-height:1.6;color:#1e293b">'
        + "".join(part[1] for part in parts)
        + "</div></body></html>"
    )
    return "\n\n".join(part[0] for part in parts), html, any(b["kind"] == "logo" for b in blocks)


def set_message_content(message, body):
    """Build MIME alternatives and attach the official image to the HTML part only."""
    plain, html, logo = email_content(body)
    message.set_content(plain, subtype="plain", charset="utf-8")
    if html is not None:
        message.add_alternative(html, subtype="html", charset="utf-8")
        if logo:
            message.get_payload()[-1].add_related(
                LOGO.read_bytes(),
                maintype="image",
                subtype="png",
                cid=f"<{LOGO_CID}>",
                disposition="inline",
            )
